# Digital Twin of Yourself

**Reverse-engineer how you think, talk, and make decisions — then turn it into a reusable AI System Prompt.**

Built by [WhyStrohm](https://whystrohm.com) — embedded creative engine for founder-led brands.

![Demo](assets/demo.gif)

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
├── EXTRACTION_PROMPT.md ...... Universal prompt (any LLM)
├── CLAUDE_CODE_PROMPT.md ..... Full 7-step pipeline with file scanning
├── SKILL.md .................. Claude Code / Claude.ai skill
├── digital-twin-skill.zip .... Upload-ready for Claude.ai
├── SAFETY_CHECKLIST.md ....... Pre-paste, pre-scan, pre-share rules
├── LICENSE ................... MIT
└── assets/
    ├── social-preview.png .... Repository social image
    └── demo.gif .............. Extraction demo animation
```

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

## Why This Exists

Most AI persona tools either interview you (slow, self-report bias) or ingest everything (privacy nightmare). This extracts patterns from your actual writing, validates them with a stress test, and gives you a usable artifact — not a profile you can't do anything with.

The output is a System Prompt you can load into any AI to:
- Draft communications in your voice
- Pre-qualify projects against your decision logic
- Onboard collaborators to your operating style
- Audit content for voice consistency

**"Discover your voice, then systematize it."**

---

## Built With
- Claude (Anthropic)
- Claude Code agent skills
- Psycholinguistic pattern analysis

## License
MIT — use it, fork it, improve it.

---

*Built by [WhyStrohm](https://whystrohm.com) — I become your brand's creative engine.*
