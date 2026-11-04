---
name: prep
description: Build an interview-preparation pack for a specific application and interview round — company research, role decode, likely questions with story mapping, role-specific drills, questions to ask. Use for "prep me for <company>", or when /track finds an interview.
argument-hint: <job-id> [round, e.g. recruiter | hiring manager | product sense | panel | final]
---

# Interview prep pack → `applications/<id>/prep.md`

Inputs: `jd.md`, `fit.md`, `answers.md` (what was claimed in the application), `profile/story-bank.md`, master CV, tracker history (which round, interviewer names if known).

## Research (web + Chrome)
- Company: business model, products, key metrics, funding/financials, recent news (last 6 months), competitors, leadership.
- What they sell or do: use the product/service (or its public site); 3 strengths, 3 problems, 1–2 ideas the user can bring up in their own field.
- Interviewers (if named): LinkedIn background, what they likely care about. Look only — no connection requests.
- Interview process signals: Glassdoor/Blind/LinkedIn posts for this company's interview loop for this kind of role.

## Pack contents
1. **60-second snapshot** — company, role mission, why the user fits (3 proof points), the main risk to address.
2. **Your pitch** — "Tell me about yourself" (90 sec) tailored to this role; plus, if needed, the story for a gap or career change (from `story-bank.md`) in 2–3 confident sentences.
3. **Likely questions** for the round, grouped: behavioral, technical/craft for this profession, situational, role-specific. For each behavioral question → the story-bank story to use + the key metric.
4. **Drills** — 2–3 exercises this profession is usually tested on (e.g. product cases for PMs, SQL/case for analysts, system design for engineers, portfolio walkthrough for designers, scenarios for nurses or teachers), in the company's context, with a strong answer outline.
5. **Questions to ask** — 5 sharp ones tied to the research.
6. **30-60-90 day sketch** (for HM/final rounds).
7. **Logistics & salary** — time, format, people; market salary range for the role/location and a negotiation stance (later rounds).

## After
- Offer a mock interview: ask questions one at a time, give candid feedback on structure, specificity and metrics.
- After the real interview: ask the user how it went, log notes in the tracker history, draft a thank-you email (send needs approval), update story-bank with any new stories.
