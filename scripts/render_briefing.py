"""Render the daily briefing from coach/briefings/<date>.json into an email (HTML + plain text) and a markdown copy.

Usage: python scripts/render_briefing.py coach/briefings/2026-11-04.json
Writes <date>.html, <date>.txt and <date>.md next to the JSON and prints the email subject.

Buttons are mailto links to the user's own address (profile/user.yaml) with subject "Rolewise action: <VERB> <target>". They tap, hit send,
and the next run reads those emails (daily skill step 0). Verbs:
  SUBMIT <job-id>   submit this application (counts as their explicit yes for that job)
  SKIP <job-id>     mark skipped (optional reason in the body)
  PREPARE <job-id>  tailor CV + cover letter and apply when nothing is open
  SEND <draft-id>   send this Gmail draft as written
  WAIT <job-id>     do nothing for now; re-surface in 3 days
  ANSWER <job-id>   their answer to an open question is in the email body
Link buttons: {"label": "Open & fill", "url": "<apply url>#rolewise-fill"} opens the form on the laptop and
Rolewise Fill fills it automatically (the #rolewise-fill marker); they review and click Submit.

JSON shape:
{"date": "YYYY-MM-DD", "headline": "one line", "stats": {"applied_week": 6, "interviews": 2, "response_rate": "17%"},
 "sections": [{"key": "today|referral|ready|needs_you|new|coach", "title": "...", "items": [
    {"title": "...", "detail": "...", "actions": [{"label": "Submit", "verb": "SUBMIT", "target": "job-id"},
                                                  {"label": "Open kit", "url": "https://..."}]}],
   "more": 4}],
 "dashboard_url": "https://...", "first_briefing": false}
"""
import datetime as dt
import json
import sys
from html import escape
from pathlib import Path
from urllib.parse import quote

from userconf import USER  # noqa: E402

ME = USER["email"]
MAX_ITEMS = 3
NAVY, INK, MUTED, LINE, SOFT = "#1d3461", "#14223b", "#5b6880", "#dde3ec", "#eef2f8"


def mailto(verb, target, date):
    subject = f"Rolewise action: {verb} {target}"
    body = (f"{verb} {target}\n\n(From the {date} briefing. Add a note below if you like, then hit send.)\n")
    return f"mailto:{ME}?subject={quote(subject)}&body={quote(body)}"


def button(action, date, primary):
    """Bulletproof email button: colour on a table cell (bgcolor), which Gmail keeps; it strips <a> backgrounds."""
    href = action.get("url") or mailto(action["verb"], action["target"], date)
    bg, fg = (NAVY, "#ffffff") if primary else ("#ffffff", NAVY)
    return (f'<td bgcolor="{bg}" style="background-color:{bg};border:1px solid {NAVY};border-radius:8px">'
            f'<a href="{escape(href)}" style="display:inline-block;padding:9px 14px;font-size:14px;font-weight:600;'
            f'line-height:16px;color:{fg};text-decoration:none;font-family:Arial,sans-serif">{escape(action["label"])}</a></td>')


def button_row(actions, date):
    cells = '<td width="8" style="width:8px;font-size:0;line-height:0">&nbsp;</td>'.join(
        button(a, date, i == 0) for i, a in enumerate(actions))
    return (f'<table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin-top:8px">'
            f'<tr>{cells}</tr></table>')


def render(data):
    date = data["date"]
    parts = [f'<div style="max-width:600px;margin:0 auto;font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;'
             f'color:{INK};font-size:15px;line-height:1.45">',
             f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"><tr>'
             f'<td bgcolor="{NAVY}" style="background-color:{NAVY};border-radius:12px 12px 0 0;padding:16px 18px">'
             f'<div style="font-size:13px;color:#c9d4e8">Rolewise · {escape(date)}</div>'
             f'<div style="font-size:18px;font-weight:700;margin-top:4px;color:#ffffff">{escape(data["headline"])}</div>'
             f'</td></tr></table>',
             f'<div style="border:1px solid {LINE};border-top:0;border-radius:0 0 12px 12px;padding:6px 18px 16px">']
    text = [f"Rolewise · {date}", data["headline"], ""]
    for sec in data["sections"]:
        items = sec.get("items", [])
        if not items:
            continue
        parts.append(f'<div style="margin-top:16px;font-size:13px;font-weight:700;letter-spacing:.03em;'
                     f'text-transform:uppercase;color:{MUTED}">{escape(sec["title"])}</div>')
        text.append(sec["title"].upper())
        for item in items[:MAX_ITEMS]:
            parts.append(f'<div style="border:1px solid {LINE};border-radius:10px;padding:10px 12px;margin-top:8px">'
                         f'<div style="font-weight:600">{escape(item["title"])}</div>')
            if item.get("detail"):
                parts.append(f'<div style="color:{MUTED};font-size:14px;margin-top:2px">{escape(item["detail"])}</div>')
            if item.get("message"):
                parts.append(f'<div style="margin-top:8px;padding:10px 12px;background-color:#f6f8fb;border-left:3px solid {NAVY};'
                             f'border-radius:6px;font-size:14px;white-space:pre-wrap">{escape(item["message"])}</div>'
                             f'<div style="color:{MUTED};font-size:12px;margin-top:4px">Press and hold to copy.</div>')
            actions = item.get("actions", [])
            if actions:
                parts.append(button_row(actions, date))
            parts.append("</div>")
            line = f"- {item['title']}" + (f" — {item['detail']}" if item.get("detail") else "")
            text.append(line)
            if item.get("message"):
                text.append("    Message: " + item["message"].replace("\n", "\n    "))
            for a in actions:
                target = a.get("url") or f'reply "Rolewise action: {a["verb"]} {a["target"]}"'
                text.append(f"    [{a['label']}] {target}")
        hidden = len(items) - MAX_ITEMS + sec.get("more", 0)
        if hidden > 0:
            parts.append(f'<div style="color:{MUTED};font-size:13px;margin-top:6px">+{hidden} more on the dashboard</div>')
            text.append(f"  +{hidden} more on the dashboard")
        text.append("")
    s = data.get("stats", {})
    if s:
        stat = (f'This week: {s.get("applied_week", 0)} applied · {s.get("interviews", 0)} interviews · '
                f'response rate {s.get("response_rate", "n/a")}')
        parts.append(f'<div style="margin-top:16px;background:{SOFT};border-radius:8px;padding:8px 12px;font-size:14px">'
                     f'📊 {escape(stat)}</div>')
        text.append(stat)
    # Users without the add-on get a short tip on the first briefing and on Mondays (not every day).
    if not USER.get("fill_addon") and (data.get("first_briefing") or dt.date.fromisoformat(date).weekday() == 0):
        tip = ("Have a laptop with Chrome? The free Rolewise Fill add-on fills application forms for you in seconds; "
               "you just check and submit. Set it up once (about 20 min, needs the Claude desktop app): ask "
               "Rolewise to \"set up Rolewise Fill\".")
        parts.append(f'<div style="margin-top:12px;border:1px dashed {NAVY};border-radius:8px;padding:8px 12px;'
                     f'font-size:14px">⚡ {escape(tip)}</div>')
        text.append("Tip: " + tip)
    if data.get("dashboard_url"):
        parts.append(button_row([{"label": "Open dashboard", "url": data["dashboard_url"]}], date))
        text.append(f"Dashboard: {data['dashboard_url']}")
    parts.append(f'<div style="margin-top:14px;color:{MUTED};font-size:12px">Buttons open a pre-written email to yourself. '
                 f'Hit send and the next Rolewise run acts on it.</div></div></div>')
    return "".join(parts), "\n".join(text)


def subject(data):
    counts = {sec["key"]: len(sec.get("items", [])) for sec in data["sections"]}
    bits = []
    if counts.get("today"):
        bits.append(f"{counts['today']} today")
    if counts.get("ready"):
        bits.append(f"{counts['ready']} ready to submit")
    if counts.get("referral"):
        bits.append(f"{counts['referral']} referral to ask")
    if counts.get("needs_you"):
        bits.append(f"{counts['needs_you']} need your tap")
    if counts.get("new"):
        bits.append(f"{counts['new']} new")
    return f"Rolewise briefing {data['date']}: " + (" · ".join(bits) or "all clear")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    src = Path(sys.argv[1])
    data = json.loads(src.read_text(encoding="utf-8"))
    html, txt = render(data)
    src.with_suffix(".html").write_text(html, encoding="utf-8")
    src.with_suffix(".txt").write_text(txt, encoding="utf-8")
    src.with_suffix(".md").write_text(txt, encoding="utf-8")
    print(subject(data))
