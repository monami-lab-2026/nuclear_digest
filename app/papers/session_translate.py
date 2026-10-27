"""Title-translation step run by the Claude session (no API key needed).

    python -m app.papers.session_translate prompt [--limit 80]   # prints the task, or a SKIP line
    python -m app.papers.session_translate apply titles.json     # validates, saves, rebuilds paper pages + home

Only the latest weekly window (state/papers/latest-run.json) is handled, like the weekly digest page:
titles there that only have a free machine translation (engine "mymemory") are replaced with a session
translation (engine "claude-session"). Older weeks are left as they are. The weekly Actions pipeline keeps these
because it only re-translates titles missing from the cache.
"""
import argparse
import json
import re
import sys
from datetime import date

from ..build_home import build_home
from . import database, translate
from .common import SETTINGS, STATE_DIR, TRANSLATIONS_PATH, Period, read_json, write_json

ENGINE = "claude-session"
HANGUL = re.compile(r"[가-힣]")

RULES = """너는 원자력공학 학술지 논문 제목을 한국어로 옮기는 번역자다.
- 한국 원자력공학계에서 통용되는 전문용어로 자연스럽게 번역한다. 직역투를 피하고 논문 제목 문체(명사형 종결)로 쓴다.
- 약어(CFD, LOCA, SMR, PIV 등), 코드명(MARS-KS, RELAP5, MCNP 등), 화학식, 고유명사(기관·장치·프로그램 이름)는 원문 그대로 둔다.
- 원문에 없는 내용을 더하거나 빼지 않는다. 문장 가운데 줄표(—)를 쓰지 않는다.
- '기존 기계번역'은 참고만 한다. 틀린 용어가 많으니 그대로 따르지 않는다.
- 아래 용어집을 따른다."""

FORMAT = """출력: 아래 형식의 JSON 하나만 파일로 저장한다(설명 문장 없이). 목록의 모든 doi 를 빠짐없이 넣는다.
{"translations": [{"doi": "목록의 doi", "ko": "한국어 제목"}, ...]}"""


def current_period():
    status = read_json(STATE_DIR / "latest-run.json", {}) or {}
    run_date = status.get("run_date")
    return Period(date.fromisoformat(run_date)) if run_date else Period.for_date(date.today())


def pending(limit):
    cache = translate.load_cache()
    period = current_period()
    con = database.connect()
    rows = database.papers_between(con, period.start, period.end)
    con.close()
    todo = [(r["doi"], r["title_en"], cache[r["doi"]]["ko"]) for r in rows
            if r["doi"] in cache and cache[r["doi"]]["engine"] == "mymemory"]
    return todo[:limit], len(todo)


def cmd_prompt(limit):
    todo, total = pending(limit)
    if not todo:
        print(f"SKIP: 이번 주({current_period().start}~{current_period().end}) 논문 중 다시 번역할 제목이 없습니다.")
        return 0
    glossary = "\n".join(f"- {en} → {ko}" for en, ko in SETTINGS["translation_glossary"].items())
    period = current_period()
    print(f"PENDING: 이번 주({period.start}~{period.end}) 논문 {len(todo)}건 (남은 {total}건)")
    print(RULES)
    print(glossary)
    print()
    print("번역할 제목:")
    for doi, en, ko in todo:
        print(json.dumps({"doi": doi, "title": en, "기존 기계번역": ko}, ensure_ascii=False))
    print()
    print(FORMAT)
    return 0


def rebuild():
    from .run_weekly import build_outputs  # heavy imports only when needed
    period = current_period()
    con = database.connect()
    database.sync_titles(con, translate.load_cache())
    build_outputs(con, period)
    database.dump(con)
    con.close()
    build_home()


def cmd_apply(path, limit):
    try:
        payload = json.loads(open(path, encoding="utf-8").read())
        items = payload["translations"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"ERROR: JSON을 읽지 못했습니다: {error}")
        return 1
    cache = translate.load_cache()
    allowed = {doi for doi, _, _ in pending(10**6)[0]}
    errors, accepted = [], {}
    for i, item in enumerate(items):
        doi, ko = (item or {}).get("doi", ""), " ".join(str((item or {}).get("ko", "")).split())
        if doi not in allowed:
            errors.append(f"{i}: 다시 번역할 목록에 없는 doi: {doi}")
        elif not ko or not HANGUL.search(ko):
            errors.append(f"{i}: 한국어 제목이 비었거나 한글이 없음: {doi}")
        elif "—" in ko:
            errors.append(f"{i}: 줄표(—) 사용: {doi}")
        else:
            accepted[doi] = ko
    if errors:
        print("ERROR:\n" + "\n".join(errors))
        return 1
    if not accepted:
        print("ERROR: 반영할 번역이 없습니다.")
        return 1
    raw = read_json(TRANSLATIONS_PATH, {}) or {}
    for doi, ko in accepted.items():
        raw[doi] = {"ko": ko, "engine": ENGINE}
    write_json(TRANSLATIONS_PATH, dict(sorted(raw.items())))
    rebuild()
    _, left = pending(limit)
    print(f"OK: 논문 제목 {len(accepted)}건 반영, 논문 페이지·홈 갱신 완료 (이번 주 남은 기계번역 {left}건)")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["prompt", "apply"])
    parser.add_argument("path", nargs="?")
    parser.add_argument("--limit", type=int, default=80)
    args = parser.parse_args(argv)
    if args.command == "prompt":
        return cmd_prompt(args.limit)
    if not args.path:
        print("ERROR: apply 에는 JSON 파일 경로가 필요합니다.")
        return 1
    return cmd_apply(args.path, args.limit)


if __name__ == "__main__":
    sys.exit(main())
