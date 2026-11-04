"""Referral matcher: find the user's own LinkedIn connections at the companies they're applying to.

Usage: .venv/Scripts/python scripts/referrals.py [--min-fit 75]
Input:  profile/connections.csv (LinkedIn → Settings → Data privacy → Get a copy of your data → Connections).
        Kept on the laptop only (gitignored): it holds other people's details.
Output: for each active job with a match, applications/<id>/referral.md (best 2 people + why) and a JSON summary
        on stdout for the daily run, which drafts ONE short personal message per suggestion. Nothing is ever sent.
Rules:  only jobs with fit >= --min-fit (or interviews), skip people asked in the last 60 days (tracker
        field referral_asked = "<name> YYYY-MM-DD; ..."), at most 2 suggestions per job.
"""
import csv
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONNECTIONS = ROOT / "profile" / "connections.csv"
ACTIVE = {"shortlisted", "preparing", "ready", "applied", "screening", "interviewing"}
SUFFIXES = r"\b(inc|ltd|llc|gmbh|bv|plc|sa|ag|group|technologies|technology|holding|holdings|company|co|uae|me)\b"
ALIASES = {"intercom": ["fin"], "fin": ["intercom"], "tiqets": ["expedia group", "expedia"]}


def norm(name):
    name = re.sub(r"\(.*?\)", " ", (name or "").lower())
    name = re.sub(SUFFIXES, " ", re.sub(r"[^a-z0-9 ]", " ", name))
    return re.sub(r"\s+", " ", name).strip()


def company_keys(job):
    raw = job["company"]
    keys = {norm(raw)}
    keys |= {norm(p) for p in re.findall(r"\((.*?)\)", raw) if not p.lower().startswith("via")}
    for k in list(keys):
        keys |= set(ALIASES.get(k, []))
    return {k for k in keys if len(k) >= 3}


def role_score(position):
    p = (position or "").lower()
    if re.search(r"recruit|talent|people partner|hr business", p):
        return 3, "recruiter: can route you straight to the hiring team"
    if re.search(r"product (manager|lead|director|owner)|head of product|vp product|cpo|chief product", p):
        return 3, "in product: can refer you and knows the team"
    if re.search(r"director|head of|vp|chief|founder|general manager|engineering manager", p):
        return 2, "senior there: a referral carries weight"
    return 1, "works there: can refer you through the internal system"


def load_connections():
    lines = CONNECTIONS.read_text(encoding="utf-8-sig").splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("First Name"))
    return list(csv.DictReader(lines[start:]))


def recently_asked(job):
    asked = {}
    for part in (job.get("referral_asked") or "").split(";"):
        m = re.match(r"\s*(.+?)\s+(\d{4}-\d{2}-\d{2})\s*$", part)
        if m:
            asked[m.group(1).lower()] = datetime.strptime(m.group(2), "%Y-%m-%d").date()
    return asked


def main(min_fit):
    sys.stdout.reconfigure(encoding="utf-8")
    if not CONNECTIONS.exists():
        sys.exit("No profile/connections.csv yet: LinkedIn → Settings → Data privacy → Get a copy of your data → "
                 "Connections. Save the emailed Connections.csv as profile/connections.csv.")
    people = load_connections()
    jobs = json.loads((ROOT / "tracker" / "applications.json").read_text(encoding="utf-8"))
    asked_anywhere = {}
    for j in jobs:
        asked_anywhere.update(recently_asked(j))
    out = []
    for job in jobs:
        if job["status"] not in ACTIVE or ((job.get("fit_score") or 0) < min_fit and job["status"] != "interviewing"):
            continue
        keys = company_keys(job)
        matches = []
        for p in people:
            ck = norm(p.get("Company"))
            if not ck or not any(ck == k or ck.startswith(k + " ") or k.startswith(ck + " ") for k in keys):
                continue
            name = f"{p.get('First Name', '').strip()} {p.get('Last Name', '').strip()}".strip()
            last = asked_anywhere.get(name.lower())
            if last and (date.today() - last).days < 60:
                continue
            score, why = role_score(p.get("Position"))
            matches.append({"name": name, "position": p.get("Position", ""), "url": p.get("URL", ""),
                            "connected_on": p.get("Connected On", ""), "score": score, "why": why})
        if not matches:
            continue
        best = sorted(matches, key=lambda m: -m["score"])[:2]
        folder = ROOT / "applications" / job["id"]
        folder.mkdir(parents=True, exist_ok=True)
        lines = [f"# Referral options: {job['company']} · {job['title']}", ""]
        for m in best:
            lines += [f"## {m['name']} · {m['position']}", f"- Why: {m['why']}",
                      f"- Connected since: {m['connected_on']}", f"- LinkedIn: {m['url']}", ""]
        lines += ["## Message (drafted by the daily run; the user sends it on LinkedIn)", "", "_to be drafted_"]
        path = folder / "referral.md"
        if not path.exists() or "_to be drafted_" in path.read_text(encoding="utf-8"):
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        out.append({"job": job["id"], "company": job["company"], "title": job["title"],
                    "fit": job.get("fit_score"), "status": job["status"], "people": best})
    # One ask per company: several roles at the same company share one person and one message.
    by_company = {}
    for r in out:
        key = norm(r["company"])
        c = by_company.setdefault(key, {"company": r["company"], "jobs": [], "people": r["people"], "fit": 0,
                                        "interviewing": False})
        c["jobs"].append({"id": r["job"], "title": r["title"], "fit": r["fit"], "status": r["status"]})
        c["fit"] = max(c["fit"], r["fit"] or 0)
        c["interviewing"] |= r["status"] == "interviewing"
    ranked = sorted(by_company.values(), key=lambda c: (not c["interviewing"], -c["fit"]))
    print(json.dumps(ranked, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    args = sys.argv[1:]
    main(int(args[args.index("--min-fit") + 1]) if "--min-fit" in args else 75)
