"""Collect nuclear news headlines from RSS/Atom feeds, filter, and group duplicates.

Only metadata is kept: headline, publisher, link, time. The short feed summary (if any) is used
in memory as model input and is never written to disk or published — article text stays with
the publisher.
"""
import calendar
import time
from datetime import datetime, timedelta, timezone

import feedparser
import requests

from .common import SETTINGS, USER_AGENT, keyword_hit, normalize_title, strip_markup

SNIPPET_CHARS = 300


def fetch_feed(feed):
    last_error = None
    for attempt in range(3):
        try:
            response = requests.get(feed["url"], headers={"User-Agent": USER_AGENT}, timeout=30)
            response.raise_for_status()
            parsed = feedparser.parse(response.content)
            if parsed.bozo and not parsed.entries:
                raise RuntimeError(f"unparseable feed: {parsed.bozo_exception}")
            return parsed.entries
        except Exception as error:  # network, HTTP, parse
            last_error = error
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(str(last_error))


def entry_time(entry):
    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key)
        if value:
            return datetime.fromtimestamp(calendar.timegm(value), tz=timezone.utc)
    return None


def entry_record(entry, feed):
    title = strip_markup(entry.get("title", ""))
    source = entry.get("source") or {}
    publisher = strip_markup(source.get("title", "")) if isinstance(source, dict) else ""
    if feed.get("aggregator") and publisher and title.endswith(f" - {publisher}"):
        title = title[: -len(publisher) - 3].strip()
    # Aggregator summaries are just link lists; specialist feeds carry a one-line lede.
    snippet = "" if feed.get("aggregator") else strip_markup(entry.get("summary", ""))[:SNIPPET_CHARS]
    published = entry_time(entry)
    return {
        "title": title,
        "publisher": publisher or feed["name"],
        "url": entry.get("link", ""),
        "published": published.isoformat() if published else None,
        "feed": feed["id"],
        "region": feed["region"],
        "priority": feed.get("priority", 2),
        "snippet": snippet,
    }


def is_relevant(record, feed):
    text = f"{record['title']} {record['snippet']}"
    if keyword_hit(text, SETTINGS["exclude_keywords"]):
        return False
    if feed.get("needs_keyword") and not keyword_hit(text, SETTINGS["include_keywords"]):
        return False
    return True


def shingles(title):
    joined = "".join(normalize_title(title))
    return {joined[i:i + 2] for i in range(max(len(joined) - 1, 1))}


def similar(a, b):
    if not a or not b:
        return False
    return len(a & b) / len(a | b) >= 0.45


def group_duplicates(records):
    """Greedy clustering: the same event reported by several outlets becomes one story."""
    records = sorted(records, key=lambda r: (r["priority"], r["published"] or ""), reverse=False)
    clusters = []
    for record in records:
        sig = shingles(record["title"])
        for cluster in clusters:
            if cluster["region"] == record["region"] and similar(sig, cluster["_sig"]):
                cluster["items"].append(record)
                break
        else:
            clusters.append({"region": record["region"], "_sig": sig, "items": [record]})
    return clusters


def story_keys(record):
    keys = [f"u:{record['url']}"] if record["url"] else []
    tokens = "".join(normalize_title(record["title"]))
    if len(tokens) >= 8:
        keys.append(f"t:{tokens[:80]}")
    return keys


def rank(cluster, now):
    items = cluster["items"]
    newest = max((i["published"] for i in items if i["published"]), default=None)
    age_h = (now - datetime.fromisoformat(newest)).total_seconds() / 3600 if newest else 24
    specialist = any(i["priority"] == 1 for i in items)
    return (2 if specialist else 0) + min(len(items), 4) - age_h / 24


def collect(seen, now=None, entries_by_feed=None):
    """Return (candidates, feed_status).

    entries_by_feed lets tests inject parsed feed entries instead of fetching.
    """
    now = now or datetime.now(timezone.utc)
    window_start = now - timedelta(hours=SETTINGS["lookback_hours"])
    feed_status, records, urls = {}, [], set()

    for feed in SETTINGS["feeds"]:
        if feed.get("enabled", True) is False:
            continue
        try:
            entries = entries_by_feed[feed["id"]] if entries_by_feed is not None else fetch_feed(feed)
        except KeyError:
            continue
        except Exception as error:
            feed_status[feed["id"]] = {"ok": False, "error": str(error)[:300]}
            continue
        kept = 0
        for entry in entries:
            record = entry_record(entry, feed)
            if not record["title"] or not record["url"] or record["url"] in urls:
                continue
            if record["published"] and datetime.fromisoformat(record["published"]) < window_start:
                continue
            if not is_relevant(record, feed):
                continue
            if any(key in seen for key in story_keys(record)):
                continue
            urls.add(record["url"])
            records.append(record)
            kept += 1
        feed_status[feed["id"]] = {"ok": True, "entries": len(entries), "kept": kept}

    clusters = group_duplicates(records)
    for cluster in clusters:
        cluster.pop("_sig")
        cluster["items"].sort(key=lambda i: (i["priority"], i["published"] or ""))
        cluster["score"] = round(rank(cluster, now), 3)
    clusters.sort(key=lambda c: c["score"], reverse=True)

    # Keep both domestic and international news in the candidate list even on a lopsided day.
    limit = SETTINGS["max_candidates"]
    by_region = {"국내": [c for c in clusters if c["region"] == "국내"],
                 "해외": [c for c in clusters if c["region"] != "국내"]}
    picked = by_region["국내"][: limit // 2] + by_region["해외"][: limit // 2]
    rest = [c for c in clusters if c not in picked]
    picked += rest[: limit - len(picked)]
    picked.sort(key=lambda c: c["score"], reverse=True)
    for index, cluster in enumerate(picked):
        cluster["id"] = index
    return picked, feed_status
