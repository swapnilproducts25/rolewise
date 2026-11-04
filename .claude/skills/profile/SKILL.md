---
name: profile
description: Show or change anything Rolewise knows about the user — contact details, work authorisation, target roles and places, salary floors, CV style, standard form answers, things to avoid — or add new standing answers. Use for "/profile", "change my …", "update my salary floor", "add an answer", "what do you have on me".
---

# Profile: view and edit in plain words

Files: `profile/user.yaml` (identity, CV style, run mode), `profile/answers.yaml` (form answers),
`profile/preferences.yaml` (what to search for), `profile/master-cv.yaml` (CV facts), `profile/story-bank.md`.

- **"/profile" alone** → a short summary card, one line per topic: name and email · phone(s) · lives in ·
  can work in (no sponsorship) · notice · target roles · places · salary floors · CV style · form defaults
  (office days, remote, WhatsApp, consents) · things to avoid. End with: "Tell me what to change, in your words."
- **A change** ("my notice period is now 2 weeks", "add Amsterdam", "switch to the compact CV") → edit the right
  file, keeping comments and other values; repeat back the one line that changed. CV style changes apply to the next
  CV built; offer to rebuild the CVs of `ready` jobs (`scripts/tailor_cv.py <ids>`, then `scripts/to_pdf.py`,
  `scripts/build_kits.py`).
- **A new standing answer** ("always say I heard about jobs on LinkedIn", "my pronouns are …") → add it under
  `standard_form_answers` (or the matching section), with a short comment, then rebuild kits (`scripts/build_kits.py`).
- **CV facts** ("add my new certification", "I also led X") → update `master-cv.yaml` only with what they state;
  never embellish. Ask for the missing date or number rather than guessing.
- Facts change, so do kits: after any edit that affects forms, run `scripts/build_kits.py` so Rolewise Fill uses it.
