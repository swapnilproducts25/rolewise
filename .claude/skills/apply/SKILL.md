---
name: apply
description: Prepare and submit a job application via Chrome for a tracked job — fills the form using profile answers, the tailored CV and a cover letter, then submits when nothing is open for the user, or stops for their approval when something is. Use for "apply to <job>" or after shortlist approval.
argument-hint: <job-id> [<job-id> ...]
---

# Apply

Submission rule: follow CLAUDE.md rule 1. If it gives standing permission to submit, **submit yourself when nothing is open; stop and ask when anything is.** If it doesn't (the default for new users), never click Submit: prepare everything, set the job `ready`, and let the user submit with Rolewise Fill.

"Open" means any of these:
- an answer not covered by `profile/answers.yaml` or the profile files (TODO values count as open), or a free-text answer that makes a claim beyond `master-cv.yaml` / `story-bank.md`;
- a CV/cover-letter fact you couldn't trace to the source files;
- salary, location, work authorization or start date that differs from the defaults in answers.yaml;
- anything unusual: assessments, video questions, legal/background-check declarations, unexpected fees or ID requests (→ scam check), consent text that goes beyond standard data processing/retention;
- the cover letter departs from the approved sample's pattern (`profile/cover-letter-sample.md`; with no sample yet, the first letter is always open: ask the user to approve it as the sample).

## 1. Prepare (batch-friendly — do all requested jobs first)
For each job id:
1. If no CV decision yet, run the `tailor` workflow. CV file = tailored `.docx` or the master CV (build `applications/_master/<file_prefix> - CV.docx` from `profile/master-cv.yaml` if missing).
2. Open `apply_url` if the tracker has one, else the job URL, in a **new Chrome tab**. For Greenhouse companies with their own careers site (e.g. Stripe), the form lives at `https://job-boards.greenhouse.io/embed/job_app?for=<board>&token=<gh_jid>`. Identify the flow: LinkedIn Easy Apply, company ATS (Greenhouse/Lever/Ashby/Workday/SmartRecruiters/Taleo), or email.
3. Login/account: create an account only via "Sign in with Google" as the user's email from `profile/user.yaml` (log it in the tracker note). Password, SMS code or payment needed → stop, ask the user.
4. Fill every field:
   - Standard fields → `profile/answers.yaml`, including `standard_form_answers` and `citizenship.export_control` (these are settled, NOT open items). TODO values → open item; never guess salary or work authorization.
   - Free-text questions ("Why us?", "Describe a time…") → draft from `story-bank.md` + JD, ≤150 words unless the form says otherwise; save all to `applications/<id>/answers.md`.
   - Upload the CV via the file-upload tool.
   - Cover letter: whenever the form asks for one or offers an optional field, write it following `profile/cover-letter-guide.md` and modelled on `profile/cover-letter-sample.md`. Save it to `applications/<id>/cover-letter.md` and build a .docx if an upload is needed.
   - Diversity/EEO → per answers.yaml.
   - Standard consent / data-retention / privacy-policy boxes → tick them.
5. Re-read the whole form (values, attachments, checkboxes) before deciding.

## 2. Decide per job
- **Nothing open** → click Submit, capture the confirmation (screenshot/text), then
  `tracker.py update <id> --status applied --set date_applied=<today> --note "auto-submitted via <channel>; CV <file>; cover letter <yes/no>; answers: <short list>" --next-action "check for response / follow up" --next-date <today+7>`, and set the experiment fields: `--set cv_angle=<angle> cover_letter=<yes|no> channel=<cold|referral|recruiter|inbound> level=<senior|lead|head|director> region=<uae|eu|uk|remote>`.
- **Something open** → don't submit. `tracker.py update <id> --status ready --note "awaiting the user: <open items>"`.

## 3. Report (one message, all jobs)
- Submitted: company/role, CV used, cover letter, every non-trivial answer.
- Waiting on the user: the open items for each, with your recommendation. When they answer, finish and submit those.
- If a referral contact exists, suggest (draft only) a short note to them.

## Cloud sessions (no Claude in Chrome)
When running in a cloud session (claude.ai/code, e.g. started from a phone):
1. `python3 -m pip install --break-system-packages playwright python-docx pyyaml && python3 -m playwright install --with-deps chromium`; run every script with the same `python3` (mixing interpreters broke the first run). Don't name scripts after stdlib modules (e.g. inspect.py).
2. Only no-login ATS forms (Greenhouse, Lever, Ashby, Workable, SmartRecruiters public forms). LinkedIn Easy Apply,
   Workday and anything needing login/SMS → `tracker.py update <id> --status ready --note "phone/laptop queue: <why>"`.
3. Write a throwaway Playwright script in /tmp for the form: fill text fields, upload CV + cover letter, pick dropdown
   options by visible text, tick standard consent boxes. Upload files FIRST, wait for the page to settle, then fill.
4. Before submitting, read every field back and screenshot the form to `logs/` for the record.
5. CAPTCHA, bot challenge or "verify you are human" → stop, do NOT try to solve or bypass it; mark the job
   `ready` with note "cloud blocked by CAPTCHA — laptop/phone". Same for any error page after submit.
6. Submit only under the normal rule (nothing open). Capture the confirmation text, update the tracker, commit + push.

## Workday (and other login portals: SuccessFactors, Taleo, iCIMS)
Rolewise Fill handles Workday itself: opened from its queue (or **Fill all pages**), it clicks Apply Manually, fills
the email on the sign-in page, fills every page, clicks **Save and Continue**, and stops on **Review**. The user only
signs in (or picks Chrome's suggested password for a new account) and clicks Submit. On a laptop run without the
add-on, Rolewise does the same in Chrome (Claude in Chrome):
1. Get the real form URL: the tracker's `apply_url`, else open the posting and click its external Apply link (one LinkedIn
   page view, never Easy Apply). Save it: `tracker.py update <id> --set apply_url=<url without ?share_id…>`.
2. **Account.** Already signed in (email shown top right) → go on. Otherwise use "Sign in with Google" if offered.
   If the portal only offers email + password: open *Create Account* and fill the email; the user sets the password
   (Chrome's "Use suggested password" = one click, saved in their Google Password Manager). Rolewise never types or
   stores a password. Then open the verification email via Gmail and click its link. Log the account in the tracker
   note ("Workday account created at <tenant>"). Each employer's Workday is a separate account.
3. Fill every step, then **Save and Continue**, until the **Review** page:
   - My Information: often pre-filled from the account; check source, "worked here before", name, phone (local
     number; the country code is its own field), state/emirate/city.
   - My Experience: one entry per role from the job's `cv.yaml` (else `master-cv.yaml`): title, company,
     "City, Country" (`answers.yaml` city_country), dates, role description = that role's bullets as "• " lines with
     the ** markers removed. Education: EVERY entry in `answers.yaml` education_entries, even if the form says
     "highest level"; a school that isn't in the form's list → "Other" (as the form itself says). Certifications from
     `answers.yaml` certifications: most Workday tenants only offer a fixed issuer list; if the issuer (or "Other")
     isn't there, delete the empty entry and leave it to the CV, never pick a near match. Languages from `answers.yaml`
     languages at the level given ("highest" = the top option, "fluent" ticked). CV: the PDF (delete any .docx
     already attached first). Cover letter field → the cover letter PDF.
     **Search-list trap:** typing + Enter auto-selects the result when exactly one comes back, even a wrong one (a
     similarly named university, an unrelated certificate). After every search, read the field's selected chip; if
     it's wrong, remove it (click the chip, Delete) or delete the whole entry and add it again.
   - Application questions / disclosures → `answers.yaml` (work authorisation, sponsorship, diversity, SMS/WhatsApp
     opt-in, `ai_screening_opt_in`); privacy acknowledgement = tick.
   - Anything open (see top of this skill) → stop on that step and ask, as usual.
   Mechanics that work on Workday: fields have stable ids like `workExperience-4--jobTitle`; set text with the native
   value setter + input/change/blur events; dates (MM/YYYY): focus the month box and type `012026`; dropdowns are
   `button[aria-haspopup=listbox]` → click, then dispatch mousedown/mouseup/click on the `[role=option]`; search lists
   (school, field of study) → type, Enter, click the option; "Add Another" adds an entry.
4. At **Review**: read the whole page back, then stop. Leave the tab open on Review and
   `tracker.py update <id> --status ready --note "filled to Review on <portal>; waiting for the user's Submit click"`.
   Report it in the briefing as "one click left". After the user submits, the job is marked applied (Rolewise Fill
   toast / Inbox Applied / next track run).
   A posting that says "The page you are looking for doesn't exist" has closed → skip it as `posting-closed`.

## Failure handling
CAPTCHA, broken form, assessment links, or anything odd → stop that one, tell the user, continue with others. Never retry submit blindly (risk of duplicate applications). Respect the daily cap (~15 applications).
