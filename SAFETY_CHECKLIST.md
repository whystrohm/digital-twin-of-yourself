# Digital Twin: Safety Checklist

## Consent
- [ ] The writing is MINE, or the person who wrote it has given written consent to a Twin of them
- [ ] No voice cloning (text or audio) of anyone else without their written consent
- [ ] Checked employer's AI usage policy (if using work communications)

## Before You Paste (Layer 1 & 2)
- [ ] Only using MY OWN writing (not client emails, not coworker messages)
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
- [ ] Understand: redaction is always on. Emails, phone numbers and money amounts are replaced when a file is read, before anything is counted or written, and again before the report is written.
- [ ] Understand: redaction does NOT catch names, company names or addresses. Scrub those yourself.
- [ ] Use `--hide-filenames` on `twin_scan.py` if your file names are themselves sensitive.
- [ ] Understand: `validation/twin_eval.py` is the one networked file. It sends your Twin and your held-out samples to the API. Run it only on writing you are allowed to send, and run `--dry-run` first.

## Before You Share
- [ ] Phase 1 analysis (my patterns): SAFE to share publicly
- [ ] twin-report.html: short redacted excerpts only, but read it before you share it
- [ ] patterns.json: contains short redacted excerpts and file names; read it before you share it
- [ ] System Prompt (my Twin): share ONLY with trusted collaborators
- [ ] twin.rules.json: safe to commit to a private repo; check the banned phrases name no one
- [ ] Raw writing samples: NEVER share publicly
- [ ] Stress test results: safe to share (shows methodology works)

## In the System Prompt Output
- [ ] No specific client names appear
- [ ] No project titles or proprietary methodology names
- [ ] No dollar amounts or contract details
- [ ] No personal details about other people
- [ ] All examples are generalized (principle, not data)

## TL;DR

The prompt extracts **principles**, not **data**. It needs your voice, not your secrets. Scrub before you scan. Get consent before you twin anyone else. Share your patterns freely. Keep the System Prompt private.
