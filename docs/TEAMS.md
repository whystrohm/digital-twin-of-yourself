# Running twins for a team

A twin is two files and a log, kept in git. That is what makes it work for
a team: anyone can read the rules, CI can enforce them, and every change
has a date, a reason and a reviewer.

## Layout

One folder per brand, person or voice:

```
twins/
  acme/
    twin.md              System Prompt, for writers and AI tools
    twin.rules.json      Checkable rules, with profile_version
    TWIN_CHANGELOG.md    Every accepted change and its evidence
  acme-support/
    ...
```

Give the support team its own twin if it should sound different from
marketing. Do not stretch one twin over both.

## Check every pull request

Copy [`templates/twin-check.yml`](../templates/twin-check.yml) to
`.github/workflows/twin-check.yml` in the repo that holds your writing, then
set three values:

| Setting | Meaning |
|---|---|
| `TWIN_RULES` | Path to the rules file, for example `twins/acme/twin.rules.json` |
| `DRAFTS` | Folder of `.md` / `.txt` drafts to check, for example `content` |
| `TWIN_REF` | A commit SHA of this repo, so every run uses the same code |

The workflow checks only the files a pull request adds or changes. Each
failure shows as an annotation on the line in the diff. Error rules fail
the check; warnings do not. Add `--strict` to the command to fail on
warnings too.

For a different CI system, run the same command and read the exit code:

```bash
python3 scripts/twin_check.py --rules twins/acme/twin.rules.json content/ --format json
```

Exit 0 passes, 1 fails, 2 means the rules file or a path is wrong.

## Compare voices across brands

```bash
python3 scripts/twin_scan.py \
  --corpus acme=writing/acme --corpus acme-support=writing/support --corpus blog=writing/blog \
  --out patterns.json
python3 scripts/twin_report.py patterns.json --out voices.html
```

The report opens with a side-by-side table (sentence length, hedge rate,
questions, dashes, lists, score) and lists the repeated phrases each voice
shares and the ones only it uses.

## Change the rules

Rules change by proposal, never by drift:

1. Collect drafts and the versions people actually sent:
   `NAME.draft.md` and `NAME.edited.md` in one folder.
2. `python3 scripts/twin_diff.py propose <folder> --rules twins/acme/twin.rules.json --out twins/acme/twin.proposals.md`
3. Open a pull request with the proposals file. A reviewer ticks
   `- [x] accept` on the ones the team agrees with.
4. `python3 scripts/twin_diff.py accept twins/acme/twin.proposals.md --rules twins/acme/twin.rules.json --changelog twins/acme/TWIN_CHANGELOG.md`
5. Commit the rules and the changelog together.

`accept` bumps `profile_version` and records which proposals were taken and
which were not. It refuses to apply proposals written against an older
version of the rules.

## Audit questions this answers

| Question | Where the answer is |
|---|---|
| What are the rules today? | `twin.rules.json` |
| When did a rule change, and why? | `TWIN_CHANGELOG.md`, then `git log -p twin.rules.json` |
| Who approved it? | The pull request that ticked the proposal |
| Did this draft pass when it shipped? | The CI run on that pull request |
| Has the voice drifted since last quarter? | Two `patterns.json` files from `twin_scan.py`, compared |

## What leaves the machine

Nothing, for everything in `scripts/`. The only networked file is
`validation/twin_eval.py`, which is optional and runs only when someone
starts it with an API key. See [SAFETY_CHECKLIST.md](../SAFETY_CHECKLIST.md).
