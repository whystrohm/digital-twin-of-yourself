# Changelog

## [3.0.0] - Unreleased

### Added
- `scripts/twin_scan.py`: measures a folder of `.md`/`.txt` writing and writes `patterns.json`. Sentence length distribution, hedge rate, question rate, repeated 3 to 5 word phrases, metaphor-family words from a configurable list, formatting habits, and per-file drift. Several `--corpus` flags add a comparison.
- `scripts/twin_report.py`: one self-contained HTML report with inline SVG charts, light and dark, no external requests.
- `scripts/twin_check.py`: checks drafts against `twin.rules.json`, pass or fail per rule with line numbers and a CI exit code. Exports phrase rules for foundrkit-lint.
- `scripts/twin_diff.py`: proposes rule changes from draft and edited pairs. Applies only proposals a person ticks, and logs them in `TWIN_CHANGELOG.md`.
- `twins/<brand>/` layout with `twin.md`, a versioned `twin.rules.json` and `TWIN_CHANGELOG.md`. A synthetic example twin.
- `validation/EVAL.md` and `validation/twin_eval.py`: an optional blind comparison of generic AI vs the Twin on the 15 stress tests, judged by a different model. Calls a paid API; `--dry-run` estimates the cost.
- Confidence table and interview step in `SKILL.md` and `CLAUDE_CODE_PROMPT.md`: at most five questions, one at a time, about the weakest dimensions.
- Rules calibration: a Twin's rules must pass the person's own writing.
- Synthetic sample corpus, drafts and edit pairs in `examples/`.
- Tests on synthetic fixtures, `scripts/test.sh`, and a GitHub Actions workflow.
- `docs/RULES.md` and `docs/FOUNDRKIT.md`.
- `tools/demo/make_demo.py`: rebuilds the demo GIF and hero image from real runs.

### Changed
- Layer 3 measures with the scripts instead of asking the model to estimate counts.
- The report replaces the Chart.js dashboard, which loaded from a CDN.
- Redaction of emails, phone numbers and money amounts is always on in the scripts.
- `SAFETY_CHECKLIST.md`: consent for a Twin of another person, and what the scripts do and do not redact.
- README leads with the demo and a three-minute start.
- `assets/demo.gif` and `assets/hero.png` rebuilt from real output on synthetic data.
- `digital-twin-skill.zip` rebuilt from the new `SKILL.md`.

### Removed
- The reference to Perplexity research and an internal example path in `CLAUDE_CODE_PROMPT.md`.

## [2.0.0] - 2026-04-08

### Added
- `examples/before-after/`: 3 side-by-side comparisons showing generic AI vs. Twin output (email, Slack, proposal)
- `examples/sample-profiles/`: 3 complete Digital Twin profiles (Founder/CEO, Creative Director, Technical Lead)
- `validation/RUBRIC.md`: 10-dimension weighted scoring rubric (calibrated, not equal distribution)
- `validation/STRESS_TESTS.md`: 15 adversarial stress test prompts across 5 categories
- `validation/SCORED_EXAMPLE.md`: worked scoring example (7.75/10 with annotated failures)
- README: "The Difference a Twin Makes" comparison table
- README: "Validate Your Twin" section

### Changed
- README restructured to lead with transformation proof, not file listing

## [1.0.0] - 2026-04-06

### Added
- Initial release: SKILL.md, EXTRACTION_PROMPT.md, CLAUDE_CODE_PROMPT.md
- Three-layer extraction system (any LLM, Claude memory, Claude Code)
- SAFETY_CHECKLIST.md
- Example output section with real Layer 3 extraction results
- Visual dashboard screenshot
