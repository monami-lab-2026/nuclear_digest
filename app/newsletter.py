"""Email alerts through Buttondown (https://buttondown.com).

Visitors subscribe with the form on docs/subscribe.html (the "이메일로 받기" button at the top of every page).
This module sends the issues:

    python -m app.newsletter news              # latest news day that has commentary and was not sent yet
    python -m app.newsletter news --date 2026-10-22
    python -m app.newsletter papers --dry-run  # print what would be sent

Settings: config/site.json "newsletter". API key: BUTTONDOWN_API_KEY (Actions secret).
With "choose_lists": true subscribers pick news and/or papers on the form (Buttondown tags, a paid add-on),
and each issue goes only to subscribers carrying that tag. With false, every subscriber gets both.
Sent issues are recorded in state/<section>/newsletter-sent.json so a rerun never sends twice.
"""
import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timezone

from .config import ROOT, SITE, section_url

API_URL = "https://api.buttondown.com/v1/emails"
LISTS = {"news": "매일 원자력 뉴스 해설", "papers": "매주 원자력공학 논문 동향"}


def settings():
    return SITE.get("newsletter") or {}


def turned_on():
    """The feature switch: button, subscribe page and sending all follow it."""
    return settings().get("enabled", True) is not False


def enabled():
    return turned_on() and bool(settings().get("username"))


def sent_log_path(section):
    return ROOT / "state" / section / "newsletter-sent.json"


def read_log(section):
    try:
        return json.loads(sent_log_path(section).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def mark_sent(section, key, subject, response_id=""):
    log = read_log(section)
    log[key] = {"sent_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "subject": subject, "id": response_id}
    path = sent_log_path(section)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(sorted(log.items())), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def payload(section, subject, html_body):
    body = "<!-- buttondown-editor-mode: fancy -->\n" + html_body
    data = {"subject": subject, "body": body, "status": "about_to_send"}
    if settings().get("choose_lists"):
        data["filters"] = {"predicate": "and", "groups": [],
                           "filters": [{"field": "subscriber.tags", "operator": "contains", "value": section}]}
    return data


def send(section, key, subject, html_body, dry_run=False, force=False):
    """Returns a short status string; never raises for 'nothing to do' cases."""
    if not turned_on():
        return "skipped: newsletter turned off (config/site.json newsletter.enabled)"
    if not enabled():
        return "skipped: newsletter.username not set in config/site.json"
    if key in read_log(section) and not force:
        return f"skipped: {section} {key} already sent"
    data = payload(section, subject, html_body)
    if dry_run:
        return "dry-run: " + json.dumps({k: (v if k != "body" else v[:200] + "...") for k, v in data.items()}, ensure_ascii=False)
    api_key = os.environ.get("BUTTONDOWN_API_KEY", "").strip()
    if not api_key:
        return "skipped: BUTTONDOWN_API_KEY not set"
    import requests

    response = requests.post(API_URL, json=data, headers={"Authorization": f"Token {api_key}"}, timeout=60)
    if response.status_code >= 300:
        raise RuntimeError(f"Buttondown {response.status_code}: {response.text[:300]}")
    mark_sent(section, key, subject, response.json().get("id", ""))
    return "sent"


# ---------- news issue ----------

def esc(value):
    return (str(value or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def news_html(record):
    day = record["date"]
    page = f"{section_url('news')}days/{day}.html"
    parts = [f'<p><strong>{esc(SITE["title"])}</strong> · {esc(day)} 원자력 뉴스 해설</p>']
    if record.get("overview"):
        parts.append(f"<p>{esc(record['overview'])}</p>")
    for n, story in enumerate(record.get("stories", []), 1):
        parts.append(f'<h3>{n:02d}. {esc(story["headline"])}</h3>')
        parts.append(f'<p><em>{esc(story["region"])} · {esc(story["category"])}</em></p>')
        parts.append(f"<p>{esc(story['summary'])}</p>")
        parts.append(f"<p><strong>공학도에게 왜 중요한가</strong><br>{esc(story['why_it_matters'])}</p>")
        if story.get("question"):
            parts.append(f"<p><strong>생각해 볼 질문</strong><br>{esc(story['question'])}</p>")
    parts.append(f'<p><a href="{esc(page)}">개념 풀이·원문 기사 링크까지 사이트에서 보기 →</a></p>')
    parts.append("<p><small>기사 원문의 저작권은 각 언론사에 있으며, 해설은 Claude(AI)가 제목과 요지만 보고 새로 쓴 글이라 틀릴 수 있습니다.</small></p>")
    return "\n".join(parts)


def latest_news_day(day=None):
    folder = ROOT / "data" / "news" / "days"
    paths = [folder / f"{day}.json"] if day else sorted(folder.glob("*.json"), reverse=True)
    for path in paths:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            continue
        if record.get("stories"):
            return record
        if day:
            return None
    return None


def send_news(day=None, dry_run=False, force=False):
    record = latest_news_day(day)
    if not record:
        return "skipped: no news day with commentary yet"
    if not day and (date.today() - date.fromisoformat(record["date"])).days > 2:
        return f"skipped: latest commentary ({record['date']}) is too old to send as news"
    d = date.fromisoformat(record["date"])
    subject = f"[{SITE['title']}] {d.month}월 {d.day}일 원자력 뉴스 · {record['stories'][0]['headline']}"
    return send("news", record["date"], subject[:150], news_html(record), dry_run=dry_run, force=force)


# ---------- papers issue ----------

def papers_html(email_html):
    """The weekly paper email is a full HTML document; keep only the body content."""
    match = re.search(r"<body[^>]*>(.*)</body>", email_html, re.S)
    return match.group(1) if match else email_html


def send_papers(run_id, email_html, dry_run=False, force=False):
    subject = SITE["email"]["subject"].format(run_date=run_id)
    return send("papers", run_id, subject, papers_html(email_html), dry_run=dry_run, force=force)


def send_latest_papers(dry_run=False, force=False):
    folder = ROOT / "outputs" / "papers"
    emails = sorted(folder.glob("email-*.html"))
    if not emails:
        return "skipped: no paper email built yet"
    run_id = emails[-1].stem.removeprefix("email-")
    return send_papers(run_id, emails[-1].read_text(encoding="utf-8"), dry_run=dry_run, force=force)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("section", choices=["news", "papers"])
    parser.add_argument("--date", help="news day (YYYY-MM-DD); default = latest day with commentary")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="send even if already sent")
    args = parser.parse_args()
    if args.section == "news":
        result = send_news(args.date, dry_run=args.dry_run, force=args.force)
    else:
        result = send_latest_papers(dry_run=args.dry_run, force=args.force)
    print(result)
    sys.exit(0)


if __name__ == "__main__":
    main()
