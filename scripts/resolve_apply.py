"""Find the real application form for queued jobs that only have a LinkedIn link.

Usage: .venv/Scripts/python scripts/resolve_apply.py            # every shortlisted / preparing / ready job
       .venv/Scripts/python scripts/resolve_apply.py <job id> ...

1. LinkedIn's public job page (no login, the same page check_open.py reads) says whether the job is applied for on
   LinkedIn (Easy Apply) or on the company's site. Sets `easy_apply` yes/no.
2. Company-site jobs: looks the role up in the company's public careers feed (Greenhouse, Lever, Ashby,
   SmartRecruiters, Workable; slug from profile/target-companies.yaml or guessed from the name) and sets `apply_url`
   when exactly one posting has the same title.
Whatever is left is opened in Chrome on a laptop run (click Apply on the LinkedIn page once; the apply skill).
Polite: about one request per company, 1 s apart.
"""
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ats_scan import FEEDS, fetch, load_registry  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (Rolewise personal job search)"}
ACTIVE = {"shortlisted", "preparing", "ready"}
STOP = {"the", "a", "an", "and", "of", "for", "in", "at", "to", "-", "&", "remote", "hybrid"}


def words(title):
    return {w for w in re.findall(r"[a-z0-9]+", title.lower()) if w not in STOP}


def same_title(a, b):
    wa, wb = words(a), words(b)
    return bool(wa) and len(wa & wb) / len(wa | wb) >= 0.8


def linkedin_mode(url):
    """'company-site', 'easy-apply', 'closed' or '' from LinkedIn's public job page."""
    m = re.search(r"linkedin\.com/(?:comm/)?jobs/view/(\d+)", url or "")
    if not m:
        return ""
    try:
        with urllib.request.urlopen(urllib.request.Request(
                f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{m.group(1)}", headers=UA), timeout=30) as r:
            body = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return "closed" if e.code in (404, 410) else ""
    except (urllib.error.URLError, TimeoutError):
        return ""
    if re.search(r"no longer accepting applications|closed-job", body, re.I):
        return "closed"
    if "offsite-apply" in body or "apply-link-offsite" in body:
        return "company-site"
    return "easy-apply" if re.search(r"easy[ -]?apply|apply-link-onsite|onsite-apply", body, re.I) else ""


def slugs_for(company, registry):
    name = re.sub(r"\(.*?\)", "", company).strip()
    for slug, info in registry.items():
        if (info or {}).get("name", "").lower() == name.lower():
            return [(slug, info.get("ats"))]
    base = re.sub(r"[^a-z0-9 ]", "", name.lower()).strip()
    guesses = dict.fromkeys([base.replace(" ", ""), base.replace(" ", "-"), base.split(" ")[0]])
    return [(g, None) for g in guesses if g]


def find_posting(job, registry):
    for slug, ats in slugs_for(job["company"], registry):
        for kind in ([ats] if ats else list(FEEDS)):
            try:
                postings = fetch(kind, slug)
            except Exception:
                postings = []
            time.sleep(1)
            hits = [p for p in postings if same_title(p[0], job["title"])]
            if len(hits) > 1:   # several locations: prefer the job's city
                city = (job.get("location") or "").split(",")[0].strip().lower()
                hits = [p for p in hits if city and city in (p[1] or "").lower()] or hits[:0]
            if len(hits) == 1:
                return hits[0][2]
            if postings:
                break   # this slug is the company's board; the role just isn't on it
    return None


def main(ids):
    sys.stdout.reconfigure(encoding="utf-8")
    jobs = json.loads((ROOT / "tracker" / "applications.json").read_text(encoding="utf-8"))
    registry = load_registry()
    todo = [j for j in jobs if (j["id"] in ids if ids else j["status"] in ACTIVE)
            and "linkedin.com" in (j.get("apply_url") or j.get("url") or "")]
    tracker = lambda *a: subprocess.run([sys.executable, str(ROOT / "scripts" / "tracker.py"), "update", *a],
                                        check=True, capture_output=True)
    left = []
    for j in todo:
        mode = linkedin_mode(j.get("url"))
        time.sleep(1)
        if mode == "closed":
            tracker(j["id"], "--status", "skipped", "--set", "skip_reason=posting-closed", "--note", "Posting closed (LinkedIn)")
            print(f"closed       {j['company']} - {j['title']}")
            continue
        if mode == "easy-apply":
            tracker(j["id"], "--set", "easy_apply=yes")
            print(f"easy apply   {j['company']} - {j['title']}")
            continue
        if mode == "company-site":
            tracker(j["id"], "--set", "easy_apply=no")
        url = find_posting(j, registry)
        if url:
            tracker(j["id"], "--set", f"apply_url={url}", "--note", "application form found on the company's careers site")
            print(f"form found   {j['company']} - {j['title']}: {url}")
        else:
            left.append(j)
            print(f"{'company site' if mode else 'unknown':12} {j['company']} - {j['title']} (form not found; laptop run opens it in Chrome)")
    print(f"{len(todo)} checked, {len(left)} still need the form link")


if __name__ == "__main__":
    main(sys.argv[1:])
