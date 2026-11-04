---
name: negotiate
description: Offer and negotiation support — market benchmarks, offer comparison, counter-offer strategy and scripts, competing-offer leverage and deadline handling. Use when an offer, salary discussion, recruiter "what are your expectations" call, or verbal offer comes up.
argument-hint: <job-id>
---

# Negotiate → `applications/<id>/negotiation.md`

Never send anything without the user's yes. Never invent competing offers or numbers.

## 1. Gather
- The offer or the question being asked: base, bonus, equity (type, vesting, valuation basis), sign-on, relocation, visa/housing (UAE), notice, title/level, start date, deadline.
- The user's floors and targets from `profile/answers.yaml` (compensation) and any updates they give; other live processes in the tracker (stage, timing).

## 2. Benchmark
- Market ranges for the role, level and city (search current sources: levels.fyi, Glassdoor, recruiter salary guides, published bands). Cite sources and dates; say when data is thin.
- UAE specifics: tax-free, housing/schooling allowances, end-of-service gratuity. EU specifics: gross vs net, 30% ruling (NL), relocation packages.

## 3. Strategy
- Recommend the ask (number and components) and the walk-away, with reasoning. Prefer anchoring on scope/level before cash.
- Use real leverage only: other processes at a similar or later stage, scarce skills from the CV.
- Script the conversation: opening, the ask, responses to the 3 most likely pushbacks, how to buy time if a deadline is tight.

## 4. Record
Write `negotiation.md`; tracker `update <id> --note "offer: <summary>; ask: <summary>"`; after it closes, record the outcome and what moved the number in `coach/learnings.md`.
