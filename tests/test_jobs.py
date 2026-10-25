"""Offline tests for the 원자력 취업 section (no network, no API key)."""
import json
import os
import unittest
from datetime import date
from unittest import mock

from app.jobs import collect


def item(sn, inst, title, start="20261020", end="20261030", hire="정규직"):
    return {"recrutPblntSn": sn, "instNm": inst, "recrutPbancTtl": title, "pbancBgngYmd": start,
            "pbancEndYmd": end, "hireTypeNmLst": hire, "recrutSeNm": "신입", "workRgnNmLst": "경북,부산",
            "srcUrl": "https://example.org/notice"}


class JobsTest(unittest.TestCase):
    def test_group_and_filter(self):
        self.assertEqual(collect.group_for(item(1, "한국수력원자력(주)", "2026년 하반기 대졸 신입사원 채용")), "원전 운영·설계·정비")
        self.assertEqual(collect.group_for(item(2, "한국원자력연구원", "연구직 채용")), "연구·안전·규제")
        self.assertEqual(collect.group_for(item(3, "국립암센터", "방사선 치료 연구원 채용")), collect.OTHER_GROUP)
        self.assertIsNone(collect.group_for(item(4, "한국도로공사", "행정직 채용")))
        # 한국전력공사 must not swallow 한국전력기술
        self.assertEqual(collect.group_for(item(5, "한국전력기술(주)", "기계 경력직")), "원전 운영·설계·정비")

    def test_collect_merge_and_close(self):
        pages = [([item(1, "한국수력원자력(주)", "신입 채용"), item(4, "한국도로공사", "행정직")], 150),
                 ([item(2, "한전KPS(주)", "청년인턴", hire="청년인턴(체험형),비정규직")], 150)]
        found, scanned = collect.collect_alio("k", pages=pages)
        self.assertEqual(scanned, 3)
        self.assertEqual([r["id"] for r in found], ["1", "2"])
        self.assertEqual(found[1]["hire"], ["청년인턴(체험형)", "비정규직"])
        self.assertTrue(found[0]["url"].endswith("idx=1"))
        today = date(2026, 10, 25)
        history = collect.merge({}, found, today, open_ids={"1", "2"})
        self.assertTrue(all(r["open"] for r in history.values()))
        history = collect.merge(history, found[:1], date(2026, 10, 26), open_ids={"1"})
        self.assertFalse(history["2"]["open"])
        self.assertEqual(history["1"]["first_seen"], "2026-10-25")

    def test_api_errors_hide_key(self):
        with self.assertRaises(RuntimeError):
            collect.parse_page(b"<OpenAPI_ServiceResponse><returnAuthMsg>SERVICE_KEY_IS_NOT_REGISTERED_ERROR</returnAuthMsg>")
        with self.assertRaises(RuntimeError):
            collect.parse_page(json.dumps({"resultCode": 401, "resultMsg": "bad"}).encode())
        msg = collect.scrub("GET https://apis.data.go.kr/x?serviceKey=abc%2B1&pageNo=1 failed abc+1", "abc+1")
        self.assertNotIn("abc", msg)

    def test_no_key(self):
        with mock.patch.dict(os.environ, {"DATA_GO_KR_KEY": ""}):
            with self.assertRaises(collect.NoKey):
                collect.service_key()
        with mock.patch.dict(os.environ, {"DATA_GO_KR_KEY": "a%2Bb%3D"}):
            self.assertEqual(collect.service_key(), "a+b=")

    def test_news_filter(self):
        entries = {"jobs-ko": [
            {"title": "한수원, 하반기 신입사원 500명 채용 - 연합뉴스", "link": "https://n/1", "source": {"title": "연합뉴스"}},
            {"title": "원전 수출 협상 진전 - 뉴시스", "link": "https://n/2", "source": {"title": "뉴시스"}},
        ], "jobs-en": [
            {"title": "US nuclear industry faces workforce shortage - Reuters", "link": "https://n/3", "source": {"title": "Reuters"}},
        ]}
        items, status = collect.collect_news(date(2026, 10, 25), entries_by_feed=entries)
        self.assertEqual([i["url"] for i in items], ["https://n/1", "https://n/3"])
        self.assertEqual(items[0]["title"], "한수원, 하반기 신입사원 500명 채용")


if __name__ == "__main__":
    unittest.main()
