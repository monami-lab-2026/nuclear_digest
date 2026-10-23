"""Korean title translation with a DOI-keyed cache.

Engine order: cache -> Claude API (if ANTHROPIC_API_KEY is set) -> MyMemory (free) + term post-correction.
A failed translation never stops the pipeline; the English title is shown instead.
"""
import json
import os
import time

import requests

from .common import SETTINGS, TRANSLATIONS_PATH, read_json, write_json

CLAUDE_MODEL = os.environ.get("TRANSLATION_MODEL", "claude-opus-5")
BATCH = 40


def load_cache():
    cache = read_json(TRANSLATIONS_PATH, {}) or {}
    cache = {doi: (v if isinstance(v, dict) else {"ko": v, "engine": "mymemory"}) for doi, v in cache.items()}
    # Re-apply the correction table so newly added rules also fix earlier machine translations.
    for entry in cache.values():
        if entry["engine"] == "mymemory":
            entry["ko"] = postfix(entry["ko"])
    return cache


def claude_translate(titles):
    import anthropic

    client = anthropic.Anthropic()
    glossary = "\n".join(f"- {en} → {ko}" for en, ko in SETTINGS["translation_glossary"].items())
    numbered = "\n".join(f"{i}. {t}" for i, t in enumerate(titles))
    prompt = (
        "다음은 원자력공학 학술지 논문 제목이다. 각 제목을 한국 원자력공학계에서 통용되는 전문용어로 자연스럽게 번역하라.\n"
        "- 약어(CFD, LOCA, SMR, PIV 등), 코드명(MARS-KS, RELAP5, MCNP 등), 화학식, 고유명사는 원문 유지\n"
        "- 직역투를 피하고 학술 논문 제목 문체(명사형 종결)로 작성\n"
        f"- 용어집:\n{glossary}\n\n"
        f"제목 목록(번호. 제목):\n{numbered}"
    )
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=16000,
        output_config={
            "effort": "low",
            "format": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "translations": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {"index": {"type": "integer"}, "ko": {"type": "string"}},
                                "required": ["index", "ko"],
                                "additionalProperties": False,
                            },
                        }
                    },
                    "required": ["translations"],
                    "additionalProperties": False,
                },
            },
        },
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason != "end_turn":
        raise RuntimeError(f"Claude translation stopped: {response.stop_reason}")
    text = next(block.text for block in response.content if block.type == "text")
    result = {item["index"]: item["ko"].strip() for item in json.loads(text)["translations"]}
    return [result.get(i, "") for i in range(len(titles))]


def mymemory_translate(title):
    response = requests.get(
        "https://api.mymemory.translated.net/get",
        params={"q": title, "langpair": "en|ko", "de": SETTINGS["contact_email"]},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if str(payload.get("responseStatus")) != "200":
        raise RuntimeError(payload.get("responseDetails", "MyMemory error"))
    return postfix((payload.get("responseData", {}).get("translatedText") or "").strip())


def postfix(text):
    """Correct recurring machine-translation term errors (config: translation_postfix)."""
    for wrong, right in SETTINGS.get("translation_postfix", {}).items():
        text = text.replace(wrong, right)
    return " ".join(text.split())


def translate_records(records, retranslate_engines=()):
    """Fill record['title_ko'] for every record; returns stats."""
    cache = load_cache()
    todo = [r for r in records if r["doi"] not in cache or cache[r["doi"]]["engine"] in retranslate_engines]
    stats = {"cached": len(records) - len(todo), "claude": 0, "mymemory": 0, "failed": 0}

    if todo and os.environ.get("ANTHROPIC_API_KEY"):
        for i in range(0, len(todo), BATCH):
            chunk = todo[i:i + BATCH]
            try:
                translated = claude_translate([r["title"] for r in chunk])
            except Exception as error:  # fall through to MyMemory for this chunk
                print(json.dumps({"warning": f"Claude translation failed: {error}"}, ensure_ascii=False))
                continue
            for record, ko in zip(chunk, translated):
                if ko:
                    cache[record["doi"]] = {"ko": ko, "engine": "claude"}
                    stats["claude"] += 1
        todo = [r for r in todo if cache.get(r["doi"], {}).get("engine") != "claude"]

    for record in todo:
        if record["doi"] in cache:  # keep the older translation rather than downgrading to English
            continue
        try:
            ko = mymemory_translate(record["title"])
            cache[record["doi"]] = {"ko": ko or record["title"], "engine": "mymemory"}
            stats["mymemory"] += 1
            time.sleep(0.3)
        except Exception:
            stats["failed"] += 1

    write_json(TRANSLATIONS_PATH, dict(sorted(cache.items())))
    for record in records:
        record["title_ko"] = cache.get(record["doi"], {}).get("ko") or record["title"]
    return stats
