#!/bin/bash
# Rolewise daily laptop run (macOS/Linux). Started by a LaunchAgent (at login + hourly); runs at most once a day.
# Same behaviour as run_daily.ps1: run_mode laptop = full /daily here; cloud = only laptop-only work.
cd "$(dirname "$0")/.." || exit 1
mkdir -p logs
stamp=$(date +%F)
done_file="logs/laptop-$stamp.done"
[ -f "$done_file" ] && exit 0

py=$( [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3 )
claude_bin=$(command -v claude || echo "$HOME/.local/bin/claude")
mode=$($py -c "import yaml;print((yaml.safe_load(open('profile/user.yaml')) or {}).get('run_mode','laptop'))")

if [ "$mode" = "cloud" ]; then git pull --rebase --autostash >> logs/git.log 2>&1; fi
# Make every ready job submission-ready for Rolewise Fill (PDFs + kits live on this laptop).
ids=$($py -c "import json;print(' '.join(j['id'] for j in json.load(open('tracker/applications.json')) if j['status'] in ('ready','preparing')))")
[ -n "$ids" ] && { $py scripts/to_pdf.py $ids; $py scripts/build_kits.py; } >> logs/kits.log 2>&1

if [ "$mode" = "cloud" ]; then
  prompt="This is the Rolewise LAPTOP run (Chrome available, the user is away). The cloud routine already did today's /daily. Do only laptop work: LinkedIn/Workday/logged-in tasks with Claude in Chrome, and the daily skill's step 5b laptop part. Supported-form applications wait in Rolewise Fill's Ready queue. Then update the tracker, note a 'Laptop run' section in today's briefing file, and commit."
else
  prompt="/daily This is the scheduled laptop run (run_mode: laptop) and the user's go-ahead for today. Do the whole daily loop, including the step 5b laptop part, send the briefing email, and commit if this folder is a git repo."
fi

"$claude_bin" -p "$prompt" --permission-mode auto --chrome > "logs/laptop-$stamp.md" 2>&1 && touch "$done_file"
if [ -d .git ]; then git add -A && git commit -qm "Laptop run $stamp" >> logs/git.log 2>&1; [ "$mode" = "cloud" ] && git push >> logs/git.log 2>&1; fi
