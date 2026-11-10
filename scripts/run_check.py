"""End-of-run check for the daily run: lists what today's run still owes, so it can't finish early.

  1. Every career-page match (scripts/ats_scan.py scan), in every target location, is in the tracker
     (shortlisted, or skipped with a reason).
  2. Every location group (Dubai / UAE, Europe, India, Remote...) has 10 current jobs ready to apply to (posted in the
     last 3 weeks), or no shortlisted job left to prepare there. Freshest good jobs first (fit + a boost for new
     postings), preferences.yaml auto_prepare_min_fit and queue_per_location; at most 2 per company and 30 jobs a day.
  3. Every job made ready today has a CV review by the cv-reviewer agent (applications/<id>/cv-review.md).

Usage: python scripts/run_check.py [--no-scan]   exit code 1 while something is open
"""
import json
import subprocess
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_kits import freshness, group  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DAILY_MAX = 30
PER_COMPANY = 2
BOOST = {"new": 8, "week": 4, "old": -6}   # same order as the add-on's queue


def main(scan=True):
    today = date.today().isoformat()
    jobs = json.loads((ROOT / "tracker" / "applications.json").read_text(encoding="utf-8"))
    prefs = yaml.safe_load((ROOT / "profile" / "preferences.yaml").read_text(encoding="utf-8")) or {}
    min_fit = prefs.get("auto_prepare_min_fit", 0) or 0
    problems = []

    if scan:
        out = subprocess.run([sys.executable, str(ROOT / "scripts" / "ats_scan.py"), "scan"], cwd=ROOT,
                             capture_output=True, text=True, encoding="utf-8").stdout
        hits = [l for l in out.splitlines() if l.count(" | ") >= 3 and not l.startswith("!")]
        if hits:
            problems.append(f"{len(hits)} career-page matches not in the tracker (add each, or skip it with a reason):")
            problems += [f"   {h[:140]}" for h in hits[:40]]

    def made_ready_today(j):
        return any(h.get("date") == today and "-> ready" in h.get("event", "") for h in j.get("history", []))

    ready_today = [j for j in jobs if made_ready_today(j)]
    per_co = Counter(j["company"] for j in ready_today)
    target = prefs.get("queue_per_location", 10)
    rank = lambda j: (j.get("fit_score") or 0) + BOOST.get(freshness(j)["urgency"], 0)
    if len(ready_today) < DAILY_MAX:
        for g in sorted({group(j) for j in jobs if j["status"] in ("ready", "shortlisted")}):
            current = [j for j in jobs if j["status"] == "ready" and group(j) == g and freshness(j)["urgency"] != "old"]
            waiting = [j for j in jobs if j["status"] == "shortlisted" and group(j) == g
                       and (j.get("fit_score") or 0) >= min_fit and per_co[j["company"]] < PER_COMPANY]
            if len(current) < target and waiting:
                top = sorted(waiting, key=lambda j: -rank(j))[:target - len(current)]
                problems.append(f"{g}: {len(current)} current jobs ready (target {target}), {len(waiting)} shortlisted "
                                f"waiting; prepare next:")
                problems += [f"   {j.get('fit_score')}  {freshness(j)['age']}d  {j['id']}" for j in top]

    unreviewed = [j["id"] for j in ready_today if not (ROOT / "applications" / j["id"] / "cv-review.md").exists()]
    if unreviewed:
        problems.append("Ready today without a cv-reviewer review (run cv-writer + cv-reviewer, or the master CV "
                        "unchanged with a cv-review.md saying so):")
        problems += [f"   {i}" for i in unreviewed]

    if problems:
        print("RUN NOT DONE\n" + "\n".join(problems))
        sys.exit(1)
    print(f"Run complete: {len(ready_today)} prepared today, every location's queue full (or nothing left to prepare), "
          f"career-page matches all tracked, all CVs reviewed.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(scan="--no-scan" not in sys.argv)
