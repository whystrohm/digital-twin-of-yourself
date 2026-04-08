# Digital Twin of Yourself

**Reverse-engineer how you think, talk, and make decisions — then turn it into a reusable AI System Prompt.**

Built by [WhyStrohm](https://whystrohm.com) — embedded creative engine for founder-led brands.

![Demo](assets/demo.gif)

---

## The Difference a Twin Makes

| Scenario | Generic AI | With a Twin |
|----------|-----------|-------------|
| **Client ghosted your proposal** | "I hope you're doing well! I wanted to follow up on the proposal I sent over..." | "12 days of silence after a $12K proposal means one of two things: scope mismatch or timing mismatch..." |
| **Teammate suggests a worse approach** | "That's an interesting idea! I can definitely see the appeal of something more straightforward..." | "That's not simpler — that's labor disguised as simplicity..." |
| **Pitching a new client** | "Great to connect! [Referrer] spoke really highly of you and your brand..." | "[Referrer] made the intro — so I'll skip the preamble and go straight to the structural problem..." |

→ [See full before/after comparisons](examples/before-after/)

---

## What This Does

This is a persona extraction workflow that analyzes your writing to build a "Digital Twin" — a System Prompt that makes any AI replicate your voice, judgment, and decision-making logic.

It's not a personality quiz. It reads how you actually communicate and extracts:
- **Linguistic Fingerprint** — vocabulary, metaphor style, crutch words, formatting habits
- **Cognitive Pattern** — how you organize information and solve problems
- **Decision Logic** — the rules you use (consciously or not) to say yes or no
- **Knowledge Map** — where you go deep vs. where you skim

Then it stress-tests the result to make sure it holds under pressure.

## Three Depth Levels

| Level | Tool | Data Source | Depth |
|-------|------|-------------|-------|
| **Layer 1** | Any LLM (ChatGPT, Gemini, Claude, etc.) | Paste your writing samples | ~70% |
| **Layer 2** | Claude with memory enabled | Pulls from conversation history | ~85% |
| **Layer 3** | Claude Code or Cowork | Scans your actual local files | ~100% |

## Quick Start

### Layer 1 — Any LLM (ChatGPT, Gemini, Claude, etc.)
1. Copy the contents of `EXTRACTION_PROMPT.md`
2. Paste into a new chat in any LLM
3. Add your writing samples at the bottom (5+ pages recommended)
4. Let it run all phases including the stress test

### Layer 2 — Claude with Memory
1. Open a new chat in Claude (memory must be enabled)
2. Paste the contents of `EXTRACTION_PROMPT.md`
3. No writing samples needed — Claude pulls from your conversation history
4. Let it run all phases

### Layer 3 — Claude Code (Full Extraction)
1. Create a folder with your writing: `mkdir ~/digital-twin-scan`
2. Copy your files in (scrub sensitive details first)
3. Paste the contents of `CLAUDE_CODE_PROMPT.md` into Claude Code
4. Follow the 7-step pipeline — includes quantitative analysis and visual dashboard

### As a Claude Skill
Upload `digital-twin-skill.zip` to Claude.ai (Settings > Skills) or drop `SKILL.md` into `~/.claude/skills/digital-twin/`

## What's In This Repo

```
├── README.md ................. You're here
├── CHANGELOG.md .............. Version history
├── EXTRACTION_PROMPT.md ...... Universal prompt (any LLM)
├── CLAUDE_CODE_PROMPT.md ..... Full 7-step pipeline with file scanning
├── SKILL.md .................. Claude Code / Claude.ai skill
├── digital-twin-skill.zip .... Upload-ready for Claude.ai
├── SAFETY_CHECKLIST.md ....... Pre-paste, pre-scan, pre-share rules
├── LICENSE ................... MIT
├── assets/ ................... Demo GIF and social preview
├── examples/
│   ├── before-after/ ......... 3 side-by-side comparisons
│   └── sample-profiles/ ...... 3 complete Twin profiles
└── validation/
    ├── RUBRIC.md ............. 10-dimension weighted scoring
    ├── STRESS_TESTS.md ....... 15 adversarial prompts
    └── SCORED_EXAMPLE.md ..... Worked scoring example (7.75/10)
```

## Validate Your Twin

Don't guess whether your Twin is good. Measure it.

- **[Scoring Rubric](validation/RUBRIC.md)** — 10 weighted dimensions. Voice Accuracy and Decision Consistency carry 30% of the score. Below 7.0 needs rework.
- **[15 Stress Tests](validation/STRESS_TESTS.md)** — adversarial prompts across 5 categories: high stakes, conflict, ambiguity, context shift, edge cases.
- **[Scored Example](validation/SCORED_EXAMPLE.md)** — a Founder/CEO Twin scored at 7.75/10. See exactly where it passed and where the AI tells leaked through.

A strong Twin passes 12+ of 15 stress tests with a weighted score above 7.0.

## Example Output (Layer 3)

Running the full extraction on 60 files (27,342 words) produced:

**Quantitative findings:**
- Zero hedging instances ("I think," "maybe," "perhaps") across the entire corpus
- Dominant metaphor family: Architectural/Structural (309 instances)
- Top crutch phrase: "content infrastructure" (26x)
- Sentence structure: 46% short (punchy), 35% medium, 19% long
- 97% declarative sentences, 0% questions

**The stress test:**
> *"$50K for manual labor — prestigious but breaks every rule in your Decision Logic."*
>
> The Twin declined, explained why using the extracted logic framework, and counter-pitched a systems version. Which is exactly what the subject would have done.

**The surprising pattern:**
> "You build measurement tools you don't use. The Content Spiral names this exact pattern in your clients. It may also be yours."

Layer 3 also generates a visual dashboard with word frequency clouds, topic cluster maps, metaphor breakdowns, and tone spectrum charts — saved as an HTML file you open in your browser.

![Dashboard](assets/example-dashboard.png)

---

## Safety

The prompt itself doesn't collect data, call APIs, or execute code. The risk is in what you paste into it.

**Rules:**
1. Only paste YOUR writing. Never client data or coworker messages.
2. Scrub names, dollar amounts, and identifying details before pasting.
3. The prompt extracts principles, not data — no names in the output.
4. Share your patterns freely. Keep the System Prompt private.
5. Layer 3: create a dedicated folder. Never scan your entire home directory.
6. Once AI reads a file, it's in the session. Scrub BEFORE you scan.

Full checklist in `SAFETY_CHECKLIST.md`.

## What's Next

Once you have your Twin, score your published content against it:
- **[Content Audit](https://github.com/whystrohm/whystrohm-audit)** — 5-layer diagnostic that scores your content and rewrites one piece live
- **[Voice Scorer](https://github.com/whystrohm/whystrohm-voice-scorer)** — measures drift between your website voice and social content

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

## License
MIT — use it, fork it, improve it.

---

*Built by [WhyStrohm](https://whystrohm.com) — I become your brand's creative engine.*
