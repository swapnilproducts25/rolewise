"""Application tracker CLI. All tracker changes go through here.

Usage (run with .venv/Scripts/python scripts/tracker.py ...):
  add --company C --title T [--location L] [--work-mode M] [--url U] [--source S]
      [--fit N] [--summary TEXT] [--status found] [--posted YYYY-MM-DD]
  update ID [--status S] [--note TEXT] [--next-action TEXT] [--next-date YYYY-MM-DD] [--set key=value ...]
  exists [--url U] [--company C --title T]
  show ID
  list [--status s1,s2] [--min-fit N]
  due                      # items whose next_date is today or earlier
  stats [--by FIELD]       # funnel counts and conversion rates, optionally split by an experiment field

Experiment fields (set with update --set, used by the learning loop in /coach):
  cv_angle      travel | ai-builder | support-platform | ads-measurement | marketplace | cx-leadership | general
  cover_letter  yes | no
  channel       cold | referral | recruiter | inbound
  level         senior | lead | head | director
  region        uae | eu | uk | remote | other
  posted_days   days between posting and applying (integer)
  first_response_days  days from applying to the first human response (integer)
"""
import argparse
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACKER = ROOT / "tracker" / "applications.json"

STATUSES = [
    "found", "shortlisted", "preparing", "ready", "applied", "screening",
    "interviewing", "offer", "rejected", "withdrawn", "ghosted", "skipped",
]
# Statuses that mean the application reached the company.
SUBMITTED = {"applied", "screening", "interviewing", "offer", "rejected", "ghosted", "withdrawn"}
RESPONDED = {"screening", "interviewing", "offer", "rejected"}


def load():
    return json.loads(TRACKER.read_text(encoding="utf-8")) if TRACKER.exists() else []


def save(jobs):
    TRACKER.write_text(json.dumps(jobs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]


def norm_url(url):
    return (url or "").split("?")[0].rstrip("/").lower()


def find(jobs, job_id):
    for j in jobs:
        if j["id"] == job_id:
            return j
    sys.exit(f"No job with id {job_id}")


def duplicate(jobs, url=None, company=None, title=None):
    for j in jobs:
        if url and norm_url(j.get("url")) == norm_url(url):
            return j
        if company and title and slug(j["company"]) == slug(company) and slug(j["title"]) == slug(title):
            return j
    return None


def applied_on_linkedin(url=None, company=None, title=None):
    """A past LinkedIn application (tracker/linkedin-applied.json, from scripts/linkedin_import.py) for this job:
    the same LinkedIn job id, or the same company and title within the last 6 months."""
    path = TRACKER.parent / "linkedin-applied.json"
    if not path.exists():
        return None
    m = re.search(r"/jobs/view/(\d+)", url or "")
    recent = (date.today() - timedelta(days=183)).isoformat()
    for a in json.loads(path.read_text(encoding="utf-8")):
        if m and a.get("job_id") == m.group(1):
            return a
        if company and title and a.get("date", "") >= recent and slug(a.get("company", "")) == slug(company) \
                and slug(a.get("title", "")) == slug(title):
            return a
    return None


def cmd_add(a, jobs):
    dup = duplicate(jobs, a.url, a.company, a.title)
    if dup:
        print(f"DUPLICATE {dup['id']} ({dup['status']})")
        return
    today = date.today().isoformat()
    base = f"{slug(a.company)}-{slug(a.title)}"
    job_id, n = base, 2
    while any(j["id"] == job_id for j in jobs):
        job_id, n = f"{base}-{n}", n + 1
    jobs.append({
        "id": job_id,
        "company": a.company,
        "title": a.title,
        "location": a.location,
        "work_mode": a.work_mode,
        "url": a.url,
        "source": a.source,
        "fit_score": a.fit,
        "fit_summary": a.summary,
        "status": a.status,
        "date_found": today,
        "posted": a.posted,
        "date_applied": None,
        "cv_file": None,
        "folder": f"applications/{job_id}",
        "contacts": [],
        "next_action": None,
        "next_date": None,
        "history": [{"date": today, "event": f"added as {a.status}"}],
    })
    save(jobs)
    print(job_id)


def cmd_update(a, jobs):
    j = find(jobs, a.id)
    today = date.today().isoformat()
    if a.status:
        if a.status not in STATUSES:
            sys.exit(f"Unknown status {a.status}. Use one of: {', '.join(STATUSES)}")
        j["history"].append({"date": today, "event": f"{j['status']} -> {a.status}"})
        j["status"] = a.status
        if a.status == "applied" and not j.get("date_applied"):
            j["date_applied"] = today
    if a.note:
        j["history"].append({"date": today, "event": a.note})
    if a.next_action is not None:
        j["next_action"] = a.next_action or None
    if a.next_date is not None:
        j["next_date"] = a.next_date or None
    for kv in a.set or []:
        key, _, value = kv.partition("=")
        try:
            j[key] = json.loads(value)
        except json.JSONDecodeError:
            j[key] = value
    save(jobs)
    print(f"{j['id']}: {j['status']}")


def line(j):
    fit = j.get("fit_score")
    fit = f"{fit:>3}" if isinstance(fit, int) else "  -"
    nxt = f"  -> {j['next_action']} ({j['next_date']})" if j.get("next_action") else ""
    return f"[{j['status']:<12}] {fit}  {j['company']} — {j['title']} | {j.get('location') or ''}  ({j['id']}){nxt}"


def cmd_list(a, jobs):
    wanted = set(a.status.split(",")) if a.status else None
    rows = [j for j in jobs
            if (not wanted or j["status"] in wanted)
            and (a.min_fit is None or (j.get("fit_score") or 0) >= a.min_fit)]
    rows.sort(key=lambda j: -(j.get("fit_score") or 0))
    for j in rows:
        print(line(j))
    print(f"{len(rows)} job(s)")


def cmd_due(a, jobs):
    today = date.today().isoformat()
    rows = [j for j in jobs if j.get("next_date") and j["next_date"] <= today]
    for j in sorted(rows, key=lambda j: j["next_date"]):
        print(line(j))
    print(f"{len(rows)} due")


def cmd_stats(a, jobs):
    counts = {s: 0 for s in STATUSES}
    for j in jobs:
        counts[j["status"]] = counts.get(j["status"], 0) + 1
    for s in STATUSES:
        if counts[s]:
            print(f"{s:<12} {counts[s]}")
    submitted = sum(1 for j in jobs if j["status"] in SUBMITTED)
    responded = sum(1 for j in jobs if j["status"] in RESPONDED)
    interviews = sum(1 for j in jobs if j["status"] in {"interviewing", "offer"}
                     or any("interviewing" in h["event"] for h in j["history"]))
    print(f"total {len(jobs)} | submitted {submitted}")
    if submitted:
        print(f"response rate {responded / submitted:.0%} | interview rate {interviews / submitted:.0%}")
    if a.by:
        # Segment submitted applications by an experiment field (see EXPERIMENT_FIELDS) for the learning loop.
        groups = {}
        for j in jobs:
            if j["status"] in SUBMITTED:
                groups.setdefault(str(j.get(a.by) or "unknown"), []).append(j)
        print(f"\nby {a.by}:  n | responded | interviews")
        for key, js in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            r = sum(1 for j in js if j["status"] in RESPONDED)
            i = sum(1 for j in js if j["status"] in {"interviewing", "offer"})
            print(f"  {key:<22} {len(js):>3} | {r:>3} ({r / len(js):.0%}) | {i:>3}")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("add")
    s.add_argument("--company", required=True)
    s.add_argument("--title", required=True)
    s.add_argument("--location")
    s.add_argument("--work-mode")
    s.add_argument("--url")
    s.add_argument("--source")
    s.add_argument("--fit", type=int)
    s.add_argument("--summary")
    s.add_argument("--status", default="found", choices=STATUSES)
    s.add_argument("--posted", help="posting date from the job page or ats_scan, YYYY-MM-DD")

    s = sub.add_parser("update")
    s.add_argument("id")
    s.add_argument("--status")
    s.add_argument("--note")
    s.add_argument("--next-action")
    s.add_argument("--next-date")
    s.add_argument("--set", nargs="*")

    s = sub.add_parser("exists")
    s.add_argument("--url")
    s.add_argument("--company")
    s.add_argument("--title")

    s = sub.add_parser("show")
    s.add_argument("id")

    s = sub.add_parser("list")
    s.add_argument("--status")
    s.add_argument("--min-fit", type=int)

    sub.add_parser("due")
    s = sub.add_parser("stats")
    s.add_argument("--by")

    a = p.parse_args()
    jobs = load()
    if a.cmd == "add":
        cmd_add(a, jobs)
    elif a.cmd == "update":
        cmd_update(a, jobs)
    elif a.cmd == "exists":
        dup = duplicate(jobs, a.url, a.company, a.title)
        past = None if dup else applied_on_linkedin(a.url, a.company, a.title)
        print(f"DUPLICATE {dup['id']} ({dup['status']})" if dup
              else f"APPLIED ON LINKEDIN {past['date']} ({past['company']} - {past['title']})" if past else "NEW")
    elif a.cmd == "show":
        print(json.dumps(find(jobs, a.id), indent=2, ensure_ascii=False))
    elif a.cmd == "list":
        cmd_list(a, jobs)
    elif a.cmd == "due":
        cmd_due(a, jobs)
    elif a.cmd == "stats":
        cmd_stats(a, jobs)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
