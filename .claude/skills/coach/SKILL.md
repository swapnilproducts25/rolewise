---
name: coach
description: Weekly job-search review and coaching — funnel analysis, what's working, positioning and CV feedback, and a short list of high-leverage actions (networking, LinkedIn profile, skills, content, gap narrative). Use for "how am I doing", "what should I improve", or weekly.
---

# Weekly coaching review → `coach/weekly-<YYYY-MM-DD>.md`

## 1. Diagnose with data
- `tracker.py stats` and the full tracker: applications this week vs. target (aim 15–25 quality applications/week), response rate, interview rate, by source/region/level/domain/tailoring level.
- Benchmarks (rough): response 10–20% cold, 30%+ with referral; if <5% after 30+ applications → positioning/CV problem, not volume.
- Where does the funnel break? (no responses → CV/targeting/channel; screens but no onsites → pitch/story; onsites but no offers → case/fit/negotiation.)
- Compare against last week's plan in `coach/log.md`: what got done.

## 1b. Run the learning loop (`coach/learnings.md`)
- For each active experiment whose check date has passed: compute the metric with `tracker.py stats --by <field>` (channel, cv_angle, level, region, cover_letter), compare with the hypothesis, and log the result with n. Decide: keep, change, or stop. Say plainly when n is too small to conclude.
- Read `applications/*/debrief-*.md` since last week: recurring weak spots become prep/story-bank work.
- If something isn't working, start at most **one or two** new experiments: name the change, why the data suggests it, the metric and a check date 10–14 days out. Implement the change in the relevant file (preferences, CV angle defaults, cover-letter guide, discover filters) and note the commit.
- Make sure every new application gets its experiment fields set (`--set cv_angle=… channel=… level=… region=… cover_letter=…`).

- If `coach/linkedin-insights.md` exists (from `scripts/linkedin_import.py`), use it: application volume and agency share
  before Rolewise, repeat applications, and profile-vs-CV differences to fix.

## 2. Recommend — max 5 actions for the week, ranked by impact
Draw from (pick what the data supports, be specific):
- **Referrals & network:** list 5–10 named people (former colleagues from the CV's employers, alumni of its schools, at target companies) to reconnect with; draft messages (send needs approval). Referrals usually beat cold applications several-fold.
- **Recruiters:** recruiters and agencies specialising in the user's field and places, worth contacting.
- **LinkedIn profile:** headline, About, Open-to-Work settings, featured work — draft concrete text; edits need approval.
- **Positioning:** sharpen the one-line narrative and any story that needs framing (career gap, short tenure, career change), using `story-bank.md`.
- **Visibility:** 1 LinkedIn post idea/week from real work (real results and lessons) — draft it.
- **Skills/proof:** only gaps that recur in target JDs (e.g. a certification, a tool, people-management evidence for lead roles).
- **Market moves:** under-explored segments/companies that fit the profile.

## 3. Write it up
`coach/weekly-<date>.md`: scorecard, diagnosis (3 bullets), this week's 5 actions (with drafts attached), what to stop doing. Append a 3-line summary + the action list to `coach/log.md` so next week can check follow-through.
Be direct and encouraging; no generic advice that ignores the data.
