#!/usr/bin/env python3
"""twin_check.py: check a draft against a twin's rules. Pass or fail per rule.

Runs offline. Standard library only.

Usage:
  python3 scripts/twin_check.py --rules twins/example/twin.rules.json draft.md
  python3 scripts/twin_check.py --rules twin.rules.json drafts/ --format json
  python3 scripts/twin_check.py --rules twin.rules.json --export-foundrkit foundrkit.config.json

Exit codes:
  0  every error rule passed (warnings allowed unless --strict)
  1  an error rule failed, or any rule with --strict
  2  setup problem: bad rules file, missing draft, unknown option

Rule types (see docs/RULES.md):
  banned_phrase       {"phrases": ["i think", ...]}
  banned_pattern      {"pattern": "/regex/flags"}
  max_sentence_words  {"max": 28}
  max_rate            {"metric": "hedge" | "question" | "exclamation", "max": 0.05}
  no_emoji            {}
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import twinlib as tl  # noqa: E402

CONTRACT = "twin-rules"
VERSION = "1"
RULE_TYPES = ("banned_phrase", "banned_pattern", "max_sentence_words", "max_rate", "no_emoji")
RATE_METRICS = ("hedge", "question", "exclamation")
SEVERITIES = ("error", "warn")
SOURCES = ("extraction", "scan", "diff", "manual")


class RulesError(Exception):
    pass


def load_rules(path):
    try:
        raw = tl.load_json(path)
    except (OSError, ValueError) as exc:
        raise RulesError("cannot read %s: %s" % (path, exc))
    problems = validate_rules(raw)
    if problems:
        raise RulesError("%s is not a valid twin-rules file:\n  - %s" % (path, "\n  - ".join(problems)))
    return raw


def validate_rules(raw):
    p = []
    if not isinstance(raw, dict):
        return ["the file is not a JSON object"]
    if raw.get("contract") != CONTRACT:
        p.append('"contract" must be "%s"' % CONTRACT)
    if raw.get("version") != VERSION:
        p.append('"version" must be the string "%s"' % VERSION)
    if not isinstance(raw.get("brand"), str) or not raw.get("brand"):
        p.append('"brand" must be a non-empty string')
    pv = raw.get("profile_version")
    if not isinstance(pv, str) or not re.match(r"^\d+\.\d+\.\d+$", pv):
        p.append('"profile_version" must look like 1.0.0')
    rules = raw.get("rules")
    if not isinstance(rules, list) or not rules:
        p.append('"rules" must be a non-empty array')
        return p
    seen = set()
    for i, r in enumerate(rules, 1):
        at = "rule #%d" % i
        if not isinstance(r, dict):
            p.append("%s must be an object" % at)
            continue
        rid = r.get("id")
        if not isinstance(rid, str) or not re.match(r"^[a-z0-9][a-z0-9-]*$", rid):
            p.append('%s: "id" must be lowercase letters, digits and dashes' % at)
        elif rid in seen:
            p.append('%s: duplicate id "%s"' % (at, rid))
        else:
            seen.add(rid)
            at = 'rule "%s"' % rid
        t = r.get("type")
        if t not in RULE_TYPES:
            p.append('%s: "type" must be one of %s' % (at, ", ".join(RULE_TYPES)))
            continue
        if r.get("severity") not in SEVERITIES:
            p.append('%s: "severity" must be "error" or "warn"' % at)
        if "source" in r and r["source"] not in SOURCES:
            p.append('%s: "source" must be one of %s' % (at, ", ".join(SOURCES)))
        if "suggestion" in r and not isinstance(r["suggestion"], str):
            p.append('%s: "suggestion" must be a string' % at)
        if t == "banned_phrase":
            ph = r.get("phrases")
            if not isinstance(ph, list) or not ph or not all(isinstance(x, str) and x.strip() for x in ph):
                p.append('%s: "phrases" must be a non-empty array of strings' % at)
        elif t == "banned_pattern":
            try:
                tl.literal_regex(r.get("pattern") or "")
            except (ValueError, re.error) as exc:
                p.append("%s: %s" % (at, exc))
        elif t == "max_sentence_words":
            if not isinstance(r.get("max"), int) or r["max"] < 1:
                p.append('%s: "max" must be a positive integer' % at)
        elif t == "max_rate":
            if r.get("metric") not in RATE_METRICS:
                p.append('%s: "metric" must be one of %s' % (at, ", ".join(RATE_METRICS)))
            m = r.get("max")
            if not isinstance(m, (int, float)) or isinstance(m, bool) or not 0 <= m <= 1:
                p.append('%s: "max" must be a number from 0 to 1' % at)
    return p


# ---------------------------------------------------------------- checking


def _prose_lines(lines):
    return [ln for ln in lines if ln["kind"] not in ("code", "frontmatter", "blank")]


def check_file(path, label, rules, lexicon):
    text = tl.read_text(path)
    lines = tl.classify_lines(text)
    prose = _prose_lines(lines)
    sents = tl.split_sentences(lines)
    results = []
    for r in rules:
        t = r["type"]
        hits = []
        measured = None
        if t in ("banned_phrase", "banned_pattern", "no_emoji"):
            if t == "banned_phrase":
                regexes = [(ph, tl.phrase_regex(ph)) for ph in r["phrases"]]
            elif t == "banned_pattern":
                regexes = [(r["pattern"], tl.literal_regex(r["pattern"]))]
            else:
                regexes = [("emoji", tl.emoji_regex())]
            for ln in prose:
                for name, rx in regexes:
                    for m in rx.finditer(ln["raw"]):
                        hits.append({"file": label, "line": ln["no"], "column": m.start() + 1,
                                     "match": m.group(0),
                                     "snippet": _centred(ln["raw"], m, rx)})
        elif t == "max_sentence_words":
            for s in sents:
                if s["words"] > r["max"]:
                    hits.append({"file": label, "line": s["line"], "column": None,
                                 "match": "%d words" % s["words"],
                                 "snippet": tl.snippet(tl.redact(s["text"]))})
        elif t == "max_rate":
            n = len(sents)
            if r["metric"] == "hedge":
                rx = [tl.phrase_regex(h) for h in lexicon["hedges"]]
                flagged = [s for s in sents if tl.sentence_has_any(s["text"], rx)]
            elif r["metric"] == "question":
                flagged = [s for s in sents if s["end"] == "?"]
            else:
                flagged = [s for s in sents if s["end"] == "!"]
            measured = round(len(flagged) / n, 3) if n else 0.0
            if measured > r["max"]:
                for s in flagged:
                    hits.append({"file": label, "line": s["line"], "column": None,
                                 "match": r["metric"], "snippet": tl.snippet(tl.redact(s["text"]))})
        hits.sort(key=lambda h: (h["line"], h["column"] or 0))
        results.append({"file": label, "rule": r, "hits": hits, "measured": measured})
    return results


def _centred(raw, match, rx):
    """Redact the line first, then centre the excerpt on the match."""
    red = tl.redact(raw)
    if red == raw:
        return tl.snippet(raw, match.start(), match.end())
    m = rx.search(red)
    if m is None:
        return tl.snippet(red)
    return tl.snippet(red, m.start(), m.end())


def summarise(rules, per_file):
    """Merge per-file results into one verdict per rule."""
    out = []
    for r in rules:
        hits = []
        measured = {}
        for results in per_file:
            for res in results:
                if res["rule"]["id"] == r["id"]:
                    hits.extend(res["hits"])
                    if res["measured"] is not None:
                        measured[res["file"]] = res["measured"]
        out.append({
            "id": r["id"], "type": r["type"], "severity": r["severity"],
            "passed": not hits, "hits": hits,
            "measured": measured or None,
            "limit": r.get("max"),
            "suggestion": r.get("suggestion", ""),
        })
    return out


def collect_drafts(paths):
    files = []
    for p in paths:
        if not os.path.exists(p):
            raise RulesError("draft not found: %s" % p)
        if os.path.isdir(p):
            base = os.path.abspath(p)
            for f in tl.list_text_files(p):
                files.append((f, os.path.relpath(f, os.path.dirname(base)).replace(os.sep, "/")))
        else:
            files.append((p, p.replace(os.sep, "/")))
    if not files:
        raise RulesError("no .md or .txt drafts found")
    return files


# ---------------------------------------------------------------- foundrkit export

# foundrkit-lint compiles patterns with JavaScript RegExp. These Python-only
# constructs would fail there or mean something else, so they are not exported.
_NOT_PORTABLE = (r"(?P", r"\A", r"\Z", "(?i", "(?m", "(?s", "(?x", r"(?#")


def foundrkit_export(rules_doc):
    """Return (config dict, skipped list) for foundrkit.config.json.

    The plain JSON config shape is {"forbidden": [{pattern, severity,
    suggestion, category}]}. It is not the foundrkit-rules v1 contract:
    that contract's "source" field does not allow a twin as a source.
    See docs/FOUNDRKIT.md.
    """
    forbidden = []
    skipped = []
    seen = set()
    for r in rules_doc["rules"]:
        t = r["type"]
        if t == "banned_phrase":
            for ph in r["phrases"]:
                key = ph.lower()
                if key in seen:
                    continue
                seen.add(key)
                if ph.startswith("/"):
                    skipped.append((r["id"], ph, "starts with / and would be read as a regex"))
                    continue
                forbidden.append(_fk(ph, r))
        elif t == "banned_pattern":
            pat = r["pattern"]
            bad = [c for c in _NOT_PORTABLE if c in pat]
            if bad:
                skipped.append((r["id"], pat, "uses %s, which JavaScript reads differently" % bad[0]))
            elif pat.lower() not in seen:
                seen.add(pat.lower())
                forbidden.append(_fk(pat, r))
        elif t == "no_emoji":
            skipped.append((r["id"], "", "emoji ranges differ between Python and JavaScript; "
                            "add foundrkit's own emoji rule instead"))
        else:
            skipped.append((r["id"], "", "foundrkit-lint matches phrases only; %s is a measurement" % t))
    return {"forbidden": forbidden}, skipped


def _fk(pattern, rule):
    item = {"pattern": pattern, "severity": rule["severity"]}
    if rule.get("suggestion"):
        item["suggestion"] = rule["suggestion"]
    item["category"] = rule["id"]
    return item


# ---------------------------------------------------------------- output


def render_text(rules_path, doc, summary, files, strict):
    out = []
    out.append("twin_check  %s  (%s, profile %s)" % (rules_path, doc["brand"], doc["profile_version"]))
    out.append("drafts      %s" % ", ".join(label for _, label in files))
    out.append("")
    width = max(len(s["id"]) for s in summary)
    for s in summary:
        verdict = "PASS" if s["passed"] else "FAIL"
        extra = ""
        if s["type"] == "max_rate" and s["measured"]:
            over = sorted((f, v) for f, v in s["measured"].items() if v > s["limit"])
            if over:
                extra = "  max %s, over in %d of %d: %s" % (
                    s["limit"], len(over), len(s["measured"]),
                    ", ".join("%s=%.3f" % kv for kv in over[:5]))
            else:
                extra = "  max %s, highest %.3f" % (s["limit"], max(s["measured"].values()))
        elif not s["passed"]:
            extra = "  %d hit%s" % (len(s["hits"]), "" if len(s["hits"]) == 1 else "s")
        out.append("%s  %-*s  %-5s%s" % (verdict, width, s["id"], s["severity"], extra))
        for h in s["hits"][:20]:
            loc = "%s:%d" % (h["file"], h["line"]) + (":%d" % h["column"] if h["column"] else "")
            out.append("      %s  %s" % (loc, h["snippet"]))
        if len(s["hits"]) > 20:
            out.append("      ... %d more" % (len(s["hits"]) - 20))
        if not s["passed"] and s["suggestion"]:
            out.append("      fix: %s" % s["suggestion"])
    errors = sum(1 for s in summary if not s["passed"] and s["severity"] == "error")
    warns = sum(1 for s in summary if not s["passed"] and s["severity"] == "warn")
    failed = errors or (strict and warns)
    out.append("")
    out.append("result      %s  (%d error rule%s failed, %d warning rule%s failed%s)" % (
        "FAIL" if failed else "PASS", errors, "" if errors == 1 else "s",
        warns, "" if warns == 1 else "s", ", strict" if strict else ""))
    return "\n".join(out), bool(failed)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rules", required=True, help="twin.rules.json")
    ap.add_argument("drafts", nargs="*", help="draft files or folders (.md, .txt)")
    ap.add_argument("--format", choices=("text", "json"), default="text")
    ap.add_argument("--strict", action="store_true", help="warnings also fail")
    ap.add_argument("--lexicon", help="JSON hedge list for max_rate hedge rules")
    ap.add_argument("--export-foundrkit", metavar="PATH",
                    help="write the banned phrases as a foundrkit-lint JSON config and exit")
    args = ap.parse_args(argv)

    try:
        doc = load_rules(args.rules)
    except RulesError as exc:
        print("twin_check: %s" % exc, file=sys.stderr)
        return 2

    if args.export_foundrkit:
        config, skipped = foundrkit_export(doc)
        if not config["forbidden"]:
            print("twin_check: no phrase rules to export", file=sys.stderr)
            return 2
        tl.write_json(args.export_foundrkit, config)
        print("wrote %s  (%d patterns)" % (args.export_foundrkit, len(config["forbidden"])))
        for rid, pat, why in skipped:
            print("skipped %s%s: %s" % (rid, " " + pat if pat else "", why))
        return 0

    if not args.drafts:
        print("twin_check: give at least one draft, or --export-foundrkit", file=sys.stderr)
        return 2
    try:
        files = collect_drafts(args.drafts)
        lexicon = tl.load_lexicon(args.lexicon)
    except (RulesError, OSError, ValueError) as exc:
        print("twin_check: %s" % exc, file=sys.stderr)
        return 2

    per_file = [check_file(path, label, doc["rules"], lexicon) for path, label in files]
    summary = summarise(doc["rules"], per_file)
    text, failed = render_text(args.rules, doc, summary, files, args.strict)
    if args.format == "json":
        print(json.dumps({
            "rules": args.rules, "brand": doc["brand"], "profile_version": doc["profile_version"],
            "drafts": [label for _, label in files], "strict": args.strict,
            "passed": not failed, "results": summary,
        }, indent=2, ensure_ascii=False))
    else:
        print(text)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
