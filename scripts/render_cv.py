"""Render a CV (master-cv.yaml schema) as a clean, ATS-safe Word file in one of three styles.

Usage: .venv/Scripts/python scripts/render_cv.py <cv.yaml> <out.docx> [classic|modern|compact]
Styles (chosen once in profile/user.yaml `cv_layout`):
  classic  black and grey, thin section rules: safe for any industry
  modern   navy headings and accent rules: tech, product, startups
  compact  classic, tighter type and spacing: long careers that must fit 2 pages
All three: one column, no tables/text boxes/images, standard section names, **bold** lead phrases kept,
right-aligned dates via a tab stop. build_cv.build() calls this when cv_layout is not "template".
"""
import re
import sys
from pathlib import Path

import yaml
from docx import Document
from docx.enum.text import WD_TAB_ALIGNMENT, WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor, Inches

STYLES = {
    "classic": {"font": "Calibri", "body": 10.5, "name": 20, "head": 11, "accent": "000000", "rule": "8C8C8C",
                "muted": "595959", "margin": 0.6, "space": 6, "bullet_space": 1.5},
    "modern": {"font": "Calibri", "body": 10.5, "name": 22, "head": 11.5, "accent": "1D3461", "rule": "1D3461",
               "muted": "4A5568", "margin": 0.6, "space": 6, "bullet_space": 1.5},
    "compact": {"font": "Calibri", "body": 9.5, "name": 18, "head": 10.5, "accent": "000000", "rule": "8C8C8C",
                "muted": "595959", "margin": 0.5, "space": 4, "bullet_space": 0.5},
}


def rgb(hexstr):
    return RGBColor.from_string(hexstr)


def add_runs(par, text, size, color=None, bold_all=False):
    """Write text with **bold** segments as separate runs."""
    for i, chunk in enumerate(re.split(r"\*\*", text or "")):
        if not chunk:
            continue
        r = par.add_run(chunk)
        r.font.size = Pt(size)
        r.bold = bold_all or (i % 2 == 1)
        if color:
            r.font.color.rgb = rgb(color)


def bottom_rule(par, color, size=6):
    pPr = par._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    for k, v in (("val", "single"), ("sz", str(size)), ("space", "1"), ("color", color)):
        bottom.set(qn(f"w:{k}"), v)
    borders.append(bottom)
    pPr.append(borders)


def spacing(par, before=0, after=0):
    par.paragraph_format.space_before = Pt(before)
    par.paragraph_format.space_after = Pt(after)
    par.paragraph_format.line_spacing = 1.0


def render(cv, out, style="classic"):
    s = STYLES[style]
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Inches(8.27), Inches(11.69)  # A4
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, side, Inches(s["margin"]))
    width = sec.page_width - sec.left_margin - sec.right_margin
    normal = doc.styles["Normal"]
    normal.font.name = s["font"]
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), s["font"])
    normal.font.size = Pt(s["body"])

    def heading(title):
        p = doc.add_paragraph()
        spacing(p, before=s["space"] + 4, after=3)
        r = p.add_run(title.upper())
        r.bold, r.font.size, r.font.color.rgb = True, Pt(s["head"]), rgb(s["accent"])
        bottom_rule(p, s["rule"])
        p.paragraph_format.keep_with_next = True

    def line_with_date(left, right, bold_left=True, color=None, size=None, before=0):
        p = doc.add_paragraph()
        spacing(p, before=before, after=0)
        p.paragraph_format.tab_stops.add_tab_stop(width, WD_TAB_ALIGNMENT.RIGHT)
        p.paragraph_format.keep_with_next = True
        add_runs(p, left, size or s["body"], color=color, bold_all=bold_left)
        if right:
            r = p.add_run("\t" + right)
            r.font.size, r.font.color.rgb = Pt(s["body"] - 0.5), rgb(s["muted"])
        return p

    def bullet(text):
        p = doc.add_paragraph()
        spacing(p, before=0, after=s["bullet_space"])
        p.paragraph_format.left_indent = Inches(0.18)
        p.paragraph_format.first_line_indent = Inches(-0.13)
        p.add_run("•  ").font.size = Pt(s["body"])
        add_runs(p, text, s["body"])

    visible = lambda items: [i for i in (items or []) if not i.get("hide")]

    # Header
    p = doc.add_paragraph()
    spacing(p, after=1)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if style != "modern" else WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run(cv["name"].upper() if style == "modern" else cv["name"])
    r.bold, r.font.size, r.font.color.rgb = True, Pt(s["name"]), rgb(s["accent"])
    if cv.get("headline"):
        p = doc.add_paragraph()
        spacing(p, after=2)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER if style != "modern" else WD_ALIGN_PARAGRAPH.LEFT
        add_runs(p, cv["headline"], s["body"] + 1, color=s["muted"])
    c = cv.get("contact", {})
    link = re.sub(r"^https?://(www\.)?", "", c.get("linkedin_url") or "") or c.get("linkedin")
    contact = " | ".join(x for x in (c.get("location"), c.get("email"), c.get("phone"), link) if x)
    # Keep the contact line on ONE line: step the size down (never below 8 pt) until it fits the text width.
    # Measured on the rendered PDF: Calibri runs ~0.464 em per character here; 0.48 leaves a small margin.
    width_pt = width / 12700
    size = next((sz for sz in (s["body"] - 0.5, 9.5, 9, 8.5, 8) if len(contact) * sz * 0.48 <= width_pt), 8)
    p = doc.add_paragraph()
    spacing(p, after=2)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if style != "modern" else WD_ALIGN_PARAGRAPH.LEFT
    add_runs(p, contact, size, color=s["muted"])

    if cv.get("summary"):
        heading("Summary")
        p = doc.add_paragraph()
        spacing(p, after=0)
        add_runs(p, " ".join(cv["summary"].split()), s["body"])

    jobs = visible(cv.get("experience"))
    if jobs:
        heading("Experience")
        for i, e in enumerate(jobs):
            line_with_date(e["title"], e.get("dates", ""), before=0 if i == 0 else s["space"])
            where = ", ".join(x for x in (e.get("company"), e.get("location")) if x)
            line_with_date(where, "", bold_left=(style == "modern"), color=s["accent"] if style == "modern" else s["muted"])
            for b in visible(e.get("bullets")):
                bullet(b["text"])

    projects = visible(cv.get("projects"))
    if projects:
        heading("Projects")
        for i, pr in enumerate(projects):
            line_with_date(pr["title"], pr.get("dates", ""), before=0 if i == 0 else s["space"])
            for b in visible(pr.get("bullets")):
                bullet(b["text"])

    if cv.get("education"):
        heading("Education")
        for e in cv["education"]:
            line_with_date(f"{e['title']}, {e['institution']}", str(e.get("dates", "")), bold_left=False)

    if cv.get("awards"):
        heading("Awards")
        for a in cv["awards"]:
            text = f"**{a['title']}**" + (f" ({a['org']})" if a.get("org") else "") + (f": {a['text']}" if a.get("text") else "")
            bullet(text)

    if cv.get("skills"):
        heading("Skills")
        for sk in cv["skills"]:
            p = doc.add_paragraph()
            spacing(p, after=1)
            add_runs(p, f"**{sk['label']}:** " + (", ".join(sk["items"]) if sk.get("items") else sk.get("text", "")), s["body"])

    doc.core_properties.author = cv["name"]
    doc.core_properties.title = f"{cv['name']} CV"
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    doc.save(out)


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    style = sys.argv[3] if len(sys.argv) > 3 else "classic"
    render(yaml.safe_load(Path(src).read_text(encoding="utf-8")), dst, style)
    print(f"{style}: {dst}")
