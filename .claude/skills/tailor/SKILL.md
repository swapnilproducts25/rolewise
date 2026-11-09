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
- Write the reasoning in `fit.md` (keywords covered, gaps, interview risks). Don't decide the tailoring here.

## 2. Draft and review the CV (two agents)
The CV rules live in `cv-principles.md` (this folder). Two separate agents apply them, so the one judging the CV
is not the one who wrote it:
1. **Draft:** run the `cv-writer` agent (Agent tool) with: "Tailor the CV for job `<id>`." It writes
   `applications/<id>/tailor.yaml`, including a `why` line per change, or decides no change is needed.
2. **Review:** run the `cv-reviewer` agent with: "Review the tailored CV for job `<id>`." It writes
   `applications/<id>/cv-review.md` with PASS or FAIL and must-fix points.
3. **FAIL →** run `cv-writer` again ("Revise job `<id>` after the review"), then `cv-reviewer` once more.
   Still FAIL after two rounds → build the **master CV unchanged** (keep only `variant` in tailor.yaml) and note it
   in `fit.md`. The master is always a safe CV; a weak tailoring is not.
4. A question either agent raises (a fact the files don't hold) → don't guess; list it for the user in the run report.
Agents unavailable (e.g. a session without the Agent tool) → do both roles yourself in two separate passes: draft,
then re-read cv-principles.md and review the draft against the rubric in `.claude/agents/cv-reviewer.md` as if
someone else wrote it.

## 3. Build
- The CV look is set by `cv_layout` in `profile/user.yaml`: `template` = the user's own Word template (`profile/cv-template*.docx`), or `classic` / `modern` / `compact`. Never change the look per job.
- **Length (2 pages):** summary ≤ 4 lines (~420 characters), bullets ≤ 210 characters without `**`, skills lines ≤ ~115 characters.
- Bullets with a `caution` key: use their `safe_text`, never the original `text`, unless master-cv.yaml has since dropped the caution.
- Build: run `.venv/Scripts/python scripts/tailor_cv.py <id>`. It applies the variant to the contact line. **Check the header** of the built CV matches the job region.
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

## 4. Optional cover letter
Only if the application asks for one or it's a ★ role: `applications/<id>/cover-letter.md`, ≤250 words, specific to the company (1 product insight about them, 2 proof points from story-bank, 1 line on why now). No clichés.

## 5. Report
Tailoring level + why (from tailor.yaml `why`), the reviewer's verdict and scores, any questions for the user.
