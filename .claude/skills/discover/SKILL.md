---
name: discover
description: Find new job openings matching the user's profile across LinkedIn, job boards and company career pages, score fit, dedupe against the tracker and produce a shortlist. Use for "find jobs", "any new roles", or as part of /daily.
---

# Discover jobs

Read first: `profile/preferences.yaml`, `profile/master-cv.yaml` (skim), and `scripts/tracker.py list` to know what's already tracked.

## 1. Search (aim for 20–40 fresh candidates every day, posted in the last ~14 days; never skip a day)

**First, LinkedIn job alerts from Gmail (safe: no LinkedIn browsing):** search `from:jobalerts-noreply@linkedin.com newer_than:3d -label:rolewise-done`. Each alert lists roles (title, company, location, a `linkedin.com/comm/jobs/view/<id>` link). For each: normalise the link to `https://www.linkedin.com/jobs/view/<id>`, skip if `tracker.py exists --url` finds it, score fit as below, and add it (`--source linkedin-alert`). Label the alert `rolewise-done`. Saved searches are set up by the user on LinkedIn (see coach notes); if no alerts arrive for 3 days, put a one-line reminder in the briefing.

**Then company career pages (best channel):** `.venv/Scripts/python scripts/ats_scan.py scan` polls public Greenhouse, Lever and Ashby feeds for every company in `profile/target-companies.yaml`. Results are filtered by `profile/preferences.yaml` (a `scan:` block if present, else `target_titles` and `locations`) and to jobs not already tracked. With no `profile/target-companies.yaml` yet, offer to build one from the user's target and `market_signal` companies. Add new companies with `ats_scan.py discover <slug> ...`. Fetch a job's description with `ats_scan.py jd <tracker id>`. These roles are often fresher and less crowded than LinkedIn. Then supplement with LinkedIn and the job boards below.
Use the Chrome extension (the user's logged-in session) and WebSearch. Rotate sources across days.

**LinkedIn: what works (learned 2026-10-29):**
- The Chrome tab Claude uses is a *hidden* tab, so LinkedIn's lazy-loaded result lists don't render past ~7 cards. Instead, in a linkedin.com tab, `fetch()` the guest search endpoint `/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=..&location=..&f_TPR=r604800[&f_WT=2]&start=0|10|20`, and parse with **regex, not DOMParser** (LinkedIn's Trusted Types CSP blocks DOMParser). Pause about 1.5s between calls. Remote = `&f_WT=2`.
- Tool output truncates around 1,000 characters, so keep results in a `window.` variable and print them in slices. Page navigations wipe `window` state.
- Full job descriptions: `.venv/Scripts/python scripts/fetch_jd.py <dir> <job_id> ...` (public endpoint, 3s spacing; on HTTP 429 wait and retry later).
- Already applied? Check LinkedIn's Job tracker (`https://www.linkedin.com/jobs-tracker/?stage=applied`, 10 per page, click "Next") and collect `/jobs/view/<id>` links. Postings ≤7 days old only need the first 2–4 pages checked.

**LinkedIn Jobs** (human pace, ≤40 job views/day; see CLAUDE.md):
- `https://www.linkedin.com/jobs/search/?keywords=<title>&location=<place>&f_TPR=r604800` (past week; `r86400` = 24h)
- Titles: `target_titles` from preferences (plus `adjacent_roles.examples` if enabled)
- Places: the `locations` in preferences (names and places); remote: add `&f_WT=2`
- Prefer reading the results list + job detail pane; note applicant count and "Easy Apply".

**Job boards:** `boards` in preferences. If empty, pick the 3–5 strongest boards for the user's field and places (e.g. Indeed and the national board; field-specific ones such as Dice for tech, NHS Jobs for UK health, eFinancialCareers for finance; WeWorkRemotely/RemoteOK for remote) and save them to `boards`.
**ATS boards via WebSearch** (high signal, often not on LinkedIn):
`site:boards.greenhouse.io OR site:jobs.lever.co OR site:jobs.ashbyhq.com "<target title>" (<place> OR <place> OR Remote)`
**Target companies:** check career pages of every company in `preferences.target_companies`.
**Market signal:** companies in `market_signal` (preferences) are actively hiring in the user's market — search their career pages too. Add new ones as you spot them hiring repeatedly.

## 2. Filter and score
- **Matching policy:** follow `fit_scoring.thresholds.matching_policy` in preferences.yaml. Be inclusive. Gaps lower the score, and only hard blockers skip a role.
- Skip: titles in `exclude.keywords`, excluded companies, duplicates (`tracker.py exists --url ... ` / `--company --title`), roles needing a language the user doesn't list (e.g. "fluent German required"), suspected scams (see CLAUDE.md rule 6).
- **Check what kind of "product" it is.** A title with "Product" can mean a physical product, menu, category or
  merchandising job (e.g. a food company's "Product Strategy Manager" who tastes and tests recipes). If the JD says it
  is not a tech/digital product role, or the work is about physical goods, culinary, retail category or brand
  management, score it as adjacent at most (fit <= 55) and say so in the summary, unless the user's targets include it.
- Read the full JD for each survivor. Score with `fit_scoring` weights from preferences (0–100). Be honest: a director role at a 2000-person org needing 5+ yrs people management is a stretch — say so but don't auto-reject; flag as `stretch`.
- **Pay** (the final score weighs it): if the JD states a salary, record it (`--set "salary=EUR 95-110k"`). If not,
  look up a market estimate for that company, level and city (levels.fyi, Glassdoor; one search) and record the
  midpoint in EUR per year: `--set salary_estimate_eur=105000`. Skip it rather than guess when nothing credible shows.
- Score the role itself (`fit_base`): don't add or subtract for the user's location preference or pay; `scripts/fit.py`
  adds those (Dubai/UAE first, Europe second, India third, then pay against the floor) after recording.
- Work authorization: check `answers.yaml` / `preferences.yaml` for where the user can work without sponsorship; elsewhere, still include but note "sponsorship?".

## 3. Record
For each job with score ≥ `thresholds.shortlist`:
```
.venv/Scripts/python scripts/tracker.py add --company "..." --title "..." --location "..." --work-mode hybrid \
  --url "<canonical job URL>" --source linkedin --fit 78 --summary "<1 line: why it fits / main gap>" --status shortlisted
```
For LinkedIn jobs, also record how they're applied to: `--set easy_apply=yes` when the alert or job page says "Easy Apply", `easy_apply=no` when it sends you to the company's site (then set `apply_url` to that site if you can see it). Save the JD to `applications/<id>/jd.md` (title, company, location, URL, date seen, full text). Then run `.venv/Scripts/python scripts/fit.py` (final fit = role fit + location preference + pay). Jobs below threshold: don't add (keep the tracker clean) unless notable.

## 4. Report to the user
A compact table sorted by fit: fit | company | role | location/mode | posted | applicants | Easy Apply? | one-line why/gap.
Mark ≥ `priority` jobs with ★ and suggest: apply today + whether a referral is worth seeking (check if the user has 1st/2nd-degree connections there — only look, never message).
End with: "Which ones should I prepare? (e.g. 'all ★', '1,3,5', 'all')".
