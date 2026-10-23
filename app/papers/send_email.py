"""SMTP delivery (Gmail App Password by default) with UTF-8 inline HTML and duplicate protection."""
import argparse
import os
import smtplib
import ssl
from datetime import datetime
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr, make_msgid

from .common import SETTINGS, STATE_DIR, read_json, write_json

SENT_LOG = STATE_DIR / "sent-runs.json"


def smtp_configured():
    return bool(os.environ.get("SMTP_USER") and os.environ.get("SMTP_PASSWORD"))


def send(subject, html_body, recipients=None, plain=False):
    recipients = recipients or SETTINGS["recipients"]
    user, password = os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"]
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "465"))
    # The body is encoded as UTF-8 base64 so Korean text survives every mail client (the Codex-era rule).
    message = MIMEText(html_body, "plain" if plain else "html", "utf-8")
    message["Subject"] = Header(subject, "utf-8")
    message["From"] = formataddr((str(Header("원자력 문헌 다이제스트", "utf-8")), user))
    message["To"] = ", ".join(recipients)
    message["Message-ID"] = make_msgid(domain=user.split("@")[-1])
    context = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=context, timeout=60) as server:
            server.login(user, password)
            server.sendmail(user, recipients, message.as_string())
    else:
        with smtplib.SMTP(host, port, timeout=60) as server:
            server.starttls(context=context)
            server.login(user, password)
            server.sendmail(user, recipients, message.as_string())


def already_sent(run_id):
    return run_id in (read_json(SENT_LOG, {}) or {})


def send_digest(run_id, html_body, force=False):
    if already_sent(run_id) and not force:
        return "skipped: already sent"
    subject = SETTINGS["email_subject"].format(run_date=run_id)
    send(subject, html_body)
    log = read_json(SENT_LOG, {}) or {}
    log[run_id] = {"sent_at": datetime.now().astimezone().isoformat(timespec="seconds"), "recipients": SETTINGS["recipients"], "subject": subject}
    write_json(SENT_LOG, dict(sorted(log.items())))
    return "sent"


def main():
    parser = argparse.ArgumentParser(description="Send a failure notice or a test mail")
    parser.add_argument("--failure", help="Send a failure notice with this text")
    parser.add_argument("--test", action="store_true", help="Send a Korean-encoding test mail")
    args = parser.parse_args()
    if not smtp_configured():
        print("SMTP_USER/SMTP_PASSWORD not set; nothing sent")
        return
    if args.failure:
        send("[원자력 문헌 다이제스트] 주간 실행 실패 알림", args.failure, plain=True)
        print("failure notice sent")
    elif args.test:
        send("[원자력 문헌 다이제스트] 한글 인코딩 테스트", "<p>원자력공학 최근 논문 다이제스트 · 주간 연구 토픽 변화 · 누적 논문</p>")
        print("test mail sent")


if __name__ == "__main__":
    main()
