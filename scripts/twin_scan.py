#!/usr/bin/env python3
"""twin_scan.py: measure how a body of writing behaves. Writes patterns.json.

Reads .md and .txt files only. Runs offline. Standard library only.
Emails, phone numbers and money amounts are redacted when each file is
read, before anything is counted or written.

Usage:
  python3 scripts/twin_scan.py --corpus samples/ --out patterns.json
  python3 scripts/twin_scan.py --corpus blog=posts/ --corpus email=sent/ --out patterns.json

Each --corpus is PATH or NAME=PATH. With two or more, patterns.json also
holds a side-by-side comparison.
"""

import argparse
import collections
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import twinlib as tl  # noqa: E402

SCHEMA = "twin-patterns"
SCHEMA_VERSION = "1"

SHORT_MAX = 8      # sentences of 8 words or fewer are short
MEDIUM_MAX = 20    # 9 to 20 words is medium, 21+ is long
HIST_BUCKETS = [(1, 5), (6, 10), (11, 15), (16, 20), (21, 25), (26, 30), (31, 40), (41, None)]

# Per-file metrics used for drift, with the smallest spread that counts.
# The floor stops two near-identical files from producing a huge z-score.
DRIFT_METRICS = [
    ("avg_sentence_words", "Average sentence length (words)", 2.0),
    ("long_sentence_share", "Share of long sentences", 0.05),
    ("hedge_rate", "Sentences with a hedge", 0.03),
    ("question_rate", "Sentences that are questions", 0.03),
    ("exclamation_rate", "Sentences ending in !", 0.03),
    ("list_line_share", "Lines that are list items", 0.05),
    ("dash_per_1k", "Dashes per 1,000 words", 1.0),
]
DRIFT_Z = 2.0
DRIFT_MIN_WORDS = 40


def parse_corpus_arg(value):
    if "=" in value and not os.path.exists(value):
        name, path = value.split("=", 1)
    else:
        path = value
        name = os.path.basename(os.path.normpath(value)) or "corpus"
    return name.strip(), path.strip()


def compile_metaphors(families):
    out = {}
    for fam, entries in families.items():
        exact = set()
        prefixes = []
        for e in entries:
            if e.endswith("*"):
                prefixes.append(e[:-1])
            else:
                exact.add(e)
        out[fam] = (exact, tuple(prefixes))
    return out


def metaphor_counts(tokens, compiled):
    counts = {fam: 0 for fam in compiled}
    words_hit = {fam: collections.Counter() for fam in compiled}
    for t in tokens:
        for fam, (exact, prefixes) in compiled.items():
            if t in exact or (prefixes and t.startswith(prefixes)):
                counts[fam] += 1
                words_hit[fam][t] += 1
    return counts, words_hit


def formatting_counts(lines, text_words):
    nonblank = [ln for ln in lines if ln["kind"] not in ("blank", "code", "frontmatter")]
    raw_prose = "\n".join(ln["raw"] for ln in nonblank)
    k = max(text_words, 1) / 1000.0
    list_lines = sum(1 for ln in nonblank if ln["kind"] == "list")
    headings = sum(1 for ln in nonblank if ln["kind"] == "heading")
    bold = len(re.findall(r"\*\*[^*\n]+\*\*|__[^_\n]+__", raw_prose))
    em = raw_prose.count("\u2014") + len(re.findall(r"\s--\s", raw_prose))
    en = raw_prose.count("–")
    emoji = len(tl.emoji_regex().findall(raw_prose))
    caps = len(re.findall(r"\b[A-Z]{3,}\b", raw_prose))
    return {
        "nonblank_lines": len(nonblank),
        "list_lines": list_lines,
        "list_line_share": tl.rnd(list_lines / len(nonblank)) if nonblank else 0.0,
        "headings": headings,
        "bold": bold,
        "em_dashes": em,
        "en_dashes": en,
        "dash_per_1k": tl.rnd((em + en) / k, 2) if text_words else 0.0,
        "emoji": emoji,
        "all_caps_words": caps,
        "all_caps_per_1k": tl.rnd(caps / k, 2) if text_words else 0.0,
        "bold_per_1k": tl.rnd(bold / k, 2) if text_words else 0.0,
    }


# Hedges that change the verb or the grammar when deleted. For these the
# fix is advice, not a rewrite.
ADVICE_ONLY = {
    "might": 'Replace "might" with what will happen, or say what it depends on.',
    "i'm not sure": "Say what you know, then what you would check.",
    "seems like": 'Drop "seems like" and state the observation.',
    "it seems": 'Drop "it seems" and state the observation.',
}
_SEEMS_PREFIX = re.compile(r"^\s*it seems(?: like| that)?\s+", re.IGNORECASE)


def hedge_fix(sentence, rx, term):
    """Remove the hedge and tidy what is left. Deterministic.

    Returns (fix_text, rewritten). rewritten is False when the fix is advice.
    """
    if term in ("it seems", "seems like") and _SEEMS_PREFIX.match(sentence):
        out = _SEEMS_PREFIX.sub("", sentence, count=1)
        return out[0].upper() + out[1:], True
    if term in ADVICE_ONLY:
        return ADVICE_ONLY[term], False
    out = rx.sub("", sentence, count=1)
    out = re.sub(r"\s+,", ",", out)
    out = re.sub(r"^\s*,\s*", "", out)
    out = re.sub(r"\s{2,}", " ", out).strip()
    out = re.sub(r"^(that|,)\s+", "", out, flags=re.IGNORECASE)
    if out and out[0].islower():
        out = out[0].upper() + out[1:]
    return out, True


def split_point(sentence):
    """Where to split a long sentence: the joint nearest the middle."""
    n = len(sentence)
    best = None
    for m in re.finditer(r";\s|,\s(?:and|but|so|which|because)\s|\s(?:and|but|because|which)\s", sentence):
        dist = abs(m.start() - n // 2)
        if best is None or dist < best[0]:
            best = (dist, m)
    return best[1] if best else None


def scan_corpus(name, root, lex, metaphors, min_repeat, max_flags, long_words, hide_names):
    files = tl.list_text_files(root)
    if not files:
        raise SystemExit("twin_scan: no .md or .txt files under %s" % root)
    root_abs = os.path.abspath(root)
    hedge_rx = [(h, tl.phrase_regex(h)) for h in lex["hedges"]]
    edge_stop = set(lex["edge_stopwords"])
    compiled_meta = compile_metaphors(metaphors)

    redactions = {}
    all_sentences = []
    file_rows = []
    ngram_counts = collections.Counter()
    ngram_files = collections.defaultdict(set)
    ngram_first = {}
    hedge_terms = collections.Counter()
    meta_total = {fam: 0 for fam in compiled_meta}
    meta_words = {fam: collections.Counter() for fam in compiled_meta}
    fmt_total = collections.Counter()
    flags = []

    for idx, path in enumerate(files, 1):
        if hide_names:
            label = "file-%02d%s" % (idx, os.path.splitext(path)[1])
        elif os.path.isfile(root_abs):
            label = os.path.basename(path)
        else:
            label = os.path.relpath(path, root_abs).replace(os.sep, "/")
        text = tl.redact(tl.read_text(path), redactions)
        lines = tl.classify_lines(text)
        sents = tl.split_sentences(lines)
        tokens = [w.lower() for s in sents for w in tl.words(s["text"])]
        n_words = len(tokens)

        hedged = 0
        questions = 0
        exclaims = 0
        long_count = 0
        for s in sents:
            s["file"] = label
            first = None
            for h, rx in hedge_rx:
                m = rx.search(s["text"])
                if m:
                    hedge_terms[h] += len(rx.findall(s["text"]))
                    if first is None or (m.start(), -len(h)) < (first[2].start(), -len(first[0])):
                        first = (h, rx, m)
            if first is not None:
                hedged += 1
                h, rx, m = first
                fix, rewritten = hedge_fix(s["text"], rx, h)
                flags.append({
                    "file": label, "line": s["line"], "kind": "hedge",
                    "match": m.group(0),
                    "snippet": tl.snippet(s["text"], m.start(), m.end()),
                    "fix": tl.snippet(fix) if rewritten else fix,
                    "fix_is_rewrite": rewritten,
                    "why": 'Hedge "%s". Say it or cut it.' % h,
                })
            questions += s["end"] == "?"
            exclaims += s["end"] == "!"
            if s["words"] > long_words:
                long_count += 1
                sp = split_point(s["text"])
                if sp is not None:
                    left = len(tl.words(s["text"][: sp.start()]))
                    fix = 'Split near word %d, at "%s".' % (left, sp.group(0).strip(" ,;") or ";")
                else:
                    fix = "Split into two sentences, or cut a clause."
                flags.append({
                    "file": label, "line": s["line"], "kind": "long_sentence",
                    "match": "%d words" % s["words"],
                    "snippet": tl.snippet(s["text"]),
                    "fix": fix,
                    "fix_is_rewrite": False,
                    "why": "%d words. Your long threshold is %d." % (s["words"], long_words),
                })
            toks = [w.lower() for w in tl.words(s["text"])]
            for n in (3, 4, 5):
                for i in range(len(toks) - n + 1):
                    gram = toks[i:i + n]
                    if gram[0] in edge_stop or gram[-1] in edge_stop:
                        continue
                    if any(t.startswith("redacted") for t in gram):
                        continue
                    key = " ".join(gram)
                    ngram_counts[key] += 1
                    ngram_files[key].add(label)
                    if key not in ngram_first:
                        ngram_first[key] = (label, s["line"])
        for ln in lines:
            if ln["kind"] in ("code", "frontmatter", "blank"):
                continue
            for m in re.finditer("\u2014|\\s--\\s", ln["raw"]):
                flags.append({
                    "file": label, "line": ln["no"], "kind": "dash",
                    "match": "dash",
                    "snippet": tl.snippet(ln["clean"] or ln["raw"]),
                    "fix": tl.snippet(re.sub(r"\s*(\u2014|--)\s*", ", ", ln["clean"] or ln["raw"])),
                    "fix_is_rewrite": True,
                    "why": "Dash. Use a comma, colon or full stop.",
                })
                break

        mc, mw = metaphor_counts(tokens, compiled_meta)
        for fam in mc:
            meta_total[fam] += mc[fam]
            meta_words[fam].update(mw[fam])
        fmt = formatting_counts(lines, n_words)
        for key in ("nonblank_lines", "list_lines", "headings", "bold", "em_dashes",
                    "en_dashes", "emoji", "all_caps_words"):
            fmt_total[key] += fmt[key]
        lens = [s["words"] for s in sents]
        ns = len(sents)
        file_rows.append({
            "file": label,
            "words": n_words,
            "sentences": ns,
            "avg_sentence_words": tl.rnd(tl.mean(lens), 2) if lens else 0.0,
            "long_sentence_share": tl.rnd(long_count / ns) if ns else 0.0,
            "hedge_rate": tl.rnd(hedged / ns) if ns else 0.0,
            "question_rate": tl.rnd(questions / ns) if ns else 0.0,
            "exclamation_rate": tl.rnd(exclaims / ns) if ns else 0.0,
            "list_line_share": fmt["list_line_share"],
            "dash_per_1k": fmt["dash_per_1k"],
            "metaphor_words": mc,
        })
        all_sentences.extend(sents)

    # ---- repeated phrases (crutch phrases)
    kept = {k: c for k, c in ngram_counts.items() if c >= min_repeat}
    # Drop a phrase when a longer kept phrase contains it with the same count.
    longer = sorted(kept, key=lambda k: -len(k.split()))
    drop = set()
    for k in kept:
        for other in longer:
            if len(other.split()) <= len(k.split()):
                break
            if kept[other] == kept[k] and (" %s " % k) in (" %s " % other):
                drop.add(k)
                break
    # A phrase longer than 5 words shows up as a chain of overlapping
    # windows with the same count. Keep the first window of each chain:
    # drop any phrase whose opening words are the closing words of
    # another kept phrase with the same count.
    grams = {tuple(k.split()): c for k, c in kept.items() if k not in drop}
    for h, c in sorted(grams.items()):
        for g, gc in grams.items():
            if g == h or gc != c or " ".join(g) in drop:
                continue
            if any(g[-s:] == h[:s] for s in range(2, min(len(g), len(h)))):
                drop.add(" ".join(h))
                break
    crutch = []
    for k in sorted((k for k in kept if k not in drop), key=lambda k: (-kept[k], -len(k.split()), k)):
        f, line = ngram_first[k]
        crutch.append({
            "phrase": k, "count": kept[k], "words": len(k.split()),
            "files": len(ngram_files[k]), "first_seen": {"file": f, "line": line},
        })
    crutch = crutch[:30]

    # ---- sentence lengths
    lens = [s["words"] for s in all_sentences]
    ns = len(all_sentences)
    hist = []
    for lo, hi in HIST_BUCKETS:
        c = sum(1 for x in lens if x >= lo and (hi is None or x <= hi))
        hist.append({"label": "%d-%d" % (lo, hi) if hi else "%d+" % lo, "count": c})
    short = sum(1 for x in lens if x <= SHORT_MAX)
    medium = sum(1 for x in lens if SHORT_MAX < x <= MEDIUM_MAX)
    long_ = ns - short - medium
    total_words = sum(r["words"] for r in file_rows)

    hedged_sent = sum(1 for s in all_sentences if any(rx.search(s["text"]) for _, rx in hedge_rx))
    questions = sum(1 for s in all_sentences if s["end"] == "?")
    exclaims = sum(1 for s in all_sentences if s["end"] == "!")

    # ---- drift
    drift = compute_drift(file_rows)

    # ---- flags: stable order, capped
    order = {"hedge": 0, "long_sentence": 1, "dash": 2}
    flags.sort(key=lambda f: (order[f["kind"]], f["file"], f["line"]))
    flagged_keys = {(f["file"], f["line"]) for f in flags}
    flag_counts = collections.Counter(f["kind"] for f in flags)

    # ---- score
    clean = 1 - (len(flagged_keys) / ns) if ns else None
    clean = max(0.0, clean) if clean is not None else None
    parts = {"clean_lines": tl.rnd(clean)}
    if drift["eligible_files"] >= 3:
        parts["consistency"] = tl.rnd(1 - drift["flagged_pairs"] / drift["total_pairs"])
    else:
        parts["consistency"] = None
    available = [v for v in parts.values() if v is not None]
    score = int(round(100 * sum(available) / len(available))) if available else None

    k = max(total_words, 1) / 1000.0
    nonblank = fmt_total["nonblank_lines"]
    return {
        "name": name,
        "files": file_rows,
        "totals": {
            "files": len(file_rows),
            "words": total_words,
            "sentences": ns,
            "unique_words": len({w.lower() for s in all_sentences for w in tl.words(s["text"])}),
        },
        "sentence_length": {
            "mean": tl.rnd(tl.mean(lens), 2) if lens else None,
            "median": tl.percentile(lens, 50),
            "p90": tl.percentile(lens, 90),
            "max": max(lens) if lens else None,
            "stdev": tl.rnd(tl.pstdev(lens), 2),
            "short_share": tl.rnd(short / ns) if ns else None,
            "medium_share": tl.rnd(medium / ns) if ns else None,
            "long_share": tl.rnd(long_ / ns) if ns else None,
            "histogram": hist,
            "bands": {"short_max": SHORT_MAX, "medium_max": MEDIUM_MAX},
        },
        "hedges": {
            "rate": tl.rnd(hedged_sent / ns) if ns else None,
            "sentences": hedged_sent,
            "terms": [{"term": t, "count": c} for t, c in sorted(hedge_terms.items(), key=lambda x: (-x[1], x[0]))],
        },
        "questions": {"rate": tl.rnd(questions / ns) if ns else None, "count": questions},
        "exclamations": {"rate": tl.rnd(exclaims / ns) if ns else None, "count": exclaims},
        "crutch_phrases": crutch,
        "metaphor_families": [
            {
                "family": fam,
                "count": meta_total[fam],
                "per_1k": tl.rnd(meta_total[fam] / k, 2),
                "top_words": [w for w, _ in sorted(meta_words[fam].items(), key=lambda x: (-x[1], x[0]))[:5]],
            }
            for fam in sorted(meta_total, key=lambda f: (-meta_total[f], f))
        ],
        "formatting": {
            "list_line_share": tl.rnd(fmt_total["list_lines"] / nonblank) if nonblank else 0.0,
            "headings": fmt_total["headings"],
            "bold_per_1k": tl.rnd(fmt_total["bold"] / k, 2),
            "dash_per_1k": tl.rnd((fmt_total["em_dashes"] + fmt_total["en_dashes"]) / k, 2),
            "emoji": fmt_total["emoji"],
            "all_caps_per_1k": tl.rnd(fmt_total["all_caps_words"] / k, 2),
        },
        "drift": drift,
        "flags": {
            "counts": {kind: flag_counts.get(kind, 0) for kind in ("hedge", "long_sentence", "dash")},
            "flagged_sentences": len(flagged_keys),
            "items": flags[:max_flags],
            "truncated": max(0, len(flags) - max_flags),
        },
        "score": {
            "value": score,
            "parts": parts,
            "formula": "score = 100 x mean(available parts). clean_lines = 1 - flagged lines / sentences. "
                       "consistency = 1 - drifting (file, metric) pairs / all pairs; needs 3+ files of "
                       "%d+ words." % DRIFT_MIN_WORDS,
        },
        "redactions": {k: redactions.get(k, 0) for k in ("email", "phone", "amount")},
    }


def compute_drift(rows):
    """Leave-one-out z-scores: each file against the rest of its corpus."""
    eligible = [r for r in rows if r["words"] >= DRIFT_MIN_WORDS]
    out_files = []
    flagged_pairs = 0
    total_pairs = 0
    if len(eligible) >= 3:
        for r in eligible:
            others = [o for o in eligible if o is not r]
            metrics = []
            for key, label, floor in DRIFT_METRICS:
                vals = [o[key] for o in others]
                mu = tl.mean(vals)
                sd = max(tl.pstdev(vals), floor)
                z = (r[key] - mu) / sd
                flagged = abs(z) >= DRIFT_Z
                total_pairs += 1
                flagged_pairs += flagged
                metrics.append({
                    "metric": key, "label": label, "value": r[key],
                    "others_mean": tl.rnd(mu, 3), "z": tl.rnd(z, 2), "drift": flagged,
                })
            worst = max(metrics, key=lambda m: (abs(m["z"]), m["metric"]))
            out_files.append({"file": r["file"], "max_abs_z": tl.rnd(abs(worst["z"]), 2),
                              "drifting": [m["metric"] for m in metrics if m["drift"]],
                              "metrics": metrics})
        out_files.sort(key=lambda f: (-f["max_abs_z"], f["file"]))
    return {
        "method": "Each file is compared with the mean of the other files. z = (file - others) / "
                  "max(spread of others, floor). |z| >= %.1f counts as drift." % DRIFT_Z,
        "threshold_z": DRIFT_Z,
        "eligible_files": len(eligible),
        "flagged_pairs": flagged_pairs,
        "total_pairs": total_pairs,
        "metrics": [{"metric": k, "label": l, "floor": f} for k, l, f in DRIFT_METRICS],
        "files": out_files,
    }


def compare(corpora):
    keys = [
        ("words", lambda c: c["totals"]["words"]),
        ("avg_sentence_words", lambda c: c["sentence_length"]["mean"]),
        ("long_share", lambda c: c["sentence_length"]["long_share"]),
        ("hedge_rate", lambda c: c["hedges"]["rate"]),
        ("question_rate", lambda c: c["questions"]["rate"]),
        ("exclamation_rate", lambda c: c["exclamations"]["rate"]),
        ("dash_per_1k", lambda c: c["formatting"]["dash_per_1k"]),
        ("list_line_share", lambda c: c["formatting"]["list_line_share"]),
        ("score", lambda c: c["score"]["value"]),
    ]
    table = [{"metric": k, "values": {c["name"]: f(c) for c in corpora}} for k, f in keys]
    phrase_sets = {c["name"]: {p["phrase"] for p in c["crutch_phrases"]} for c in corpora}
    shared = sorted(set.intersection(*phrase_sets.values())) if phrase_sets else []
    only = {n: sorted(s - set.union(*(o for m, o in phrase_sets.items() if m != n)))
            for n, s in phrase_sets.items()}
    return {"corpora": [c["name"] for c in corpora], "table": table,
            "shared_phrases": shared, "only_in": only}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", action="append", required=True, metavar="[NAME=]PATH",
                    help="folder or file of .md/.txt writing; repeat to compare")
    ap.add_argument("--out", default="patterns.json")
    ap.add_argument("--metaphors", help="JSON word list of metaphor families")
    ap.add_argument("--lexicon", help="JSON hedge and stopword lists")
    ap.add_argument("--min-repeat", type=int, default=3, help="minimum count for a repeated phrase")
    ap.add_argument("--long-words", type=int, default=30, help="flag sentences longer than this")
    ap.add_argument("--max-flags", type=int, default=60, help="flagged lines kept per corpus")
    ap.add_argument("--hide-filenames", action="store_true", help="write file-01.md, file-02.md ...")
    args = ap.parse_args(argv)

    lex = tl.load_lexicon(args.lexicon)
    metaphors = tl.load_metaphors(args.metaphors)
    seen = set()
    corpora = []
    for raw in args.corpus:
        name, path = parse_corpus_arg(raw)
        if not os.path.exists(path):
            ap.error("corpus path not found: %s" % path)
        if name in seen:
            ap.error("two corpora named %r; use NAME=PATH" % name)
        seen.add(name)
        corpora.append(scan_corpus(name, path, lex, metaphors, args.min_repeat,
                                   args.max_flags, args.long_words, args.hide_filenames))
    data = {
        "schema": SCHEMA,
        "version": SCHEMA_VERSION,
        "tool": "twin_scan.py",
        "settings": {
            "min_repeat": args.min_repeat,
            "long_words": args.long_words,
            "metaphors": os.path.basename(args.metaphors) if args.metaphors else "default",
            "lexicon": os.path.basename(args.lexicon) if args.lexicon else "default",
            "redaction": "on",
        },
        "corpora": corpora,
        "comparison": compare(corpora) if len(corpora) > 1 else None,
    }
    tl.write_json(args.out, data)
    for c in corpora:
        t = c["totals"]
        print("%-12s %3d files  %6d words  %5d sentences  score %s" % (
            c["name"], t["files"], t["words"], t["sentences"],
            c["score"]["value"] if c["score"]["value"] is not None else "n/a"))
        if c["crutch_phrases"]:
            top = c["crutch_phrases"][0]
            print("%-12s top repeat: \"%s\" x%d" % ("", top["phrase"], top["count"]))
        red = c["redactions"]
        if any(red.values()):
            print("%-12s redacted: %d email, %d phone, %d amount" % ("", red["email"], red["phone"], red["amount"]))
    print("wrote %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
