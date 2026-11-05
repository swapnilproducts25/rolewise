---
name: tailor
description: Decide whether the user's CV needs tailoring for a specific job and, if so, build a tailored .docx from master-cv.yaml without inventing facts. Use for "tailor my CV for <job>", or as part of /apply.
argument-hint: <job-id>
---

# Tailor CV for a job

Inputs: `applications/<id>/jd.md`, `profile/master-cv.yaml`, `profile/story-bank.md`.

## 1. Analyse fit → `applications/<id>/fit.md`
- Extract from the JD: must-haves, nice-to-haves, top 8–12 keywords/phrases (exact wording the ATS will look for), seniority signals, domain.
- Map each must-have to evidence (bullet ids from master CV / story-bank). Mark gaps honestly.
- Decide the **tailoring level**:
  - **None** — master CV already leads with the right evidence and covers ≥80% of keywords. Use the master CV.
  - **Light** — new headline/summary + reorder bullets + skills re-ordering. (Most common.)
  - **Deep** — also reword bullets to mirror JD language, hide less relevant roles/bullets (e.g. InfoCepts, strategist detail), reorder sections.
- Write the reasoning in `fit.md` (keywords covered before/after, gaps, interview risks).

## 2. Build (only if Light or Deep)
- The CV look is set by `cv_layout` in `profile/user.yaml`: `template` = the user's own Word template (`profile/cv-template*.docx`), or `classic` / `modern` / `compact`. Never change the look per job. Mark bold with `**...**`: a bold lead phrase plus bold key results.
- **Length rules (the CV must fit on 2 pages):** summary of 4 lines or fewer (about 420 characters); each bullet 2 lines or fewer (210 characters or fewer, not counting `**`); each skills line 1 line or fewer (about 115 characters). Check before building.
- Copy master to `applications/<id>/cv.yaml` and edit:
  - `headline`: mirror the JD title where truthful (e.g. "Senior Data Analyst — Pricing & Forecasting").
  - `summary`: aimed at this role, using JD language, only facts from the master CV. Keep it comprehensive (company-by-company impact plus strengths). Never copy phrasing from notes written for another application (anything in `profile/reference/`); use them only as a source of facts.
  - Reorder bullets within each role so the most relevant comes first; reword to echo JD terminology. Keep every metric exactly as in master.
  - `hide: true` on low-relevance bullets to keep it to 2 pages.
  - Skills: reorder/rename to match JD wording (only skills already evidenced).
  - Bullets with a `caution` key: use their `safe_text`, never the original `text`, unless master-cv.yaml has since been updated to drop the caution.
  - If `profile/reference/` holds extra notes the user has approved, they may supply detail for rewording a bullet, **never a number or claim marked [VERIFY] or [ADD]**. Note any such use in `fit.md`.
- **Truth check before building** — diff every changed bullet against its master id: same facts, same numbers, no new tools/claims. If a JD requirement could be covered by something not in the files, ask the user and add it to master/story-bank once confirmed.
- Build: write `applications/<id>/tailor.yaml` (set `variant: <name>` when `master-cv.yaml` has a contact variant for the job's region, e.g. `eu`) and run `.venv/Scripts/python scripts/tailor_cv.py <id>`. It applies the variant to the contact line. **Check the header** of the built CV matches the job region.
- Then make the files submission-ready: `.venv/Scripts/python scripts/build_cover_letter.py <id>` (if a cover letter was written), `.venv/Scripts/python scripts/to_pdf.py <id>` (PDF versions; on a cloud machine it installs LibreOffice once per session, and if that fails the .docx is used) and `.venv/Scripts/python scripts/build_kits.py <id>` (Rolewise Fill kit, prefers the PDFs).
- **Draft the form's own questions** (Greenhouse and Lever publish them): run `python scripts/form_questions.py <id>`. For every
  question it lists as open, add an answer to `applications/<id>/kit.yaml` under `questions:` as
  `{match: [2-3 distinctive lowercase words from the label], value: "...", review: true}`. Free text: 60-120 words, first
  person, facts only from `master-cv.yaml` / `story-bank.md`, same voice rules as the cover letter. Yes/No and choices:
  pick the option the CV supports and add a `# why` comment. A question needing a fact the files don't hold (a personal
  preference, a legal declaration not in answers.yaml) is an open item: leave it out and ask. Optional questions about
  the company's own values or culture: answer only from the JD or the company page you actually read, else skip.
  Then rebuild the kit (`scripts/build_kits.py <id>`); the add-on outlines drafted answers in blue for checking.
- Update tracker: `tracker.py update <id> --status preparing --set cv_file="applications/<id>/<file_prefix> - CV - <Company>.docx"`

## 3. Optional cover letter
Only if the application asks for one or it's a ★ role: `applications/<id>/cover-letter.md`, ≤250 words, specific to the company (1 product insight about them, 2 proof points from story-bank, 1 line on why now). No clichés.

## 4. Report
Tailoring level + why, top 3 changes, keyword coverage before→after, any gap questions for the user.
