"""Check a cover letter against profile/cover-letter-guide.md and build its .docx.

Usage: .venv/Scripts/python scripts/build_cover_letter.py <job id> [<job id> ...]
Reads applications/<id>/cover-letter.md, prints word count, longest sentence and any banned words/patterns,
and writes "<file_prefix> - Cover Letter - <Company>.docx" next to it. Exits 1 if a banned item is found.
"""
import json
import re
import sys
from pathlib import Path

from docx import Document
from docx.shared import Pt

from userconf import file_name  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BANNED = ("delve tapestry testament pivotal underscore crucial intricate meticulous vibrant landscape interplay garner "
          "bolster enhance foster leverage multifaceted showcase highlighting emphasizing resonate seamless robust "
          "dynamic passionate thrilled synergy spearhead cutting-edge game-changer unwavering invaluable boasts "
          "additionally moreover furthermore renowned groundbreaking").split()
PHRASES = ["align with", "rather than", "not just", "serves as", "stands as", "ensuring", "contributing to", "—",
           "i hope this", "[company]"]


def check(text):
    low = text.lower()
    hits = [w for w in BANNED if re.search(r"\b" + re.escape(w), low)] + [p for p in PHRASES if p in low]
    body = text.split("\n\n", 1)[1].rsplit("\n\nKind", 1)[0]
    sents = [s for s in re.split(r"(?<=[.!?])\s+", body) if len(s.split()) > 2]
    return hits, len(body.split()), max(len(s.split()) for s in sents)


def build(job_id):
    folder = ROOT / "applications" / job_id
    text = (folder / "cover-letter.md").read_text(encoding="utf-8")
    hits, words, longest = check(text)
    jobs = {j["id"]: j for j in json.loads((ROOT / "tracker" / "applications.json").read_text(encoding="utf-8"))}
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)
    for para in text.strip().split("\n\n"):
        doc.add_paragraph(para)
    out = folder / file_name("Cover Letter", jobs[job_id]["company"])
    doc.save(out)
    print(f"{job_id}: words {words} | longest {longest} | banned {hits or 'none'} -> {out.name}")
    return not hits


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ok = all([build(j) for j in sys.argv[1:]])
    sys.exit(0 if ok else 1)
