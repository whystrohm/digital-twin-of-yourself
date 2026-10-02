#!/usr/bin/env python3
"""twin_diff.py: learn from your edits. Proposes rule changes; never applies them alone.

Runs offline. Standard library only.

Put pairs in one folder: NAME.draft.md and NAME.edited.md (or .txt).
The draft is what you or an AI wrote first. The edited file is what you sent.

Step 1, propose. Writes twin.proposals.md. Changes nothing else.
  python3 scripts/twin_diff.py propose PAIRS_DIR --rules twins/acme/twin.rules.json \\
      --out twins/acme/twin.proposals.md

Step 2, you read the proposals and tick "- [x] accept" on the ones you want.

Step 3, accept. Applies only the ticked proposals, bumps profile_version,
and appends an entry to TWIN_CHANGELOG.md.
  python3 scripts/twin_diff.py accept twins/acme/twin.proposals.md \\
      --rules twins/acme/twin.rules.json --changelog twins/acme/TWIN_CHANGELOG.md

accept refuses to run if the rules file changed after the proposals were
written, so a stale proposal cannot overwrite a newer decision.
"""

import argparse
import collections
import datetime
import difflib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import twinlib as tl  # noqa: E402
import twin_check  # noqa: E402

PAIR_RX = re.compile(r"^(?P<name>.+)\.(?P<side>draft|edited)\.(?P<ext>md|txt)$")
MATCH_RATIO = 0.5      # sentence alignment threshold
SHORTEN_SHARE = 0.6    # share of matched sentences that must get shorter


# ---------------------------------------------------------------- reading


def find_pairs(folder):
    sides = collections.defaultdict(dict)
    for name in sorted(os.listdir(folder)):
        m = PAIR_RX.match(name)
        if m:
            sides[m.group("name")][m.group("side")] = os.path.join(folder, name)
    pairs = [(tl.redact(n), s["draft"], s["edited"]) for n, s in sorted(sides.items()) if len(s) == 2]
    lonely = sorted(tl.redact(n) for n, s in sides.items() if len(s) != 2)
    return pairs, lonely


def doc(path):
    text = tl.redact(tl.read_text(path))
    sents = tl.split_sentences(tl.classify_lines(text))
    tokens = [[w.lower() for w in tl.words(s["text"])] for s in sents]
    return sents, tokens


def ngrams(sentence_tokens, n):
    """n-grams inside each sentence, never across a sentence boundary."""
    out = []
    for toks in sentence_tokens:
        out.extend(" ".join(toks[i:i + n]) for i in range(len(toks) - n + 1))
    return out


# ---------------------------------------------------------------- analysis


def deleted_phrases(pairs_docs, function_words, min_pairs):
    """Phrases removed in every pair whose draft used them."""
    stats = collections.defaultdict(lambda: {"pairs_seen": [], "pairs_removed": [], "draft_count": 0})
    for name, (dsents, dtok), (esents, etok) in pairs_docs:
        for n in (1, 2, 3):
            dc = collections.Counter(ngrams(dtok, n))
            ec = collections.Counter(ngrams(etok, n))
            for g, c in dc.items():
                toks = g.split()
                if all(t in function_words for t in toks):
                    continue
                if toks[0] in function_words and toks[-1] in function_words:
                    continue
                if any(t == tl.REDACTED_WORD or t.isdigit() for t in toks):
                    continue
                st = stats[g]
                st["pairs_seen"].append(name)
                st["draft_count"] += c
                if ec.get(g, 0) == 0:
                    st["pairs_removed"].append(name)
    always = {g: s for g, s in stats.items()
              if len(s["pairs_removed"]) >= min_pairs
              and len(s["pairs_removed"]) == len(s["pairs_seen"])
              and s["draft_count"] >= 2}
    # Keep the shortest form: drop a phrase that contains another kept phrase.
    keep = {}
    for g in sorted(always, key=lambda x: (len(x.split()), x)):
        if any((" %s " % k) in (" %s " % g) for k in keep):
            continue
        keep[g] = always[g]
    return keep


def sentence_shortening(pairs_docs):
    """Align draft and edited sentences; measure how length changed."""
    before = []
    after = []
    shorter = 0
    matched = 0
    edited_lengths = []
    for _name, (dsents, _), (esents, _) in pairs_docs:
        edited_lengths.extend(s["words"] for s in esents)
        dt = [[w.lower() for w in tl.words(s["text"])] for s in dsents]
        used = set()
        for s in esents:
            et = [w.lower() for w in tl.words(s["text"])]
            best = None
            for i, d in enumerate(dt):
                if i in used:
                    continue
                r = difflib.SequenceMatcher(None, d, et, autojunk=False).ratio()
                # An edit that splits one long sentence in two keeps most of
                # the edited words inside the draft sentence.
                cover = sum((collections.Counter(et) & collections.Counter(d)).values()) / max(len(et), 1)
                score = max(r, cover if len(et) < len(d) else 0)
                if score >= MATCH_RATIO and (best is None or score > best[0]):
                    best = (score, i)
            if best is None:
                continue
            i = best[1]
            used.add(i)
            matched += 1
            before.append(dsents[i]["words"])
            after.append(s["words"])
            shorter += s["words"] < dsents[i]["words"]
    return {"matched": matched, "shorter": shorter, "before": before, "after": after,
            "edited_lengths": edited_lengths}


def hedge_rates(pairs_docs, hedges):
    rx = [tl.phrase_regex(h) for h in hedges]
    rows = []
    for name, (dsents, _), (esents, _) in pairs_docs:
        d = sum(1 for s in dsents if tl.sentence_has_any(s["text"], rx)) / max(len(dsents), 1)
        e = sum(1 for s in esents if tl.sentence_has_any(s["text"], rx)) / max(len(esents), 1)
        rows.append((name, round(d, 3), round(e, 3)))
    return rows


# ---------------------------------------------------------------- proposals


def banned_now(rules_doc):
    out = set()
    for r in rules_doc["rules"]:
        if r["type"] == "banned_phrase":
            out.update(p.lower() for p in r["phrases"])
    return out


def rule_by_type(rules_doc, rtype, metric=None):
    for r in rules_doc["rules"]:
        if r["type"] == rtype and (metric is None or r.get("metric") == metric):
            return r
    return None


def build_proposals(pairs_docs, rules_doc, lex, min_pairs):
    props = []
    banned = banned_now(rules_doc)
    target = rule_by_type(rules_doc, "banned_phrase")
    target_id = "deleted-in-edits"
    for r in rules_doc["rules"]:
        if r["id"] == target_id:
            target = r
    for g, st in sorted(deleted_phrases(pairs_docs, set(lex["function_words"]), min_pairs).items(),
                        key=lambda kv: (-len(kv[1]["pairs_removed"]), -kv[1]["draft_count"], kv[0])):
        if g in banned:
            continue
        props.append({
            "title": 'Ban "%s"' % g,
            "evidence": 'Deleted in %d of %d pairs where the draft used it (%d uses). Pairs: %s.' % (
                len(st["pairs_removed"]), len(st["pairs_seen"]), st["draft_count"],
                ", ".join(st["pairs_removed"])),
            "op": {"op": "add_phrase", "rule_id": target_id, "phrase": g},
        })

    sh = sentence_shortening(pairs_docs)
    current = rule_by_type(rules_doc, "max_sentence_words")
    if sh["matched"] >= 3 and sh["shorter"] / sh["matched"] >= SHORTEN_SHARE:
        new_max = tl.percentile(sh["edited_lengths"], 95)
        if new_max and (current is None or new_max < current["max"]):
            props.append({
                "title": "Lower the sentence limit to %d words" % new_max,
                "evidence": "%d of %d matched sentences got shorter in your edits. Median %s words "
                            "before, %s after. 95%% of edited sentences are %d words or fewer.%s" % (
                                sh["shorter"], sh["matched"], tl.percentile(sh["before"], 50),
                                tl.percentile(sh["after"], 50), new_max,
                                " Current limit: %d." % current["max"] if current else ""),
                "op": {"op": "set_max", "rule_id": current["id"] if current else "sentence-length",
                       "max": int(new_max)},
            })

    rows = hedge_rates(pairs_docs, lex["hedges"])
    fell = [r for r in rows if r[2] < r[1]]
    current = rule_by_type(rules_doc, "max_rate", "hedge")
    if len(fell) >= min_pairs:
        new_max = max(r[2] for r in rows)
        if current is None or new_max < current["max"]:
            props.append({
                "title": "Lower the hedge rate limit to %.2f" % new_max,
                "evidence": "Hedged sentences fell in %d of %d pairs (%s). Highest rate after editing: %.3f.%s" % (
                    len(fell), len(rows),
                    "; ".join("%s %.2f to %.2f" % r for r in fell[:5]), new_max,
                    " Current limit: %.2f." % current["max"] if current else ""),
                "op": {"op": "set_rate", "rule_id": current["id"] if current else "hedge-rate",
                       "metric": "hedge", "max": new_max},
            })
    return props, sh


def render_proposals(props, rules_path, rules_doc, rules_sha, pairs_dir, n_pairs, lonely):
    out = ["# Twin proposals", ""]
    out.append("Rules file: `%s` (brand `%s`, profile %s)." % (
        rules_path, rules_doc["brand"], rules_doc["profile_version"]))
    out.append("Based on %d draft/edited pairs in `%s`." % (n_pairs, pairs_dir))
    out.append("")
    out.append("Nothing here has changed your rules. To accept a proposal, change its "
               "`- [ ] accept` line to `- [x] accept`, then run:")
    out.append("")
    out.append("    python3 scripts/twin_diff.py accept <this file> --rules %s --changelog <TWIN_CHANGELOG.md>" % rules_path)
    out.append("")
    if lonely:
        out.append("Skipped, no partner file: %s." % ", ".join(lonely))
        out.append("")
    if not props:
        out.append("No proposals. Your edits did not show a pattern strong enough to change a rule.")
    for i, p in enumerate(props, 1):
        out.append("## P%d. %s" % (i, p["title"]))
        out.append("")
        out.append("- [ ] accept")
        out.append("")
        out.append(p["evidence"])
        out.append("")
        out.append("```json")
        out.append(json.dumps(dict(p["op"], id="P%d" % i), sort_keys=True))
        out.append("```")
        out.append("")
    out.append("<!-- twin-proposals rules_sha256=%s -->" % rules_sha)
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- accepting

_SECTION = re.compile(r"^## (P\d+)\. (.+)$", re.M)


def parse_proposals(text):
    sha = re.search(r"<!-- twin-proposals rules_sha256=([0-9a-f]{64}) -->", text)
    if not sha:
        raise ValueError("this is not a twin_diff proposals file (no rules_sha256 marker)")
    items = []
    heads = list(_SECTION.finditer(text))
    for i, h in enumerate(heads):
        body = text[h.end(): heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        ticked = re.search(r"^- \[[xX]\] accept\s*$", body, re.M) is not None
        block = re.search(r"```json\n(.+?)\n```", body, re.S)
        if not block:
            raise ValueError("%s has no json block" % h.group(1))
        op = json.loads(block.group(1))
        if op.get("id") != h.group(1):
            raise ValueError("%s: json id %r does not match its heading" % (h.group(1), op.get("id")))
        items.append({"id": h.group(1), "title": h.group(2), "ticked": ticked, "op": op})
    return sha.group(1), items


def apply_op(rules_doc, op):
    rules = rules_doc["rules"]
    by_id = {r["id"]: r for r in rules}
    kind = op["op"]
    if kind == "add_phrase":
        r = by_id.get(op["rule_id"])
        if r is None:
            r = {"id": op["rule_id"], "type": "banned_phrase", "severity": "warn", "phrases": [],
                 "suggestion": "You delete this in your own edits.", "source": "diff"}
            rules.append(r)
        if r["type"] != "banned_phrase":
            raise ValueError("rule %s is not a banned_phrase rule" % r["id"])
        if op["phrase"].lower() not in (p.lower() for p in r["phrases"]):
            r["phrases"].append(op["phrase"])
        return 'added "%s" to %s' % (op["phrase"], r["id"])
    if kind == "set_max":
        r = by_id.get(op["rule_id"])
        if r is None:
            r = {"id": op["rule_id"], "type": "max_sentence_words", "severity": "warn",
                 "max": op["max"], "source": "diff"}
            rules.append(r)
            return "added %s with max %d" % (r["id"], op["max"])
        old = r["max"]
        r["max"] = op["max"]
        return "%s max %d -> %d" % (r["id"], old, op["max"])
    if kind == "set_rate":
        r = by_id.get(op["rule_id"])
        if r is None:
            r = {"id": op["rule_id"], "type": "max_rate", "severity": "warn",
                 "metric": op["metric"], "max": op["max"], "source": "diff"}
            rules.append(r)
            return "added %s with max %.3f" % (r["id"], op["max"])
        old = r["max"]
        r["max"] = op["max"]
        return "%s max %.3f -> %.3f" % (r["id"], old, op["max"])
    raise ValueError("unknown op %r" % kind)


def bump_minor(version):
    major, minor, _patch = (int(x) for x in version.split("."))
    return "%d.%d.0" % (major, minor + 1)


def cmd_accept(args):
    try:
        rules_doc = twin_check.load_rules(args.rules)
    except twin_check.RulesError as exc:
        print("twin_diff: %s" % exc, file=sys.stderr)
        return 2
    try:
        sha, items = parse_proposals(tl.read_text(args.proposals))
    except (OSError, ValueError) as exc:
        print("twin_diff: %s" % exc, file=sys.stderr)
        return 2
    if sha != tl.sha256_file(args.rules):
        print("twin_diff: %s changed after these proposals were written. "
              "Run propose again." % args.rules, file=sys.stderr)
        return 2
    chosen = [i for i in items if i["ticked"]]
    if not chosen:
        print("twin_diff: no proposal is ticked. Nothing changed.")
        return 0
    old_version = rules_doc["profile_version"]
    notes = []
    for item in chosen:
        try:
            notes.append((item, apply_op(rules_doc, item["op"])))
        except (KeyError, ValueError) as exc:
            print("twin_diff: %s: %s" % (item["id"], exc), file=sys.stderr)
            return 2
    rules_doc["profile_version"] = bump_minor(old_version)
    problems = twin_check.validate_rules(rules_doc)
    if problems:
        print("twin_diff: result would be invalid:\n  - %s" % "\n  - ".join(problems), file=sys.stderr)
        return 2
    tl.write_json(args.rules, rules_doc)

    date = args.date or datetime.date.today().isoformat()
    entry = ["## %s (%s)" % (rules_doc["profile_version"], date), ""]
    entry.append("Accepted from `%s`, written against profile %s." % (
        os.path.basename(args.proposals), old_version))
    entry.append("")
    for item, note in notes:
        entry.append("- %s %s: %s" % (item["id"], item["title"], note))
    skipped = [i for i in items if not i["ticked"]]
    if skipped:
        entry.append("")
        entry.append("Not accepted: %s." % ", ".join("%s %s" % (i["id"], i["title"]) for i in skipped))
    entry.append("")
    existing = tl.read_text(args.changelog) if os.path.exists(args.changelog) else ""
    if not existing.strip():
        existing = "# Twin changelog: %s\n\nEvery accepted rule change, newest first.\n\n" % rules_doc["brand"]
    head, sep, rest = existing.partition("\n## ")
    new = head.rstrip("\n") + "\n\n" + "\n".join(entry) + ("\n## " + rest if sep else "")
    with open(args.changelog, "w", encoding="utf-8") as fh:
        fh.write(new.rstrip("\n") + "\n")
    print("profile %s -> %s, %d change%s. Logged in %s." % (
        old_version, rules_doc["profile_version"], len(notes), "" if len(notes) == 1 else "s", args.changelog))
    return 0


def cmd_propose(args):
    try:
        rules_doc = twin_check.load_rules(args.rules)
    except twin_check.RulesError as exc:
        print("twin_diff: %s" % exc, file=sys.stderr)
        return 2
    if not os.path.isdir(args.pairs):
        print("twin_diff: not a folder: %s" % args.pairs, file=sys.stderr)
        return 2
    pairs, lonely = find_pairs(args.pairs)
    if not pairs:
        print("twin_diff: no NAME.draft.md + NAME.edited.md pairs in %s" % args.pairs, file=sys.stderr)
        return 2
    lex = tl.load_lexicon(args.lexicon)
    pairs_docs = [(n, doc(d), doc(e)) for n, d, e in pairs]
    props, _ = build_proposals(pairs_docs, rules_doc, lex, args.min_pairs)
    text = render_proposals(props, args.rules.replace(os.sep, "/"), rules_doc, tl.sha256_file(args.rules),
                            args.pairs.replace(os.sep, "/"), len(pairs), lonely)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("%d pair%s, %d proposal%s. Wrote %s. Nothing applied." % (
        len(pairs), "" if len(pairs) == 1 else "s", len(props), "" if len(props) == 1 else "s", args.out))
    for i, p in enumerate(props, 1):
        print("  P%d  %s" % (i, p["title"]))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("propose", help="read pairs, write proposals")
    p.add_argument("pairs", help="folder of NAME.draft.md / NAME.edited.md")
    p.add_argument("--rules", required=True)
    p.add_argument("--out", default="twin.proposals.md")
    p.add_argument("--min-pairs", type=int, default=2, help="pairs a pattern must show up in")
    p.add_argument("--lexicon")
    a = sub.add_parser("accept", help="apply ticked proposals and log them")
    a.add_argument("proposals")
    a.add_argument("--rules", required=True)
    a.add_argument("--changelog", required=True)
    a.add_argument("--date", help="date for the changelog entry, YYYY-MM-DD (default today)")
    args = ap.parse_args(argv)
    return cmd_propose(args) if args.cmd == "propose" else cmd_accept(args)


if __name__ == "__main__":
    sys.exit(main())
