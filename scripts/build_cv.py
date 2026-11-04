"""Render a CV YAML (master-cv.yaml schema) into a copy of the owner's own Word resume template (cv_layout: template),
keeping its exact formatting, or into simple HTML for a Google Doc.

Usage: .venv/Scripts/python scripts/build_cv.py <cv.yaml> <out.docx|out.html> [--variant eu]

Text may mark bold with **double asterisks** (bold lead phrase + bold results).
In template mode the .docx is built from the user's own Word resume (user.yaml cv_template.file): section headings, divider lines, the contact
line, company/date lines and project headings (with their links) come from the template; the headline,
summary, role titles, bullets, award text and skills come from the YAML.

Optional keys a tailored cv.yaml may add on top of the master schema:
  headline            - overrides the title after the name
  experience[].hide   - true to drop a role entirely
  bullets[].hide      - true to drop a bullet
"""
import copy
import re
import sys
from html import escape
from pathlib import Path

import yaml
from docx import Document
from docx.oxml.ns import qn

sys.path.insert(0, str(Path(__file__).resolve().parent))
from userconf import USER  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
# Own-template mode (cv_layout: template) is configured in profile/user.yaml `cv_template`:
#   file: the Word resume; roles/projects: master-cv.yaml ids in the order of the template's blocks;
#   contact_swaps: {variant: [[old, new], ...]} text swaps on the contact line.
_TPL = USER.get("cv_template") or {}
TEMPLATE = ROOT / _TPL.get("file", "profile/cv-template.docx")
TEMPLATE_ROLES = _TPL.get("roles") or []
TEMPLATE_PROJECTS = _TPL.get("projects") or []
CONTACT_SWAPS = {k: [tuple(x) for x in v] for k, v in (_TPL.get("contact_swaps") or {}).items()}


def visible(items):
    return [i for i in items or [] if not i.get("hide")]


def segments(text):
    """'a **b** c' -> [('a ', False), ('b', True), (' c', False)]"""
    if "****" in text or text.count("**") % 2:
        sys.exit(f"Unbalanced **bold** markers in: {text[:80]}")
    parts = re.split(r"(\*\*.+?\*\*)", text)
    return [(p[2:-2], True) if p.startswith("**") else (p, False) for p in parts if p]


def run_props(p, want_bold):
    """Copy the rPr of a run in paragraph p, with bold set as requested."""
    runs = [r for r in p.runs if r.text.strip()]
    src = next((r for r in runs if bool(r.bold) == want_bold), runs[0] if runs else None)
    rpr = copy.deepcopy(src._r.rPr) if src is not None and src._r.rPr is not None else None
    if rpr is None:
        rpr = p._p.makeelement(qn("w:rPr"), {})
    for b in rpr.findall(qn("w:b")) + rpr.findall(qn("w:bCs")):
        rpr.remove(b)
    if want_bold:
        rpr.insert(0, rpr.makeelement(qn("w:b"), {}))
    return rpr


def set_text(p, text, bold_rpr=None, normal_rpr=None):
    """Replace a paragraph's runs/links with text (supporting **bold**), keeping its paragraph format."""
    bold_rpr = bold_rpr if bold_rpr is not None else run_props(p, True)
    normal_rpr = normal_rpr if normal_rpr is not None else run_props(p, False)
    for child in list(p._p):
        if child.tag in (qn("w:r"), qn("w:hyperlink")):
            p._p.remove(child)
    for chunk, is_bold in segments(text):
        r = p._p.makeelement(qn("w:r"), {})
        r.append(copy.deepcopy(bold_rpr if is_bold else normal_rpr))
        t = r.makeelement(qn("w:t"), {qn("xml:space"): "preserve"})
        t.text = chunk
        r.append(t)
        p._p.append(r)


def set_bullets(first, bullets, existing):
    """Replace the bullet paragraphs `existing` (first is existing[0]) with one per bullet."""
    bold_rpr, normal_rpr = run_props(first, True), run_props(first, False)
    proto = copy.deepcopy(first._p)
    anchor = existing[-1]._p
    for p in existing[1:]:
        p._p.getparent().remove(p._p)
    texts = [b["text"] for b in visible(bullets)]
    if not texts:
        first._p.getparent().remove(first._p)
        return
    set_text(first, texts[0], bold_rpr, normal_rpr)
    anchor = first._p
    from docx.text.paragraph import Paragraph
    for text in texts[1:]:
        el = copy.deepcopy(proto)
        anchor.addnext(el)
        set_text(Paragraph(el, first._parent), text, bold_rpr, normal_rpr)
        anchor = el


def is_blank(p):
    return p.style.name.lower() == "normal" and not p.text.strip() and not p._p.xpath(".//w:drawing|.//w:pict")


def build(cv, out, variant=None):
    # Users without their own Word template get one of the built-in styles (profile/user.yaml cv_layout).
    layout = USER.get("cv_layout", "template")
    if layout != "template":
        from render_cv import render
        return render(cv, out, layout)
    doc = Document(str(TEMPLATE))
    P = doc.paragraphs

    # Header: name - headline, and the contact line.
    set_text(P[1], f"{cv['name'].upper()} - {cv.get('headline', 'Senior Product Manager').upper()}")
    for old, new in CONTACT_SWAPS.get(variant, []):
        for t in P[2]._p.iter(qn("w:t")):
            if old in (t.text or ""):
                t.text = t.text.replace(old, new)

    # Summary: the first non-empty normal paragraph after the SUMMARY heading.
    heads = {p.text.strip().upper(): i for i, p in enumerate(P) if p.style.name == "Heading 2"}
    i = heads["SUMMARY"] + 1
    while not P[i].text.strip():
        i += 1
    set_text(P[i], cv["summary"].strip())

    # Experience + projects: walk Heading 3 blocks between EXPERIENCE and EDUCATION.
    start, end = heads["EXPERIENCE"], next(v for k, v in heads.items() if k.startswith("EDUCATION"))
    blocks = []  # (kind, title_para, header_para(H4), bullet paras)
    cur = None
    for p in P[start + 1:end]:
        s = p.style.name
        if s == "Heading 3" and p.text.strip() != "Product Development":
            cur = {"title": p, "h4": None, "bullets": []}  # a role
            blocks.append(cur)
        elif s == "Heading 4" and cur is not None and cur["title"] is not None and cur["h4"] is None:
            cur["h4"] = p  # the role's company/date line
        elif s == "Heading 4":
            cur = {"title": None, "h4": p, "bullets": []}  # a project
            blocks.append(cur)
        elif cur is not None and p.style.name == "normal" and p.text.strip():
            cur["bullets"].append(p)
    roles = [b for b in blocks if b["title"] is not None]
    projects = [b for b in blocks if b["title"] is None]
    by_id = {e["id"]: e for e in cv.get("experience", [])}
    for role_id, block in zip(TEMPLATE_ROLES, roles):
        e = by_id.get(role_id)
        if e is None or e.get("hide"):
            for p in [block["title"], block["h4"], *block["bullets"]]:
                p._p.getparent().remove(p._p)
            continue
        set_text(block["title"], e["title"])
        set_bullets(block["bullets"][0], e.get("bullets"), block["bullets"])
    proj_by_id = {e["id"]: e for e in cv.get("projects", [])}
    for proj_id, block in zip(TEMPLATE_PROJECTS, projects):
        e = proj_by_id.get(proj_id)
        if e is None or e.get("hide"):
            for p in [block["h4"], *block["bullets"]]:
                p._p.getparent().remove(p._p)
            continue
        # header_swaps: [[old, new], ...] edits the template's project heading text, keeping its link.
        for old, new in e.get("header_swaps", []):
            for t in block["h4"]._p.iter(qn("w:t")):
                if old in (t.text or ""):
                    t.text = t.text.replace(old, new)
        set_bullets(block["bullets"][0], e.get("bullets"), block["bullets"])

    # Awards text and skills.
    P = doc.paragraphs
    heads = {p.text.strip().upper(): i for i, p in enumerate(P) if p.style.name == "Heading 2"}
    if cv.get("awards"):
        a = heads["AWARDS & RECOGNITION"]
        text_paras = [p for p in P[a + 1:heads["SKILLS"]] if p.style.name == "normal" and p.text.strip() and p.text.strip() != "GOOGLE"]
        if text_paras:
            set_text(text_paras[0], cv["awards"][0]["text"])
    skill_paras = [p for p in P[heads["SKILLS"] + 1:] if p.text.strip()]
    from docx.text.paragraph import Paragraph
    bold_rpr, normal_rpr = run_props(skill_paras[0], True), run_props(skill_paras[0], False)
    proto = copy.deepcopy(skill_paras[0]._p)
    anchor = skill_paras[-1]._p
    for p in skill_paras[1:]:
        p._p.getparent().remove(p._p)
    anchor = skill_paras[0]._p
    for k, s in enumerate(cv.get("skills", [])):
        text = f"**{s['label']}:** {', '.join(s['items'])}"
        if k == 0:
            set_text(skill_paras[0], text, bold_rpr, normal_rpr)
        else:
            el = copy.deepcopy(proto)
            anchor.addnext(el)
            set_text(Paragraph(el, skill_paras[0]._parent), text, bold_rpr, normal_rpr)
            anchor = el

    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out)


def build_html(cv, out, variant=None):
    """Same CV as simple HTML, for uploading to Google Drive as a Google Doc."""
    def md(s):
        return "".join(f"<b>{escape(c)}</b>" if b else escape(c) for c, b in segments(s))
    c = dict(cv["contact"])
    parts = [f"<h1>{escape(cv['name'].upper())} - {escape(cv.get('headline', '').upper())}</h1>",
             "<p>" + escape("  •  ".join(x for x in [c.get("location"), c.get("email"), c.get("phone"), c.get("linkedin")] if x)) + "</p>",
             "<h2>SUMMARY</h2>", f"<p>{md(cv['summary'].strip())}</p>", "<h2>EXPERIENCE</h2>"]
    for x in visible(cv.get("experience")) + visible(cv.get("projects")):
        meta = ", ".join(v for v in [x.get("dates"), x.get("location")] if v)
        parts.append(f"<h3>{escape(x['title'])}</h3><h4>{escape((x.get('company') or '').upper())}  {escape(meta)}</h4><ul>"
                     + "".join(f"<li>{md(b['text'])}</li>" for b in visible(x.get("bullets"))) + "</ul>")
    parts.append("<h2>EDUCATION &amp; CERTIFICATIONS</h2>")
    parts += [f"<h3>{escape(x['title'])}</h3><p>{escape(x['institution'])} • {escape(str(x['dates']))}</p>" for x in cv.get("education", [])]
    parts.append("<h2>AWARDS &amp; RECOGNITION</h2>")
    parts += [f"<h3>{escape(x['title'])}</h3><p><b>{escape(x['org'].upper())}</b></p><p>{md(x.get('text', ''))}</p>" for x in cv.get("awards", [])]
    parts.append("<h2>SKILLS</h2>")
    parts += [f"<p><b>{escape(s['label'])}:</b> {escape(', '.join(s['items']))}</p>" for s in cv.get("skills", [])]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("<html><body>" + "".join(parts) + "</body></html>", encoding="utf-8")


def apply_variant(cv, name):
    """Overlay a named variant (contact fields + bullet text by id) onto the CV."""
    variant = (cv.get("variants") or {}).get(name)
    if variant is None:
        sys.exit(f"Unknown variant {name}")
    cv["contact"].update(variant.get("contact", {}))
    texts = variant.get("bullets", {})
    for e in cv.get("experience", []) + cv.get("projects", []):
        for b in e.get("bullets", []):
            if b["id"] in texts:
                b["text"] = texts[b["id"]]


if __name__ == "__main__":
    args = sys.argv[1:]
    variant = None
    if "--variant" in args:
        i = args.index("--variant")
        variant = args[i + 1]
        del args[i:i + 2]
    if len(args) != 2:
        sys.exit(__doc__)
    src, dst = Path(args[0]), Path(args[1])
    cv = yaml.safe_load(src.read_text(encoding="utf-8"))
    if variant:
        apply_variant(cv, variant)
    (build_html if dst.suffix == ".html" else build)(cv, dst, variant)
    print(f"Wrote {dst}")
