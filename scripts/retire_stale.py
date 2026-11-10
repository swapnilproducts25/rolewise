"""Retire queue jobs the user has left alone for 3 weeks, so fresh ones get the room.

A `ready` job that has been ready for 21+ days with no action is skipped with reason `no-action-21d` (a "restore <id>"
from the user puts it back with tracker.py update <id> --status ready). Prints what it retired, for the briefing.

Usage: python scripts/retire_stale.py [--dry-run]
"""
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAYS = 21


def ready_since(j):
    days = [h["date"] for h in j.get("history", []) if "-> ready" in h.get("event", "") or h.get("event") == "added as ready"]
    return date.fromisoformat(days[-1]) if days else None


def main(dry):
    jobs = json.loads((ROOT / "tracker" / "applications.json").read_text(encoding="utf-8"))
    today = date.today()
    stale = [j for j in jobs if j["status"] == "ready" and ready_since(j) and (today - ready_since(j)).days >= DAYS]
    for j in stale:
        print(f"retired: {j['id']} (ready since {ready_since(j)})")
        if not dry:
            subprocess.run([sys.executable, str(ROOT / "scripts" / "tracker.py"), "update", j["id"], "--status", "skipped",
                            "--set", "skip_reason=no-action-21d", "--note", f"No action for {DAYS}+ days in the queue"],
                           cwd=ROOT, check=True, capture_output=True)
    print(f"{len(stale)} retired")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main("--dry-run" in sys.argv)
