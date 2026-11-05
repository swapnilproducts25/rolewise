"""Read a job's application-form questions before the user opens the form, and list the ones Rolewise can't answer
from its standard rules, so they can be drafted (from master-cv.yaml / story-bank.md) into applications/<id>/kit.yaml.

Usage: .venv/Scripts/python scripts/form_questions.py <job id> [<job id> ...]
Writes applications/<id>/form-questions.json (every question) and prints the open ones.
Supported: Greenhouse (public boards API) and Lever (the form's own page). Others print "not supported".
Polite: one request per job.
"""
import html
import json
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_kits import RULES, form_urls  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (Rolewise personal job search)"}
STANDARD = re.compile(r"^(first name|last name|full name|name|email|phone|resume|resume/cv|cv|cover letter|linkedin.*|website|"
                      r"current company|current location|location)$", re.I)


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def greenhouse(url):
    m = (re.search(r"greenhouse\.io/(?:embed/job_app\?for=)?([\w-]+)(?:/jobs/|&token=)(\d+)", url)
         or re.search(r"for=([\w-]+)&token=(\d+)", url))
    if not m:
        return None
    d = json.loads(get(f"https://boards-api.greenhouse.io/v1/boards/{m.group(1)}/jobs/{m.group(2)}?questions=true"))
    out = []
    for q in d.get("questions") or []:
        f = (q.get("fields") or [{}])[0]
        out.append({"label": q["label"].strip(), "required": q.get("required", False), "type": f.get("type", ""),
                    "options": [v["label"] for v in f.get("values") or []]})
    return out


def lever(url):
    m = re.search(r"jobs\.lever\.co/([\w-]+)/([0-9a-f-]{20,})", url)
    if not m:
        return None
    page = get(f"https://jobs.lever.co/{m.group(1)}/{m.group(2)}/apply")
    out = []
    for raw in re.findall(r'value="([^"]+)" name="cards\[[^\]]+\]\[baseTemplate\]"', page):
        card = json.loads(html.unescape(raw))
        for f in card.get("fields") or []:
            out.append({"label": f.get("text", "").strip(), "required": f.get("required", False), "type": f.get("type", ""),
                        "options": [o.get("text") for o in f.get("options") or []]})
    return out


CONSENT = re.compile(r"consent|agree|acknowledg|privacy|data (protection|transfer|retention|processing)|point of data|terms|gdpr")


def covered(label):
    low = label.lower()
    if STANDARD.match(low.strip(" *?")) or CONSENT.search(low):
        return True
    return any(re.search(p, low) and key for p, key in RULES)


def main(ids):
    sys.stdout.reconfigure(encoding="utf-8")
    jobs = {j["id"]: j for j in json.loads((ROOT / "tracker" / "applications.json").read_text(encoding="utf-8"))}
    for jid in ids:
        job = jobs[jid]
        qs = None
        for u in form_urls(job):
            qs = greenhouse(u) if "greenhouse" in u else lever(u) if "lever.co" in u else None
            if qs is not None:
                break
        if qs is None:
            print(f"{jid}: form not supported (questions appear only in the live form)")
            continue
        for q in qs:
            q["open"] = not covered(q["label"])
        folder = ROOT / "applications" / jid
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "form-questions.json").write_text(json.dumps(qs, indent=1, ensure_ascii=False), encoding="utf-8")
        opened = [q for q in qs if q["open"]]
        print(f"{jid}: {len(qs)} questions, {len(opened)} to draft")
        for q in opened:
            opts = f"  [{' / '.join(q['options'])}]" if q["options"] else ""
            print(f"  - {'*' if q['required'] else ' '} {q['label'][:140]}{opts}")


if __name__ == "__main__":
    main(sys.argv[1:])
