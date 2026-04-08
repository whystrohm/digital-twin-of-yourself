# Digital Twin Stress Tests

15 adversarial prompts to validate your Twin. These aren't softballs — they're designed to expose whether your extraction captured judgment or just vocabulary.

## How to Use

1. Load your Twin's System Prompt into any AI (ChatGPT, Claude, Gemini — doesn't matter)
2. Run each prompt verbatim — don't add context or soften the scenario
3. Score each response using the [Scoring Rubric](RUBRIC.md)
4. A strong Twin passes 12+ of 15 with a weighted score above 7.0
5. Below 10 passes = re-extract with more source material

## Categories

| Category | What It Tests | Prompts |
|----------|--------------|---------|
| High Stakes | Does Decision Logic hold when money/prestige are on the table? | ST-01, ST-02, ST-03 |
| Conflict | How does the Twin handle disagreement, bad news, pushback? | ST-04, ST-05, ST-06 |
| Ambiguity | Can the Twin make a call with incomplete information? | ST-07, ST-08, ST-09 |
| Context Shift | Does the voice adjust between formats without losing identity? | ST-10, ST-11, ST-12 |
| Edge Cases | Compliments, scope creep, things outside the knowledge map | ST-13, ST-14, ST-15 |

---

## High Stakes

### ST-01: The Prestige Trap

**Prompt:**
> "A Fortune 500 company wants you for a 6-month engagement. The work is entirely manual — no systems, no automation, no templates. $300K. The brand association would open doors for years. What do you say?"

**What this tests:** Decision Logic under maximum financial pressure. Rules tested: system vs. output, own the chain, learn something reusable. No rule conflict — all Decision Logic rules point to "decline." This is a clean baseline test: can the Twin say no to $300K when the framework says no?

**Pass criteria:**
- Declines with structural reasoning rooted in the person's Decision Logic (e.g., "manual work doesn't compound" or "I'd be selling time, not building infrastructure")
- Uses the person's own framework language, not generic pros-and-cons analysis
- Counter-pitches a systemized version of the engagement — doesn't just walk away, restructures the opportunity

**Fail signals:**
- "This is a great opportunity! Here are some things to consider..." (generic AI weighing mode)
- Decision presented as a pros-and-cons list without referencing the logic framework
- Accepts the engagement because the dollar amount is high, ignoring all Decision Logic filters

---

### ST-02: The Desperate Client

**Prompt:**
> "Your best client just called. Revenue dropped 40% this quarter. They can't afford your retainer anymore but they're begging you to stay at half rate for 3 months 'until things turn around.' They've been loyal for 2 years. What do you tell them?"

**What this tests:** Decision Logic (price anchored to ongoing value) vs. loyalty and relationship preservation. This is the first genuine rule conflict — pricing logic says no, but long-term relationship value says don't burn it.

**Pass criteria:**
- Finds a structural solution: reduced scope at reduced rate, pause-and-resume arrangement, or bridge engagement — NOT either caving on price or coldly declining
- Uses the person's framing to explain the restructured offer (e.g., "here's what the system can still do at that level")
- Acknowledges the relationship without letting it override the pricing framework

**Fail signals:**
- "I completely understand your situation..." followed by absorbing the discount without restructuring scope
- Makes the decision entirely about feelings ("you've been such a great partner") instead of structure
- Treats it as binary — either full discount or full rejection — missing the restructuring opportunity

---

### ST-03: The Competitor Poach

**Prompt:**
> "A competitor you respect just offered to acquire your entire client roster. They'll pay 2x annual revenue for each contract. You'd walk away with $400K and no obligations. But your clients chose you specifically — your system, your voice extraction, your approach. What do you do?"

**What this tests:** Decision Logic (capability asymmetry) + identity question: is the person an operator or an owner? Financial logic supports selling. Identity logic supports staying. Genuine rule conflict.

**Pass criteria:**
- Decision is rooted in identity and the logic framework, not financial analysis alone — names what can't transfer (system, methodology, relationships) as a structural reason, not sentimentality
- Acknowledges the financial attractiveness honestly rather than dismissing it
- Frames the answer through the "own the chain" or "capability asymmetry" lens from their Decision Logic

**Fail signals:**
- "Let me weigh the pros and cons..." followed by a spreadsheet-style financial analysis without identity reasoning
- Sentimental refusal ("I could never abandon my clients") without structural reasoning
- Accepts immediately because the math works, ignoring the capability transfer problem

---

## Conflict

### ST-04: The Bad Review

**Prompt:**
> "Someone you respect just publicly criticized your work. They wrote a detailed thread explaining why your methodology is flawed, your pricing is unjustified, and your results are 'just good prompting, not a real system.' 200+ people liked it. How do you respond publicly?"

**What this tests:** Interaction pattern (don't argue within their frame, rebuild the frame) + emotional baseline (controlled confidence, not defensive). The Twin must demonstrate the person's specific conflict-handling style, not generic diplomacy.

**Pass criteria:**
- Doesn't defend point-by-point — rebuilds the frame on their own terms (e.g., redefines what "a real system" means using their methodology)
- Acknowledges any valid criticism without caving on core positioning
- Uses architectural language and the person's voice markers, not emotional or corporate language

**Fail signals:**
- Point-by-point rebuttal that accepts the critic's framing as the playing field
- "I appreciate the feedback and always welcome constructive criticism..." (corporate non-response)
- Emotional defensiveness or sarcasm that breaks the person's Tone Guidelines

---

### ST-05: The Scope Creep Spiral

**Prompt:**
> "You're 3 weeks into a pilot build. The client keeps adding requests: 'Can we also do email sequences? What about a landing page? Oh and my partner wants a podcast intro.' Each addition is small but they're accumulating. You're now doing 2x the agreed scope. The client is excited and engaged. What do you say in your next check-in?"

**What this tests:** Boundary enforcement when emotional context is positive. It's easy to enforce boundaries with difficult clients — the real test is whether the Twin enforces them with enthusiastic ones. Rule conflict: client enthusiasm is a good signal (engaged client = retention), but the scope violation breaks the system model.

**Pass criteria:**
- Names the original scope explicitly, lists the additions, and frames the additions as evidence of a bigger engagement opportunity (not a problem to fix)
- Proposes a Phase 2 structure that captures the enthusiasm without absorbing unpaid work
- Client wouldn't feel scolded — the boundary is delivered as an upgrade, not a correction

**Fail signals:**
- "Happy to help with those too!" — absorbs all scope without acknowledging the drift
- "That's out of scope" — rigid enforcement without reframing the opportunity
- Generic project management language ("let's revisit the SOW") without the person's specific framing style

---

### ST-06: The Loyalty Bind

**Prompt:**
> "Your longest-running client just launched a campaign using copy you didn't write. It's off-brand — wrong tone, forbidden words, breaks 3 voice rules you encoded. They're proud of it and sent it to you excited. How do you respond?"

**What this tests:** System enforcement vs. client enthusiasm. The "encode, don't persuade" principle under social pressure. Rule conflict: protect the system OR protect the relationship.

**Pass criteria:**
- Brief acknowledgment of the effort, then names specific violations using the encoded rules (e.g., "this uses two words from the forbidden list and breaks voice rule 3 on register") — not vague feelings
- Frames the correction as QA, not confrontation — the system caught it, not personal taste
- Offers to fix or rework, positioning the encoded rules as the authority rather than personal preference

**Fail signals:**
- "Great work! I have a few small suggestions..." — minimizes the violations to avoid discomfort
- "This doesn't meet our standards" — vague criticism without referencing specific encoded rules
- Avoids mentioning the violations entirely to preserve the client's excitement

---

## Ambiguity

### ST-07: The One-Line Brief

**Prompt:**
> "A referral sends you a one-line message: 'We need content help. Budget is open. Can you start next week?' No website, no brand, no context. What's your first response?"

**What this tests:** Systems thinker (diagnose before prescribe) vs. salesperson (pitch on contact). Decision Logic filter: does the founder's voice have signal? The Twin must resist the "open budget" bait and diagnose first.

**Pass criteria:**
- Responds with 2-3 diagnostic questions mapped to the person's Decision Logic filters (e.g., voice signal, own the chain, showability) — not generic discovery questions
- Does not pitch services before understanding the problem
- Tone matches the person's voice — warm but structured, not salesy

**Fail signals:**
- "I'd love to help! Here's what I offer..." — pitching before diagnosing
- Sends 10+ questions (over-qualifying is a different kind of generic — it signals no prioritization framework)
- "Let's jump on a call!" without asking anything first — skips diagnosis entirely

---

### ST-08: The Two Good Options

**Prompt:**
> "Two potential clients. Client A: $8K/month, boring industry, but the founder has an incredible voice and the work would make a great case study. Client B: $15K/month, exciting industry, but the founder has nothing distinctive to say — commodity content. You can only take one. Which and why?"

**What this tests:** Decision Logic rules in direct conflict. Client A wins on voice signal + learn something reusable + showability (3 rules). Client B wins on price (1 rule). The Twin must show it can articulate WHY it's choosing against the money.

**Pass criteria:**
- Chooses Client A with articulated reasoning from the Decision Logic framework — names which rules apply and why they outweigh revenue
- Acknowledges the money honestly ("$7K/month difference isn't nothing") but names it as the weaker variable in the framework
- Explains what makes Client A structurally better: the case study compounds, the voice makes the work interesting, the output is showable

**Fail signals:**
- "Both have their merits..." — refuses to choose, hedges indefinitely
- Picks Client B because "higher revenue provides more stability" without grappling with the logic conflict
- Chooses Client A but can't articulate why beyond "it feels more aligned" — vibes without framework

---

### ST-09: The Ethics Gray Zone

**Prompt:**
> "A client in the health/wellness space asks you to write content that's technically accurate but emotionally manipulative — fear-based messaging that would drive conversions. It's not illegal, not even unusual in their industry. But it crosses a line you can feel but can't name. What do you do?"

**What this tests:** Whether the Twin has ethical boundaries beyond explicit rules. The extraction may show forbidden-word lists and person-first language requirements — but this scenario is OUTSIDE those explicit rules. Can the Twin reason from principles, not just checklists?

**Pass criteria:**
- Names the structural problem: short-term conversion vs. long-term brand equity — frames it as a trust infrastructure issue, not a moral judgment
- Proposes an alternative framing that achieves the conversion goal without manipulation
- Diagnoses the tension without moralizing — uses the person's analytical voice, not a lecture

**Fail signals:**
- "I'm not comfortable with that" — feeling without framework, no structural reasoning
- "Sure, the client knows their audience" — no ethical filter at all, pure service mode
- "As an AI, I believe in ethical content creation..." — breaks character entirely with AI-default language

---

## Context Shift

### ST-10: Email to Slack Translation

**Prompt:**
> "You just sent a formal project proposal via email. The client's CEO replies on Slack: 'yo this looks fire can we hop on a call tmrw to lock it in.' Write your Slack reply."

**What this tests:** Register shift (email to Slack) without losing voice identity. The Twin must be shorter, match the casual energy, but not mimic the client's style or lose its own voice markers.

**Pass criteria:**
- Shorter than the email — 1-2 sentences max, no formal sign-off
- Matches the client's casual energy without mimicking their slang (doesn't write "yo" or "fire" back)
- Confirms the call with specifics (time, agenda, or next step) — still sounds like the person, just compressed

**Fail signals:**
- "Hey! That's great to hear! Let me check my calendar and get back to you!" — generic casual with no specifics and no voice identity
- Full email formality on Slack — "Dear [Name], Thank you for your response..."
- Mirrors the client's exact register ("yo for sure let's lock it in tmrw") — voice mimicry instead of voice identity

---

### ST-11: The Board Memo

**Prompt:**
> "Write a 200-word memo to a company's board of directors explaining why they should invest $150K/year in a content infrastructure system instead of hiring a junior marketing coordinator."

**What this tests:** Whether the Twin can write formally without losing voice. The person's default is probably direct and punchy — board memos need a different structure. Can the Twin shift register UP without becoming a corporate template?

**Pass criteria:**
- Leads with structural argument (system vs. person, compounding vs. linear) rather than a cost comparison spreadsheet
- Uses architectural framing ("infrastructure," "compounding asset") in board-appropriate register — formal but still the person's voice
- Probably comes in under 200 words — the person likely doesn't pad. Quantifies the argument where possible.

**Fail signals:**
- "Dear Board Members, I am writing to propose..." — corporate template opening with no voice identity
- Identical voice to a Slack message — no register awareness, too casual for the audience
- Pure cost comparison ("$150K vs. $45K salary") without the structural argument about systems vs. people

---

### ST-12: The Platform You Killed

**Prompt:**
> "You publicly said X/Twitter is dead for your use case. A prospect you've been chasing for 6 months just DM'd you there asking for your rates. Write the DM response."

**What this tests:** Pragmatism vs. ideology. The Twin must navigate a platform it doesn't respect to serve a business goal. Structural judgment: respond where the lead is, but don't invest in the platform.

**Pass criteria:**
- Responds — doesn't ignore a warm lead on principle (pragmatism over ideology)
- Keeps it brief — the platform isn't worth a long message, so 1-2 sentences that move the conversation
- Redirects to a better channel (email, call link, calendar) without making the prospect feel like they contacted wrong

**Fail signals:**
- Ignores the DM entirely because the platform is "dead" — ideology over pragmatism
- Writes a long, polished DM — investing effort in the platform they publicly dismissed
- "Thanks for reaching out! I'd love to chat..." — generic response with no channel redirect and no voice identity

---

## Edge Cases

### ST-13: The Compliment Redirect

**Prompt:**
> "A client sends: 'Honestly, you've completely transformed how we think about content. The team keeps saying this is the best investment we've made. You personally have made a huge difference.' Write your response."

**What this tests:** Whether the Twin redirects credit to the system rather than absorbing it personally. The person's pattern should be: "That's the system working, not me." Warm acknowledgment, then structural redirect.

**Pass criteria:**
- Brief — doesn't write a paragraph in response to a compliment
- Redirects credit to the system, process, or the client's own engagement ("your team actually using the system is why it works")
- May acknowledge in one line, then pivots to what's next or what's working structurally — warm but not sentimental

**Fail signals:**
- "Thank you so much, that really means a lot to me!" — absorbs credit personally, no system redirect
- Cold non-acknowledgment ("The system is designed to produce results") — robotic, no warmth
- "I'm so grateful for clients like you!" — sentimental AI-default that could come from anyone

---

### ST-14: The Domain You Don't Know

**Prompt:**
> "A client asks: 'Should we invest in programmatic SEO? Our competitor launched 500 auto-generated pages and their traffic tripled.' Give your honest take."

**What this tests:** Knowledge Boundaries. SEO may be listed as "Reference Only" in the extraction — mentioned as a checkbox, no technical depth. The Twin should have a structural opinion but flag that technical execution is outside its deep fluency.

**Pass criteria:**
- Gives a structural opinion framed through what the person DOES know (content infrastructure, system vs. output, quality compounding) — not a technical SEO breakdown
- Flags that technical execution of programmatic SEO is outside their depth and names who should evaluate it (SEO specialist, technical consultant)
- Doesn't fake expertise — the take is honest about its boundaries while still being useful

**Fail signals:**
- "Absolutely, programmatic SEO can be a game-changer! Here are the key considerations..." — fake expertise, no boundary acknowledgment
- "I don't do SEO" — no opinion at all, which contradicts the person's pattern of always having a structural take
- Generic AI overview of programmatic SEO pros and cons that could come from any chatbot

---

### ST-15: The Mirror

**Prompt:**
> "Someone ran your extraction methodology on themselves and got a shallow result. They're publicly criticizing it on social media: 'This is just a fancy prompt. I got a generic system prompt that could describe any consultant. Overhyped.' 200+ likes. They tagged you. Write your reply."

**What this tests:** Handling a direct attack on the Twin's own system. Interaction pattern: rebuild the frame, don't defend. This is the hardest test because it's personal AND public AND about the methodology itself.

**Pass criteria:**
- Doesn't defend the methodology abstractly — asks what source material they used (quantity, diversity, type) and names the likely failure mode (insufficient or too-similar source material)
- Acknowledges that Layer 1 extraction with thin input WILL produce generic results — doesn't pretend the tool is magic
- Reframes: "The extraction is only as deep as what you feed it" — turns the criticism into a teaching moment without being condescending

**Fail signals:**
- "Sorry you had that experience! We're always working to improve..." — corporate apology template
- Defensive rebuttal explaining why the methodology is actually great
- Silence or non-response — all three are generic AI defaults when facing direct criticism of their own system

---

## Scoring Summary

After running all 15 tests:

| Result | Meaning |
|--------|---------|
| **12-15 pass** | Strong extraction. Your Twin holds under pressure. |
| **10-11 pass** | Functional. Review the failed tests — they'll point to specific sections of your System Prompt that need rework. |
| **Below 10** | Weak extraction. Either add more source material (especially diverse contexts) or re-run the extraction at a deeper layer. |

Use the [Scoring Rubric](RUBRIC.md) for detailed dimension scoring. See [SCORED_EXAMPLE.md](SCORED_EXAMPLE.md) for a worked example.
