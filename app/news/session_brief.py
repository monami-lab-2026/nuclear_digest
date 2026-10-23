"""Commentary step run by the daily Claude Code session (no API key needed).

    python3 -m app.news.session_brief prompt            # prints the task, or a SKIP line
    python3 -m app.news.session_brief apply brief.json  # validates, saves, re-renders docs/

Without --date both commands work on the oldest day in the last `backfill_days` days that still waits
for commentary, so a run that found nothing (collection came in late) is caught up by the next run.

Standard library only, so the session does not need to install anything.
"""
import argparse
import json
import sys
from datetime import date, timedelta

from ..build_home import build_home
from .brief import SYSTEM, build_prompt, validate
from .build_site import build_site
from .common import DAYS_DIR, SETTINGS, date_label, now_utc, read_json, today_kst, write_json

FORMAT = """출력: 아래 형식의 JSON 하나만 파일로 저장한다(설명 문장 없이).
{{"overview": "오늘 흐름 2~3문장",
 "stories": [{{"source_ids": [후보 번호...], "region": "국내|해외", "category": "{categories}",
   "importance": 1~3, "headline": "새로 쓴 한 줄 제목", "summary": "무슨 일이 있었나 2~3문장(후보 목록의 사실만)",
   "background": "기술 배경 3~5문장", "why_it_matters": "공학도에게 왜 중요한가 4~6문장",
   "concepts": [{{"term": "", "explain": ""}}, ... 2~4개],
   "question": "생각해 볼 질문", "study": ["교과 개념·검색어"], "reference_ids": ["참고 자료 id"]}}]}}"""


def pending_day(day):
    record = read_json(DAYS_DIR / f"{day.isoformat()}.json")
    if not record:
        return None, f"SKIP: {day} 수집 결과가 아직 없습니다(수집 워크플로가 늦었거나 실패)."
    if record.get("engine", {}).get("engine") != "pending":
        return None, f"SKIP: {day} 은(는) 해설할 필요가 없습니다(engine={record.get('engine', {}).get('engine')})."
    if not record.get("sources"):
        return None, f"SKIP: {day} 수집된 기사가 없습니다."
    return record, ""


def pick_day(today):
    """Oldest day in the backfill window that still needs commentary; else (None, SKIP line)."""
    days = SETTINGS.get("backfill_days", 3)
    for back in range(days - 1, -1, -1):
        day = today - timedelta(days=back)
        if pending_day(day)[0]:
            return day, ""
    first = today - timedelta(days=days - 1)
    if not read_json(DAYS_DIR / f"{today.isoformat()}.json"):
        return None, (f"SKIP: {today} 수집 결과가 아직 없습니다(수집 워크플로가 늦었거나 실패). "
                      f"{first}~{today} 중 밀린 해설도 없습니다.")
    return None, f"SKIP: {first}~{today} 중 해설할 날이 없습니다."


def check(brief):
    """Hard errors the session must fix before the brief is accepted."""
    errors = []
    if not isinstance(brief, dict) or not isinstance(brief.get("stories"), list) or not brief["stories"]:
        return ["stories 배열이 비어 있거나 없습니다."]
    text_fields = ("headline", "summary", "background", "why_it_matters", "question")
    for n, story in enumerate(brief["stories"]):
        if story.get("region") not in ("국내", "해외"):
            errors.append(f"stories[{n}].region 은 국내/해외 중 하나")
        if story.get("category") not in SETTINGS["categories"]:
            errors.append(f"stories[{n}].category 는 {SETTINGS['categories']} 중 하나")
        if story.get("importance") not in (1, 2, 3):
            errors.append(f"stories[{n}].importance 는 1~3")
        if not isinstance(story.get("source_ids"), list) or not story["source_ids"]:
            errors.append(f"stories[{n}].source_ids 가 비었습니다")
        errors += [f"stories[{n}].{f} 가 비었습니다" for f in text_fields if not str(story.get(f, "")).strip()]
        story.setdefault("concepts", [])
        story.setdefault("study", [])
        story.setdefault("reference_ids", [])
    return errors


def cmd_prompt(day):
    record, skip = pending_day(day)
    if not record:
        print(skip)
        return 0
    print(f"DATE: {day.isoformat()}")
    print(SYSTEM)
    print()
    print(build_prompt(record["sources"], date_label(day)))
    print()
    print(FORMAT.format(categories="|".join(SETTINGS["categories"])))
    return 0


def cmd_apply(day, path):
    record, skip = pending_day(day)
    if not record:
        print(skip)
        return 0
    try:
        brief = json.loads(open(path, encoding="utf-8").read())
    except (OSError, json.JSONDecodeError) as error:
        print(f"ERROR: JSON을 읽지 못했습니다: {error}")
        return 1
    errors = check(brief)
    if errors:
        print("ERROR:\n" + "\n".join(errors))
        return 1
    result = validate(brief, record["sources"])
    if not result["stories"]:
        print("ERROR: source_ids 가 후보 번호와 맞는 뉴스가 하나도 없습니다.")
        return 1
    record.update(overview=result["overview"], stories=result["stories"],
                  engine={"engine": "claude-code-session", "briefed_at": now_utc().isoformat(timespec="seconds")})
    write_json(DAYS_DIR / f"{day.isoformat()}.json", record)
    build_site()
    build_home()
    print(f"OK: {day} 해설 {len(result['stories'])}건 반영, docs/ 갱신 완료")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["prompt", "apply"])
    parser.add_argument("file", nargs="?")
    parser.add_argument("--date", help="YYYY-MM-DD (default: oldest pending day in the last backfill_days)")
    args = parser.parse_args()
    if args.date:
        day = date.fromisoformat(args.date)
    else:
        day, skip = pick_day(today_kst())
        if not day:
            print(skip)
            sys.exit(0)
    if args.command == "prompt":
        sys.exit(cmd_prompt(day))
    if not args.file:
        parser.error("apply 에는 JSON 파일 경로가 필요합니다")
    sys.exit(cmd_apply(day, args.file))


if __name__ == "__main__":
    main()
