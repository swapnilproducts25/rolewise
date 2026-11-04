# Rolewise daily laptop run (Windows). Registered in Task Scheduler (ON IDLE and/or ON LOGON); runs at most once a day.
# profile/user.yaml run_mode:
#   cloud  - the Claude routine does /daily in the cloud; this run only does what needs the laptop
#            (Chrome-only tasks, referral drafting). Skips when there's nothing for it.
#   laptop - no cloud: this run does the full /daily loop (briefing included).
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
New-Item -ItemType Directory -Force "logs" | Out-Null
$stamp = Get-Date -Format "yyyy-MM-dd"
$done = "logs\laptop-$stamp.done"
if (Test-Path $done) { exit 0 }

$py = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } else { "python" }
$claude = if (Test-Path "$env:USERPROFILE\.local\bin\claude.exe") { "$env:USERPROFILE\.local\bin\claude.exe" } else { "claude" }
$mode = & $py -c "import yaml;print((yaml.safe_load(open('profile/user.yaml',encoding='utf-8')) or {}).get('run_mode','laptop'))"
$git = (Test-Path ".git") -and ($mode -eq "cloud")
if ($git) { git pull --rebase --autostash *>> "logs\git.log" }

# Make every ready job submission-ready for Rolewise Fill (PDFs need LibreOffice, kits live on this laptop).
$readyIds = & $py -c "import json;print(' '.join(j['id'] for j in json.load(open('tracker/applications.json',encoding='utf-8')) if j['status'] in ('ready','preparing')))"
if ($readyIds) { & $py scripts/to_pdf.py $readyIds.Split(" ") *>> "logs/kits.log"; & $py scripts/build_kits.py *>> "logs/kits.log" }

if ($mode -eq "cloud") {
  # Nothing for Chrome to do and no referral to draft? Skip without spending a run.
  $queue = & $py -c "import json;print(sum(1 for j in json.load(open('tracker/applications.json',encoding='utf-8')) if j['status'] in ('ready','preparing')))"
  if ([int]$queue -eq 0 -and -not (Test-Path 'profile\connections.csv')) { New-Item -ItemType File $done | Out-Null; exit 0 }
  $prompt = "This is the Rolewise LAPTOP run (Chrome available, the user is away from the keyboard). The cloud routine already did today's /daily. Do only work that needs this laptop: LinkedIn/Workday/logged-in tasks with Claude in Chrome (one tab at a time), and the daily skill's step 5b laptop part (referrals.py + one drafted referral message, if profile/connections.csv exists). Applications on supported forms are NOT submitted here: they wait in Rolewise Fill's Ready queue for the user. If Chrome is hidden or typing doesn't land, stop and note it. Then update the tracker, add a short 'Laptop run' section to today's coach/briefings file, and commit."
} else {
  $prompt = "/daily This is the scheduled laptop run (run_mode: laptop) and the user's go-ahead for today. Do the whole daily loop, including the step 5b laptop part, send the briefing email, and commit if this folder is a git repo."
}

if (-not (Get-Process chrome -ErrorAction SilentlyContinue)) { Start-Process "chrome.exe"; Start-Sleep -Seconds 15 }
$log = "logs\laptop-$stamp.md"
& $claude -p $prompt --permission-mode auto --chrome *>&1 | Out-File -FilePath $log -Encoding utf8
if ($LASTEXITCODE -eq 0) { New-Item -ItemType File $done -Force | Out-Null }

if (Test-Path ".git") { git add -A; git commit -q -m "Laptop run $stamp" *>> "logs\git.log"; if ($git) { git push *>> "logs\git.log" } }
