"""Shared paths, settings, and small helpers for the daily news pipeline.

The same pipeline serves several news sections. NEWS_TOPIC picks one (default: nuclear news):
    NEWS_TOPIC=news    config/news.json         data/news    state/news    docs/news
    NEWS_TOPIC=fusion  config/news_fusion.json  data/fusion  state/fusion  docs/fusion
"""
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from ..config import DOCS_DIR, ROOT, SITE, _load, section_url

TOPIC = os.environ.get("NEWS_TOPIC", "news").strip() or "news"
DATA_DIR = ROOT / "data" / TOPIC
DAYS_DIR = DATA_DIR / "days"          # one JSON per published day (the archive)
STATE_DIR = ROOT / "state" / TOPIC
SEEN_PATH = STATE_DIR / "seen.json"   # story keys already published, so a story is not repeated the next day
LATEST_RUN_PATH = STATE_DIR / "latest-run.json"
SITE_DIR = DOCS_DIR / TOPIC

SETTINGS = _load("news.json" if TOPIC == "news" else f"news_{TOPIC}.json")
SETTINGS.update(site_url=section_url(TOPIC), contact_email=SITE["contact_email"],
                timezone=SITE.get("timezone", "Asia/Seoul"),
                interests=SITE.get("interests", {}) if TOPIC == "news" else {})
# Words that differ between sections (page titles, model instructions).
SETTINGS.setdefault("label", "원자력")
SETTINGS.setdefault("audience", SITE.get("audience", "원자력공학을 공부하는 학생"))
SETTINGS.setdefault("reader", "원자력공학도")
SETTINGS.setdefault("eyebrow", "Nuclear News Brief")
# The paper section of this same site is always available as a reference link.
SETTINGS["reference_library"] = [r for r in SETTINGS["reference_library"] if r["id"] != "papers"] + [
    {"id": "papers", "name": "이번 주 원자력공학 논문 (이 사이트)", "url": section_url("papers"),
     "about": "주요 저널 신규 논문 주간 동향과 누적 논문 DB"}]
KST = ZoneInfo(SETTINGS["timezone"])
USER_AGENT = f"NuclearDailyDigest/1.0 (+{SITE['site_url']}; mailto:{SITE['contact_email']})"

WEEKDAYS_KO = "월화수목금토일"


def now_utc():
    return datetime.now(timezone.utc)


def today_kst():
    return now_utc().astimezone(KST).date()


def date_label(value):
    """2026-09-28 -> '2026년 9월 28일 (월)'"""
    return f"{value.year}년 {value.month}월 {value.day}일 ({WEEKDAYS_KO[value.weekday()]})"


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def strip_markup(value):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value or "")).strip()


def normalize_title(title):
    """Lower-case word tokens used for de-duplication (publisher suffix and punctuation removed)."""
    text = re.sub(r"\s[-–|]\s[^-–|]{1,40}$", "", title or "")  # 'headline - 언론사'
    text = re.sub(r"\[[^\]]{1,20}\]|【[^】]{1,20}】", " ", text)   # [단독], [포토] ...
    return re.findall(r"[0-9a-z가-힣]+", text.lower())


def keyword_hit(text, keywords):
    """Case-insensitive match. Short Latin keywords (SMR, NRC ...) need word boundaries."""
    lowered = (text or "").lower()
    for word in keywords:
        w = word.lower()
        if re.fullmatch(r"[a-z0-9\-]{2,6}", w):
            if re.search(rf"(?<![a-z0-9]){re.escape(w)}(?![a-z0-9])", lowered):
                return True
        elif w in lowered:
            return True
    return False


def prune_seen(seen, today, days):
    cutoff = (today - timedelta(days=days)).isoformat()
    return {key: day for key, day in seen.items() if day >= cutoff}
