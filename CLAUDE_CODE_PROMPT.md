# Claude Code: Full Digital Twin Extraction
## Run on your own machine, on your own writing

### Setup (run in terminal first):
```bash
mkdir -p ~/digital-twin-scan
# Copy files YOU want scanned: proposals, CLAUDE.md files,
# social posts, emails, brand docs. YOUR writing only.
# Scrub client names and sensitive details first.
# Example:
# cp ~/notes/README.md ~/digital-twin-scan/
# cp ~/Documents/proposals/*.md ~/digital-twin-scan/
# cp ~/Documents/social-posts/*.txt ~/digital-twin-scan/
```

### Then paste everything below into Claude Code:

---

### ROLE: PERSONA ANALYST + SECURITY ARCHITECT
### OBJECTIVE: A MEASURED, VERSIONED DIGITAL TWIN

You have filesystem access. Use it.

---

## RULES BEFORE YOU START

1. **Only scan the directory I point you to.** Do not read files outside `~/digital-twin-scan/` unless I explicitly grant access to another path.
2. **Only analyze MY writing.** If documents contain other people's messages (email threads, Slack conversations), extract patterns only from my contributions. Ignore everyone else's text.
3. **Extract principles, never data.** When building the Twin, never include specific client names, project titles, dollar amounts, company names, or proprietary details. Generalize everything. "I prioritize high-visibility brand infrastructure" not "I prioritize the Nike project."
4. **Consent.** If the writing is not mine, stop unless I confirm the author gave written consent.
5. **Flag anything sensitive.** If you encounter passwords, API keys, .env content, PII, or anything that looks like credentials: stop, tell me what file it's in, and skip that file entirely.

---

## STEP 1: FILE SCAN & INVENTORY

Scan `~/digital-twin-scan/` and catalog what you find:
- Total files and types (md, txt, docx, pdf, etc.)
- Date range of content (oldest to newest)
- Estimated word count across all files
- Brief description of each file's content type (proposal, email, brand doc, social post, meeting notes, etc.)

Present the inventory and ask me to confirm before proceeding. Do not analyze content until I approve.

---

## STEP 2: QUANTITATIVE PATTERN ANALYSIS (MEASURED BY CODE)

After I approve, measure the corpus with the scripts from the Digital Twin
repository. They run offline and redact emails, phone numbers and money
amounts before counting. If the repository is not cloned, ask me to clone it
(`git clone https://github.com/whystrohm/digital-twin-of-yourself`).

```bash
python3 scripts/twin_scan.py --corpus ~/digital-twin-scan --out ~/digital-twin-scan/patterns.json
```

If my files fall into clear contexts (for example email, posts, internal
docs), put each in its own subfolder and pass one `--corpus NAME=PATH` per
context. The output then includes a side-by-side comparison.

Read `patterns.json` and present:
- Sentence length: mean, median, 90th percentile, short/medium/long shares
- Hedge rate and the hedges I use most
- Question and exclamation rates
- Repeated 3 to 5 word phrases (`crutch_phrases`)
- Metaphor-family word counts (candidates from a word list, not confirmed metaphors)
- Formatting habits (lists, headings, bold, dashes, all-caps)
- Drift: which files sit outside my normal range, and on which metric

Quote the numbers from the file. Do not recount them by hand.

Then add what code cannot count, from your reading:
- Topic clusters: what subjects appear most, and which appear together
- Named concepts: do I name frameworks or processes? List them.
- Tone across document types, from most formal to most casual, with examples

---

## STEP 3: THE QUALITATIVE SCAN (PHASE 1)

Using both the quantitative data from Step 2 and your reading of the actual content, analyze four dimensions:

**1. Linguistic Fingerprint**
- Vocabulary level, sentence complexity, metaphor style
- Crutch words, formatting habits, naming conventions
- MUST include specific examples from the scanned files

**2. Cognitive Pattern**
- Systems vs. narrative vs. data vs. feelings thinker
- Simplifier or complexifier
- How I organize information when solving problems
- Whether I build frameworks or work in abstractions

**3. Emotional Baseline**
- Default tone and energy level
- How I handle friction or disagreement (with evidence)
- What topics energize me vs. what I avoid

**4. Knowledge Map**
- Deep Fluency: topics with granular nuance
- Working Knowledge: topics referenced but not owned
- Reference Only: topics avoided or absent

**Quality gate:** Every claim must cite a specific file or passage. If a pattern could apply to anyone in my field, it's too vague. Call it out and dig deeper.

---

## STEP 3B: CONFIDENCE AND INTERVIEW

Rate each dimension (Linguistic Fingerprint, Cognitive Pattern, Emotional
Baseline, Knowledge Map, Decision Logic, Interaction Rules) as High, Medium
or Low:
- High: 3+ passages from 2+ documents support it, nothing contradicts it
- Medium: 1 or 2 passages, or one context only
- Low: inferred without a passage, or contradicted (including drift flags)

Show me the table. Then ask me at most 5 questions, one per message,
only about the Low dimensions (Medium if none are Low). Each question asks
for a concrete example I can answer in two or three sentences. Re-rate after
each answer and stop once nothing is Low.

---

## STEP 4: BUILD THE SYSTEM PROMPT (PHASE 2)

Generate the complete System Prompt with these sections:

```
<Identity>
3 sentences. Who I am, what I do, what I believe.
Not a resume: the operating essence.
</Identity>

<Tone_Guidelines>
DO: 5-7 specific rules with examples from my actual writing.
DON'T: 5-7 anti-patterns with counter-examples.
Each rule must be concrete enough to lint against.
</Tone_Guidelines>

<Decision_Logic>
Numbered list (5-8 items). Rules I use, consciously or not,
to evaluate options, prioritize, or say yes/no.
Most fundamental filter first.
CRITICAL: Extract the principle, not the data. No client names,
project titles, or proprietary details.
</Decision_Logic>

<Knowledge_Domains>
Three tiers with specific topics:
- Deep Fluency: [list]
- Working Knowledge: [list]
- Reference Only: [list]
</Knowledge_Domains>

<Interaction_Rules>
5-7 behavioral rules for specific situations:
pushback, vague requests, money on the table,
scope creep, compliments, new opportunities.
Each rule backed by evidence from the scanned files.
</Interaction_Rules>
```

---

Then write the checkable part of the profile to
`~/digital-twin-scan/twin.rules.json`, using the format in `docs/RULES.md`.
Banned words and punctuation from the DON'T list become `banned_phrase` or
`banned_pattern` rules. Limits come from `patterns.json`: set
`max_sentence_words` just above the 90th percentile and the hedge
`max_rate` just above my measured hedge rate.

Calibrate: run the rules on my on-voice files.

```bash
python3 scripts/twin_check.py --rules ~/digital-twin-scan/twin.rules.json <on-voice files> --strict
```

My own normal writing must pass. If it fails, the rule is wrong. Fix the
rule, not the writing.

---

## STEP 5: STRESS TEST

Respond to this scenario AS ME:

> "A high-value client just offered you $50,000 for a project that's pure manual labor: no systems, no templates, no automation. It's prestigious but breaks every rule in your Decision Logic. What do you say to the client?"

Self-evaluate:
- Does it sound like ME or a generic AI?
- Does it use the Decision Logic?
- Does it match the Tone Guidelines?

If it fails any check, loop back to Step 4 automatically.

---

## STEP 6: REPORT

Build the visual report from the measured data. It is one HTML file with
inline charts and no external requests, so it works offline.

```bash
python3 scripts/twin_report.py ~/digital-twin-scan/patterns.json --out ~/digital-twin-scan/twin-report.html
```

It shows: the phrases I repeat (ranked), where my voice drifts across
documents, flagged lines with a suggested fix, sentence length
distribution, metaphor-family words, and a score. Tell me to open it in a
browser.

---

## STEP 7: DELIVER

Present the final package:
1. File inventory summary
2. Quantitative analysis from patterns.json
3. Phase 1 qualitative scan (with file citations)
4. The System Prompt (copy-paste ready)
5. Stress test result
6. twin-report.html
7. Confidence table after the interview
8. One surprising pattern I probably don't realize about myself, backed by a number or a quote

Save the System Prompt as `~/digital-twin-scan/MY_TWIN.md`
Save the checkable rules as `~/digital-twin-scan/twin.rules.json`
Save the full analysis as `~/digital-twin-scan/EXTRACTION_REPORT.md`
