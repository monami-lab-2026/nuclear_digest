"""Weekly pipeline entry point.

    python -m app.papers.run_weekly                     # this week's Monday (Asia/Seoul)
    python -m app.papers.run_weekly --run-date 2026-09-21
    python -m app.papers.run_weekly --skip-collect --no-email   # rebuild outputs from the DB only

Missed weeks between the last recorded run and the target Monday are collected automatically
(emails are sent only for the target week).
"""
import argparse
import json
import os
import traceback
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import shutil

from .. import newsletter
from ..build_home import build_home
from . import build_dashboard, build_database_page, build_email, build_excel, collect, database, send_email, translate
from .common import (OUTPUT_DIR, SETTINGS, SITE_DIR, STATE_DIR, Period, all_journals, in_domain, raw_path, read_json,
                     use_domain, write_json)

KST = ZoneInfo("Asia/Seoul")
STATUS_PATH = STATE_DIR / "latest-run.json"
JOURNALS_PATH = STATE_DIR / "journals-covered.json"


def log(event, **fields):
    print(json.dumps({"time": datetime.now(KST).isoformat(timespec="seconds"), "event": event, **fields}, ensure_ascii=False, default=str), flush=True)


def weeks_to_collect(con, target, max_backfill):
    last = database.last_run_id(con)
    weeks = []
    if last:
        monday = date.fromisoformat(last) + timedelta(days=7)
        while monday < target.run_date:
            weeks.append(Period(monday))
            monday += timedelta(days=7)
    if len(weeks) > max_backfill:
        raise RuntimeError(f"{len(weeks)} missed weeks since {last}; run with --max-backfill {len(weeks)} to confirm")
    return weeks + [target]


def collect_week(con, period):
    records = collect.collect(period)
    stats = translate.translate_records(records)
    write_json(raw_path(period, "current"), records)
    found, new = database.upsert_run(con, period, records)
    log("collected", run_id=period.run_id, start=period.start, end=period.end, found=found, new=new, translation=stats)
    return found


def backfill_new_journals(con):
    """A journal added to config/settings.json is collected for every period already in the DB,
    so weekly trends never compare weeks with different journal sets."""
    covered = read_json(JOURNALS_PATH, None)
    # Coverage is keyed by name + ISSNs, so adding an ISSN to an existing journal also triggers a backfill.
    configured = [f"{name} [{issns}]" for name, issns in all_journals().items()]
    if covered is None:  # first run with this feature: everything configured so far is complete
        write_json(JOURNALS_PATH, configured)
        return
    new_keys = [key for key in configured if key not in covered]
    if not new_keys:
        return
    new = [key.split(" [")[0] for key in new_keys]
    runs = con.execute("SELECT run_id, period_start, period_end FROM collection_runs ORDER BY run_id").fetchall()
    # Optionally only the most recent weeks (keeps the first run after adding many journals short).
    if SETTINGS.get("new_journal_backfill_weeks"):
        runs = runs[-int(SETTINGS["new_journal_backfill_weeks"]):]
    for run in runs:
        period = Period(date.fromisoformat(run["run_id"]))
        records = collect.collect(period, journals=new, start=run["period_start"], end=run["period_end"])
        translate.translate_records(records)
        found, added = database.upsert_run(con, period, records, additive=True)  # only newly found papers are added to the run counts
        log("journal-backfill", run_id=run["run_id"], journals=new, found=found, new=added)
    write_json(JOURNALS_PATH, [key for key in covered if key in configured] + new_keys)


def domain_payload(payload, name):
    """The DB export restricted to one section, with that section's topic rules applied."""
    from .common import topics_for
    papers = [dict(p) for p in payload["papers"] if in_domain(database.as_record(p), name)]
    links = []
    with use_domain(name):
        for p in papers:
            areas = topics_for({"title": p["title_en"], "journal": p["journal"], "abstract": p.get("abstract") or ""})
            p["primary_topic"] = areas[0]
            links += [{"doi": p["doi"], "topic_ko": a, "is_primary": int(i == 0)} for i, a in enumerate(areas)]
    return {**payload, "papers": papers, "paper_topics": links}


def build_section(name, period, all_current, all_previous, payload, run_count):
    """Weekly dashboard + archive + DB page for one section. Nuclear lives in papers/, fusion in papers/fusion/."""
    base = SITE_DIR if name == "nuclear" else SITE_DIR / name
    depth = "" if name == "nuclear" else "../"
    section = domain_payload(payload, name)
    current = [r for r in all_current if in_domain(r, name)]
    previous = [r for r in all_previous if in_domain(r, name)]
    cumulative = [database.as_record(r) for r in section["papers"]]
    (base / "archive").mkdir(parents=True, exist_ok=True)
    for path, prefix in [(base / "index.html", "./" + depth), (base / "archive" / f"{period.run_id}.html", "../" + depth)]:
        try:
            page = build_dashboard.render(period, [dict(r) for r in current], [dict(r) for r in previous], cumulative,
                                          run_count, prefix, domain=name)
        except ValueError as error:  # e.g. no papers yet in this section for the week
            if name == "nuclear":
                raise
            page = build_dashboard.render_empty(period, prefix, name, str(error))
        path.write_text(page, encoding="utf-8")
    archives = [path.stem for path in (base / "archive").glob("*.html")]
    with use_domain(name):
        (base / "database.html").write_text(build_database_page.render(section, archives, domain=name), encoding="utf-8")
    return current, previous, section


def build_outputs(con, period):
    all_current = [database.as_record(r) for r in database.papers_between(con, period.start, period.end)]
    all_previous = [database.as_record(r) for r in database.papers_between(con, period.previous.start, period.previous.end)]
    payload = database.export_payload(con)
    run_count = len(payload["runs"])
    fusion_current, _, _ = build_section("fusion", period, all_current, all_previous, payload, run_count)
    current, previous, nuclear = build_section("nuclear", period, all_current, all_previous, payload, run_count)

    email_html = build_email.render(period, current, previous, len(nuclear["papers"]), run_count)
    email_path = OUTPUT_DIR / f"email-{period.run_id}.html"
    email_path.parent.mkdir(parents=True, exist_ok=True)
    email_path.write_text(email_html, encoding="utf-8")

    excel_path = build_excel.build(payload, OUTPUT_DIR / "nuclear-literature-database.xlsx")
    shutil.copy2(excel_path, SITE_DIR / excel_path.name)
    return {"current": len(current), "previous": len(previous), "papers": len(nuclear["papers"]), "runs": run_count,
            "fusion_current": len(fusion_current), "all_papers": len(payload["papers"]),
            "email_html": email_html, "email_path": email_path, "excel_path": excel_path}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-date", default=os.environ.get("RUN_DATE") or datetime.now(KST).date().isoformat())
    parser.add_argument("--skip-collect", action="store_true")
    parser.add_argument("--no-email", action="store_true")
    parser.add_argument("--force-email", action="store_true", help="Send even if this week was already sent")
    parser.add_argument("--max-backfill", type=int, default=6)
    args = parser.parse_args()

    period = Period.for_date(date.fromisoformat(args.run_date))
    started = datetime.now(KST)
    status = {"run_date": period.run_id, "period_start": str(period.start), "period_end": str(period.end), "started_at": started.isoformat(timespec="seconds")}
    try:
        con = database.connect()
        if not args.skip_collect:
            backfill_new_journals(con)
            for week in weeks_to_collect(con, period, args.max_backfill):
                collect_week(con, week)
            log("enriched", **collect.enrich_recent(con, since=period.start - timedelta(weeks=11)))
        log("reclassified", papers=database.reclassify_all(con))
        database.sync_titles(con, translate.load_cache())
        integrity = database.validate(con)
        result = build_outputs(con, period)
        database.dump(con)
        con.close()
        if result["current"] == 0:
            raise RuntimeError(f"no papers found for {period.start}~{period.end}; Crossref may be delayed. Not sending an empty digest.")

        email_state = "disabled (--no-email)"
        if not args.no_email:
            if send_email.smtp_configured():
                email_state = send_email.send_digest(period.run_id, result["email_html"], force=args.force_email)
            else:
                email_state = "skipped: SMTP_USER/SMTP_PASSWORD not configured"
        newsletter_state = "disabled (--no-email)"
        if not args.no_email:
            try:
                newsletter_state = newsletter.send_papers(period.run_id, result["email_html"], force=args.force_email)
            except Exception as error:  # subscribers missing one issue must not fail the run
                newsletter_state = f"failed: {error}"
        status.update({
            "status": "success", "article_count": result["current"], "previous_count": result["previous"],
            "total_papers": result["papers"], "total_runs": result["runs"],
            "fusion_article_count": result["fusion_current"], "all_papers": result["all_papers"], "integrity": integrity,
            "email": email_state, "newsletter": newsletter_state, "recipients": SETTINGS["recipients"], "dashboard_url": SETTINGS.get("dashboard_url", ""),
            "email_path": str(result["email_path"].relative_to(OUTPUT_DIR.parent)),
            "excel_path": str(result["excel_path"].relative_to(OUTPUT_DIR.parent)),
            "finished_at": datetime.now(KST).isoformat(timespec="seconds"),
        })
        write_json(STATUS_PATH, status)
        build_home()
        log("done", **{k: v for k, v in status.items() if k != "recipients"})
    except Exception as error:
        status.update({"status": "failed", "error": f"{type(error).__name__}: {error}", "finished_at": datetime.now(KST).isoformat(timespec="seconds")})
        write_json(STATUS_PATH, status)
        traceback.print_exc()
        log("failed", error=status["error"])
        raise SystemExit(1)


if __name__ == "__main__":
    main()
