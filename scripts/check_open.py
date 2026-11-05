"""Check that tracked job postings are still open, and skip the closed ones.

Usage: .venv/Scripts/python scripts/check_open.py                 # every shortlisted / preparing / ready job
       .venv/Scripts/python scripts/check_open.py <job id> ...    # just these
Greenhouse and Lever: their public job APIs (404 = closed). LinkedIn: the public job page ("No longer accepting
applications" or 404 = closed). Others are left alone. Closed jobs become `skipped` (skip_reason posting-closed).
Polite: one request per job, 1.5 s apart.
"""
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (Rolewise personal job search)"}
CHECK = {"shortlisted", "preparing", "ready"}


def status_of(url):
    """'open', 'closed' or 'unknown' for one posting URL."""
    probe, closed_text = None, None
    if m := re.search(r"greenhouse\.io/(?:embed/job_app\?for=)?([\w-]+)(?:/jobs/|&token=)(\d+)", url or ""):
        probe = f"https://boards-api.greenhouse.io/v1/boards/{m.group(1)}/jobs/{m.group(2)}"
    elif m := re.search(r"jobs\.lever\.co/([\w-]+)/([0-9a-f-]{20,})", url or ""):
        probe = f"https://api.lever.co/v0/postings/{m.group(1)}/{m.group(2)}"
    elif m := re.search(r"linkedin\.com/(?:comm/)?jobs/view/(\d+)", url or ""):
        probe = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{m.group(1)}"
        closed_text = re.compile(r"no longer accepting applications|closed-job|this job is no longer available", re.I)
    if not probe:
        return "unknown"
    try:
        with urllib.request.urlopen(urllib.request.Request(probe, headers=UA), timeout=30) as r:
            body = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return "closed" if e.code in (404, 410) else "unknown"
    except (urllib.error.URLError, TimeoutError):
        return "unknown"
    return "closed" if closed_text and closed_text.search(body) else "open"


def main(ids):
    sys.stdout.reconfigure(encoding="utf-8")
    jobs = json.loads((ROOT / "tracker" / "applications.json").read_text(encoding="utf-8"))
    todo = [j for j in jobs if (j["id"] in ids if ids else j["status"] in CHECK)]
    closed = 0
    for j in todo:
        urls = [u for u in (j.get("apply_url"), j.get("url")) if u]
        st = "unknown"
        for u in urls:
            st = status_of(u)
            if st != "unknown":
                break
        if st == "closed":
            closed += 1
            subprocess.run([sys.executable, str(ROOT / "scripts" / "tracker.py"), "update", j["id"], "--status", "skipped",
                            "--set", "skip_reason=posting-closed", "--note", "Posting closed (checked automatically)"],
                           check=True, capture_output=True)
        print(f"{st:8} {j['company']} - {j['title']}")
        time.sleep(1.5)
    print(f"{len(todo)} checked, {closed} closed and skipped")


if __name__ == "__main__":
    main(sys.argv[1:])
