"""Who this Rolewise install belongs to: profile/user.yaml, plus a few facts derived from profile/master-cv.yaml.

    from userconf import USER, file_name, current_role, education, past_employers
"""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
USER = yaml.safe_load((ROOT / "profile" / "user.yaml").read_text(encoding="utf-8")) or {}


def _cv():
    path = ROOT / "profile" / "master-cv.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}


def file_name(kind, company, ext="docx"):
    """kind = 'CV' or 'Cover Letter' -> '<prefix> - CV - <Company>.docx'."""
    return f"{USER.get('file_prefix') or USER.get('name', 'Candidate')} - {kind} - {company}.{ext}"


def file_glob(kind="*"):
    return f"{USER.get('file_prefix') or USER.get('name', 'Candidate')} - {kind} - *"


def current_role():
    exp = (_cv().get("experience") or [{}])[0]
    return exp.get("company", ""), exp.get("title", "")


DEGREE_WORDS = ("mba", "master of", "master's", "masters", "msc", "m.sc", "bachelor", "b.tech", "btech", "b.e.",
                "bsc", "b.sc", "b.com", "phd", "ph.d", "doctorate", "llb", "llm")


def is_degree(title):
    """A real degree, not a course: 'MBA', 'B.Tech, Computer Science' yes; 'Mastering Generative AI' no."""
    words = re.split(r"[\s,;()]+", title.lower())
    return any(w in title.lower() for w in DEGREE_WORDS if " " in w) or any(w in DEGREE_WORDS for w in words)


def education():
    """Schools and degrees (real degrees only, not courses), highest first, as option lists for form dropdowns."""
    edu = [e for e in (_cv().get("education") or []) if e.get("institution") and is_degree(e.get("title", ""))]
    schools = [e["institution"].split(",")[0] for e in edu] + ["Other"]
    words = []
    for e in edu:
        t = e["title"].lower()
        if "mba" in t:
            words += ["Master of Business Administration", "MBA", "Master's Degree"]
        elif re.search(r"master|m\.?sc|m\.?s\b|m\.?a\b|llm", t):
            words += ["Master's Degree", e["title"]]
        elif re.search(r"phd|ph\.d|doctor", t):
            words += ["Doctorate", "PhD", e["title"]]
        else:
            words += ["Bachelor's Degree", e["title"]]
    return schools, words or ["Other"]


def past_employers():
    return sorted({e.get("company", "") for e in (_cv().get("experience") or []) if e.get("company")})


def disciplines():
    """Field-of-study options for form dropdowns, highest degree first: an explicit `field`, else what follows the
    comma in the title ("B.Tech, Computer Science"); an MBA maps to Business Administration."""
    out = []
    for e in _cv().get("education") or []:
        title = e.get("title", "")
        if not is_degree(title):
            continue
        if e.get("field"):
            out.append(e["field"])
        elif "mba" in title.lower():
            out += ["Business Administration", "Business", "Management"]
        elif "," in title:
            out.append(title.split(",", 1)[1].strip())
    return out + ["Other"]
