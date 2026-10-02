# twin.rules.json reference

`twin.rules.json` holds the parts of a Twin that code can check. The System
Prompt (`twin.md`) holds everything else. `scripts/twin_check.py` reads the
rules file and checks drafts against it.

## File

```json
{
  "contract": "twin-rules",
  "version": "1",
  "brand": "example",
  "profile_version": "1.0.0",
  "generated_from": ["examples/sample-corpus"],
  "rules": [ ... ]
}
```

| Field | Required | Meaning |
|---|---|---|
| `contract` | yes | Always `"twin-rules"`. |
| `version` | yes | Format version, the string `"1"`. |
| `brand` | yes | The folder name under `twins/`. The tests check that they match. |
| `profile_version` | yes | Semantic version of this Twin, `MAJOR.MINOR.PATCH`. `twin_diff.py accept` bumps the minor number. |
| `generated_from` | no | Folders or files the rules were drawn from. |
| `rules` | yes | One or more rules. |

## Rules

Every rule has `id` (lowercase letters, digits, dashes; unique), `type`,
and `severity` (`error` or `warn`). Optional: `suggestion` (shown on
failure) and `source` (`extraction`, `scan`, `diff` or `manual`), which
records where the rule came from.

| Type | Fields | Fails when |
|---|---|---|
| `banned_phrase` | `phrases`: list of strings | Any phrase appears. |
| `banned_pattern` | `pattern`: `"/body/flags"` | The regex matches. Flags `i`, `m`, `s`; `g` is ignored. No flags means case-insensitive. |
| `max_sentence_words` | `max`: integer | Any sentence has more words than `max`. |
| `max_rate` | `metric`: `hedge`, `question` or `exclamation`; `max`: 0 to 1 | The share of sentences with that feature, per file, is above `max`. |
| `no_emoji` | none | Any emoji appears. |

### How phrases match

The same way foundrkit-lint matches a plain string: case-insensitive, and a
word boundary on any side that starts or ends with a letter, digit or
underscore. `"maybe"` matches "Maybe" but not "maybeline". A phrase made of
punctuation, such as `"--"`, matches anywhere.

### What is checked

`.md` and `.txt` files. Code blocks, front matter and HTML comments are
skipped. Headings are skipped for sentence rules, because a heading is a
label, not a sentence. Phrase and pattern rules run on every other line.

## twin_check.py

```bash
python3 scripts/twin_check.py --rules twins/example/twin.rules.json draft.md
python3 scripts/twin_check.py --rules twins/example/twin.rules.json drafts/ --format json
python3 scripts/twin_check.py --rules twins/example/twin.rules.json drafts/ --strict
```

| Exit | Meaning |
|---|---|
| 0 | Every `error` rule passed. Warnings are allowed unless `--strict`. |
| 1 | An `error` rule failed, or with `--strict` any rule failed. |
| 2 | Setup problem: invalid rules file, missing draft, bad option. |

Snippets in the output are redacted (emails, phone numbers, money amounts)
and cut to 90 characters.

## Versioning and the audit trail

- `profile_version` changes whenever the rules change.
- `TWIN_CHANGELOG.md`, next to the rules, records every accepted change,
  newest first, with the evidence that led to it.
- `twin_diff.py propose` writes proposals with the SHA-256 of the rules file
  they were computed against. `twin_diff.py accept` refuses to apply them if
  the rules have changed since, so an old proposal cannot undo a newer
  decision.
- Commit `twins/<brand>/` to git. The history of `twin.rules.json` plus the
  changelog shows who changed which rule, when, and why.
