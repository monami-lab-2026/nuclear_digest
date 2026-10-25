"""Daily jobs run: public-institution postings + hiring news -> data/jobs -> docs/jobs (+ home page).

python -m app.jobs.run_daily                 # collect and render
python -m app.jobs.run_daily --render-only   # rebuild pages from data/jobs only
python -m app.jobs.run_daily --backfill      # also read past postings to fill the trend charts

Without DATA_GO_KR_KEY the page is still built (links + news) and says the key is missing.
"""
import argparse
import json
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from ..build_home import build_home
from .build_site import build_site
from .collect import (HISTORY_PATH, LATEST_RUN_PATH, NEWS_PATH, SETTINGS, NoKey, collect_alio, collect_news,
                      merge, read_json, service_key, write_json)

KST = ZoneInfo("Asia/Seoul")


def run(backfill=False):
    now = datetime.now(KST)
    today = now.date()
    status = read_json(LATEST_RUN_PATH, {}) or {}
    status.update(run_date=today.isoformat(), started_at=now.isoformat(timespec="seconds"))
    history = read_json(HISTORY_PATH, {}) or {}

    try:
        key = service_key()
        if backfill or not history:
            past, scanned = collect_alio(key, ongoing=False, max_pages=SETTINGS["alio"]["backfill_pages"])
            history = merge(history, past, today)
            status["backfill"] = {"scanned": scanned, "nuclear": len(past)}
        current, scanned = collect_alio(key, ongoing=True)
        history = merge(history, current, today, open_ids={r["id"] for r in current})
        write_json(HISTORY_PATH, dict(sorted(history.items(), key=lambda kv: kv[0], reverse=True)))
        status.update(alio="ok", alio_date=today.isoformat(), scanned=scanned, open=len(current))
    except NoKey:
        status.update(alio="no_key")
    except Exception as error:  # message is already scrubbed of the key
        status.update(alio="error", alio_error=str(error)[:300])

    previous = (read_json(NEWS_PATH, {}) or {}).get("items")
    items, feeds = collect_news(today, previous=previous)
    write_json(NEWS_PATH, {"updated": today.isoformat(), "items": items})
    status.update(news=feeds, news_items=len(items), finished_at=datetime.now(KST).isoformat(timespec="seconds"))
    write_json(LATEST_RUN_PATH, status)
    return status


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render-only", action="store_true")
    parser.add_argument("--backfill", action="store_true")
    args = parser.parse_args(argv)
    status = None if args.render_only else run(args.backfill)
    print(build_site(datetime.now(KST).date()))
    build_home()
    if status:
        print(json.dumps({k: v for k, v in status.items() if k != "news"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
