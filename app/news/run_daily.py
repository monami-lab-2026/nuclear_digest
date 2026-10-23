"""Daily entry point: collect -> brief -> save day JSON -> render site.

python -m app.news.run_daily                  # today (KST)
python -m app.news.run_daily --date 2026-09-28
python -m app.news.run_daily --render-only    # rebuild docs/ from data/news/days only
"""
import argparse
import json
import sys
from datetime import date

from ..build_home import build_home
from .brief import write_brief
from .build_site import build_site
from .collect import collect, story_keys
from .common import (DAYS_DIR, LATEST_RUN_PATH, SEEN_PATH, SETTINGS, date_label, now_utc, prune_seen,
                     read_json, today_kst, write_json)


def run(day, force=False):
    day_path = DAYS_DIR / f"{day.isoformat()}.json"
    existing = read_json(day_path)
    # Only a failed model call is worth redoing automatically; everything else needs --force.
    if existing and existing.get("engine", {}).get("engine") != "failed" and not force:
        print(json.dumps({"skip": f"{day} already published"}, ensure_ascii=False))
        return existing

    seen = prune_seen(read_json(SEEN_PATH, {}) or {}, day, SETTINGS["seen_retention_days"])
    # News marked on this same day must stay eligible when the day is rebuilt.
    candidates, feed_status = collect({k: v for k, v in seen.items() if v < day.isoformat()})
    if not any(s.get("ok") for s in feed_status.values()):
        raise RuntimeError(f"every feed failed: {json.dumps(feed_status, ensure_ascii=False)}")

    brief, engine = write_brief(candidates, date_label(day))

    for cluster in candidates:  # feed ledes are model input only; never stored or published
        for item in cluster["items"]:
            item.pop("snippet", None)
            item.pop("priority", None)

    record = {
        "date": day.isoformat(),
        "generated_at": now_utc().isoformat(timespec="seconds"),
        "engine": engine,
        "overview": brief["overview"],
        "stories": brief["stories"],
        "sources": candidates,
        "feeds": feed_status,
    }
    write_json(day_path, record)

    # Mark as seen unless the model call failed — then the retry run can brief the same news.
    if engine["engine"] != "failed":
        for cluster in candidates:
            for item in cluster["items"]:
                for key in story_keys(item):
                    seen[key] = day.isoformat()
        write_json(SEEN_PATH, dict(sorted(seen.items())))
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="YYYY-MM-DD (default: today in KST)")
    parser.add_argument("--render-only", action="store_true")
    parser.add_argument("--force", action="store_true", help="rebuild a day that was already briefed")
    args = parser.parse_args()
    day = date.fromisoformat(args.date) if args.date else today_kst()

    state = {"run_date": day.isoformat(), "started_at": now_utc().isoformat(timespec="seconds")}
    try:
        if not args.render_only:
            record = run(day, force=args.force)
            state.update(
                engine=record["engine"],
                stories=len(record["stories"]),
                sources=len(record["sources"]),
                feeds=record["feeds"],
            )
        state["days_rendered"] = build_site()
        build_home()
        # 'partial' = page published without commentary because the model call failed; the 09:00 retry runs again.
        state["status"] = "partial" if state.get("engine", {}).get("engine") == "failed" else "success"
    except Exception as error:
        state.update(status="failed", error=str(error)[:500])
        write_json(LATEST_RUN_PATH, state)
        print(json.dumps(state, ensure_ascii=False, indent=2))
        sys.exit(1)
    state["finished_at"] = now_utc().isoformat(timespec="seconds")
    if not args.render_only:
        write_json(LATEST_RUN_PATH, state)
    print(json.dumps(state, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
