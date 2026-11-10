"""Render the daily briefing from coach/briefings/<date>.json into an email (HTML + plain text) and a markdown copy.

Usage: python scripts/render_briefing.py coach/briefings/2026-11-04.json
Writes <date>.html, <date>.txt and <date>.md next to the JSON and prints the email subject.
SEND IT AS HTML: the Gmail send call must pass htmlBody = the whole .html file (body = the .txt as the fallback).
A text-only send arrives with no formatting at all.

Buttons open the user's private Rolewise Inbox page (`inbox_url` in profile/user.yaml, scripts/inbox.py), where one
tap saves the action and the next run applies it. A job's Skip opens it at #skip-<job> with a one-tap confirm.
Verbs: SKIP / APPLIED / WAIT <job-id>, SEND <draft-id>, PREPARE <job-id>, ANSWER <job-id>, PAUSE / RESUME.
Link buttons: {"label": "...", "url": "https://..."}.

Design: a soft grey page with one white card; a slim brand line, the headline, the week's numbers as three small tiles;
sections with a thin coloured edge (today amber, needs-you blue, referral green, coach violet); prepared jobs as a
compact list with a fit badge and a quiet Skip link. Email-safe: tables, inline styles, bgcolor for colours.

JSON shape:
{"date": "YYYY-MM-DD", "headline": "one line", "stats": {"applied_week": 6, "interviews": 2, "response_rate": "17%"},
 "sections": [{"key": "today|needs_you|referral|ready|coach", "title": "...", "note": "...", "more": 0, "items": [
    {"title": "...", "detail": "...", "message": "text to copy", "fit": 78,
     "actions": [{"label": "Send", "verb": "SEND", "target": "draft-id"}, {"label": "Open", "url": "https://..."}]}]}],
 "dashboard_url": "https://...", "first_briefing": false}
"""
import datetime as dt
import json
import re
import sys
from html import escape
from pathlib import Path
from urllib.parse import quote

from userconf import USER  # noqa: E402
from build_kits import freshness  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
JOBS = {j["id"]: j for j in json.loads((ROOT / "tracker" / "applications.json").read_text(encoding="utf-8"))}     if (ROOT / "tracker" / "applications.json").exists() else {}


def repo_url():
    """https://github.com/<owner>/<repo> of this copy, for links to the prepared CV and cover letter."""
    import subprocess
    try:
        remote = subprocess.run(["git", "remote", "get-url", "origin"], cwd=ROOT, capture_output=True, text=True).stdout
    except OSError:
        return ""
    m = re.search(r"([\w.-]+)/([\w.-]+?)(?:\.git)?\s*$", remote)
    return f"https://github.com/{m[1]}/{m[2]}" if m else ""


REPO = repo_url()


def job_files(job_id):
    """Links to the job's CV and cover letter (PDF if built, else Word), on the user's private GitHub copy."""
    folder, links = ROOT / "applications" / job_id, []
    for label, pattern in (("CV", "* - CV - *"), ("Cover letter", "* - Cover Letter - *")):
        found = sorted(folder.glob(pattern), key=lambda f: f.suffix.lower() != ".pdf")
        if found and REPO:
            links.append((label, f"{REPO}/blob/main/applications/{quote(job_id)}/{quote(found[0].name)}"))
    return links

ME = USER["email"]
MAX_ITEMS = 3      # cards per section
MAX_LIST = 10      # rows in the Ready list
NAVY, INK, MUTED, LINE, PAGE, SOFT = "#1d3461", "#14223b", "#5b6880", "#e4e9f1", "#f3f5f9", "#f6f8fb"
FONT = "-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
# section key -> (emoji, accent colour for the card edge)
SECTIONS = {"today": ("🔥", "#d98e04"), "needs_you": ("💬", "#2f6fdb"), "referral": ("🤝", "#1f8a5b"),
            "ready": ("✅", NAVY), "new": ("🔎", NAVY), "coach": ("🎯", "#7357c7")}
EMOJI = re.compile(r"^[\W_]+\s*", re.UNICODE)   # a leading emoji the JSON may already carry


INBOX = USER.get("inbox_url") or ""
HASH = {"SKIP": "skip", "APPLIED": "applied", "WAIT": "later", "PAUSE": "pause", "RESUME": "resume"}


def action_href(verb, target, date):
    """The Rolewise Inbox, opened on that action when it has a one-tap confirm, else on the page (its cards)."""
    if not INBOX:
        return ""
    h = HASH.get(verb)
    return f"{INBOX}#{h}-{target}" if h and target else f"{INBOX}#{h}" if h else INBOX


def button(action, date, primary):
    """Email-safe button: colour on a table cell (bgcolor), which Gmail keeps; it strips <a> backgrounds."""
    href = action.get("url") or action_href(action["verb"], action["target"], date)
    if not href:
        return ""
    bg, fg, border = (NAVY, "#ffffff", NAVY) if primary else ("#ffffff", NAVY, "#c9d4e8")
    return (f'<td bgcolor="{bg}" style="background-color:{bg};border:1px solid {border};border-radius:7px">'
            f'<a href="{escape(href)}" style="display:inline-block;padding:6px 12px;font-size:13px;font-weight:600;'
            f'line-height:16px;color:{fg};text-decoration:none;font-family:{FONT}">{escape(action["label"])}</a></td>')


def button_row(actions, date):
    cells = '<td width="6" style="width:6px;font-size:0;line-height:0">&nbsp;</td>'.join(
        filter(None, (button(a, date, i == 0) for i, a in enumerate(actions))))
    if not cells:
        return ""
    return (f'<table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin-top:10px">'
            f'<tr>{cells}</tr></table>')


def heading(sec):
    emoji, _ = SECTIONS.get(sec["key"], ("", NAVY))
    title = EMOJI.sub("", sec["title"]) or sec["title"]
    return (f'<div style="margin:22px 0 8px;font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;'
            f'color:{MUTED}">{emoji}&nbsp; {escape(title)}</div>'), title


def card(item, accent, date):
    inner = [f'<div style="font-weight:600;font-size:15px;color:{INK}">{escape(item["title"])}</div>']
    if item.get("detail"):
        inner.append(f'<div style="color:{MUTED};font-size:14px;margin-top:3px">{escape(item["detail"])}</div>')
    if item.get("message"):
        inner.append(f'<div style="margin-top:10px;padding:10px 12px;background-color:{SOFT};border-radius:8px;'
                     f'font-size:14px;color:{INK};white-space:pre-wrap">{escape(item["message"])}</div>')
    if item.get("actions"):
        inner.append(button_row(item["actions"], date))
    return (f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-top:8px">'
            f'<tr><td width="4" bgcolor="{accent}" style="width:4px;background-color:{accent};border-radius:4px 0 0 4px"></td>'
            f'<td style="padding:12px 14px;border:1px solid {LINE};border-left:0;border-radius:0 10px 10px 0">'
            + "".join(inner) + "</td></tr></table>")


def stat_tiles(s):
    tiles = [(s.get("applied_week", 0), "applied this week"), (s.get("interviews", 0), "interviews"),
             (s.get("response_rate", "–"), "reply rate")]
    cells = '<td width="8" style="width:8px">&nbsp;</td>'.join(
        f'<td bgcolor="{SOFT}" style="background-color:{SOFT};border-radius:10px;padding:10px 12px" width="33%">'
        f'<div style="font-size:20px;font-weight:700;color:{INK};line-height:1.1">{escape(str(v))}</div>'
        f'<div style="font-size:12px;color:{MUTED};margin-top:2px">{escape(label)}</div></td>' for v, label in tiles)
    return (f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-top:16px">'
            f'<tr>{cells}</tr></table>')


def compact_list(sec, items, date):
    """Prepared jobs as rows: company and role, where and why it fits, the CV and cover letter, a fit badge and Skip.
    Facts come from the tracker by job id, so every row has them even when the run's JSON is thin."""
    rows = []
    for i in items[:MAX_LIST]:
        skip = next((a for a in i.get("actions", []) if a.get("verb") == "SKIP"), None)
        link = next((a for a in i.get("actions", []) if a.get("url")), None)
        job = JOBS.get(i.get("id") or (skip or {}).get("target") or "", {})
        fit = i.get("fit") or job.get("fit_score") or (re.search(r"fit (\d+)", i.get("detail", "")) or [None, None])[1]
        detail = " · ".join(p for p in re.split(r"\s*·\s*", i.get("detail", "")) if p and not re.fullmatch(r"fit \d+", p))
        why = i.get("why") or re.sub(r"^(ADJACENT|STRONG|STRETCH)\.\s*", "", job.get("fit_summary") or "", flags=re.I)
        why = why if len(why) <= 140 else why[:137].rsplit(" ", 1)[0] + "…"
        url = (link or {}).get("url") or job.get("apply_url") or job.get("url")
        title = escape(i["title"])
        if url:
            title = f'<a href="{escape(url)}" style="color:{INK};text-decoration:none">{title}</a>'
        if job and freshness(job)["urgency"] == "new":
            title += (' <span style="display:inline-block;background-color:#1f8a5b;color:#ffffff;font-size:11px;'
                      'font-weight:700;border-radius:4px;padding:1px 5px;vertical-align:2px">NEW</span>')
        files = job_files(job["id"]) if job else []
        file_links = " &nbsp;·&nbsp; ".join(f'<a href="{escape(u)}" style="color:{NAVY};font-size:13px">{escape(lbl)}</a>'
                                            for lbl, u in files)
        badge = (f'<span style="display:inline-block;background-color:{SOFT};color:{NAVY};font-size:12px;font-weight:700;'
                 f'border-radius:10px;padding:2px 8px">{escape(str(fit))}</span>') if fit else ""
        target = job.get("id") or (skip or {}).get("target")
        skip_link = (f'<a href="{escape(action_href("SKIP", target, date))}" style="color:{MUTED};font-size:12px;'
                     f'text-decoration:underline">Skip</a>') if target and INBOX else ""
        rows.append(f'<tr><td style="padding:10px 0;border-bottom:1px solid {LINE}">'
                    f'<div style="font-weight:600;font-size:15px">{title}</div>'
                    + (f'<div style="color:{MUTED};font-size:13px;margin-top:2px">{escape(detail)}</div>' if detail else "")
                    + (f'<div style="color:{INK};font-size:13px;margin-top:3px">{escape(why)}</div>' if why else "")
                    + (f'<div style="margin-top:4px">{file_links}</div>' if file_links else "")
                    + f'</td><td align="right" valign="middle" style="padding:10px 0 10px 10px;border-bottom:1px solid {LINE};'
                      f'white-space:nowrap">{badge}&nbsp;&nbsp;{skip_link}</td></tr>')
    hidden = len(items) - MAX_LIST + sec.get("more", 0)
    foot = []
    if hidden > 0:
        foot.append(f"+{hidden} more in the add-on")
    if sec.get("note"):
        foot.append(sec["note"])
    return (f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">' + "".join(rows) + "</table>"
            + (f'<div style="color:{MUTED};font-size:13px;margin-top:8px">{escape(" · ".join(foot))}</div>' if foot else ""))


def render(data):
    date = data["date"]
    day = dt.date.fromisoformat(date).strftime("%A, %-d %B") if sys.platform != "win32" else \
        dt.date.fromisoformat(date).strftime("%A, %#d %B")
    body = [f'<div style="font-size:12px;font-weight:700;letter-spacing:.12em;color:{NAVY}">ROLEWISE'
            f'<span style="font-weight:400;letter-spacing:0;color:{MUTED}">&nbsp;&nbsp;·&nbsp;&nbsp;{escape(day)}</span></div>',
            f'<div style="font-size:21px;font-weight:700;line-height:1.3;margin-top:6px;color:{INK}">{escape(data["headline"])}</div>']
    text = [f"Rolewise · {day}", data["headline"], ""]
    s = data.get("stats", {})
    if s:
        body.append(stat_tiles(s))
        text += [f'This week: {s.get("applied_week", 0)} applied · {s.get("interviews", 0)} interviews · '
                 f'reply rate {s.get("response_rate", "n/a")}', ""]
    for sec in data["sections"]:
        items = sec.get("items", [])
        if not items:
            continue
        h, title = heading(sec)
        body.append(h)
        text.append(title.upper())
        if sec["key"] in ("ready", "new"):   # prepared automatically: a scannable list, not a card per job
            body.append(compact_list(sec, items, date))
            text += [f"- {i['title']}" + (f" ({i['detail']})" if i.get("detail") else "") for i in items[:MAX_LIST]]
            if sec.get("note"):
                text.append(f"  {sec['note']}")
            text.append("")
            continue
        accent = SECTIONS.get(sec["key"], ("", NAVY))[1]
        for item in items[:MAX_ITEMS]:
            body.append(card(item, accent, date))
            text.append(f"- {item['title']}" + (f" — {item['detail']}" if item.get("detail") else ""))
            if item.get("message"):
                text.append("    Message: " + item["message"].replace("\n", "\n    "))
            for a in item.get("actions", []):
                text.append(f"    [{a['label']}] " + (a.get("url") or action_href(a["verb"], a["target"], date) or "open a Rolewise session"))
        hidden = len(items) - MAX_ITEMS + sec.get("more", 0)
        if hidden > 0:
            body.append(f'<div style="color:{MUTED};font-size:13px;margin-top:6px">+{hidden} more on the progress page</div>')
            text.append(f"  +{hidden} more on the progress page")
        text.append("")
    # Users without the add-on get a short tip on the first briefing and on Mondays (not every day).
    if not USER.get("fill_addon") and (data.get("first_briefing") or dt.date.fromisoformat(date).weekday() == 0):
        tip = ("Have a laptop with Chrome? The free Rolewise Fill add-on fills application forms for you in seconds; "
               "you just check and submit. Ask Rolewise to \"set up Rolewise Fill\" (about 10 minutes, one command).")
        body.append(f'<div style="margin-top:18px;background-color:{SOFT};border-radius:10px;padding:10px 12px;'
                    f'font-size:14px;color:{INK}">⚡ {escape(tip)}</div>')
        text.append("Tip: " + tip)
    links = [f'<a href="{escape(data["dashboard_url"])}" style="color:{MUTED}">Progress page</a>'] if data.get("dashboard_url") else []
    if INBOX:
        links.insert(0, f'<a href="{escape(INBOX)}" style="color:{NAVY};font-weight:600">Open your Rolewise Inbox</a>')
        links.append(f'<a href="{escape(action_href("PAUSE", "", date))}" style="color:{MUTED}">Pause Rolewise</a>')
    body.append(f'<div style="margin-top:24px;padding-top:12px;border-top:1px solid {LINE};color:{MUTED};font-size:12px">'
                + " &nbsp;·&nbsp; ".join(links) + "</div>")
    if data.get("dashboard_url"):
        text.append(f"Progress page: {data['dashboard_url']}")
    if INBOX:
        text.append(f"Rolewise Inbox (Applied, Later, Skip, Pause): {INBOX}")
    html = (f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" bgcolor="{PAGE}" '
            f'style="background-color:{PAGE}"><tr><td align="center" style="padding:20px 10px">'
            f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:600px">'
            f'<tr><td height="4" bgcolor="{NAVY}" style="height:4px;background-color:{NAVY};border-radius:12px 12px 0 0;'
            f'font-size:0;line-height:0">&nbsp;</td></tr>'
            f'<tr><td bgcolor="#ffffff" style="background-color:#ffffff;border-radius:0 0 12px 12px;padding:22px 24px 20px;'
            f'font-family:{FONT};color:{INK};font-size:15px;line-height:1.45">'
            + "".join(body) + "</td></tr></table></td></tr></table>")
    return html, "\n".join(text)


def subject(data):
    counts = {sec["key"]: len(sec.get("items", [])) for sec in data["sections"]}
    bits = []
    if counts.get("today"):
        bits.append(f"{counts['today']} today")
    if counts.get("ready"):
        bits.append(f"{counts['ready']} ready")
    if counts.get("referral"):
        bits.append(f"{counts['referral']} referral to ask")
    if counts.get("needs_you"):
        bits.append(f"{counts['needs_you']} need you")
    return f"Rolewise {data['date']}: " + (" · ".join(bits) or "all clear")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    src = Path(sys.argv[1])
    data = json.loads(src.read_text(encoding="utf-8"))
    html, txt = render(data)
    src.with_suffix(".html").write_text(html, encoding="utf-8")
    src.with_suffix(".txt").write_text(txt, encoding="utf-8")
    src.with_suffix(".md").write_text(txt, encoding="utf-8")
    print(subject(data))
    print(f"SEND AS HTML: htmlBody = {src.with_suffix('.html')} ({len(html)} chars), body = {src.with_suffix('.txt')}")
