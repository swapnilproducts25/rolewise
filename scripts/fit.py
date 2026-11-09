"""Final fit score = the role/skills fit from discover, plus the user's location preference and the pay on offer.

  fit_score = 0.75 x fit_base  +  location points (preferences.yaml fit_scoring.location_points)
                               +  salary points (0-10: listed pay against the region's floor; 5 when not listed)

fit_base is the score discover gave (kept on first run, so this can run any number of times). Pay: a stated salary
(the job's `salary` field, else applications/<id>/jd.md) scores up to 10; without one, discover's market estimate
`salary_estimate_eur` (levels.fyi / Glassdoor for that company, level and city) scores up to 8; neither: 5.

Usage: .venv/Scripts/python scripts/fit.py [--show]
"""
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_kits import REGION_WORDS, region_of  # noqa: E402

TRACKER = ROOT / "tracker" / "applications.json"
PREFS = yaml.safe_load((ROOT / "profile" / "preferences.yaml").read_text(encoding="utf-8")) or {}
SCORING = PREFS.get("fit_scoring") or {}
LOCATION_POINTS = SCORING.get("location_points") or {"uae": 15, "eu": 10, "uk": 10, "remote": 12, "in": 5, "other": 3}
SALARY_MAX = SCORING.get("salary", 10)
OPEN = {"found", "shortlisted", "preparing", "ready"}

# Rough EUR rates: enough to rank pay, not to quote it.
EUR = {"eur": 1, "€": 1, "gbp": 1.17, "£": 1.17, "usd": 0.92, "$": 0.92, "aed": 0.25, "chf": 1.05, "sek": 0.088,
       "dkk": 0.134, "nok": 0.085, "pln": 0.23, "inr": 0.0108, "₹": 0.0108, "sar": 0.245}
CUR = r"(€|£|\$|₹|eur|gbp|usd|aed|chf|sek|dkk|nok|pln|inr|sar)"
NUM = r"(\d{1,3}(?:[,.\s]\d{3})+|\d+(?:\.\d+)?\s?k\b)"
PAY_WORDS = re.compile(r"salary|compensation|pay\b|base|range|per (year|annum|month)|annual|ote|package|ctc|gross", re.I)


def floors():
    """Each region's floor in EUR per year, from preferences.yaml compensation."""
    comp = PREFS.get("compensation") or {}
    out = {}
    if comp.get("UAE_min_monthly_AED"):
        out["uae"] = comp["UAE_min_monthly_AED"] * 12 * EUR["aed"]
    if comp.get("EU_min_annual_EUR"):
        out["eu"] = out["uk"] = comp["EU_min_annual_EUR"]
    if comp.get("India_min_annual_INR"):
        out["in"] = comp["India_min_annual_INR"] * EUR["inr"]
    return out


def to_number(s):
    s = s.lower().replace(" ", "")
    if s.endswith("k"):
        return float(s[:-1]) * 1000
    return float(re.sub(r"[,.](?=\d{3}\b)", "", s).replace(",", ""))


def salary_eur(text):
    """Highest pay figure in the text, in EUR per year (None if no salary is stated)."""
    best = None
    t = text.lower()
    hits = [(m.start(), m.group(1), m.group(2)) for m in re.finditer(CUR + r"\s?" + NUM, t)]
    hits += [(m.start(), m.group(2), m.group(1)) for m in re.finditer(NUM + r"\s?" + CUR, t)]
    for pos, cur, num in hits:
        if not PAY_WORDS.search(t[max(0, pos - 160):pos + 80]):
            continue
        try:
            v = to_number(num)
        except ValueError:
            continue
        if cur == "aed" and v < 150000 or re.search(r"per month|monthly|/ ?month|a month", t[pos:pos + 60]):
            v *= 12
        eur = v * EUR[cur]
        if 15000 <= eur <= 600000:
            best = max(best or 0, eur)
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(?:-|to|–)?\s*(\d+(?:\.\d+)?)?\s*(lpa|lakhs?)", t):   # Indian "40-60 LPA"
        best = max(best or 0, float(m.group(2) or m.group(1)) * 100000 * EUR["inr"])
    return round(best) if best else None


def salary_points(job, region, floor_by_region):
    pay, top = job.get("salary_eur"), SALARY_MAX
    if not pay and job.get("salary_estimate_eur"):
        pay, top = job["salary_estimate_eur"], SALARY_MAX * 0.8   # an estimate counts a little less than a stated salary
    floor = floor_by_region.get(region)
    if not pay or not floor:
        return round(SALARY_MAX / 2), pay
    r = pay / floor
    share = 1.0 if r >= 1.4 else 0.8 if r >= 1.2 else 0.6 if r >= 1.0 else 0.3 if r >= 0.85 else 0.0
    return round(top * share), pay


def location_key(job):
    """The job's place: a named region wins ("Remote, UK/NL" is a UK/EU job); remote with no place: "remote"."""
    loc = (job.get("location") or "").lower()
    named = next((r for r, words in REGION_WORDS.items() if any(re.search(r"\b" + re.escape(w) + r"\b", loc) for w in words)), None)
    if named or job.get("region"):
        region = named or job["region"]
    elif re.search(r"\bremote\b", loc + " " + (job.get("work_mode") or "").lower()):
        return "remote"
    else:
        region = region_of(job)
    return region if region in LOCATION_POINTS else "other"


def main(show=False):
    jobs = json.loads(TRACKER.read_text(encoding="utf-8"))
    floor_by_region = floors()
    for j in jobs:
        if j.get("status") not in OPEN or not isinstance(j.get("fit_score"), (int, float)):
            continue
        j.setdefault("fit_base", j["fit_score"])
        if j.get("salary") and not j.get("salary_eur"):
            j["salary_eur"] = salary_eur("salary " + str(j["salary"]))
        if not j.get("salary_eur"):
            jd = ROOT / (j.get("folder") or f"applications/{j['id']}") / "jd.md"
            if jd.exists():
                j["salary_eur"] = salary_eur(jd.read_text(encoding="utf-8", errors="ignore"))
        loc = location_key(j)
        sal, pay = salary_points(j, region_of(j), floor_by_region)
        j["fit_location"], j["fit_salary"] = LOCATION_POINTS.get(loc, LOCATION_POINTS.get("other", 3)), sal
        j["fit_score"] = min(100, round(0.75 * j["fit_base"] + j["fit_location"] + sal))
        if show:
            print(f"{j['fit_score']:>3} (base {j['fit_base']}, {loc} +{j['fit_location']}, pay +{sal}"
                  f"{f' ~EUR {pay:,}' if pay else ''})  {j['company']} - {j['title']}")
    TRACKER.write_text(json.dumps(jobs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main("--show" in sys.argv)
