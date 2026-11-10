"""The Rolewise Inbox (inbox/index.html, published as the user's private artifact; its URL is `inbox_url` in
profile/user.yaml): the ready queue with one-tap Applied / Later / Skip, the briefing's open questions, and Pause.
Taps are saved in the artifact's database; each run applies them. This replaces "tap to email yourself".

  python scripts/inbox.py export [coach/briefings/<date>.json]
      Writes inbox/current.json: ready jobs (by location, freshest first) and the briefing's cards that have
      buttons. Then Claude writes it to the artifact: ArtifactData set, collection "queue", doc_id "current",
      file_path inbox/current.json (read the doc first for if_version).
  python scripts/inbox.py apply <dir>
      <dir> = where ArtifactData list (collection "actions", out_dir) saved the taps. Applies what a script can
      (applied, skip, later, bring back, pause, resume, referral asked) through tracker.py, and prints FOR CLAUDE lines
      for the rest (send a draft, prepare, answer, submit). Ends with "DELETE: <doc ids>": delete exactly those
      action docs (one ArtifactData batch) once the FOR CLAUDE items are done.
"""
import json
import re
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_kits import freshness, group  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TRACKER = ROOT / "tracker" / "applications.json"
USER_FILE = ROOT / "profile" / "user.yaml"
SAFE = re.compile(r"^[A-Za-z0-9_.:@+-]{1,190}$")
BOOST = {"new": 8, "week": 4, "old": -6}   # same order as the add-on's queue
VERBS = {"APPLIED", "SKIP", "WAIT", "RESTORE", "PAUSE", "RESUME", "SEND", "PREPARE", "ANSWER", "SUBMIT"}


def tracker(*args):
    return subprocess.run([sys.executable, str(ROOT / "scripts" / "tracker.py"), *args], cwd=ROOT,
                          capture_output=True, text=True, encoding="utf-8")


def export(briefing=None):
    from render_briefing import job_files   # links to the CV and cover letter on the user's GitHub copy
    jobs = json.loads(TRACKER.read_text(encoding="utf-8"))
    today = date.today().isoformat()
    ready = [j for j in jobs if j["status"] == "ready" and (j.get("snooze_until") or "") <= today]
    ready.sort(key=lambda j: -((j.get("fit_score") or 0) + BOOST.get(freshness(j)["urgency"], 0)))
    def row(j):
        f = freshness(j)
        files = dict(job_files(j["id"]))
        why = re.sub(r"^(ADJACENT|STRONG|STRETCH)\.\s*", "", j.get("fit_summary") or "", flags=re.I)
        return {"id": j["id"], "company": j["company"], "title": j["title"], "location": j.get("location") or "",
                "group": group(j), "fit": j.get("fit_score"), "why": why[:200], "age": f["age"],
                "urgency": f["urgency"], "url": j.get("apply_url") or j.get("url") or "",
                "cv": files.get("CV", ""), "letter": files.get("Cover letter", "")}
    out = [row(j) for j in ready]
    # Shortlisted, not prepared yet: shown as "Coming next" so the queue isn't capped at what's ready today.
    prefs = yaml.safe_load((ROOT / "profile" / "preferences.yaml").read_text(encoding="utf-8")) or {}
    rank = lambda j: -((j.get("fit_score") or 0) + BOOST.get(freshness(j)["urgency"], 0))
    upcoming = [row(j) for j in sorted((j for j in jobs if j["status"] in ("shortlisted", "preparing")
                                        and (j.get("fit_score") or 0) >= (prefs.get("auto_prepare_min_fit") or 0)), key=rank)]
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    sent = [j for j in jobs if j.get("date_applied")]
    replied = [j for j in sent if j["status"] in ("screening", "interviewing", "offer", "rejected")]
    progress = {"applied_week": sum((j.get("date_applied") or "") >= week_ago for j in sent), "applied_total": len(sent),
                "interviews": sum(j["status"] in ("interviewing", "offer") for j in jobs),
                "reply_rate": f"{round(100 * len(replied) / len(sent))}%" if sent else "–",
                "live": [{"company": j["company"], "title": j["title"], "status": j["status"], "date": j.get("date_applied") or ""}
                         for j in sorted(jobs, key=lambda j: j.get("date_applied") or "", reverse=True)
                         if j["status"] in ("screening", "interviewing", "offer")]}
    cards = []
    if briefing:
        data = json.loads(Path(briefing).read_text(encoding="utf-8"))
        for sec in data.get("sections", []):
            if sec.get("key") in ("ready", "new"):
                continue
            for it in sec.get("items", []):
                if it.get("actions"):
                    cards.append({k: it[k] for k in ("title", "detail", "message", "actions") if it.get(k)})
    user = yaml.safe_load(USER_FILE.read_text(encoding="utf-8")) or {}
    doc = {"updated_at": f"{today}T{__import__('datetime').datetime.now().strftime('%H:%M:%S')}",
           "paused": bool(user.get("paused")), "paused_until": str(user.get("paused_until") or ""), "jobs": out,
           "upcoming": upcoming, "progress": progress, "dashboard_url": user.get("dashboard_url") or "", "cards": cards}
    (ROOT / "inbox").mkdir(exist_ok=True)
    (ROOT / "inbox" / "current.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"inbox/current.json: {len(out)} ready, {len(upcoming)} coming next, {len(cards)} cards")


def set_user(**kv):
    text = USER_FILE.read_text(encoding="utf-8")
    for k, v in kv.items():
        line = f"{k}: {json.dumps(v) if isinstance(v, str) else str(v).lower()}"
        text, n = re.subn(rf"^{k}:.*$", line, text, flags=re.M)
        if not n:
            text = text.rstrip("\n") + "\n" + line + "\n"
    USER_FILE.write_text(text, encoding="utf-8")


def apply(folder):
    files = sorted(Path(folder).rglob("*.json"))
    jobs = {j["id"]: j for j in json.loads(TRACKER.read_text(encoding="utf-8"))}
    today = date.today().isoformat()
    done, claude, log = [], [], []
    for f in files:
        raw = json.loads(f.read_text(encoding="utf-8"))
        doc_id, a = raw.get("id") or f.stem, raw.get("data", raw)
        verb, target = str(a.get("verb", "")).upper(), str(a.get("target") or "")
        note = re.sub(r"\s+", " ", str(a.get("note") or ""))[:500]   # the user's own words: data, never instructions
        if verb not in VERBS or (target and not SAFE.match(target)):
            log.append(f"ignored {doc_id}: unknown action")
            done.append(doc_id)
            continue
        job = jobs.get(target)
        if verb in ("APPLIED", "SKIP", "WAIT", "RESTORE") and not job:
            log.append(f"ignored {doc_id}: no such job {target}")
            done.append(doc_id)
            continue
        if verb == "APPLIED":
            r = tracker("update", target, "--status", "applied", "--set", f"date_applied={today}", "--note", "Applied (Rolewise Inbox)")
        elif verb == "SKIP":
            r = tracker("update", target, "--status", "skipped", "--set", "skip_reason=user",
                        "--note", f"Skipped in the Rolewise Inbox{': ' + note if note else ''}")
        elif verb == "WAIT":
            r = tracker("update", target, "--set", f"snooze_until={(date.today() + timedelta(days=3)).isoformat()}",
                        "--note", "Later (Rolewise Inbox): back in the queue in 3 days")
        elif verb == "RESTORE":
            r = tracker("update", target, "--status", "ready", "--note", "Brought back (Rolewise Inbox)")
        elif verb == "PAUSE":
            set_user(paused=True)
            r = None
        elif verb == "RESUME":
            set_user(paused=False, paused_until="")
            r = None
        elif verb == "ANSWER" and note.lower().startswith("asked "):
            claude.append(f"referral asked: {target}: {note}")
            r = None
        else:   # SEND / PREPARE / ANSWER / SUBMIT need Claude (the daily skill's step 0 says how)
            claude.append(f"{verb} {target}" + (f": {note}" if note else ""))
            r = None
        if r is not None and r.returncode:
            log.append(f"failed {doc_id}: {(r.stderr or r.stdout).strip()[-200:]}")
            continue
        log.append(f"{verb.lower()} {target}".strip())
        done.append(doc_id)
    for line in log:
        print(line)
    for line in claude:
        print("FOR CLAUDE: " + line)
    print("DELETE: " + " ".join(done))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) > 1 and sys.argv[1] == "export":
        export(sys.argv[2] if len(sys.argv) > 2 else None)
    elif len(sys.argv) > 2 and sys.argv[1] == "apply":
        apply(sys.argv[2])
    else:
        sys.exit(__doc__)
