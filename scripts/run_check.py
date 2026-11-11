"""End-of-run check for the daily run: lists what today's run still owes, so it can't finish early.

  1. Every career-page match (scripts/ats_scan.py scan), in every target location, is in the tracker
     (shortlisted, or skipped with a reason).
  2. New jobs are prepared every run, whatever is already waiting: every posting from the last 7 days with fit of at
     least fresh_min_fit (60), and up to prepare_per_location (10) per location group, freshest good jobs first
     (fit + a boost for new postings; preferences.yaml auto_prepare_min_fit). At most 2 per company and 40 a day.
  3. Every job added today was scored from its job description (applications/<id>/jd.md), not its title.
  4. Every job made ready today has a CV review by the cv-reviewer agent (applications/<id>/cv-review.md).

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
DAILY_MAX = 40
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
    per_loc = prefs.get("prepare_per_location", prefs.get("queue_per_location", 10))
    fresh_fit = prefs.get("fresh_min_fit", 60)
    rank = lambda j: (j.get("fit_score") or 0) + BOOST.get(freshness(j)["urgency"], 0)
    if len(ready_today) < DAILY_MAX:
        waiting = [j for j in jobs if j["status"] == "shortlisted" and (j.get("fit_score") or 0) >= min_fit
                   and per_co[j["company"]] < PER_COMPANY]
        # Early applications get read first: a good fresh posting never waits for room in the queue.
        fresh = [j for j in waiting if (freshness(j)["age"] or 99) <= 7 and (j.get("fit_score") or 0) >= fresh_fit]
        if fresh:
            problems.append(f"{len(fresh)} fresh postings (last 7 days, fit {fresh_fit}+) not prepared yet; prepare them first:")
            problems += [f"   {j.get('fit_score')}  {freshness(j)['age']}d  {j['id']}" for j in sorted(fresh, key=lambda j: -rank(j))]
        for g in sorted({group(j) for j in waiting}):
            done = sum(group(j) == g for j in ready_today)
            left = [j for j in waiting if group(j) == g and j not in fresh]
            if done < per_loc and left:
                top = sorted(left, key=lambda j: -rank(j))[:per_loc - done]
                problems.append(f"{g}: {done} prepared today (aim {per_loc} a run), {len(left)} more waiting; prepare next:")
                problems += [f"   {j.get('fit_score')}  {freshness(j)['age']}d  {j['id']}" for j in top]

    no_jd = [j["id"] for j in jobs if j.get("date_found") == today and j["status"] in ("shortlisted", "preparing", "ready")
             and not (ROOT / "applications" / j["id"] / "jd.md").exists()]
    if no_jd:
        problems.append("Added today but scored without the job description (save applications/<id>/jd.md from the "
                        "company's careers page, then re-score with fit.py):")
        problems += [f"   {i}" for i in no_jd]

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
