# Exporting rules to foundrkit-lint

[foundrkit-lint](https://github.com/whystrohm/foundrkit-lint) checks a repo's
files for banned phrases on every commit. `twin_check.py` can export a
Twin's phrase rules in a format it reads:

```bash
python3 scripts/twin_check.py --rules twins/example/twin.rules.json \
  --export-foundrkit foundrkit.config.json
npx foundrkit-lint
```

## What was verified

Checked against foundrkit-lint 0.2.0 (commit `e23cac3`, 2026-09-26) by
reading `README.md`, `src/config.js`, `src/matcher.js`, `src/contract.js`
and `contracts/foundrkit-rules.v1.schema.json`, then running it.

- The export is the plain JSON config: `{"forbidden": [{"pattern",
  "severity", "suggestion", "category"}]}`. foundrkit-lint loads it as
  `foundrkit.config.json`.
- Plain phrases match the same way in both tools (case-insensitive, word
  boundaries only on word-character sides). Regex literals use the same
  `/body/flags` form, with case-insensitive matching when no flags are given.
- On the synthetic sample plus an edge-case draft, foundrkit-lint and
  `twin_check.py` reported the same hits: same file, line, column and match.
  The test `test_same_hits_as_foundrkit_lint` repeats this comparison when
  `FOUNDRKIT_LINT` points at `bin/foundrkit-lint.js`. CI does not run it,
  because it needs Node and a clone of foundrkit-lint.

## Gaps

These are differences in the formats. The export does not hide them.

1. **The shared contract has no slot for a Twin.** foundrkit-lint's
   `foundrkit-rules` v1 contract (`brand/foundrkit.rules.json`) requires each
   rule's `source` to be `voice-profile`, `brand-lock` or `manual`. A rule
   from a Twin is none of these. Writing `manual` would misstate where the
   rule came from, so the export writes the plain config instead. To close
   the gap, the canonical schema in whystrohm/shotkit would need a new
   source value (for example `digital-twin`) and a copy in each repo that
   uses it.
2. **Measurements do not export.** foundrkit-lint matches phrases.
   `max_sentence_words` and `max_rate` rules are skipped, and the export
   prints each skipped rule and why. Keep running `twin_check.py` for them.
3. **Emoji.** Python and JavaScript emoji ranges differ, so `no_emoji` is
   skipped. Add foundrkit-lint's own emoji rule if you want it there.
4. **Regex dialects.** Patterns that use Python-only syntax (`(?P<name>`,
   `\A`, `\Z`, inline flags) are skipped with a reason.
5. **Code blocks.** `twin_check.py` skips fenced code, front matter and HTML
   comments. foundrkit-lint scans every line. A banned phrase inside a code
   block is reported by foundrkit-lint only.
