"""Offline end-to-end check: fake feeds + fake model output -> day JSON + rendered pages.

python -m unittest tests.test_news_offline -v
"""
import copy
import os
import tempfile
import time
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import feedparser

import io
import json
from contextlib import redirect_stdout

from app.news import brief, build_site, collect, run_daily, session_brief

NOW = datetime(2026, 9, 27, 21, 0, tzinfo=timezone.utc)  # 06:00 KST 9/28


def rss(items):
    source = '<source url="https://x">{}</source>'
    body = "".join(
        f"<item><title>{t}</title><link>{u}</link><pubDate>{d}</pubDate>"
        f"{source.format(s) if s else ''}<description>{desc}</description></item>"
        for t, u, d, s, desc in items
    )
    return feedparser.parse(f'<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>{body}</channel></rss>').entries


def rfc(hours_ago):
    return time.strftime("%a, %d %b %Y %H:%M:%S GMT", (NOW - timedelta(hours=hours_ago)).timetuple())


FEEDS = {
    "gnews-ko": rss([
        ("한수원, i-SMR 표준설계인가 신청 - 가나일보", "https://a.kr/1", rfc(3), "가나일보", "x"),
        ("한수원 i-SMR 표준설계인가 신청했다 - 다라뉴스", "https://b.kr/2", rfc(4), "다라뉴스", "x"),
        ("북핵 위협 고조, 핵무기 대응 논의 - 가나일보", "https://a.kr/3", rfc(2), "가나일보", "x"),
        ("원안위, 고리2호기 계속운전 심의 - 마바신문", "https://c.kr/4", rfc(5), "마바신문", "x"),
        ("부동산 시장 동향 - 가나일보", "https://a.kr/5", rfc(5), "가나일보", "x"),
        ("원전 옛 기사 - 가나일보", "https://a.kr/6", rfc(80), "가나일보", "x"),
    ]),
    "wnn": rss([
        ("NRC accepts SMR construction permit application", "https://wnn.example/1", rfc(6), "", "The regulator docketed the application."),
    ]),
    "nrc": rss([]),
}

FAKE_BRIEF = {
    "overview": "국내에서는 SMR 인허가가, 해외에서는 신형로 인허가가 이어졌다.",
    "stories": [
        {"source_ids": [0, 1, 99], "region": "국내", "category": "SMR·신형로", "importance": 3,
         "headline": "한수원이 i-SMR 표준설계 인가를 신청", "summary": "제목 기준으로 신청이 이뤄졌다.",
         "background": "표준설계인가는 부지와 무관하게 설계 자체의 안전성을 먼저 심사받는 제도다.",
         "why_it_matters": "인허가는 설계가 규제 요건을 만족하는지 확인하는 단계다.",
         "concepts": [{"term": "표준설계인가", "explain": "같은 설계를 여러 부지에 쓰도록 미리 받는 인가"}],
         "question": "모듈 수가 늘면 안전 심사는 무엇이 달라질까?", "study": ["피동안전계통"],
         "reference_ids": ["iaea-smr", "made-up"]},
    ],
}


class OfflinePipeline(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        patches = [
            mock.patch.object(run_daily, "DAYS_DIR", self.tmp / "data/days"),
            mock.patch.object(run_daily, "SEEN_PATH", self.tmp / "state/seen.json"),
            mock.patch.object(run_daily, "LATEST_RUN_PATH", self.tmp / "state/latest-run.json"),
            mock.patch.object(build_site, "DAYS_DIR", self.tmp / "data/days"),
            mock.patch.object(build_site, "SITE_DIR", self.tmp / "docs"),
            mock.patch.object(session_brief, "DAYS_DIR", self.tmp / "data/days"),
            # The home page reads the real data folders; it has its own test below.
            mock.patch.object(run_daily, "build_home", lambda: None),
            mock.patch.object(session_brief, "build_home", lambda: None),
            mock.patch.object(run_daily, "collect", lambda seen: collect.collect(seen, now=NOW, entries_by_feed=FEEDS)),
            mock.patch.object(brief, "call_claude", lambda prompt: (copy.deepcopy(FAKE_BRIEF), {"model": "fake", "input_tokens": 1, "output_tokens": 1})),
            mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test"}),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def test_filter_and_group(self):
        candidates, status = collect.collect({}, now=NOW, entries_by_feed=FEEDS)
        titles = [c["items"][0]["title"] for c in candidates]
        self.assertFalse(any("북핵" in t or "부동산" in t or "옛 기사" in t for t in titles))
        ismr = [c for c in candidates if "i-SMR" in c["items"][0]["title"]]
        self.assertEqual(len(ismr), 1)
        self.assertEqual(len(ismr[0]["items"]), 2)          # two outlets, one story
        self.assertIn("한수원, i-SMR 표준설계인가 신청", [i["title"] for i in ismr[0]["items"]])  # publisher suffix removed
        self.assertTrue(status["wnn"]["ok"])

    def test_end_to_end(self):
        record = run_daily.run(date(2026, 9, 28))
        story = record["stories"][0]
        self.assertNotIn(99, story["source_ids"])            # unknown source id dropped
        self.assertEqual(story["reference_ids"], ["iaea-smr"])  # invented reference dropped
        for cluster in record["sources"]:
            for item in cluster["items"]:
                self.assertNotIn("snippet", item)             # feed text never stored

        # A second day must not repeat the same news.
        record2 = run_daily.run(date(2026, 9, 29))
        self.assertEqual(record2["sources"], [])

        self.assertEqual(build_site.build_site(), 2)
        page = (self.tmp / "docs/days/2026-09-28.html").read_text(encoding="utf-8")
        self.assertIn("한수원이 i-SMR 표준설계 인가를 신청", page)
        self.assertIn('id="day-picker"', page)
        self.assertIn("https://a.kr/1", page)
        self.assertNotIn("The regulator docketed", page)
        index = (self.tmp / "docs/index.html").read_text(encoding="utf-8")
        self.assertIn('max="2026-09-29"', index)
        self.assertTrue((self.tmp / "docs/archive.html").exists())

    def test_rerun_same_day_is_skipped(self):
        first = run_daily.run(date(2026, 9, 28))
        again = run_daily.run(date(2026, 9, 28))
        self.assertEqual(first["generated_at"], again["generated_at"])
        forced = run_daily.run(date(2026, 9, 28), force=True)
        self.assertEqual(len(forced["sources"]), len(first["sources"]))  # same-day seen keys stay eligible

    def test_session_flow_without_api_key(self):
        """Default setup: Actions saves a pending day, the Claude Code session applies the commentary."""
        day = date(2026, 9, 28)
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
            record = run_daily.run(day)
        self.assertEqual(record["engine"]["engine"], "pending")
        build_site.build_site()
        self.assertIn("해설을 준비하고 있습니다", (self.tmp / "docs/index.html").read_text(encoding="utf-8"))

        out = io.StringIO()
        with redirect_stdout(out):
            session_brief.cmd_prompt(day)
        self.assertIn("후보 기사", out.getvalue())
        self.assertIn('"stories"', out.getvalue())

        bad = self.tmp / "bad.json"
        bad.write_text(json.dumps({"overview": "", "stories": [{"region": "국외"}]}), encoding="utf-8")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(session_brief.cmd_apply(day, bad), 1)

        good = self.tmp / "good.json"
        good.write_text(json.dumps(FAKE_BRIEF, ensure_ascii=False), encoding="utf-8")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(session_brief.cmd_apply(day, good), 0)
        saved = json.loads((self.tmp / "data/days/2026-09-28.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["engine"]["engine"], "claude-code-session")
        page = (self.tmp / "docs/index.html").read_text(encoding="utf-8")
        self.assertIn("한수원이 i-SMR 표준설계 인가를 신청", page)
        self.assertIn("기술 배경", page)
        self.assertNotIn("해설을 준비하고 있습니다", page)

        out = io.StringIO()
        with redirect_stdout(out):
            session_brief.cmd_prompt(day)                  # second call: nothing left to do
        self.assertTrue(out.getvalue().startswith("SKIP"))

    def test_session_catches_up_missed_days(self):
        """A session that ran before collection finished leaves a pending day; the next run picks it up."""
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
            record = run_daily.run(date(2026, 9, 28))
        for n in (26, 29):                                 # 9/26 falls outside the 3-day window on 9/30
            path = self.tmp / f"data/days/2026-09-{n}.json"
            path.write_text(json.dumps(dict(record, date=f"2026-09-{n}"), ensure_ascii=False), encoding="utf-8")
        today = date(2026, 9, 30)                          # today's collection has not arrived yet
        self.assertEqual(session_brief.pick_day(today)[0], date(2026, 9, 28))

        out = io.StringIO()
        with redirect_stdout(out):
            session_brief.cmd_prompt(date(2026, 9, 28))
        self.assertTrue(out.getvalue().startswith("DATE: 2026-09-28\n"))

        good = self.tmp / "good.json"
        good.write_text(json.dumps(FAKE_BRIEF, ensure_ascii=False), encoding="utf-8")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(session_brief.cmd_apply(date(2026, 9, 28), good), 0)
        self.assertEqual(session_brief.pick_day(today)[0], date(2026, 9, 29))
        with redirect_stdout(io.StringIO()):
            self.assertEqual(session_brief.cmd_apply(date(2026, 9, 29), good), 0)

        day, skip = session_brief.pick_day(today)
        self.assertIsNone(day)
        self.assertIn("2026-09-30 수집 결과가 아직 없습니다", skip)


if __name__ == "__main__":
    unittest.main()
