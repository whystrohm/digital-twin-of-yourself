# Blind evaluation: generic AI vs your Twin

The rubric and stress tests in this folder are scored by a person, and the
person scoring usually built the Twin. That is a self-report. This page
describes a check that removes the author from the scoring:
`validation/twin_eval.py` runs the 15 stress tests twice, once with no
system prompt and once with your Twin, and asks a different model to pick,
blind, which answer the real person more likely wrote.

**Status: written, not run.** The script calls a paid API. It has been run
only with `--dry-run`, which sends nothing. No results are published here.

## What it does

1. Reads the 15 prompts from [STRESS_TESTS.md](STRESS_TESTS.md).
2. The generation model (default `claude-opus-5-5`) answers each prompt
   twice: with no system prompt (generic), and with your `twin.md` as the
   system prompt (twin). Same model, same settings.
3. The judge model (default `claude-sonnet-5-5`, and it must differ from the
   generator) gets reference writing by the person, the scenario, and the
   two answers labelled A and B. Which one is A is decided by a seeded random
   number generator, so the order is random but repeatable (`--seed`).
4. The judge returns JSON: `winner` (A, B or tie), `confidence`, `reason`.
   The request uses structured output, so the reply always parses.
5. Code, not a model, maps A and B back to twin and generic, counts wins,
   and runs an exact two-sided sign test (ties dropped).
6. With `--rules`, code also checks every answer against `twin.rules.json`
   offline, so you can see whether the Twin's answers keep its own rules.

Results go to `validation/results/eval.json`: every answer, every verdict
with its reason, token use, and the summary.

## Run it

```bash
# 1. Estimate only. Sends nothing.
python3 validation/twin_eval.py --twin twins/<brand>/twin.md --samples <held-out folder> --dry-run

# 2. The real run. Needs an API key in the environment.
export ANTHROPIC_API_KEY=...
python3 validation/twin_eval.py --twin twins/<brand>/twin.md --samples <held-out folder> \
  --rules twins/<brand>/twin.rules.json --out validation/results/<brand>.json
```

Options: `--tests ST-01,ST-06` for a subset, `--both-orders` to judge each
pair as A/B and B/A (a split verdict then counts as neither), `--effort`
for the thinking effort (default `medium`), `--gen-model` and `--judge-model`.

### Held-out samples matter

`--samples` should be a folder of the person's real writing that was **not**
used to build the Twin. If the judge compares answers to the same text the
Twin was built from, or to the Twin profile itself (what happens without
`--samples`), it rewards answers that copy the profile. The script says
which reference it used in every run.

## Cost estimate

Token counts are estimated from character counts (about 4 characters per
token). The real count can be higher; newer Claude tokenizers can use up to
about 1.35 times as many tokens. Output tokens include the model's thinking,
which is the largest uncertainty, so the script assumes 1,500 output tokens
per generation and 800 per judgement.

Prices used: Opus 5.5 at $4 input and $20 output per million tokens, Sonnet
5.5 at $2 and $10 (Anthropic list prices as published 2026-09-25; check
current pricing before you run).

| Run | Calls | Estimated tokens | Estimated cost |
|---|---|---|---|
| Synthetic example twin, `--dry-run` output | 30 generation, 15 judge | 10k gen in, 45k gen out, 39k judge in, 12k judge out | $1.14 |
| Same, `--both-orders` | 30 generation, 30 judge | 10k, 45k, 77k, 24k | $1.34 |
| Full-size twin (about 2,500 tokens) and 12,000 characters of samples | 30 generation, 15 judge | about 40k, 45k, 70k, 12k | about $1.30 |
| Same, if thinking runs twice as long | 30 generation, 15 judge | about 40k, 90k, 70k, 24k | about $2.35 |

Expect between $1 and $3 for a full run of all 15 tests. A subset with
`--tests` costs proportionally less. The script prints its own estimate
before it sends anything, and the actual token use when it finishes.

## Reading the result

- With 15 tests and no ties, the twin needs **12 or more wins** for the sign
  test to reach p < 0.05 (12 of 15 gives p = 0.035; 11 of 15 gives
  p = 0.118). Fewer tests or more ties need a bigger margin.
- A win means the judge thought the answer sounded more like the reference
  writing. It does not mean the answer was better, more accurate, or what the
  person would have decided.
- The generator and the judge are both Claude models. A judge from the same
  family may share blind spots with the generator. For a stricter check,
  repeat with a human who knows the person, given the same blind A/B pairs
  from `eval.json`.
- One run is one sample. Model output varies between runs. Run twice with
  different `--seed` values before you rely on a number.

## What this does not replace

The rubric in [RUBRIC.md](RUBRIC.md) scores ten dimensions by hand and
catches things a pairwise judgement cannot, such as Decision Logic applied
to the wrong rule. Use both: the rubric to find what to fix, the blind
comparison to check that the Twin beats a generic answer at all.
