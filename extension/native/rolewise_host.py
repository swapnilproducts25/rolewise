"""Rolewise Fill's local helper (Chrome native messaging): lets the add-on update Rolewise on this laptop directly.

Chrome starts it when the add-on sends a message; it reads one JSON message, acts, replies and exits.
Actions (all local, nothing leaves the laptop except the usual git push in cloud mode):
  {"action": "skip", "id": "<job id>", "reason": "..."}       -> tracker: skipped
  {"action": "applied", "id": "<job id>"}                       -> tracker: applied, date_applied today
  {"action": "debrief", "id": "<job id>", "notes": "..."}       -> applications/<id>/debrief-notes-<date>.md; the next
                                                                    run turns it into a full debrief (debrief skill)
  {"action": "pause", "until": "YYYY-MM-DD"} / {"action": "resume"} -> profile/user.yaml paused / paused_until
  {"action": "ping"}                                            -> {"ok": true}
Installed once with: python scripts/install_native_host.py <extension id>
"""
import json
import re
import struct
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = str(ROOT / ".venv" / "Scripts" / "python.exe") if (ROOT / ".venv" / "Scripts" / "python.exe").exists() else sys.executable
SAFE_ID = re.compile(r"^[a-z0-9-]{3,120}$")


def read_message():
    raw = sys.stdin.buffer.read(4)
    if len(raw) < 4:
        return None
    size = struct.unpack("<I", raw)[0]
    return json.loads(sys.stdin.buffer.read(size).decode("utf-8"))


def send(obj):
    data = json.dumps(obj).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("<I", len(data)) + data)
    sys.stdout.buffer.flush()


def tracker(*args):
    r = subprocess.run([PY, str(ROOT / "scripts" / "tracker.py"), *args], cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError((r.stderr or r.stdout).strip()[-300:])
    return r.stdout.strip()


def save_and_sync(message):
    """Rebuild the add-on's kits (queue, pause state), commit, and push in cloud mode, without making Chrome wait."""
    script = (f"import subprocess as s; s.run([r'{PY}', 'scripts/build_kits.py'], cwd=r'{ROOT}', capture_output=True); "
              f"s.run(['git', 'add', '-A', 'tracker', 'applications', 'profile/user.yaml'], cwd=r'{ROOT}', capture_output=True); "
              f"s.run(['git', 'commit', '-q', '-m', {message!r}], cwd=r'{ROOT}', capture_output=True); "
              f"m = open(r'{ROOT / 'profile' / 'user.yaml'}', encoding='utf-8').read(); "
              f"'run_mode: cloud' in m and s.run(['git', 'push', '-q'], cwd=r'{ROOT}', capture_output=True)")
    flags = 0x08000000 if sys.platform == "win32" else 0   # CREATE_NO_WINDOW
    subprocess.Popen([PY, "-c", script], cwd=ROOT, creationflags=flags, stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def set_user(key, value):
    p = ROOT / "profile" / "user.yaml"
    t = p.read_text(encoding="utf-8")
    line = f"{key}: {value}"
    t, n = re.subn(rf"^{key}:.*$", line, t, count=1, flags=re.M)
    p.write_text(t if n else t.rstrip("\n") + "\n" + line + "\n", encoding="utf-8")


def handle(msg):
    action = msg.get("action")
    if action == "ping":
        return {"ok": True}
    job = msg.get("id", "")
    if action in ("skip", "applied", "debrief") and not SAFE_ID.match(job):
        return {"ok": False, "error": "unknown job"}
    today = date.today().isoformat()
    if action == "skip":
        reason = re.sub(r"\s+", " ", str(msg.get("reason") or "skipped from the add-on"))[:200]
        tracker("update", job, "--status", "skipped", "--set", "skip_reason=user", "--note", f"Skipped in Rolewise Fill: {reason}")
        save_and_sync(f"Skip {job} (Rolewise Fill)")
    elif action == "applied":
        tracker("update", job, "--status", "applied", "--set", f"date_applied={today}", "--note", "Submitted with Rolewise Fill")
        save_and_sync(f"Applied {job} (Rolewise Fill)")
    elif action == "debrief":
        notes = str(msg.get("notes") or "").strip()
        if not notes:
            return {"ok": False, "error": "empty notes"}
        out = ROOT / "applications" / job / f"debrief-notes-{today}.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("a", encoding="utf-8") as f:
            f.write(f"# Debrief notes {today} (typed in Rolewise Fill)\n\n{notes}\n\n")
        tracker("update", job, "--note", "Debrief notes saved from Rolewise Fill; next run writes the full debrief")
        save_and_sync(f"Debrief notes {job} (Rolewise Fill)")
    elif action == "pause":
        until = msg.get("until") or ""
        if until and not re.match(r"^\d{4}-\d{2}-\d{2}$", until):
            return {"ok": False, "error": "date must be YYYY-MM-DD"}
        set_user("paused", "true")
        set_user("paused_until", f'"{until}"')
        save_and_sync("Pause Rolewise (Rolewise Fill)")
    elif action == "resume":
        set_user("paused", "false")
        set_user("paused_until", '""')
        save_and_sync("Resume Rolewise (Rolewise Fill)")
    else:
        return {"ok": False, "error": f"unknown action {action}"}
    return {"ok": True}


if __name__ == "__main__":
    try:
        m = read_message()
        send(handle(m) if m else {"ok": False, "error": "no message"})
    except Exception as e:   # always answer, so the add-on can fall back to a tap email
        send({"ok": False, "error": str(e)[:300]})
