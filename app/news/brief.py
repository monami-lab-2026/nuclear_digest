"""Write the daily student briefing from the collected headlines with the Claude API.

Input to the model: headline, publisher, coverage count, and the specialist feeds' one-line lede.
Output: our own Korean explanation (no article text is reproduced). Links come only from the
collected sources and the curated reference library in config — the model never invents URLs.
"""
import json
import os

from .common import SETTINGS, SITE

SYSTEM = """너는 매일 아침 발행되는 개인 학습용 '원자력 뉴스 브리핑'의 해설자다.
독자는 """ + SITE.get("audience", "원자력공학을 공부하는 학생") + """이다.

해야 할 일
1. 후보 기사 목록에서 원자력공학도에게 의미 있는 뉴스를 고른다. 국내와 해외를 모두 다루고,
   같은 사건은 하나로 묶는다. 단순 인사·행사·주가 기사, 핵무기·북핵 등 군사·안보 기사는 뺀다.
2. 고른 뉴스마다 쉬운 한국어로 상황을 정리하고, 공학도 관점의 의미를 설명한다.

정확성 규칙 (가장 중요)
- '무슨 일이 있었나(summary)'에는 후보 목록에 실제로 적힌 사실만 쓴다. 제목과 요지에 없는 수치·날짜·
  기관명·인용을 만들지 않는다. 제목만으로 불분명하면 "제목 기준으로는 ~로 보인다"처럼 불확실성을 밝힌다.
- 배경 설명(background, why_it_matters, concepts)에는 교과서 수준에서 확립된 일반 지식만 쓴다. 최신 수치나
  특정 사업의 세부 사항을 기억에 의존해 단정하지 않는다.
- 추측·전망을 쓸 때는 '가능성', '관전 포인트'처럼 추측임이 드러나게 쓴다.

저작권 규칙
- 기사 문장을 옮겨 적지 않는다. 직접 인용도 하지 않는다. 사실을 네 말로 짧게 다시 쓴다.
- headline 은 기사 제목을 그대로 베끼지 말고 상황을 한 줄로 새로 쓴다.

글쓰기 규칙
- 쉬운 말. 전문용어는 처음 나올 때 괄호로 짧게 풀거나 concepts 에서 설명한다.
- 감탄·과장·홍보 문구를 쓰지 않는다. 문장 가운데 줄표(—)를 쓰지 않는다.
- 분량: summary 는 후보 목록의 사실만으로 2~3문장. 해설은 넉넉히 쓴다.
  background(기술 배경) 3~5문장: 이 뉴스를 이해하는 데 필요한 원리·제도·설비를 교과서 수준으로 설명한다
  (예: 연료 장전 절차, 계속운전 제도, 원자로 피트 구조, SMR 인허가 단계).
  why_it_matters 4~6문장: 공학적 의미, 관련 설계·안전 쟁점, 앞으로 볼 점을 구체적으로 쓴다.
  concepts 는 2~4개.
- 학생이 스스로 생각해 볼 수 있는 질문을 하나씩 붙인다(정답을 암기하는 질문이 아니라 공학적 판단을 요구하는 질문).
- study 에는 이 뉴스를 이해하는 데 필요한 교과 개념이나 검색 키워드를 적는다(예: "붕괴열", "피동 잔열제거계통").
- reference_ids 는 주어진 참고 자료 목록의 id 에서만 고른다. 없으면 빈 배열."""

SCHEMA = {
    "type": "object",
    "properties": {
        "overview": {"type": "string", "description": "오늘 뉴스 흐름을 3~4문장으로 정리"},
        "stories": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source_ids": {"type": "array", "items": {"type": "integer"}},
                    "region": {"type": "string", "enum": ["국내", "해외"]},
                    "category": {"type": "string", "enum": SETTINGS["categories"]},
                    "importance": {"type": "integer", "enum": [1, 2, 3]},
                    "headline": {"type": "string"},
                    "summary": {"type": "string"},
                    "background": {"type": "string"},
                    "why_it_matters": {"type": "string"},
                    "concepts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"term": {"type": "string"}, "explain": {"type": "string"}},
                            "required": ["term", "explain"],
                            "additionalProperties": False,
                        },
                    },
                    "question": {"type": "string"},
                    "study": {"type": "array", "items": {"type": "string"}},
                    "reference_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["source_ids", "region", "category", "importance", "headline", "summary",
                             "background", "why_it_matters", "concepts", "question", "study", "reference_ids"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["overview", "stories"],
    "additionalProperties": False,
}


def candidate_lines(candidates):
    lines = []
    for c in candidates:
        lead = c["items"][0]
        publishers = ", ".join(dict.fromkeys(i["publisher"] for i in c["items"]))[:120]
        line = f"[{c['id']}] ({c['region']}) {lead['title']} | 매체: {publishers} ({len(c['items'])}곳 보도)"
        snippet = next((i["snippet"] for i in c["items"] if i.get("snippet")), "")
        if snippet:
            line += f" | 요지: {snippet}"
        lines.append(line)
    return "\n".join(lines)


def interest_line():
    """Readers' interest areas: a tie-breaker when choosing stories, never a reason to drop major news."""
    names = list(SETTINGS.get("interests", {}))
    if not names:
        return ""
    return (f"독자의 관심 분야: {', '.join(names)}. 비슷하게 중요한 뉴스라면 이 분야와 관련된 것을 우선 고르고, "
            "관련이 있으면 why_it_matters 에서 그 연결을 짚어 준다. 다만 큰 뉴스를 관심 분야 밖이라고 빼지는 않는다.\n\n")


def build_prompt(candidates, day_label):
    library = "\n".join(f"- {r['id']}: {r['name']} ({r['about']})" for r in SETTINGS["reference_library"])
    return (
        f"오늘은 {day_label}이다. 아래는 지난 하루 동안 수집한 원자력 관련 기사 후보다.\n"
        f"{SETTINGS['min_stories']}~{SETTINGS['max_stories']}개 뉴스를 골라 중요한 순서로 브리핑을 작성하라. "
        "importance 는 3이 가장 중요하다. source_ids 에는 같은 사건을 다룬 후보 번호를 모두 넣는다.\n\n"
        f"{interest_line()}"
        f"참고 자료 목록(reference_ids 에 쓸 수 있는 id):\n{library}\n\n"
        f"후보 기사:\n{candidate_lines(candidates)}"
    )


def call_claude(prompt):
    import anthropic

    client = anthropic.Anthropic()
    request = dict(
        model=os.environ.get("NEWS_MODEL", SETTINGS["model"]),
        max_tokens=16000,
        system=SYSTEM,
        thinking={"type": "adaptive"},
        output_config={"effort": SETTINGS["effort"], "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": prompt}],
    )
    try:
        # Server-side fallback: if the primary model declines, the API reruns on the recommended model.
        response = client.beta.messages.create(
            **request, betas=["server-side-fallback-2026-07-01"], fallbacks="default"
        )
    except anthropic.BadRequestError as error:
        print(json.dumps({"warning": f"fallback request rejected, retrying without it: {error}"}, ensure_ascii=False))
        response = client.messages.create(**request)

    if response.stop_reason == "refusal":
        raise RuntimeError("Claude declined the briefing request")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("briefing output hit max_tokens")
    text = next(block.text for block in response.content if block.type == "text")
    usage = response.usage
    return json.loads(text), {
        "model": response.model,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
    }


def validate(brief, candidates):
    """Drop anything that does not point back to a collected source or a known reference."""
    valid_ids = {c["id"] for c in candidates}
    library = {r["id"] for r in SETTINGS["reference_library"]}
    stories, used = [], set()
    for story in brief.get("stories", []):
        ids = [i for i in dict.fromkeys(story.get("source_ids", [])) if i in valid_ids and i not in used]
        if not ids:
            continue
        used.update(ids)
        story["source_ids"] = ids
        story["reference_ids"] = [r for r in story.get("reference_ids", []) if r in library]
        story["concepts"] = story.get("concepts", [])[:4]
        story["study"] = story.get("study", [])[:4]
        stories.append(story)
    stories.sort(key=lambda s: -s.get("importance", 1))
    return {"overview": brief.get("overview", "").strip(), "stories": stories[: SETTINGS["max_stories"]]}


def write_brief(candidates, day_label):
    """Return (brief, meta).

    Default setup has no API key: the day is saved as 'pending' and the daily Claude Code session
    (pipeline/session_brief.py) writes the commentary. With ANTHROPIC_API_KEY set, it is written here.
    """
    empty = {"overview": "", "stories": []}
    if not candidates:
        return empty, {"engine": "none", "reason": "no candidates"}
    mode = SITE.get("news_commentary", "session")
    if mode == "none":
        return empty, {"engine": "none", "reason": "commentary turned off (config/site.json news_commentary)"}
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return empty, {"engine": "pending", "reason": "waiting for the Claude Code session"}
    try:
        raw, usage = call_claude(build_prompt(candidates, day_label))
    except Exception as error:
        print(json.dumps({"warning": f"briefing failed: {error}"}, ensure_ascii=False))
        return empty, {"engine": "failed", "reason": f"model call failed: {str(error)[:200]}"}
    return validate(raw, candidates), {"engine": "claude", **usage}
