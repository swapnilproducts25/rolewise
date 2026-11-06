"""Scan company career pages (public ATS job APIs) for roles matching profile/preferences.yaml.

Usage:
  .venv/Scripts/python scripts/ats_scan.py discover <slug> [<slug> ...]   # find which ATS hosts each slug, add to registry
  .venv/Scripts/python scripts/ats_scan.py scan [--all]                  # list matching roles not yet in the tracker

Registry: profile/target-companies.yaml  ({slug: {ats, name?, note?}}).
Supported: Greenhouse, Lever, Ashby (public, no login). Polite: 1 request per company.
"""
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "profile" / "target-companies.yaml"
TRACKER = ROOT / "tracker" / "applications.json"
UA = {"User-Agent": "Mozilla/5.0 (Rolewise personal job search)"}

PREFS = yaml.safe_load((ROOT / "profile" / "preferences.yaml").read_text(encoding="utf-8")) or {}
US_ONLY = re.compile(r"\b(US|USA|United States|New York|NY|NYC|SF|San Francisco|Seattle|Chicago|Atlanta|Toronto|Pittsburgh|Raleigh|Tokyo)\b")


def _any(words):
    """Regex matching any of the given words/phrases as whole words."""
    words = [re.escape(str(w).strip()) for w in words if str(w or "").strip()]
    return r"\b(" + "|".join(words) + r")\b" if words else r"(?!)"


# Filters come from preferences.yaml: an explicit `scan:` block (regexes) wins; otherwise they are
# derived from target_titles, exclude.keywords and locations, so the scanner works for any profession.
_scan = PREFS.get("scan") or {}
_places = [p for loc in PREFS.get("locations") or [] for p in [loc.get("name")] + list(loc.get("places") or [])]
if PREFS.get("remote_ok"):
    _places.append("remote")
# Match the core role too ("Senior Data Analyst" -> "Data Analyst"); fit scoring judges the level later.
_SENIORITY = re.compile(r"^(senior|sr\.?|lead|principal|staff|junior|jr\.?|associate|head of|chief)\s+", re.I)
_titles = PREFS.get("target_titles") or []
TITLE = re.compile(_scan.get("title_regex") or _any(set(_titles) | {_SENIORITY.sub("", t) for t in _titles}), re.I)
TITLE_EXCLUDE = re.compile(_scan.get("title_exclude_regex") or _any(
    ["intern", "internship", "junior", "graduate", "apprentice"] + list((PREFS.get("exclude") or {}).get("keywords") or [])), re.I)
PLACE = re.compile(_scan.get("place_regex") or _any(_places), re.I)

FEEDS = {
    "greenhouse": ("https://boards-api.greenhouse.io/v1/boards/{}/jobs", lambda d: [
        (j["title"], (j.get("location") or {}).get("name", ""), j["absolute_url"], j.get("updated_at", "")) for j in d.get("jobs", [])]),
    "lever": ("https://api.lever.co/v0/postings/{}?mode=json", lambda d: [
        (j["text"], (j.get("categories") or {}).get("location", "") + (" / " + j.get("workplaceType", "") if j.get("workplaceType") else ""),
         j["hostedUrl"], str(j.get("createdAt", ""))) for j in d]),
    "ashby": ("https://api.ashbyhq.com/posting-api/job-board/{}", lambda d: [
        (j["title"], ", ".join(filter(None, [j.get("location", "")] + [s.get("location", "") for s in j.get("secondaryLocations", [])]))
         + (" / remote" if j.get("isRemote") else ""), j["jobUrl"], j.get("publishedAt", "")) for j in d.get("jobs", [])]),
    # SmartRecruiters (talabat/Delivery Hero and many Gulf and EU companies): public postings API, first 100 roles
    "smartrecruiters": ("https://api.smartrecruiters.com/v1/companies/{}/postings?limit=100", lambda d: [
        (j["name"], ", ".join(filter(None, [(j.get("location") or {}).get("city", ""), (j.get("location") or {}).get("country", "")]))
         + (" / remote" if (j.get("location") or {}).get("remote") else ""),
         f"https://jobs.smartrecruiters.com/{(j.get('company') or {}).get('identifier', '')}/{j['id']}", j.get("releasedDate", ""))
        for j in d.get("content", [])]),
    # Workable: the public careers widget feed
    "workable": ("https://apply.workable.com/api/v1/widget/accounts/{}", lambda d: [
        (j["title"], ", ".join(filter(None, [j.get("city", ""), j.get("country", "")])) + (" / remote" if j.get("telecommuting") else ""),
         j.get("url") or j.get("shortlink", ""), j.get("published_on", "")) for j in d.get("jobs", [])]),
}


def fetch(ats, slug):
    url, parse = FEEDS[ats]
    with urllib.request.urlopen(urllib.request.Request(url.format(slug), headers=UA), timeout=20) as r:
        return parse(json.loads(r.read().decode("utf-8")))


def load_registry():
    return yaml.safe_load(REGISTRY.read_text(encoding="utf-8")) if REGISTRY.exists() else {}


def discover(slugs):
    reg = load_registry()
    for slug in slugs:
        found = None
        for ats in FEEDS:
            try:
                jobs = fetch(ats, slug)
                if jobs:
                    found = (ats, len(jobs))
                    break
            except Exception:
                pass
            time.sleep(0.3)
        if found:
            reg[slug] = {**reg.get(slug, {}), "ats": found[0]}
        print(f"{slug}: {found[0] + ' (' + str(found[1]) + ' jobs)' if found else 'not found'}")
    REGISTRY.write_text(yaml.safe_dump(dict(sorted(reg.items())), sort_keys=False), encoding="utf-8")


def scan(show_all=False):
    reg = load_registry()
    tracked = {(j.get("url") or "").split("?")[0].rstrip("/").lower() for j in json.loads(TRACKER.read_text(encoding="utf-8"))}
    hits = []
    for slug, info in reg.items():
        try:
            jobs = fetch(info["ats"], slug)
        except Exception as e:
            print(f"! {slug}: {e}")
            continue
        for title, loc, url, posted in jobs:
            if TITLE.search(title) and not TITLE_EXCLUDE.search(title) and PLACE.search(loc or "") and not (US_ONLY.search(loc or "") and not PLACE.search(re.sub(US_ONLY, '', loc or ''))):
                new = url.split("?")[0].rstrip("/").lower() not in tracked
                if new or show_all:
                    hits.append((info.get("name", slug), title, loc, url, str(posted)[:10], "" if new else "TRACKED"))
        time.sleep(0.3)
    for h in sorted(hits):
        print(" | ".join(h))
    print(f"{len(hits)} matching roles across {len(reg)} companies")


def jd(job_id, url, out_dir):
    """Save a career-page job description (Greenhouse/Lever/Ashby URL) to <out_dir>/jd.md."""
    import html
    m = re.search(r"greenhouse\.io/(?:embed/job_app\?for=)?([\w-]+)/jobs/(\d+)", url) or \
        re.search(r"(stripe)\.com/jobs/search\?gh_jid=(\d+)", url) or re.search(r"careers\.(hellofresh)\.com/.*?/job/(\d+)", url) or \
        re.search(r"(\w+)\.com/(?:en-eu/)?careers/positions/(\d+)", url)
    if m:
        api = f"https://boards-api.greenhouse.io/v1/boards/{m.group(1)}/jobs/{m.group(2)}"
        d = json.loads(urllib.request.urlopen(urllib.request.Request(api, headers=UA), timeout=20).read())
        title, loc, body = d["title"], (d.get("location") or {}).get("name", ""), html.unescape(d.get("content", ""))
    elif "lever.co" in url:
        slug, pid = re.search(r"lever\.co/([\w-]+)/([\w-]+)", url).groups()
        d = json.loads(urllib.request.urlopen(urllib.request.Request(f"https://api.lever.co/v0/postings/{slug}/{pid}", headers=UA), timeout=20).read())
        title, loc = d["text"], (d.get("categories") or {}).get("location", "")
        body = d.get("descriptionPlain", "") + "\n" + "\n".join(l["text"] + "\n" + l.get("content", "") for l in d.get("lists", []))
    elif "ashbyhq.com" in url:
        slug, pid = re.search(r"ashbyhq\.com/([\w-]+)/([\w-]+)", url).groups()
        d = json.loads(urllib.request.urlopen(urllib.request.Request(FEEDS["ashby"][0].format(slug), headers=UA), timeout=20).read())
        j = next(j for j in d["jobs"] if pid in j["jobUrl"])
        title, loc, body = j["title"], j.get("location", ""), j.get("descriptionPlain") or j.get("descriptionHtml", "")
    else:
        sys.exit(f"Unsupported URL {url}")
    body = re.sub(r"<br\s*/?>|</p>|</li>|</h\d>", "\n", body)
    body = re.sub(r"<li[^>]*>", "- ", body)
    body = re.sub(r"<[^>]+>", "", body)
    body = "\n".join(l.strip() for l in body.splitlines() if l.strip())
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "jd.md").write_text(f"# {title}\nLocation: {loc}\nURL: {url}\n\n{body}\n", encoding="utf-8")
    print(f"{job_id}: {title} ({len(body)} chars)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) > 1 and sys.argv[1] == "jd":
        # jd <tracker id> ... : fetch JDs for tracked career-page jobs into applications/<id>/jd.md
        jobs = {j["id"]: j for j in json.loads(TRACKER.read_text(encoding="utf-8"))}
        for jid in sys.argv[2:]:
            try:
                jd(jid, jobs[jid]["url"], ROOT / "applications" / jid)
            except Exception as e:
                print(f"{jid}: FAILED {e}")
            time.sleep(0.5)
    elif len(sys.argv) > 2 and sys.argv[1] == "discover":
        discover(sys.argv[2:])
    elif len(sys.argv) > 1 and sys.argv[1] == "scan":
        scan("--all" in sys.argv)
    else:
        sys.exit(__doc__)
