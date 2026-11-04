"""Fetch public LinkedIn job descriptions (guest endpoint, no login) and save them as text.

Usage: .venv/Scripts/python scripts/fetch_jd.py <out_dir> <linkedin_job_id> [<job_id> ...]
Writes <out_dir>/<job_id>.md with title, company, location, criteria, applicants and description.
Polite by design: one request every few seconds.
"""
import html
import re
import sys
import time
import urllib.request
from pathlib import Path

URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{}"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


def text(fragment):
    fragment = re.sub(r"<br\s*/?>|</p>|</li>|</h\d>", "\n", fragment)
    fragment = re.sub(r"<li[^>]*>", "- ", fragment)
    fragment = re.sub(r"<[^>]+>", "", fragment)
    lines = [re.sub(r"\s+", " ", l).strip() for l in html.unescape(fragment).split("\n")]
    return "\n".join(l for l in lines if l)


def first(pattern, page):
    m = re.search(pattern, page, re.S)
    return text(m.group(1)) if m else ""


def fetch(job_id):
    req = urllib.request.Request(URL.format(job_id), headers={"User-Agent": UA})
    page = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    criteria = re.findall(r'description__job-criteria-subheader">(.*?)</h3>.*?criteria-text[^>]*>(.*?)</span>', page, re.S)
    return "\n".join([
        f"# {first(r'top-card-layout__title[^>]*>(.*?)</h2>', page)}",
        f"Company: {first(r'topcard__org-name-link[^>]*>(.*?)</a>', page) or first(r'topcard__flavor\">(.*?)</span>', page)}",
        f"Location: {first(r'topcard__flavor topcard__flavor--bullet\">(.*?)</span>', page)}",
        f"Posted: {first(r'posted-time-ago__text[^>]*>(.*?)</span>', page)}",
        f"Applicants: {first(r'num-applicants__caption[^>]*>(.*?)</(?:span|figcaption)>', page)}",
        f"URL: https://www.linkedin.com/jobs/view/{job_id}",
        *[f"{text(k)}: {text(v)}" for k, v in criteria],
        "",
        first(r'show-more-less-html__markup[^>]*>(.*?)</div>', page),
    ])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for i, job_id in enumerate(sys.argv[2:]):
        if i:
            time.sleep(3)
        try:
            body = fetch(job_id)
            (out / f"{job_id}.md").write_text(body, encoding="utf-8")
            print(f"{job_id}: {body.splitlines()[0][2:]} ({len(body)} chars)")
        except Exception as e:  # keep going on individual failures
            print(f"{job_id}: FAILED {e}")
