"""Build a tailored CV for a tracked job from applications/<id>/tailor.yaml.

tailor.yaml keys (all optional; without the file the master CV is used as is):
  variant: <name>            # optional contact-line variant (user.yaml cv_template.contact_swaps or master-cv variants)
  headline: "..."            # title after the name
  summary: "..."             # <= ~420 chars; **bold** allowed
  first: [bullet ids]        # move these bullets to the top of their role, in this order
  hide: [bullet ids]         # drop these bullets
  text: {bullet id: "..."}   # reworded bullets (same facts as master; <= 210 chars)

Usage: .venv/Scripts/python scripts/tailor_cv.py <job id> [<job id> ...]
Writes applications/<id>/cv.yaml and "<file_prefix> - CV - <Company>.docx", updates the tracker.
"""
import copy
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_cv import apply_variant, build  # noqa: E402
from userconf import file_name  # noqa: E402


def plain(s):
    return s.replace("**", "")


def tailor(job_id):
    jobs = {j["id"]: j for j in json.loads((ROOT / "tracker" / "applications.json").read_text(encoding="utf-8"))}
    job, folder = jobs[job_id], ROOT / "applications" / job_id
    spec_file = folder / "tailor.yaml"   # no file = the master CV as is, under this job's file name
    spec = (yaml.safe_load(spec_file.read_text(encoding="utf-8")) or {}) if spec_file.exists() else {}
    folder.mkdir(parents=True, exist_ok=True)
    cv = yaml.safe_load((ROOT / "profile" / "master-cv.yaml").read_text(encoding="utf-8"))
    if spec.get("variant") == "eu":
        apply_variant(cv, "eu")
    cv.pop("variants", None)
    for key in ("headline", "summary"):
        if spec.get(key):
            cv[key] = spec[key]
    first, hide, text = spec.get("first", []), set(spec.get("hide", [])), spec.get("text", {})
    known = set()
    for e in cv["experience"] + cv["projects"]:
        bullets = e["bullets"]
        known |= {b["id"] for b in bullets}
        bullets.sort(key=lambda b: first.index(b["id"]) if b["id"] in first else len(first))
        for b in bullets:
            if b["id"] in text:
                b["text"] = text[b["id"]]
            if b["id"] in hide:
                b["hide"] = True
    unknown = (set(first) | hide | set(text)) - known
    problems = [f"unknown bullet ids: {sorted(unknown)}"] if unknown else []
    if len(plain(cv["summary"]).split()) and len(plain(cv["summary"])) > 430:
        problems.append(f"summary {len(plain(cv['summary']))} chars > 430")
    for e in cv["experience"] + cv["projects"]:
        for b in e["bullets"]:
            if not b.get("hide") and len(plain(b["text"])) > 212:
                problems.append(f"{b['id']} {len(plain(b['text']))} chars > 212")
    if problems:
        sys.exit(f"{job_id}: " + "; ".join(problems))
    (folder / "cv.yaml").write_text(yaml.safe_dump(cv, sort_keys=False, allow_unicode=True, width=1000), encoding="utf-8")
    name = file_name("CV", job["company"])
    build(cv, folder / name, spec.get("variant"))  # variant drives the contact-line swap
    subprocess.run([sys.executable, str(ROOT / "scripts" / "tracker.py"), "update", job_id, "--status", "preparing",
                    "--set", f"cv_file=applications/{job_id}/{name}", "--note", "tailored CV built"], check=True,
                   capture_output=True)
    print(f"{job_id}: {name}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    for jid in sys.argv[1:]:
        tailor(jid)
