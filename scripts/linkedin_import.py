"""Import a LinkedIn data export ("Get a copy of your data") into Rolewise.

Usage: .venv/Scripts/python scripts/linkedin_import.py "<export folder>"

What it does (and only this; messages, logins, ads and identity files are never read):
  Connections.csv          -> profile/connections.csv (laptop only, gitignored) for scripts/referrals.py
  Jobs/Job Applications*   -> tracker/linkedin-applied.json: date, company, title, job id per past application, so
                              discovery never re-suggests a role you already applied to (tracker.py exists checks it)
  Profile, Positions, Skills, Job Seeker Preferences, SavedJobAlerts, Saved Jobs
                           -> coach/linkedin-insights.md: your application history in numbers, and where your
                              LinkedIn profile and master-cv.yaml disagree (titles, dates, years)
The export folder itself stays where it is (gitignored); delete it whenever you like.
"""
import collections
import csv
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
AGENCY = re.compile(r"recruit|talent|staffing|search|hire|hiring|consult|resourc|people|jobgether|discovered|salt\b|"
                    r"found by few|pulse group|lancesoft|michael page|hays|robert walters|cooper fitch|confidential", re.I)


def rows(path):
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    start = next((i for i, l in enumerate(lines) if "," in l and not l.startswith(("Notes", '"When'))), 0)
    return list(csv.DictReader(lines[start:]))


def parse_date(s):
    s = (s or "").split(",")[0].strip()
    for fmt in ("%m/%d/%y", "%m/%d/%Y", "%b %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def applications(folder):
    out = []
    for f in sorted((folder / "Jobs").glob("Job Applications*.csv")):
        for r in rows(f):
            m = re.search(r"/jobs/view/(\d+)", r.get("Job Url", ""))
            d = parse_date(r.get("Application Date"))
            out.append({"date": d.isoformat() if d else "", "company": (r.get("Company Name") or "").strip(),
                        "title": (r.get("Job Title") or "").strip(), "job_id": m.group(1) if m else ""})
    return sorted(out, key=lambda a: a["date"], reverse=True)


def consistency(folder):
    """Where the LinkedIn profile and the master CV tell different stories (titles, dates, years)."""
    cv = yaml.safe_load((ROOT / "profile" / "master-cv.yaml").read_text(encoding="utf-8"))
    notes = []
    prof = (rows(folder / "Profile.csv") or [{}])[0]
    cv_years = re.search(r"(\d+)\+? years", re.sub(r"\*", "", cv.get("summary", "")))
    li_years = re.search(r"(\d+)\+? years", prof.get("Summary", "") + " " + prof.get("Headline", ""))
    if cv_years and li_years and cv_years.group(1) != li_years.group(1):
        notes.append(f"LinkedIn summary says {li_years.group(1)}+ years; your CV says {cv_years.group(1)}+ years.")
    def start_of(dates):
        d = parse_date(re.split(r"\s+-\s+", dates or "")[0].replace("January", "Jan").replace("February", "Feb")
                       .replace("March", "Mar").replace("April", "Apr").replace("August", "Aug").replace("September", "Sep")
                       .replace("October", "Oct").replace("November", "Nov").replace("December", "Dec")
                       .replace("June", "Jun").replace("July", "Jul"))
        return d

    cv_roles = [(e["company"], e["title"], e.get("dates", ""), start_of(e.get("dates", ""))) for e in cv.get("experience") or []]
    for p in rows(folder / "Positions.csv"):
        company, title = p.get("Company Name", ""), p.get("Title", "")
        dates = f"{p.get('Started On', '')} - {p.get('Finished On', '') or 'Present'}"
        li_start = parse_date(p.get("Started On"))
        same_co = [r for r in cv_roles if company.split()[0].lower() in r[0].lower()]
        if not same_co:
            notes.append(f"On LinkedIn, not on the CV: {title}, {company} ({dates}). Fine to leave off a CV; just be ready to mention it.")
            continue
        # the CV role at this company that starts closest to the LinkedIn role
        cv_co, cv_title, cv_dates, cv_start = min(
            same_co, key=lambda r: abs((r[3] - li_start).days) if r[3] and li_start else 9999)
        same_title = cv_title.lower().startswith(title.lower()) or title.lower().startswith(cv_title.lower())
        gap = abs((cv_start - li_start).days) if cv_start and li_start else 0
        if not same_title:
            notes.append(f"Title differs at {company}: LinkedIn \"{title}\" ({dates}) vs CV \"{cv_title}\" ({cv_dates}).")
        elif gap > 62:
            notes.append(f"Dates differ at {company}: LinkedIn {dates} vs CV {cv_dates} for \"{title}\".")
    return notes


def insights(folder, apps):
    lines = ["# What your LinkedIn data says", "",
             f"_Imported {datetime.now():%Y-%m-%d} from the LinkedIn data export. Rolewise reads only jobs, profile and "
             "connection counts; messages and account data are never read._", ""]
    by_year = collections.Counter(a["date"][:4] for a in apps if a["date"])
    recent = [a for a in apps if a["date"] >= "2026-01-01"]
    by_month = collections.Counter(a["date"][:7] for a in recent)
    agency = [a for a in recent if AGENCY.search(a["company"])]
    repeats = [(c, n) for c, n in collections.Counter(a["company"] for a in recent if a["company"]).most_common() if n >= 4]
    lines += ["## Application history",
              f"- {len(apps)} applications through LinkedIn since 2023: " + ", ".join(f"{y}: {n}" for y, n in sorted(by_year.items())) + ".",
              f"- {len(recent)} in 2026, by month: " + ", ".join(f"{m[5:]}/{m[:4]}: {n}" for m, n in sorted(by_month.items())) + ".",
              f"- {len(agency)} of the 2026 ones ({len(agency) * 100 // max(len(recent), 1)}%) went to recruitment agencies or "
              "job aggregators rather than the hiring company.",
              "- Companies applied to 4+ times in 2026: " + (", ".join(f"{c} ({n})" for c, n in repeats) or "none") + ".", ""]
    saved = sum(len(rows(f)) for f in (folder / "Jobs").glob("Saved Jobs*.csv"))
    alerts = rows(folder / "SavedJobAlerts.csv")
    prefs = (rows(folder / "Jobs" / "Job Seeker Preferences.csv") or [{}])[0]
    lines += ["## Job search setup on LinkedIn",
              f"- {saved} saved jobs; {len(alerts)} job alert(s): " +
              "; ".join(re.search(r"keywords=([^,}]+)", a.get("QUERY_CONTEXT", "")).group(1) if re.search(r"keywords=([^,}]+)", a.get("QUERY_CONTEXT", "")) else "?"
                        for a in alerts) + ".",
              f"- Open-to-work preferences: locations {prefs.get('Locations', '?')}; titles {prefs.get('Job Titles', '?')}; "
              f"open to recruiters: {prefs.get('Open To Recruiters', '?')}; visibility: {prefs.get('Open Candidate Visibility', '?')}.", ""]
    notes = consistency(folder)
    lines += ["## Profile vs CV (worth aligning: recruiters and background checks compare them)"]
    lines += [f"- {n}" for n in notes] or ["- No differences found."]
    conns = rows(folder / "Connections.csv")
    lines += ["", "## Network", f"- {len(conns)} connections imported for referral suggestions (kept on this laptop only)."]
    return "\n".join(lines) + "\n", notes


def main(folder):
    sys.stdout.reconfigure(encoding="utf-8")
    folder = Path(folder)
    if not (folder / "Connections.csv").exists():
        sys.exit(f"{folder}: no Connections.csv here. Point me at the unzipped export folder.")
    shutil.copy2(folder / "Connections.csv", ROOT / "profile" / "connections.csv")
    apps = applications(folder)
    (ROOT / "tracker" / "linkedin-applied.json").write_text(json.dumps(apps, indent=0, ensure_ascii=False), encoding="utf-8")
    report, notes = insights(folder, apps)
    (ROOT / "coach" / "linkedin-insights.md").write_text(report, encoding="utf-8")
    print(f"connections -> profile/connections.csv ({len(rows(folder / 'Connections.csv'))})")
    print(f"past applications -> tracker/linkedin-applied.json ({len(apps)})")
    print(f"insights -> coach/linkedin-insights.md ({len(notes)} profile/CV differences)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
