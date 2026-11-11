"""Build apply kits for the "Rolewise Fill" Chrome add-on (extension/).

Usage: .venv/Scripts/python scripts/build_kits.py            # every job with a CV (shortlisted..ready)
       .venv/Scripts/python scripts/build_kits.py <job id> ...

For each job it writes extension/kits/<id>.json and copies the CV + cover letter into extension/kits/files/<id>/,
then rewrites extension/kits/index.json (url -> kit) so the add-on can match the open form to its job.
Answers come from profile/answers.yaml; a job can override or add questions in applications/<id>/kit.yaml:
  answers:            # same keys as below, e.g. salary: "100,000-110,000 EUR"
  questions:          # free-text or choice questions specific to this form
    - match: ["why", "interest"]      # label keywords (all must appear, case-insensitive)
      value: "..."
"""
import json
from datetime import date, timedelta
import re
import shutil
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from userconf import USER, current_role, disciplines, education, file_glob  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
EXT = ROOT / "extension"
KITS = EXT / "kits"
ACTIVE = {"shortlisted", "preparing", "ready"}
REGION_WORDS = {   # job location words -> region key (matches user.yaml home_region and answers.yaml per-region keys)
    "uae": ("uae", "dubai", "abu dhabi", "sharjah", "united arab emirates"),
    "uk": ("london", "united kingdom", "uk", "england", "scotland", "wales", "manchester", "edinburgh", "bristol"),
    "us": ("united states", "usa", "new york", "san francisco", "seattle", "boston", "chicago", "austin"),
    "in": ("india", "bangalore", "bengaluru", "mumbai", "pune", "delhi", "gurgaon", "gurugram", "hyderabad"),
    "eu": ("ireland", "dublin", "germany", "berlin", "munich", "netherlands", "amsterdam", "france", "paris", "spain",
           "madrid", "barcelona", "portugal", "lisbon", "sweden", "denmark", "finland", "belgium", "austria",
           "italy", "poland", "europe", "emea", "copenhagen", "stockholm", "oslo", "norway", "helsinki", "warsaw", "krakow",
           "prague", "czech", "vienna", "zurich", "geneva", "switzerland", "brussels", "milan", "rome", "valencia",
           "porto", "hamburg", "frankfurt", "cologne", "rotterdam", "the hague", "utrecht", "luxembourg", "tallinn",
           "estonia", "riga", "vilnius", "lithuania", "bucharest", "romania", "budapest", "athens", "greece", "cork",
           "galway", "lyon", "toulouse", "nice", "remote europe", "eu"),
    "gcc": ("saudi", "riyadh", "jeddah", "qatar", "doha", "bahrain", "manama", "kuwait", "oman", "muscat"),
    "other": ("singapore", "australia", "sydney", "melbourne", "canada", "toronto", "vancouver", "tokyo", "japan",
              "hong kong", "brazil", "mexico", "south africa", "cape town", "nairobi", "lagos", "cairo", "istanbul", "tel aviv"),
}
HOME = USER.get("home_region") or "other"


def region_of(job):
    if job.get("region"):
        return job["region"]
    loc = (job.get("location") or "").lower()
    for region, words in REGION_WORDS.items():
        if any(re.search(r"\b" + re.escape(w) + r"\b", loc) for w in words):
            return region
    return HOME   # remote / unknown: answer as the user is today


# Queue groups, in the user's order of preference (preferences.yaml fit_scoring.location_points)
GROUP = {"uae": "Dubai / UAE", "eu": "Europe", "uk": "Europe", "in": "India", "us": "US"}


def group(j):
    return "Remote" if re.search(r"\bremote\b", j.get("location") or "", re.I) and region_of(j) not in GROUP else GROUP.get(region_of(j), "Other")


def age_days(j):
    """Days since the job was posted (date_found when the posting date isn't known)."""
    d = str(j.get("posted") or j.get("date_found") or "")[:10]
    try:
        return (date.today() - date.fromisoformat(d)).days
    except ValueError:
        return None


# Early applicants get read first: new postings jump the queue, ones over 3 weeks old sink to "Older".
FRESH_DAYS, OLD_DAYS = 3, 21


def freshness(j):
    age = age_days(j)
    if age is None:
        return {"age": None, "urgency": ""}
    urgency = "new" if age <= FRESH_DAYS else "week" if age <= 10 else "old" if age > OLD_DAYS else ""
    return {"age": age, "posted": str(j.get("posted") or "")[:10], "urgency": urgency}


def city_of(job):
    loc = (job.get("location") or "").split(",")[0].strip()
    return loc or "the role's city"


# Label pattern (JS regex, matched on the lower-cased label) -> answer key. Order matters: specific first.
# Written to extension/kits/rules.json, which the add-on reads on every fill (no extension reload needed).
RULES = [
    [r"preferred (first )?name", None],
    [r"^country$|country code", None],   # phone-country picker; it sets itself from the phone number
    [r"first\s*name|given name", "first_name"],
    [r"last\s*name|surname|family name", "last_name"],
    [r"email me|future (job )?openings|job alerts|keep me (updated|informed)", "future_emails"],
    # Free-text questions that mention "phone" or "email" in passing: before the contact rules below
    [r"how many years|years of (work |relevant |professional )?experience|years' experience", "years"],
    [r"adjustment|accommodat|if a (video|phone) (or (video|phone) )?interview is not", "adjustments"],
    [r"what interests you|why (do you want|are you interested|would you like)|why .{0,40}(join|apply|this role|\bus\b)|motivat|excites? you|excited about|your interest (in )?working|interest in (this|the) (role|position|company)", "why"],
    [r"whatsapp", "whatsapp"],
    [r"\bsms\b|text messages", None],
    [r"e-?mail", "email"],
    [r"phone|mobile", "phone"],
    [r"linkedin", "linkedin"],
    [r"github", None],
    [r"website|portfolio|personal site", "website"],
    [r"iran|cuba|north korea|sanction", "export_sanctioned"],
    [r"additional citizenship", "export_additional"],
    [r"citizenship.*first|first.*citizenship", "export_first"],
    [r"hispanic|latin[oa]", "hispanic"],
    [r"gender|identify as (a )?(man|woman)", "gender"],
    [r"ethnic|race\b|racial", "ethnicity"],
    [r"disabilit", "disability"],
    [r"veteran|military", "veteran"],
    [r"sexual orientation", "sexual_orientation"],
    [r"pronoun", "pronouns"],
    [r"criminal|convict", "criminal"],
    [r"transgender|neurodiver|household earner", "diversity"],
    [r"brighthire|record(ed|ing)? (the |our |your )?(interview|conversation|call)|interview recording", "recording_consent"],
    # Standing rule (2026-10-29): standard consent and data-sharing questions get a yes, as a dropdown or a tick box.
    [r"\bconsent\b|do you (agree|acknowledge)|privacy (policy|notice|statement)|data (protection|processing|retention|sharing)|gdpr|"
     r"(share|shared|sharing|transfer) (my |your )?(application|information|data|details)", "consent"],
    # "Are you currently residing in this country?": Yes only when the job is in the country the user lives in.
    [r"(currently )?(resid(e|ing)|liv(e|ing)|based) in (this|the) (country|location|city|region)|"
     r"do you (currently )?(live|reside) in\b", "lives_in_job_country"],
    # "Are you authorised to work…?" first: its label often mentions sponsorship too ("we sponsor some roles").
    [r"authori[sz]ed to work|right to work|eligible to work|legally (able|permitted) to work|work permit", "authorised"],
    [r"(require|need|will you).{0,60}sponsor|sponsorship (now|in the future)|visa sponsorship", "sponsorship"],
    [r"relocat", "relocate"],
    [r"remote location|work remotely|remote work|fully remote", "remote"],
    [r"(interested in|prefer).{0,40}(office|location)s?\b.{0,30}(following|below)|following office locations|which (of our )?offices?", "job_office"],   # the job's own city
    [r"hybrid|in-?office|on-?site|office location|days per week", "hybrid"],
    [r"previously (worked|been employed)|former employee|worked (for|at) .{0,40}before|ever worked|ever been employed|employed by", "previously_worked"],
    [r"if (you )?(selected|chose|picked|answered) .{0,3}other|if other", None],   # follow-up box: only when "Other" was picked
    [r"how did you (hear|find|learn|get to know|come across|discover)|get to know (us|about)|where did you (hear|find)|source", "heard"],
    [r"country (where|in which) you (currently )?reside|country of residence|country (do )?you live|what is your location|"
     r"which country|where do you (currently )?live", "residence_country"],
    [r"^school\b|university|institution", "school"],
    [r"^degree\b", "degree"],
    [r"discipline|field of study|major", "discipline"],
    [r"location \(city\)|^city\b", "city"],
    [r"current (or (most recent|previous) )?(company|employer)|(most recent|previous) (company|employer)|current organi[sz]ation", "current_company"],
    [r"(current|most recent|latest|previous)( or (most recent|previous|latest))? (job )?(title|role|position)", "current_title"],
    [r"salary|compensation|pay expectation|expected (pay|package)", "salary"],
    [r"notice period", "notice"],
    [r"start date|when can you start|earliest (start|availability)|availability", "start_date"],
    [r"current location|where are you (currently )?(based|located)|^location\b|city of residence", "location"],
    [r"full name|^name\b|your name", "full_name"],
]

COUNTRY_ALIASES = [
    (("dublin", "ireland"), ["Ireland"]),
    (("london", "england", "united kingdom", "uk"), ["UK", "United Kingdom"]),
    (("berlin", "cologne", "munich", "germany"), ["Germany"]),
    (("amsterdam", "netherlands"), ["The Netherlands", "Netherlands"]),
    (("paris", "france"), ["France"]),
    (("zurich", "switzerland"), ["Switzerland"]),
    (("dubai", "abu dhabi", "sharjah", "uae", "united arab emirates"), ["UAE", "United Arab Emirates"]),
    (("spain", "madrid", "barcelona"), ["Spain"]),
    (("portugal", "lisbon"), ["Portugal"]),
    (("united states", "usa", "new york", "san francisco", "seattle", "boston"), ["United States", "USA"]),
    (("india", "bangalore", "bengaluru", "mumbai", "pune", "delhi", "hyderabad"), ["India"]),
    (("canada", "toronto", "vancouver"), ["Canada"]),
    (("australia", "sydney", "melbourne"), ["Australia"]),
    (("singapore",), ["Singapore"]),
    (("saudi", "riyadh", "jeddah"), ["Saudi Arabia"]),
]


def job_country(job):
    loc = (job.get("location") or "").lower()
    for words, names in COUNTRY_ALIASES:
        if any(w in loc for w in words):
            return names
    return []


def base_answers(profile, job):
    c, w = profile["contact"], profile["work_authorization"]
    comp, avail = profile.get("compensation", {}), profile.get("availability", {})
    std = profile.get("standard_form_answers", {})
    exp = profile.get("citizenship", {}).get("export_control", {})
    div = profile.get("diversity") if isinstance(profile.get("diversity"), dict) else {}
    asList = lambda v: [str(x) for x in v] if isinstance(v, list) else ([str(v)] if v else [])
    region = region_of(job)
    home = region == HOME

    def per_region(by_region, src, key, default):
        """Per-region value: the `*_by_region` map first, then older `<key>_<region>` fields (UK falls back to EU)."""
        keys = [f"{key}_{region}"] + ([f"{key}_eu"] if region == "uk" else [])
        return (by_region or {}).get(region) or next((src[k] for k in keys if src.get(k)), None) or default

    first, last = (c["full_name"].split(" ", 1) + [""])[:2]
    here = c.get("location", "")
    away = c.get("location_relocating") or c.get("location_eu") or "<current location> (relocating to <city>)"
    location = here if home else away.replace("<current location>", here).replace("<city>", city_of(job))
    phone = c.get("phone", "") if home else per_region(c.get("phone_by_region"), c, "phone", c.get("phone", ""))
    salary = per_region(comp.get("expected_by_region"), comp, "expected_salary", comp.get("fallback", ""))
    salary = re.sub(r"\s*\(.*?\)", "", salary.split("if a number is required:")[-1]).strip() or "Negotiable"
    # Dropdown forms list salary bands: also give the floor as a yearly number ("*band:N*"), and monthly as backup.
    floor = next((float(x.replace(",", "").replace(" ", "")) * (1000 if x.lower().endswith("k") else 1)
                  for x in re.findall(r"\d[\d, ]*\d(?:k\b)?|\d+k\b", salary, re.I)), None)
    monthly = bool(re.search(r"month", salary, re.I))
    salary_answer = [salary] + ([f"*band:{int(floor * 12 if monthly else floor)}*", f"*band:{int(floor if monthly else floor / 12)}*"]
                                if floor and floor >= 1000 else [])
    parts = [p.strip() for p in here.split(",") if p.strip()]
    country = job_country({"location": here}) or parts[-1:]
    return {
        "first_name": first, "last_name": last, "full_name": c["full_name"], "email": c["email"],
        "phone": phone,
        "linkedin": c.get("linkedin", ""), "website": (c.get("websites") or [""])[0], "location": location,
        "current_company": current_role()[0], "current_title": current_role()[1],
        "city": parts[:1], "residence_country": country,
        # education from master-cv.yaml (highest first)
        "school": education()[0],
        "degree": education()[1],
        "job_country": job_country(job),
        "discipline": disciplines(),
        "salary": salary_answer, "notice": avail.get("notice_period", "Immediately available"),
        "start_date": avail.get("start_date", "Immediately"),
        # choice answers: list of option prefixes to try, in order
        # Right to work only where answers.yaml says so (<region>_authorized: "Yes ..."); elsewhere the form flags it.
        **({"authorised": ["I am authorised", "Yes"],
            "sponsorship": [w.get(f"requires_sponsorship_{region}") or "No"]}
           if str(w.get(f"{region}_authorized") or "").lower().startswith("yes")
           else {"sponsorship": [w[f"requires_sponsorship_{region}"]]} if w.get(f"requires_sponsorship_{region}") else {}),
        "job_office": [city_of(job)] + job_country(job),
        "lives_in_job_country": ["Yes" if {x.lower() for x in country} & {x.lower() for x in job_country(job)} else "No"],
        "consent": ["Yes", "I consent", "I agree", "I acknowledge", "Agree", "Accept"],
        "relocate": ["Yes"],
        "hybrid": ["Yes"], "previously_worked": ["No"],
        "heard": [std.get("how_did_you_hear", "Job Board"), "Job Board", "Company website", "Careers", "LinkedIn",
                  "Other", "*any*"],   # low-stakes: if none fits, the first real option
        "future_emails": ["Yes"],
        "whatsapp": [std.get("whatsapp_opt_in", "Yes")], "remote": [std.get("remote_work_preference", "No")],
        "recording_consent": ["Yes", "I consent", "I agree", "I acknowledge"], "location_choice": [std.get("location_dropdown_no_uae_option", "EMEA - Other"), "Other"],
        "export_sanctioned": [exp.get("sanctioned_country_citizen_or_resident", "No")],
        "export_additional": ["N/A"], "export_first": ["N/A"],
        "diversity": ["I don't wish", "Prefer not", "Decline", "I do not wish"],
        # Diversity answers the user chose to give (answers.yaml diversity); anything unset stays "prefer not"
        **{key: (asList(div.get(key)) or []) + ["I don't wish", "Prefer not", "Decline", "I do not wish"]
           for key in ("gender", "ethnicity", "hispanic", "disability", "veteran", "sexual_orientation", "pronouns")},
        "adjustments": std.get("interview_adjustments", "No adjustments needed, thank you."),
        # A legal declaration: answered only when the user has saved it (answers.yaml standard_form_answers)
        **({"criminal": [std["criminal_convictions"]]} if std.get("criminal_convictions") else {}),
        # "How many years of experience with X?" (LinkedIn Easy Apply asks these a lot): only topics the user stated
        "years": {**{str(k).lower(): v for k, v in (profile.get("experience_years") or {}).items()},
                  **({"total": profile["experience"]["years_total"]} if (profile.get("experience") or {}).get("years_total") else {})},
    }


_SR = {}


def sr_form(company, posting_id):
    """The SmartRecruiters apply page for a posting (its publication uuid comes from the public postings API)."""
    if (company, posting_id) not in _SR:
        try:
            import urllib.request
            with urllib.request.urlopen(f"https://api.smartrecruiters.com/v1/companies/{company}/postings/{posting_id}", timeout=8) as r:
                uuid = json.loads(r.read()).get("uuid")
            _SR[company, posting_id] = (f"https://jobs.smartrecruiters.com/oneclick-ui/company/{company}/publication/{uuid}"
                                        f"?dcr_ci={company}") if uuid else ""
        except Exception:
            _SR[company, posting_id] = ""
    return _SR[company, posting_id]


def form_urls(job):
    """Kit URLs, the form first: a Lever or Ashby posting page has no form until you click Apply."""
    urls = []
    for u in (job.get("apply_url"), job.get("url")):
        if not u:
            continue
        base = u.split("?")[0].rstrip("/")
        sr = re.match(r"https://jobs\.smartrecruiters\.com/([^/]+)/(\d{6,})", base)
        if sr and sr_form(*sr.groups()):   # SmartRecruiters: the posting page has no form; open the apply page itself
            urls.append(sr_form(*sr.groups()))
        if re.match(r"https://jobs\.lever\.co/[^/]+/[0-9a-f-]{20,}$", base):
            urls.append(base + "/apply")
        elif re.match(r"https://jobs\.ashbyhq\.com/[^/]+/[0-9a-f-]{20,}$", base):
            urls.append(base + "/application")
        urls.append(u)
    return list(dict.fromkeys(urls))


def why_from_letter(folder):
    """'What interests you about X?': the cover letter's opening paragraph (already written and checked for this job)."""
    letter = folder / "cover-letter.md"
    if not letter.exists():
        return None
    paras = [p.strip() for p in re.split(r"\n\s*\n", letter.read_text(encoding="utf-8")) if p.strip()]
    body = [p for p in paras if not p.lower().startswith(("dear ", "kind regards", "best", "sincerely"))]
    return " ".join(body[:2]) if body else None


def cv_context(folder, limit=2500):
    """Facts for the add-on's "Draft with Claude" link: the job's tailored CV (or the master), as short plain lines."""
    src = folder / "cv.yaml" if (folder / "cv.yaml").exists() else ROOT / "profile" / "master-cv.yaml"
    cv = yaml.safe_load(src.read_text(encoding="utf-8")) or {}
    plain = lambda s: re.sub(r"\*\*", "", str(s or "")).strip()
    lines = [plain(cv.get("summary"))]
    for role in (cv.get("experience") or []) + (cv.get("projects") or []):
        lines.append(f"{role.get('title', '')} at {role.get('company', '')} ({role.get('dates', '')}):".replace(" at  ", " "))
        lines += [f"- {plain(b.get('text'))}" for b in role.get("bullets") or [] if not b.get("hide")]
    out = "\n".join(l for l in lines if l)
    return out[:limit]


def debriefed(job):
    """Notes or a debrief saved since the last interview round (or in the last 10 days when the round date is unknown)."""
    folder = ROOT / "applications" / job["id"]
    dates = sorted(p.stem.split("-", 2)[-1].replace("notes-", "") for p in folder.glob("debrief*.md"))
    if not dates:
        return False
    since = job.get("last_interview") or (date.today() - timedelta(days=10)).isoformat()
    return dates[-1] >= since


def jd_excerpt(folder, limit=3500):
    """The job description as plain text, for drafting answers in the form."""
    jd = folder / "jd.md"
    if not jd.exists():
        return ""
    text = re.sub(r"<[^>]+>", " ", jd.read_text(encoding="utf-8"))
    return re.sub(r"\s+", " ", text).strip()[:limit]


def build(job, profile):
    folder = ROOT / "applications" / job["id"]
    files = {}
    for kind, pattern in (("cv", file_glob("CV")), ("cover_letter", file_glob("Cover Letter"))):
        found = sorted(p for p in folder.glob(pattern) if p.suffix.lower() in (".pdf", ".docx"))
        pdf = [p for p in found if p.suffix.lower() == ".pdf"]
        pick = (pdf or found or [None])[0]
        if pick:
            dest = KITS / "files" / job["id"] / pick.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(pick, dest)
            files[kind] = f"kits/files/{job['id']}/{pick.name}"
    if "cv" not in files:
        return None
    answers = base_answers(profile, job)
    answers["why"] = why_from_letter(folder) or answers.get("why")
    questions = []
    extra = folder / "kit.yaml"
    if extra.exists():
        override = yaml.safe_load(extra.read_text(encoding="utf-8")) or {}
        answers.update(override.get("answers") or {})
        questions = override.get("questions") or []
    kit = {"id": job["id"], "company": job["company"], "title": job["title"], "status": job["status"],
           "fit": job.get("fit_score"),
           "urls": form_urls(job),
           "files": files, "answers": answers, "questions": questions, "context": cv_context(folder), "jd": jd_excerpt(folder)}
    (KITS / f"{job['id']}.json").write_text(json.dumps(kit, indent=2, ensure_ascii=False), encoding="utf-8")
    return kit


def main(ids):
    sys.stdout.reconfigure(encoding="utf-8")
    profile = yaml.safe_load((ROOT / "profile" / "answers.yaml").read_text(encoding="utf-8"))
    jobs = json.loads((ROOT / "tracker" / "applications.json").read_text(encoding="utf-8"))
    KITS.mkdir(parents=True, exist_ok=True)
    chosen = [j for j in jobs if (j["id"] in ids if ids else j["status"] in ACTIVE)]
    for j in chosen:
        kit = build(j, profile)
        print(f"{'kit' if kit else 'no CV, skipped'}: {j['id']}")
    index = []
    status = {j["id"]: j["status"] for j in jobs}
    # How the job is applied to, for the add-on's queue: LinkedIn Easy Apply, or the company's own site
    def apply_mode(j):
        ea = str(j.get("easy_apply", "")).lower()
        on_linkedin = "linkedin.com" in (j.get("apply_url") or j.get("url") or "")
        if ea in ("yes", "true"):
            return "easy-apply"
        if ea in ("no", "false") and on_linkedin:
            return "company-site"
        return "linkedin" if on_linkedin else ""   # not known yet: the add-on says how to tell
    mode = {j["id"]: apply_mode(j) for j in jobs}   # the tracker is the truth: applied/skipped jobs leave the queue
    by_id = {j["id"]: j for j in jobs}
    for path in sorted(KITS.glob("*.json")):
        if path.name in ("index.json", "rules.json", "status.json"):
            continue
        k = json.loads(path.read_text(encoding="utf-8"))
        index.append({"id": k["id"], "label": f"{k['company']} · {k['title']}", "urls": k["urls"],
                      "status": "later" if (by_id.get(k["id"]) or {}).get("snooze_until", "") > date.today().isoformat()
                      else status.get(k["id"], k.get("status")),   # "Later" in the Rolewise Inbox hides it for 3 days
                      "fit": (by_id.get(k["id"]) or {}).get("fit_score", k.get("fit")),
                      "mode": mode.get(k["id"], ""), "group": group(by_id.get(k["id"]) or {}),
                      "location": (by_id.get(k["id"]) or {}).get("location") or "",
                      "salary_eur": (by_id.get(k["id"]) or {}).get("salary_eur"),
                      **freshness(by_id.get(k["id"]) or {})})
    (KITS / "index.json").write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    (KITS / "rules.json").write_text(json.dumps(RULES, indent=1, ensure_ascii=False), encoding="utf-8")
    (KITS / "status.json").write_text(json.dumps({"paused": bool(USER.get("paused")), "paused_until": USER.get("paused_until") or "",
                                                  "email": USER.get("email", ""), "inbox_url": USER.get("inbox_url", ""),
                                                  "interviews": [{"id": j["id"], "label": f"{j['company']} · {j['title']}",
                                                                  "debriefed": debriefed(j)}
                                                                 for j in jobs if j["status"] in ("screening", "interviewing")]},
                                                 indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"index: {len(index)} kits")


if __name__ == "__main__":
    main(sys.argv[1:])
