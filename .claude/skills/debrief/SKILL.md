---
name: debrief
description: Capture a post-interview debrief while it's fresh — what was asked, what landed, what didn't, interviewer signals — then turn it into lessons for the story bank, the next prep pack and the learning log. Use after any interview or recruiter call ("the interview happened", "how did it go", "debrief").
argument-hint: <job-id>
---

# Debrief → `applications/<id>/debrief-<YYYY-MM-DD>.md`

## 1. Interview the user (short, one message, max 6 questions)
Ask only what isn't already known:
1. Round, interviewer(s) and their roles, length.
2. Questions asked, as close to verbatim as they remember (technical/craft, behavioural, case, situational).
3. Which answers felt strong, which felt weak or got pushback, and why they think so.
4. Signals: interest, follow-ups, time checks, "what questions do you have", next steps or timeline mentioned.
5. Anything they wish they'd said.
6. Their gut feel 1–5.

## 2. Analyse candidly
- Separate signal from anxiety: a flat interviewer is weak evidence; specific pushback, cut-short answers or no next-step talk are stronger.
- For each weak answer: the likely gap (content, structure, evidence, level/seniority framing, technical depth) and a better answer built only from `master-cv.yaml` / `story-bank.md`.
- Score the round: likely pass / coin flip / likely no, with one line of reasoning.

## 3. Feed the system
- Write the debrief file (questions, analysis, improved answers, score).
- `story-bank.md`: add or sharpen stories that were needed; note questions that recur across companies.
- `coach/learnings.md` → "Interview observations": one line per pattern (e.g. "CTOs probe technical depth of AI work").
- Tracker: `update <id> --note "debrief: <score>, <1-line>" --set last_round=<round> gut=<1-5>`; set `next-action`/`next-date` (thank-you note today, check-in in 3–5 working days).
- Draft a short thank-you note to the interviewer(s) if appropriate; sending needs the user's yes.
