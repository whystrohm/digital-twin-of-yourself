# Digital Twin: Safety Checklist

## Consent
- [ ] The writing is MINE, or the person who wrote it has given written consent to a Twin of them
- [ ] No voice cloning (text or audio) of anyone else without their written consent
- [ ] Have permission to use this writing for this purpose, including company approval for work material

## Before You Paste (Layer 1 & 2)
- [ ] Using my own permitted writing, or another author's writing with written consent. No client or coworker words are included without that consent
- [ ] Removed all client names and company names
- [ ] Removed dollar amounts, contract terms, proprietary details
- [ ] Removed other people's personal information (emails, phone numbers)

## Before You Scan (Layer 3: Cowork / Claude Code)
- [ ] Created a DEDICATED folder (e.g., ~/digital-twin-scan/)
- [ ] Only copied MY writing into the folder
- [ ] Scrubbed sensitive details from files BEFORE scanning
- [ ] Verified no .env files, API keys, or credentials in the folder
- [ ] NOT pointing Claude at entire home directory or Documents folder
- [ ] Understand: once a file is read by an AI, the data is in the active session

## What the Scripts Do (scripts/)
- [ ] Understand: `twin_scan.py`, `twin_report.py`, `twin_check.py` and `twin_diff.py` run offline. They make no network calls; a test fails if any of them imports a network module.
- [ ] Understand: the scanner removes emails, phone numbers and money amounts before measuring the corpus, and the report scrubs displayed data again. The checker examines raw drafts and redacts reported matches and excerpts. App chat, priorities and voice profiles are not covered by that promise.
- [ ] Understand: redaction does NOT catch names, company names or addresses. Scrub those yourself.
- [ ] Use `--hide-filenames` on `twin_scan.py` if your file names are themselves sensitive.
- [ ] Understand: optional `validation/twin_eval.py` sends the profile, held-out samples, scenarios and generated answers to the configured API provider. Use only material permitted for that provider, and run `--dry-run` first.
- [ ] Understand: `validation/twin_loop.py` calls the Claude CLI with sample prompts and notes. It uses your account and can incur usage charges. App remote features and connected MCP clients have separate data flows in `docs/TWIN.md`.

## Before You Share
- [ ] Read the pattern analysis before sharing. Remove identifying or confidential details
- [ ] twin-report.html: short redacted excerpts only, but read it before you share it
- [ ] patterns.json: contains short redacted excerpts and file names; read it before you share it
- [ ] System Prompt (my Twin): share ONLY with trusted collaborators
- [ ] twin.rules.json: safe to commit to a private repo; check the banned phrases name no one
- [ ] Raw writing samples: NEVER share publicly
- [ ] Read stress test results before sharing. They can repeat material from the profile, prompt or samples

## In the System Prompt Output
- [ ] No specific client names appear
- [ ] No project titles or proprietary methodology names
- [ ] No dollar amounts or contract details
- [ ] No personal details about other people
- [ ] All examples are generalized (principle, not data)

## TL;DR

The prompt asks for principles, but its output can still contain source details. Scrub before you scan. Get permission and consent before using another person's material. Review every output before sharing. Keep the System Prompt private.
