#!/usr/bin/env python3
"""twin_eval.py: generic AI vs your Twin on the 15 stress tests, judged blind.

THIS SCRIPT CALLS A PAID API. It is the only file in this repository that
uses the network. Everything in scripts/ runs offline. Read validation/EVAL.md
and run --dry-run first: it prints the estimated token use and cost and
sends nothing.

For each stress test in validation/STRESS_TESTS.md:
  1. The generation model answers twice: once with no system prompt (generic),
     once with your twin.md as the system prompt (twin).
  2. A different judge model sees the two answers as A and B, in an order
     chosen by a seeded random number generator, plus real writing by the
     person (--samples). It picks which answer that person more likely wrote.
  3. Code maps A/B back to twin/generic, counts wins, and runs an exact
     two-sided sign test. With --rules, code also checks both answers against
     twin.rules.json offline.

Needs ANTHROPIC_API_KEY in the environment. Standard library only (urllib).

Usage:
  python3 validation/twin_eval.py --twin twins/acme/twin.md --samples held-out/ --dry-run
  python3 validation/twin_eval.py --twin twins/acme/twin.md --samples held-out/ \\
      --rules twins/acme/twin.rules.json --out validation/results/acme.json
"""

import argparse
import json
import math
import os
import random
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import twinlib as tl  # noqa: E402

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
DEFAULT_GEN = "claude-opus-5-5"
DEFAULT_JUDGE = "claude-sonnet-5-5"
# USD per million tokens (input, output), Anthropic first-party list prices
# as published 2026-09-25. Check current prices before relying on these.
PRICES = {
    "claude-fable-5-1": (10.0, 50.0),
    "claude-opus-5-5": (4.0, 20.0),
    "claude-opus-5": (5.0, 25.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-sonnet-5": (2.0, 10.0),
    "claude-haiku-4-5": (1.0, 5.0),
}
# Output budgets used by the estimate. Output includes thinking tokens.
EST_GEN_OUTPUT = 1500
EST_JUDGE_OUTPUT = 800
CHARS_PER_TOKEN = 4.0

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "winner": {"type": "string", "enum": ["A", "B", "tie"]},
        "confidence": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
        "reason": {"type": "string"},
    },
    "required": ["winner", "confidence", "reason"],
    "additionalProperties": False,
}

JUDGE_INSTRUCTIONS = """You are judging writing style, blind.

Below is REFERENCE writing by one person. Then a SCENARIO, and two
RESPONSES to it, labelled A and B. One response may have been written to
imitate that person; you do not know which, and the order is random.

Decide which response that person is more likely to have written, judging
by voice, word choice, sentence rhythm, how they reason and decide, and
what they would never say. Ignore which answer is more helpful or more
polite. If neither is distinguishable, answer "tie".

Reply with JSON: winner ("A", "B" or "tie"), confidence (1 to 5), and a
reason of at most two sentences that points to specific words or moves."""


def parse_stress_tests(path):
    text = tl.read_text(path)
    tests = []
    for m in re.finditer(r"^### (ST-\d+): (.+?)\n(.*?)(?=^### ST-|\Z)", text, re.S | re.M):
        body = m.group(3)
        p = re.search(r"\*\*Prompt:\*\*\s*\n((?:>.*\n?)+)", body)
        if not p:
            continue
        prompt = " ".join(ln.lstrip("> ").strip() for ln in p.group(1).splitlines()).strip()
        prompt = prompt.strip('"').strip("“”")
        tests.append({"id": m.group(1), "title": m.group(2).strip(), "prompt": prompt})
    return tests


def read_samples(folder, limit):
    parts = []
    used = 0
    for f in tl.list_text_files(folder):
        text = tl.redact(tl.read_text(f)).strip()
        if not text:
            continue
        room = limit - used
        if room <= 0:
            break
        piece = text[:room]
        parts.append("--- %s ---\n%s" % (tl.redact(os.path.basename(f)), piece))
        used += len(piece)
    return "\n\n".join(parts)


def judge_prompt(reference, scenario, a, b):
    return "%s\n\nREFERENCE\n%s\n\nSCENARIO\n%s\n\nRESPONSE A\n%s\n\nRESPONSE B\n%s" % (
        JUDGE_INSTRUCTIONS, reference, scenario, a, b)


def tokens(chars):
    return int(math.ceil(chars / CHARS_PER_TOKEN))


def estimate(tests, twin_text, reference, gen, judge, both_orders):
    gen_in = sum(tokens(len(t["prompt"])) * 2 + tokens(len(twin_text)) for t in tests)
    gen_out = EST_GEN_OUTPUT * 2 * len(tests)
    visible = 600  # a typical stress-test answer, in tokens
    per_judge_in = tokens(len(JUDGE_INSTRUCTIONS) + len(reference)) + 2 * visible + 60
    judge_calls = len(tests) * (2 if both_orders else 1)
    judge_in = sum(per_judge_in + tokens(len(t["prompt"])) for t in tests) * (2 if both_orders else 1)
    judge_out = EST_JUDGE_OUTPUT * judge_calls
    gp, jp = PRICES.get(gen), PRICES.get(judge)
    cost = None
    if gp and jp:
        cost = (gen_in * gp[0] + gen_out * gp[1] + judge_in * jp[0] + judge_out * jp[1]) / 1e6
    return {"tests": len(tests), "generation_calls": 2 * len(tests), "judge_calls": judge_calls,
            "generation_input_tokens": gen_in, "generation_output_tokens": gen_out,
            "judge_input_tokens": judge_in, "judge_output_tokens": judge_out,
            "estimated_usd": None if cost is None else round(cost, 2)}


def call(model, key, prompt, system=None, schema=None, effort="medium", retries=3):
    body = {"model": model, "max_tokens": 16000,
            "messages": [{"role": "user", "content": prompt}],
            "output_config": {"effort": effort}}
    if system:
        body["system"] = system
    if schema:
        body["output_config"]["format"] = {"type": "json_schema", "schema": schema}
    data = json.dumps(body).encode("utf-8")
    for attempt in range(retries + 1):
        req = urllib.request.Request(API_URL, data=data, method="POST", headers={
            "content-type": "application/json", "x-api-key": key, "anthropic-version": API_VERSION})
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                msg = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:300]
            if exc.code in (429, 500, 502, 503, 504, 529) and attempt < retries:
                time.sleep(2 ** attempt * 5)
                continue
            raise RuntimeError("HTTP %d from the API: %s" % (exc.code, detail))
        except urllib.error.URLError as exc:
            if attempt < retries:
                time.sleep(2 ** attempt * 5)
                continue
            raise RuntimeError("network error: %s" % exc)
    usage = msg.get("usage", {})
    if msg.get("stop_reason") == "refusal":
        return None, usage, "refusal"
    text = "".join(b.get("text", "") for b in msg.get("content", []) if b.get("type") == "text").strip()
    return text, usage, msg.get("stop_reason")


def sign_test(wins, losses):
    """Exact two-sided binomial sign test, ties dropped."""
    n = wins + losses
    if n == 0:
        return None
    k = min(wins, losses)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return round(min(1.0, 2 * tail), 4)


def rule_check(rules_path, text):
    import twin_check  # noqa: E402
    doc = twin_check.load_rules(rules_path)
    lex = tl.load_lexicon()
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as fh:
        fh.write(text)
        path = fh.name
    try:
        results = twin_check.check_file(path, "response", doc["rules"], lex)
    finally:
        os.unlink(path)
    failed = [r["rule"]["id"] for r in results if r["hits"] and r["rule"]["severity"] == "error"]
    return {"passed": not failed, "failed_error_rules": failed}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--twin", required=True, help="twin.md, used as the system prompt")
    ap.add_argument("--samples", help="folder of REAL writing by the person, not used to build the twin")
    ap.add_argument("--rules", help="twin.rules.json, for an offline rule check of every answer")
    ap.add_argument("--tests", help="comma-separated ids, e.g. ST-01,ST-06 (default: all 15)")
    ap.add_argument("--gen-model", default=DEFAULT_GEN)
    ap.add_argument("--judge-model", default=DEFAULT_JUDGE)
    ap.add_argument("--effort", default="medium", choices=("low", "medium", "high"))
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--both-orders", action="store_true", help="judge each pair twice, A/B and B/A")
    ap.add_argument("--max-sample-chars", type=int, default=12000)
    ap.add_argument("--out", default=os.path.join(HERE, "results", "eval.json"))
    ap.add_argument("--dry-run", action="store_true", help="print the estimate and exit; no network")
    args = ap.parse_args(argv)

    if args.gen_model == args.judge_model:
        ap.error("the judge must be a different model from the generator")
    tests = parse_stress_tests(os.path.join(HERE, "STRESS_TESTS.md"))
    if args.tests:
        want = {t.strip() for t in args.tests.split(",")}
        tests = [t for t in tests if t["id"] in want]
    if not tests:
        ap.error("no stress tests selected")
    # Everything sent to the API is redacted first, the Twin included.
    twin_text = tl.redact(tl.read_text(args.twin))
    if args.samples:
        reference = read_samples(args.samples, args.max_sample_chars)
        ref_kind = "held-out writing samples"
    else:
        reference = twin_text
        ref_kind = "the twin profile itself (weaker: rewards answers that echo the profile)"
    if not reference.strip():
        ap.error("the reference is empty")

    est = estimate(tests, twin_text, reference, args.gen_model, args.judge_model, args.both_orders)
    print("tests            %d" % est["tests"])
    print("generator        %s (%d calls)" % (args.gen_model, est["generation_calls"]))
    print("judge            %s (%d calls)" % (args.judge_model, est["judge_calls"]))
    print("judge reference  %s" % ref_kind)
    print("est. tokens      gen in %d, gen out %d, judge in %d, judge out %d" % (
        est["generation_input_tokens"], est["generation_output_tokens"],
        est["judge_input_tokens"], est["judge_output_tokens"]))
    print("est. cost        %s" % ("$%.2f (list prices in this file; output includes thinking)" % est["estimated_usd"]
                                   if est["estimated_usd"] is not None else "unknown model price"))
    if args.dry_run:
        print("dry run: nothing sent")
        return 0

    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("twin_eval: set ANTHROPIC_API_KEY, or use --dry-run", file=sys.stderr)
        return 2

    rng = random.Random(args.seed)
    rows = []
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)

    def save(done):
        """Write what has been paid for so far, after every test."""
        tl.write_json(args.out, {"generator": args.gen_model, "judge": args.judge_model,
                                 "effort": args.effort, "seed": args.seed, "complete": done,
                                 "tests": rows})
    spent = {"input_tokens": 0, "output_tokens": 0}
    for t in tests:
        row = {"id": t["id"], "title": t["title"]}
        generic, u1, s1 = call(args.gen_model, key, t["prompt"], effort=args.effort)
        twin, u2, s2 = call(args.gen_model, key, t["prompt"], system=twin_text, effort=args.effort)
        for u in (u1, u2):
            spent["input_tokens"] += u.get("input_tokens", 0)
            spent["output_tokens"] += u.get("output_tokens", 0)
        if generic is None or twin is None:
            row["error"] = "generation stopped: %s / %s" % (s1, s2)
            rows.append(row)
            save(False)
            print("%s  error: %s" % (t["id"], row["error"]))
            continue
        row["generic"], row["twin"] = generic, twin
        orders = [rng.random() < 0.5]
        if args.both_orders:
            orders.append(not orders[0])
        verdicts = []
        for twin_first in orders:
            a, b = (twin, generic) if twin_first else (generic, twin)
            text, u, s = call(args.judge_model, key, judge_prompt(reference, t["prompt"], a, b),
                              schema=JUDGE_SCHEMA, effort=args.effort)
            spent["input_tokens"] += u.get("input_tokens", 0)
            spent["output_tokens"] += u.get("output_tokens", 0)
            if text is None:
                verdicts.append({"twin_was": "A" if twin_first else "B", "pick": "error", "stop": s})
                continue
            try:
                v = json.loads(text)
                pick = v["winner"]
                if pick not in ("A", "B", "tie"):
                    raise ValueError(pick)
            except (ValueError, KeyError, TypeError):
                verdicts.append({"twin_was": "A" if twin_first else "B", "pick": "error",
                                 "stop": s, "raw": text[:500]})
                continue
            mapped = "tie" if pick == "tie" else ("twin" if (pick == "A") == twin_first else "generic")
            verdicts.append({"twin_was": "A" if twin_first else "B", "judge_said": pick, "pick": mapped,
                             "confidence": v.get("confidence"), "reason": v.get("reason", "")})
        row["verdicts"] = verdicts
        picks = [v["pick"] for v in verdicts if v["pick"] != "error"]
        row["result"] = (picks[0] if len(set(picks)) == 1 else "split") if picks else "error"
        if args.rules:
            row["rules"] = {"generic": rule_check(args.rules, generic), "twin": rule_check(args.rules, twin)}
        rows.append(row)
        save(False)
        print("%s  %-8s %s" % (t["id"], row["result"], t["title"]))

    wins = sum(1 for r in rows if r.get("result") == "twin")
    losses = sum(1 for r in rows if r.get("result") == "generic")
    summary = {
        "twin_wins": wins, "generic_wins": losses,
        "ties_or_split": sum(1 for r in rows if r.get("result") in ("tie", "split")),
        "errors": sum(1 for r in rows if r.get("result") in (None, "error") or "error" in r),
        "sign_test_p": sign_test(wins, losses),
        "tokens_used": spent,
    }
    if args.rules:
        summary["rule_pass"] = {
            side: sum(1 for r in rows if r.get("rules", {}).get(side, {}).get("passed")) for side in ("generic", "twin")}
    out = {"generator": args.gen_model, "judge": args.judge_model, "effort": args.effort, "seed": args.seed,
           "both_orders": args.both_orders, "reference": ref_kind, "twin": os.path.basename(args.twin),
           "complete": True, "summary": summary, "tests": rows}
    tl.write_json(args.out, out)
    print("twin %d, generic %d, tie/split %d, errors %d, sign test p=%s" % (
        wins, losses, summary["ties_or_split"], summary["errors"], summary["sign_test_p"]))
    print("tokens used: %d in, %d out. Wrote %s" % (spent["input_tokens"], spent["output_tokens"], args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
