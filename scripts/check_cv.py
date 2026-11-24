"""Layout check for a built CV, read from its PDF (what the recruiter sees): catches formatting errors the builder
cannot see in the .docx.

Usage: .venv/Scripts/python scripts/check_cv.py <job id | file.pdf> [...]      # or --all for every job folder
Exit code 1 if any CV fails. to_pdf.py runs it on every CV it converts.

Checks
  - dates: every "Month YYYY - ..." date sits flush right (same right edge as the others) with a clear gap after
    the title, i.e. the title is not so long that it runs into the date;
  - section headings (capitals, larger than body text) each have a rule line under them;
  - no text runs past the right margin; at most `max_pages` pages (2);
  - no leftover markup: **, [CONFIRM, TODO, {{, ##.
Needs PyMuPDF (pip install pymupdf).
"""
import re
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
MONTH = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
DATE = re.compile(MONTH + r"\s+\d{4}\s*[-–]\s*(?:Present|" + MONTH + r"\s+\d{4})")
_STEMS = r"(?:optimi|personali|prioriti|organi|recogni|reali|speciali|standardi|summari|utili|centrali|moneti|capitali|customi|visuali|categori|minimi|maximi)"
UK = re.compile(r"\b(?:" + _STEMS + r"s(?:e|ed|es|ing|ation|ations)|analys(?:e|ed|ing)|programmes?|travell(?:er|ers|ing)|behaviours?|colours?|centres?|catalogues?|favourites?|labelled|modelling|cancelled|fulfil|enrolment)\b", re.I)
US = re.compile(r"\b(?:" + _STEMS + r"z(?:e|ed|es|ing|ation|ations)|analyz(?:e|ed|ing)|programs?|travel(?:er|ers|ing)|behaviors?|colors?|centers?|catalogs?|favorites?|labeled|modeling|canceled|fulfill|enrollment)\b", re.I)
LEFTOVER = re.compile(r"\*\*|\[CONFIRM|\bTODO\b|\{\{|##")
MIN_GAP = 6.0      # points between the end of a title and the start of its date
EDGE_TOL = 3.0     # points of slack on the shared right edge
MAX_PAGES = 2


def lines_of(page):
    """[(text, chars)] per visual line; chars are (char, x0, x1, size, bold)."""
    # PDF writers split one visual line into several pieces (e.g. at a tab), so group characters by baseline.
    rows = []   # [baseline, chars]
    for b in page.get_text("rawdict")["blocks"]:
        for ln in b.get("lines", []):
            for sp in ln["spans"]:
                bold = "bold" in sp["font"].lower() or bool(sp["flags"] & 16)
                base = sp["origin"][1]
                row = next((r for r in rows if abs(r[0] - base) < 2), None)
                if row is None:
                    row = [base, []]
                    rows.append(row)
                for c in sp["chars"]:
                    row[1].append((c["c"], c["bbox"][0], c["bbox"][2], sp["size"], bold, c["bbox"][1], c["bbox"][3]))
    out = []
    for base, chars in sorted(rows, key=lambda r: r[0]):
        chars.sort(key=lambda c: c[1])
        if chars:
            out.append(("".join(c[0] for c in chars), chars))
    return out


def check_pdf(pdf):
    errs = []
    doc = pymupdf.open(str(pdf))
    if len(doc) > MAX_PAGES:
        errs.append(f"{len(doc)} pages (max {MAX_PAGES})")
    body_sizes = []
    dated = []   # (page, text, date_x0, gap, right_x)
    for pno, page in enumerate(doc, 1):
        width = page.rect.width
        lines = lines_of(page)
        rules = [d["rect"] for d in page.get_drawings() if d["rect"].height <= 3 and d["rect"].width > width * 0.5]
        for text, chars in lines:
            body_sizes += [c[3] for c in chars]
            if LEFTOVER.search(text):
                errs.append(f"p{pno}: leftover markup in '{text[:60]}'")
            if max(c[2] for c in chars) > width - 12:
                errs.append(f"p{pno}: text past the right margin: '{text[:60]}'")
            m = DATE.search(text)
            if m:
                prev = [c for c in chars[:m.start()] if c[0].strip()]
                if prev:
                    gap = chars[m.start()][1] - prev[-1][2]
                    dated.append((pno, text, gap, chars[-1][2]))
                else:      # the title was too long, so the date wrapped onto a line of its own
                    errs.append(f"p{pno}: date wrapped onto its own line: '{text.strip()[:90]}'")
        # Section headings: whole line in capitals, bold, clearly bigger than bullet text, not the name line.
        for k, (text, chars) in enumerate(lines):
            letters = [c for c in text if c.isalpha()]
            size = max(c[3] for c in chars)
            if (pno, k) == (1, 0) or len(letters) < 4 or text != text.upper() or not all(c[4] for c in chars if c[0].strip()):
                continue
            if not 11 <= size <= 14:
                continue
            bottom = max(c[6] for c in chars)
            if not any(bottom - 2 <= r.y0 <= bottom + 22 for r in rules):
                errs.append(f"p{pno}: heading '{text.strip()}' has no rule line under it")
    # Spelling: one convention per CV (UK or US), never both. The name/headline line is skipped: it may mirror the
    # employer's job title exactly (e.g. "Monetization").
    full = " ".join(page.get_text() for page in doc).split("\n", 1)[-1]
    uk = sorted({m.group(0) for m in UK.finditer(full)})
    us = sorted({m.group(0) for m in US.finditer(full)})
    if uk and us:
        errs.append(f"mixed UK/US spelling: UK {', '.join(uk[:5])} vs US {', '.join(us[:5])}")
    if dated:
        edges = sorted(d[3] for d in dated)
        edge = edges[len(edges) // 2]
        for pno, text, gap, right in dated:
            if gap < MIN_GAP:
                errs.append(f"p{pno}: date runs into the title (gap {gap:.1f}pt): '{text.strip()[:90]}'")
            elif abs(right - edge) > EDGE_TOL:
                errs.append(f"p{pno}: date not flush right ({right - edge:+.1f}pt): '{text.strip()[:90]}'")
    return errs


def targets(args):
    if args == ["--all"]:
        args = [p.name for p in (ROOT / "applications").iterdir() if p.is_dir()]
    for a in args:
        p = Path(a)
        if p.suffix.lower() == ".pdf":
            yield p
        else:
            yield from sorted((ROOT / "applications" / a).glob("* - CV - *.pdf"))


def main(args):
    bad = 0
    for pdf in targets(args):
        errs = check_pdf(pdf)
        if errs:
            bad += 1
            print(f"FAIL {pdf.parent.name}/{pdf.name}")
            for e in errs:
                print("   ", e)
    print(f"check_cv: {'all OK' if not bad else f'{bad} CV(s) failed'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
