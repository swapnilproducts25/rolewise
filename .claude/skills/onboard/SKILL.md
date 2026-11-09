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
exactly; **bold** the lead phrase and the key result of each bullet; no new numbers, tools or claims. Add `anchors:`
(the 3-4 facts every tailored summary must keep: years and companies, the biggest result, a signature strength) and
`flagship: true` on their 5-7 strongest bullets; the CV agents (`.claude/agents/cv-writer.md`, `cv-reviewer.md`) rely on them. Then show a
6-line summary (name, latest role, years, top 3 strengths you see) and ask "Anything wrong or missing?". Fix, move on.

## 2. Ten questions: tap, don't type
Make answering effortless:
- **Use the AskUserQuestion tool for every question with likely answers** (it shows clickable options plus "Other"
  for typing). Put your best guess from the CV first, marked "(from your CV)". Ask up to 4 questions per call.
  Only if the tool isn't available, fall back to one short numbered message.
- **Facts already in the CV** (name, email, phone, city): don't ask them one by one. Show one pre-filled card
  ("Name: … · Email: … · Phone: … · Lives in: …") and ask a single question: "All correct?" with options
  "Yes" / "Change something".
- Never ask for something you can derive; say what you assumed instead ("I set your home region to UK").

Round A, about them (one AskUserQuestion call after the confirm card):
1–3. Name, email, phone, city: the pre-filled card above. The email must be the Gmail connected to Claude.
4. Right to work: options built from their citizenship/location, e.g. "UK only", "UK + EU", "Need sponsorship
   everywhere except <country>" (multi-select of regions works well).
5. Notice period: "Available now", "2 weeks", "1 month", "3 months".
Round B, about the search (one call):
6. Roles: 3–4 title sets suggested from the CV as options (multi-select), e.g. "Senior Data Analyst",
   "Analytics Manager"; "Other" for their own.
7. Places: options from their city/region plus "Remote" and "Open to relocating" (multi-select).
8. Salary floor: 3 bands around the market rate for their level and city, plus "Prefer not to say" (forms then say
   "negotiable"). State the currency.
9. CV style (its own call, after previews): build previews from THEIR CV (`python scripts/render_cv.py
   profile/master-cv.yaml "cv-styles/<Name> - <style>.docx" <style>` for classic, modern and compact), then
   `python scripts/to_pdf.py --styles` (it installs LibreOffice on a cloud machine if needed; if that fails, use the
   .docx). Upload the PDFs to their Drive "Rolewise" folder (step 3) and give one link per style; on a laptop, also
   open them. Options: Classic / Modern (Recommended) / Compact, each with a one-line description.
10. Anything to avoid (companies, industries)? Optional: options "Nothing for now" / "Yes, let me list them".

Write `profile/user.yaml`, `profile/answers.yaml` and `profile/preferences.yaml` from `profile/templates/`, filling
these answers in and keeping every default. Copy `profile/templates/cover-letter-guide.md` to `profile/` if missing.
Draft `profile/story-bank.md` with 4–6 story rows from the CV (headline + best use), marked "draft: add detail after
interviews". Create `tracker/applications.json` as `[]` if missing. Also fill `answers.yaml` `experience_years` from the CV dates (whole years, rounded down; only topics a role clearly covers, e.g. the field, its domains, key methods), then show the list once and ask "Anything to change?". Leave out anything the CV can't back up. Commit and push (web).

Close the round with: "That's all I need. You can change any of this any time: just say /profile."

## 3. Connections (Claude does the access; nothing is shared)
- **Gmail and Google Drive**: check the connectors are on (claude.ai → Settings → Connectors). If not, give the
  one-line instruction and wait. Test: search their inbox for one recent email; create a private "Rolewise" folder
  in Drive and save its id to `user.yaml` (`drive_folder_id`). Never share it.
- **LinkedIn job alerts** (recommended, 2 min, they do it in LinkedIn): suggest 2–4 saved searches from Q6/Q7 with
  "Daily, Email". Rolewise reads the alert emails; it never browses LinkedIn for them on the web route.

- **LinkedIn data** (optional, recommended; laptop): LinkedIn → Settings → Data privacy → Get a copy of your data (the
  full archive arrives by email within a day). Unzip it into this folder and run
  `python scripts/linkedin_import.py "<folder>"`: connections for referral suggestions (they stay on the laptop), past
  applications so nothing is suggested twice, and `coach/linkedin-insights.md`.

## 4. The daily run
- **Web/phone**: create a daily cloud routine. Prefer doing it yourself with `/schedule` (or the RemoteTrigger tool):
  name "Rolewise Daily", 08:00 in their timezone (convert to UTC and confirm), this repo, the Gmail and Google Drive
  connectors, allowed tools Bash, Read, Write, Edit, Glob, Grep, WebSearch, WebFetch and **Agent** (the CV writer and
  reviewer agents), prompt:
  > Run Rolewise's /daily loop for the user in profile/user.yaml. Start with `git pull --rebase` and
  > `pip install python-docx pyyaml`. Follow CLAUDE.md hard rules: never submit an application or send any message
  > except the daily briefing to the user's own email. Prepare jobs (CV, cover letter, answers) and send the briefing.
  > End with a commit and `git push`.
  If the tool isn't available, give them the same settings to paste at claude.ai/code/routines.
- **Laptop**: Windows: they paste one command:
  `schtasks /Create /TN "Rolewise Daily" /TR "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File <repo>\scripts\run_daily.ps1" /SC ONIDLE /I 10 /F`
  (or `/SC ONLOGON` if they rarely leave it idle). macOS: `scripts/run_daily.sh` with a LaunchAgent (write the plist
  after they agree; they run `launchctl load …`).

## 5. Optional: Rolewise Fill (only if they have a laptop with Chrome; also run this part alone when a user says "set up Rolewise Fill")
The add-on fills application forms. It needs this folder on the laptop: `git clone` their repo (or download it as a
zip from GitHub), then `chrome://extensions` → Developer mode → Load unpacked → the `extension` folder, and run
`python scripts/build_kits.py` (the laptop run does this daily). Set `fill_addon: true`. Skip it on phone-only setups.
Then, in this order:
1. **Local helper** (one-click Skip, applied, Pause, Debrief without tap emails): ask for the add-on's ID from
   `chrome://extensions` (32 letters under "Rolewise Fill") and run `python scripts/install_native_host.py <id>`
   (a per-user Chrome setting; no admin rights). Ask them to reload the add-on.
2. **✨ Draft in forms** (optional): explain it needs their own Anthropic API key (console.anthropic.com → Billing,
   then API keys), billed separately from their Claude plan, a fraction of a cent per answer. They paste it on the
   add-on's options page themselves; never ask for the key in chat.
3. Show the three ways to fill: a job in the add-on's queue; LinkedIn Easy Apply (click Easy Apply, then Fill this
   step on each step); any other form via the icon → **Fill this page** (Alt+Shift+F).

## 6. First results
Run the `discover` skill once (small: 10–15 roles), then render and send a first briefing to their email
(`scripts/render_briefing.py`, with `"first_briefing": true` in the JSON so it includes the Rolewise Fill tip). Tell them what happens tomorrow and what they'll do: read the briefing, tap buttons,
and apply (with Rolewise Fill, or by opening the job and uploading the CV from the Drive link). Point to `/profile`.
