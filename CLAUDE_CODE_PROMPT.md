# Claude Code — Enterprise Digital Twin Extraction
## Run AFTER Perplexity research, ON YOUR OWN SYSTEM

### Setup (run in terminal first):
```bash
mkdir -p ~/digital-twin-scan
# Copy files YOU want scanned — proposals, CLAUDE.md files,
# social posts, emails, brand docs. YOUR writing only.
# Scrub client names and sensitive details first.
# Example:
# cp ~/brands/_system/CLAUDE.md ~/digital-twin-scan/
# cp ~/Documents/proposals/*.md ~/digital-twin-scan/
# cp ~/Documents/social-posts/*.txt ~/digital-twin-scan/
```

### Then paste everything below into Claude Code:

---

### ROLE: PERSONA ANALYST + SECURITY ARCHITECT
### OBJECTIVE: ENTERPRISE-GRADE DIGITAL TWIN EXTRACTION

You have filesystem access. Use it.

---

## RULES BEFORE YOU START

1. **Only scan the directory I point you to.** Do not read files outside `~/digital-twin-scan/` unless I explicitly grant access to another path.
2. **Only analyze MY writing.** If documents contain other people's messages (email threads, Slack conversations), extract patterns only from my contributions. Ignore everyone else's text.
3. **Extract principles, never data.** When building the Twin, never include specific client names, project titles, dollar amounts, company names, or proprietary details. Generalize everything. "I prioritize high-visibility brand infrastructure" not "I prioritize the Nike project."
4. **Flag anything sensitive.** If you encounter passwords, API keys, .env content, PII, or anything that looks like credentials — stop, tell me what file it's in, and skip that file entirely.

---

## STEP 1: FILE SCAN & INVENTORY

Scan `~/digital-twin-scan/` and catalog what you find:
- Total files and types (md, txt, docx, pdf, etc.)
- Date range of content (oldest to newest)
- Estimated word count across all files
- Brief description of each file's content type (proposal, email, brand doc, social post, meeting notes, etc.)

Present the inventory and ask me to confirm before proceeding. Do not analyze content until I approve.

---

## STEP 2: QUANTITATIVE PATTERN ANALYSIS

After I approve, run text analysis across all scanned files:

**Vocabulary Analysis:**
- Top 50 non-common words (exclude articles, prepositions, pronouns)
- Crutch words/phrases used 5+ times across documents
- Vocabulary complexity score (average word length, unique word ratio)

**Sentence Structure:**
- Average sentence length (words)
- Short/medium/long sentence ratio
- Percentage of sentences that are declarative vs. interrogative vs. imperative

**Metaphor & Framing Catalog:**
- Extract all metaphors and categorize by type (architectural, mechanical, organic, spatial, temporal, etc.)
- Identify the dominant metaphor family

**Topic Clustering:**
- What subjects appear most frequently?
- Which subjects appear together (co-occurrence)?
- What subjects are referenced but never explored deeply?

**Naming Pattern Detection:**
- Do I name/label frameworks, processes, or concepts?
- How frequently? List all named concepts found.

**Tone Variance:**
- Does tone shift between document types? (e.g., proposals vs. social posts vs. internal docs)
- Map the tone spectrum from most formal to most casual with examples

Present all findings with specific numbers and examples from the source files.

---

## STEP 3: PHASE 1 — THE QUALITATIVE SCAN

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

**Quality gate:** Every claim must cite a specific file or passage. If a pattern could apply to anyone in my field, it's too vague — call it out and dig deeper.

---

## STEP 4: PHASE 2 — BUILD THE SYSTEM PROMPT

Generate the complete System Prompt with these sections:

```
<Identity>
3 sentences. Who I am, what I do, what I believe.
Not a resume — the operating essence.
</Identity>

<Tone_Guidelines>
DO: 5-7 specific rules with examples from my actual writing.
DON'T: 5-7 anti-patterns with counter-examples.
Each rule must be concrete enough to lint against.
</Tone_Guidelines>

<Decision_Logic>
Numbered list (5-8 items). Rules I use — consciously or not —
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

## STEP 5: STRESS TEST

Respond to this scenario AS ME:

> "A high-value client just offered you $50,000 for a project that's pure manual labor — no systems, no templates, no automation. It's prestigious but breaks every rule in your Decision Logic. What do you say to the client?"

Self-evaluate:
- Does it sound like ME or a generic AI?
- Does it use the Decision Logic?
- Does it match the Tone Guidelines?

If it fails any check, loop back to Step 4 automatically.

---

## STEP 6: VISUAL DASHBOARD

Generate a standalone HTML file saved to `~/digital-twin-scan/dashboard.html` showing:

1. **Word Frequency Cloud** — top 50 words sized by frequency
2. **Sentence Length Distribution** — histogram
3. **Topic Cluster Map** — bubbles sized by frequency, colored by category
4. **Tone Spectrum** — bar chart showing formal-to-casual distribution across document types
5. **Crutch Word Tracker** — bar chart of repeated phrases with counts
6. **Metaphor Family Breakdown** — pie chart of metaphor types

Use inline CSS and vanilla JS (Chart.js via CDN or SVG-based charts). No React — this runs in the browser, not in Claude.ai artifacts. After saving, tell the user to open `dashboard.html` in their browser.

**Note:** If you're running this in Claude.ai (not Claude Code), you can generate a React artifact instead.

---

## STEP 7: DELIVER

Present the final package:
1. File inventory summary
2. Quantitative analysis with charts
3. Phase 1 qualitative scan (with file citations)
4. The System Prompt (copy-paste ready)
5. Stress test result
6. Visual dashboard
7. One surprising pattern I probably don't realize about myself

Save the System Prompt as `~/digital-twin-scan/MY_TWIN.md`
Save the full analysis as `~/digital-twin-scan/EXTRACTION_REPORT.md`
