# Contributing

Thanks for looking. Small, focused pull requests are the easiest to review.

## What is welcome

- **A fix**, with a test that fails without it.
- **A new measurement** in `scripts/twin_scan.py`, with a fixture in `tests/fixtures/`
  that shows what it counts.
- **A new rule type** for `scripts/twin_check.py`, with a draft that fails it and a
  draft that passes.
- **Clearer docs.** If a step tripped you up, it will trip up the next person.

Open an issue first for anything that changes a file format (`patterns.json`,
`twin.rules.json`). Other tools and saved twins read those files.

## Run the checks

```bash
scripts/test.sh
```

That is the same entry point CI runs. It needs Python 3.9 or newer and nothing else.

## Rules

- **The scripts need no install.** Python standard library only.
- **Nothing leaves the machine.** No script may send writing or results anywhere.
- **Sample writing is made up.** Never commit a real person's writing, names, emails,
  phone numbers or amounts. See [`SAFETY_CHECKLIST.md`](SAFETY_CHECKLIST.md).
- **Same input, same output.** Anything code measures must give the same answer every run.

## Writing

Plain words and short sentences. Say what the thing does. No hype.

## Licence

By contributing you agree that your work is released under the repo's MIT licence.
