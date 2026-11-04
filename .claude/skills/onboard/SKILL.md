---
name: onboard
description: First-time setup of Rolewise for a new user — read their CV, ask ~10 short questions, create their profile, pick a CV style, connect Gmail/Drive, set up the daily run (cloud routine, or laptop), optionally install Rolewise Fill, and send a first briefing. Use for "set me up", "/onboard", or when profile/user.yaml has no name yet.
---

# Onboard a new user (target: 20–30 minutes, most of it hands-off)

Principles: ask only what's needed to start; default everything else (from `profile/templates/`); every answer can be
changed later with `/profile`. Be warm and brief, plain words, no jargon. One message per step. Never invent facts.

## 0. Where are we running?
- **Web/phone (default)**: a claude.ai/code session on their own private GitHub copy (a cloud machine; no Chrome,
  no LibreOffice by default). Set `run_mode: cloud`, `fill_addon: false`. Run `pip install python-docx pyyaml` and
  use `python` for every script.
- **Laptop**: Claude Code on their own computer. Run `python scripts/check_setup.py` and fix what it flags (it prints
  the exact command for each). Set `run_mode: laptop`.
If `profile/user.yaml` already has a name, this is a re-run: offer `/profile` instead.

## 1. Their CV (the source of truth)
Ask for their current CV and LinkedIn URL. Ways to share it, easiest first: attach it to the chat; or put it in their
Google Drive and tell you the file name (read it with the Drive connector); or paste the text.
Write `profile/master-cv.yaml` in the schema of `scripts/render_cv.py` (name, headline, contact, summary,
experience[{id, title, company, location, dates, bullets[{id, text}]}], projects, education, awards,
skills[{label, items[]}], plus `variants` only if they use a different contact line per region). Rules: copy facts
exactly; **bold** the lead phrase and the key result of each bullet; no new numbers, tools or claims. Then show a
6-line summary (name, latest role, years, top 3 strengths you see) and ask "Anything wrong or missing?". Fix, move on.

## 2. Ten questions (two short rounds; pre-fill what the CV already answers and just ask to confirm)
Round A, about them:
1. Name and email for the daily briefing (default: from the CV; must be the Gmail connected to Claude).
2. Phone number(s), international format. A second number for another region is optional.
3. Where do you live now (city, country)?
4. Citizenship(s) and any visa or residency. Which regions can you work in without sponsorship?
5. Notice period / earliest start date.
Round B, about the search:
6. Which roles? Titles and seniority (suggest 3–5 from the CV; they can edit).
7. Where? Cities, countries, remote. Open to relocating?
8. Salary floor per region (or "prefer not to state": forms then say "negotiable").
9. CV style: build previews from THEIR CV (`python scripts/render_cv.py profile/master-cv.yaml
   "cv-styles/<Name> - <style>.docx" <style>` for classic, modern and compact). On the web, upload the three to their
   Drive "Rolewise" folder (step 3) and give the links; on a laptop, convert with LibreOffice and open them.
   Ask them to pick one. Default: modern.
10. Anything Rolewise should never do or always avoid (companies, industries, words)? Optional.

Write `profile/user.yaml`, `profile/answers.yaml` and `profile/preferences.yaml` from `profile/templates/`, filling
these answers in and keeping every default. Copy `profile/templates/cover-letter-guide.md` to `profile/` if missing.
Draft `profile/story-bank.md` with 4–6 story rows from the CV (headline + best use), marked "draft: add detail after
interviews". Create `tracker/applications.json` as `[]` if missing. Commit and push (web).

Close the round with: "That's all I need. You can change any of this any time: just say /profile."

## 3. Connections (Claude does the access; nothing is shared)
- **Gmail and Google Drive**: check the connectors are on (claude.ai → Settings → Connectors). If not, give the
  one-line instruction and wait. Test: search their inbox for one recent email; create a private "Rolewise" folder
  in Drive and save its id to `user.yaml` (`drive_folder_id`). Never share it.
- **LinkedIn job alerts** (recommended, 2 min, they do it in LinkedIn): suggest 2–4 saved searches from Q6/Q7 with
  "Daily, Email". Rolewise reads the alert emails; it never browses LinkedIn for them on the web route.

## 4. The daily run
- **Web/phone**: create a daily cloud routine. Prefer doing it yourself with `/schedule` (or the RemoteTrigger tool):
  name "Rolewise Daily", 08:00 in their timezone (convert to UTC and confirm), this repo, the Gmail and Google Drive
  connectors, prompt:
  > Run Rolewise's /daily loop for the user in profile/user.yaml. Start with `git pull --rebase` and
  > `pip install python-docx pyyaml`. Follow CLAUDE.md hard rules: never submit an application or send any message
  > except the daily briefing to the user's own email. Prepare jobs (CV, cover letter, answers) and send the briefing.
  > End with a commit and `git push`.
  If the tool isn't available, give them the same settings to paste at claude.ai/code/routines.
- **Laptop**: Windows: they paste one command:
  `schtasks /Create /TN "Rolewise Daily" /TR "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File <repo>\scripts\run_daily.ps1" /SC ONIDLE /I 10 /F`
  (or `/SC ONLOGON` if they rarely leave it idle). macOS: `scripts/run_daily.sh` with a LaunchAgent (write the plist
  after they agree; they run `launchctl load …`).

## 5. Optional: Rolewise Fill (only if they have a laptop with Chrome)
The add-on fills application forms. It needs this folder on the laptop: `git clone` their repo (or download it as a
zip from GitHub), then `chrome://extensions` → Developer mode → Load unpacked → the `extension` folder, and run
`python scripts/build_kits.py` (the laptop run does this daily). Set `fill_addon: true`. Skip it on phone-only setups.

## 6. First results
Run the `discover` skill once (small: 10–15 roles), then render and send a first briefing to their email
(`scripts/render_briefing.py`). Tell them what happens tomorrow and what they'll do: read the briefing, tap buttons,
and apply (with Rolewise Fill, or by opening the job and uploading the CV from the Drive link). Point to `/profile`.
