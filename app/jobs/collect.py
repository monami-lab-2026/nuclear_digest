"""Collect nuclear-related job postings and hiring news.

Public institutions: 공공데이터포털 15125273 '공공기관 채용정보 조회서비스' (잡알리오).
    GET https://apis.data.go.kr/1051000/recruitment/list
        ?serviceKey=...&resultType=json&ongoingYn=Y&pageNo=1&numOfRows=100
    -> {"resultCode":200,"resultMsg":"...","totalCount":N,"result":[{"recrutPblntSn":305916,"instNm":"...",
        "recrutPbancTtl":"...","pbancBgngYmd":"20261012","pbancEndYmd":"20261019","workRgnNmLst":"...",
        "hireTypeNmLst":"...","recrutSeNm":"...","srcUrl":"...", ...}]}
The key comes from the DATA_GO_KR_KEY environment variable (a GitHub Actions secret) and is never
written to disk or logs.

Everything else on the page (private companies, overseas, graduate school/postdoc) is the curated
link directory in config/jobs.json — those sites have no open feed we may republish.
"""
import json
import os
import re
import time
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote, unquote

import requests

from ..config import ROOT, SITE, _load

SETTINGS = _load("jobs.json")
DATA_DIR = ROOT / "data" / "jobs"
STATE_DIR = ROOT / "state" / "jobs"
HISTORY_PATH = DATA_DIR / "postings.json"   # every nuclear posting seen, keyed by 잡알리오 번호
NEWS_PATH = DATA_DIR / "news.json"
LATEST_RUN_PATH = STATE_DIR / "latest-run.json"
USER_AGENT = f"NuclearDailyDigest/1.0 (+{SITE['site_url']}; mailto:{SITE['contact_email']})"
OTHER_GROUP = "기타 관련"
ROWS = 100


class NoKey(Exception):
    pass


def read_json(path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def service_key():
    key = os.environ.get("DATA_GO_KR_KEY", "").strip()
    if not key:
        raise NoKey("DATA_GO_KR_KEY 미설정")
    return unquote(key) if "%" in key else key  # the portal's 'Encoding' key also works


def scrub(text, key):
    """Remove the service key (raw or URL-encoded) from an error message before it is logged."""
    text = str(text)
    for form in {key, quote(key, safe=""), quote(key)}:
        if form:
            text = text.replace(form, "***")
    return re.sub(r"(?i)(servicekey=)[^&\s'\"]+", r"\1***", text)


def ymd(value):
    """'20261018' -> '2026-10-18'. Empty, '1900…' or invalid -> None."""
    m = re.fullmatch(r"(\d{4})(\d{2})(\d{2})", str(value or "").strip())
    if not m or m.group(1) < "2000":
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
    except ValueError:
        return None


def parse_page(content):
    """(items, totalCount). Gateway errors arrive as XML, API errors as resultCode != 200."""
    try:
        data = json.loads(content)
    except ValueError:
        text = content.decode("utf-8", "replace") if isinstance(content, bytes) else str(content)
        raise RuntimeError(f"잡알리오 API 오류: {' '.join(text.split())[:200]}") from None
    if str(data.get("resultCode")) != "200":
        raise RuntimeError(f"잡알리오 API 오류: {data.get('resultCode')} {data.get('resultMsg', '')}")
    return list(data.get("result") or []), int(data.get("totalCount") or 0)


def fetch_page(key, page, ongoing=True):
    params = {"serviceKey": key, "resultType": "json", "pageNo": page, "numOfRows": ROWS}
    if ongoing:
        params["ongoingYn"] = "Y"
    last = None
    for attempt in range(3):
        try:
            response = requests.get(SETTINGS["alio"]["endpoint"], params=params,
                                    headers={"User-Agent": USER_AGENT}, timeout=40)
            response.raise_for_status()
            return parse_page(response.content)
        except Exception as error:  # network, HTTP, API error
            last = RuntimeError(scrub(error, key))
            time.sleep(2 * (attempt + 1))
    raise last


def group_for(item):
    """Institution group for a nuclear posting, or None if the posting is not nuclear-related."""
    inst = str(item.get("instNm") or "")
    for entry in SETTINGS["institutions"]:
        if any(name in inst for name in entry["names"]):
            return entry["group"]
    title = str(item.get("recrutPbancTtl") or "")
    if any(word.lower() in title.lower() for word in SETTINGS["title_keywords"]):
        return OTHER_GROUP
    return None


def split_list(value):
    return [part.strip() for part in re.split(r"[,/]", str(value or "")) if part.strip()]


def to_record(item, group):
    sn = str(item.get("recrutPblntSn") or "").strip()
    return {
        "id": sn,
        "inst": str(item.get("instNm") or "").strip(),
        "group": group,
        "title": " ".join(str(item.get("recrutPbancTtl") or "").split()),
        "start": ymd(item.get("pbancBgngYmd")),
        "end": ymd(item.get("pbancEndYmd")),
        "hire": split_list(item.get("hireTypeNmLst")),
        "kind": str(item.get("recrutSeNm") or "").strip(),
        "region": split_list(item.get("workRgnNmLst")),
        "count": item.get("recrutNope"),
        "url": SETTINGS["alio"]["view_url"].format(sn=sn),
        "src": str(item.get("srcUrl") or "").strip(),
    }


def collect_alio(key, ongoing=True, max_pages=None, pages=None):
    """Return nuclear postings from the API. `pages` lets tests inject [(items, total), ...]."""
    max_pages = max_pages or SETTINGS["alio"]["max_pages"]
    found, scanned = [], 0
    for page in range(1, max_pages + 1):
        items, total = pages[page - 1] if pages is not None else fetch_page(key, page, ongoing)
        scanned += len(items)
        for item in items:
            group = group_for(item)
            if group and item.get("recrutPblntSn") and item.get("recrutPbancTtl"):
                found.append(to_record(item, group))
        if not items or page * ROWS >= total or (pages is not None and page >= len(pages)):
            break
    return found, scanned


def merge(history, records, today, open_ids=None):
    """Fold today's records into the history. Postings missing from a complete 'open' fetch are closed."""
    iso = today.isoformat()
    for record in records:
        old = history.get(record["id"], {})
        record["first_seen"] = old.get("first_seen") or iso
        record["last_seen"] = iso
        history[record["id"]] = {**old, **record}
    if open_ids is not None:
        for pid, record in history.items():
            record["open"] = pid in open_ids and (not record.get("end") or record["end"] >= iso)
    cutoff = (today - timedelta(days=SETTINGS["history_days"])).isoformat()
    return {pid: r for pid, r in history.items()
            if r.get("open") or (r.get("end") or r.get("start") or r.get("first_seen") or iso) >= cutoff}


# ---------------------------------------------------------------- hiring news

def _has_any(text, words):
    low = text.lower()
    return any(w.lower() in low for w in words)


def collect_news(today, entries_by_feed=None, previous=None):
    """Hiring/workforce headlines (title, publisher, link, time only). Keeps older items if a feed fails."""
    from ..news.collect import entry_record, fetch_feed
    from ..news.common import normalize_title

    cfg = SETTINGS["news"]
    since = datetime.combine(today - timedelta(days=cfg["lookback_days"]), datetime.min.time(), tzinfo=timezone.utc)
    items, status = [], {}
    for feed in cfg["feeds"]:
        feed = {"priority": 2, **feed}
        try:
            entries = entries_by_feed[feed["id"]] if entries_by_feed is not None else fetch_feed(feed)
        except KeyError:
            continue
        except Exception as error:
            status[feed["id"]] = {"ok": False, "error": str(error)[:200]}
            continue
        kept = 0
        for entry in entries:
            record = entry_record(entry, feed)
            if not record["title"] or not record["url"]:
                continue
            if not (_has_any(record["title"], cfg["must_have_any"]) and _has_any(record["title"], cfg["topic_any"])):
                continue
            items.append({k: record[k] for k in ("title", "publisher", "url", "published", "region")})
            kept += 1
        status[feed["id"]] = {"ok": True, "entries": len(entries), "kept": kept}
    if not any(s.get("ok") for s in status.values()) and previous:
        items = list(previous)
    seen, unique = set(), []
    for item in sorted(items, key=lambda i: i.get("published") or "", reverse=True):
        if item.get("published") and datetime.fromisoformat(item["published"]) < since:
            continue
        sig = "".join(normalize_title(item["title"]))[:40]
        if sig in seen or item["url"] in seen:
            continue
        seen.update({sig, item["url"]})
        unique.append(item)
    return unique[: cfg["limit"] * 2], status
