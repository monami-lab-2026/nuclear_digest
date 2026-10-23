"""Checks for the merged app: shared settings, menu links, home page, commentary modes.

python -m unittest tests.test_app -v
"""
import os
import re
import unittest
from pathlib import Path
from unittest import mock

from app import build_home, build_subscribe, config, newsletter, site_theme
from app.news import brief
from app.papers import common as papers_common


class MergedApp(unittest.TestCase):
    def test_interests_feed_both_sections(self):
        self.assertEqual(list(papers_common.SETTINGS["watchlists"]), list(config.SITE["interests"]))
        prompt = brief.build_prompt([], "2026년 10월 22일 (목)")
        for name in config.SITE["interests"]:
            self.assertIn(name, prompt)

    def test_menu_links_resolve_from_every_depth(self):
        docs = config.DOCS_DIR
        for page, root in [(docs / "index.html", "./"), (docs / "news/index.html", "../"),
                           (docs / "news/days/x.html", "../../"), (docs / "papers/archive/x.html", "../../")]:
            html = site_theme.site_header("home", root) + site_theme.site_footer("news", root)
            for href in re.findall(r'href="([^"]+\.html)"', html):
                target = (page.parent / href).resolve()
                self.assertTrue(target.exists(), f"{page}: {href}")

    def test_commentary_off(self):
        with mock.patch.dict(brief.SITE, {"news_commentary": "none"}):
            result, engine = brief.write_brief([{"id": 0}], "x")
        self.assertEqual(engine["engine"], "none")
        self.assertEqual(result["stories"], [])

    def test_home_page_builds(self):
        path = build_home.build_home()
        html = Path(path).read_text(encoding="utf-8")
        self.assertIn(config.SITE["title"], html)
        self.assertIn('href="news/index.html"', html)
        self.assertIn('href="papers/index.html"', html)


    def test_subscribe_page_pending_until_configured(self):
        with mock.patch.dict(config.SITE, {"newsletter": {"enabled": True, "username": ""}}):
            html = Path(build_subscribe.build_subscribe()).read_text(encoding="utf-8")
        self.assertIn("준비하고 있습니다", html)
        self.assertIn('<button type="submit" disabled>', html)

    def test_subscribe_form_with_lists(self):
        with mock.patch.dict(config.SITE, {"newsletter": {"enabled": True, "username": "tester", "choose_lists": True}}):
            html = build_subscribe.form_html()
        self.assertIn("https://buttondown.com/api/emails/embed-subscribe/tester", html)
        self.assertIn('name="tag" value="news"', html)
        self.assertIn('name="tag" value="papers"', html)
        self.assertIn('name="embed" value="1"', html)

    def test_newsletter_payload_filters_by_tag_only_when_choosing(self):
        with mock.patch.dict(config.SITE, {"newsletter": {"username": "t", "choose_lists": True}}):
            data = newsletter.payload("news", "s", "<p>x</p>")
        self.assertEqual(data["filters"]["filters"][0], {"field": "subscriber.tags", "operator": "contains", "value": "news"})
        self.assertTrue(data["body"].startswith("<!-- buttondown-editor-mode: fancy -->"))
        self.assertEqual(data["status"], "about_to_send")
        with mock.patch.dict(config.SITE, {"newsletter": {"username": "t", "choose_lists": False}}):
            self.assertNotIn("filters", newsletter.payload("news", "s", "x"))

    def test_news_issue_skips_when_unconfigured_and_dry_runs(self):
        with mock.patch.dict(config.SITE, {"newsletter": {"enabled": True, "username": ""}}):
            self.assertTrue(newsletter.send_news("2026-10-22").startswith("skipped"))
        with mock.patch.dict(config.SITE, {"newsletter": {"enabled": True, "username": "t"}}):
            result = newsletter.send_news("2026-10-22", dry_run=True)
        self.assertTrue(result.startswith("dry-run"), result)
        record = newsletter.latest_news_day("2026-10-22")
        html = newsletter.news_html(record)
        self.assertIn(record["stories"][0]["headline"].replace("&", "&amp;"), html)
        self.assertIn("news/days/2026-10-22.html", html)


    def test_newsletter_off_hides_button_and_page(self):
        with mock.patch.dict(config.SITE, {"newsletter": {"enabled": False, "username": "t"}}):
            self.assertNotIn("subscribe.html", site_theme.site_header("home", "./"))
            html = Path(build_subscribe.build_subscribe()).read_text(encoding="utf-8")
            self.assertIn('http-equiv="refresh"', html)
            self.assertTrue(newsletter.send_news("2026-10-22").startswith("skipped: newsletter turned off"))
        with mock.patch.dict(config.SITE, {"newsletter": {"enabled": True, "username": ""}}):
            self.assertIn("subscribe.html", site_theme.site_header("home", "./"))


    def test_keyword_matching_is_word_aware(self):
        from app.papers.common import term_hit, topics_for
        self.assertFalse(term_hit("neutron diffusion calculation", "fusion"))
        self.assertTrue(term_hit("fusion blanket", "fusion"))
        self.assertFalse(term_hit("local power distribution", "loca"))
        self.assertTrue(term_hit("large break locas", "loca"))
        self.assertFalse(term_hit("an automated workflow", "flow"))
        self.assertTrue(term_hit("heating of the rod", "heat"))
        self.assertTrue(term_hit("neutronics model", "neutron"))
        # "thermal" in "thermal neutron" is reactor physics, not thermal-hydraulics
        title = ("Hybrid adaptive RSM-GA Monte Carlo optimization method (HRG-MCO) and its application in the design of "
                 "moderator-collimator systems for accelerator-based thermal neutron radiography")
        self.assertNotIn("열수력·유체", topics_for({"title": title}))
        self.assertIn("원자로물리·해석", topics_for({"title": title}))
        self.assertIn("열수력·유체", topics_for({"title": "Thermal stratification in a pool"}))


    def test_trend_sphere_uses_curated_keywords(self):
        import math
        from app.papers import wordcloud as wc
        from app.papers.common import SETTINGS, matches_any
        trends, english = wc.split_config(SETTINGS["trend_keywords"])
        self.assertEqual(english["소형모듈원자로"], "SMR")
        records = [{"title": t, "primary_area": "열수력·유체"} for t in [
            "Thermal-hydraulic design of a small modular reactor", "Digital twin for autonomous operation of an SMR",
            "Molten salt reactor multiphysics coupling", "Neutron transport in a pressurized water reactor",
            "Machine learning surrogate for CHF prediction"]]
        wc.tag_trends(records, trends, lambda r: r["title"].lower(), matches_any)
        self.assertEqual(records[0]["trends"], ["소형모듈원자로"])
        self.assertEqual(set(records[1]["trends"]), {"소형모듈원자로", "디지털트윈", "자율운전"})
        self.assertEqual(set(records[2]["trends"]), {"용융염원자로", "다중물리"})
        self.assertEqual(records[3]["trends"], [])                 # generic words give no trend keyword
        self.assertEqual(set(records[4]["trends"]), {"인공지능", "대리모델"})
        size, words = wc.layout([("소형모듈원자로", 2), ("디지털트윈", 1), ("용융염원자로", 1), ("인공지능", 1)])
        self.assertEqual(len(words), 4)
        for term, _, font, x, y, vertical in words:
            w, h = wc._text_width(term, font), font
            bw, bh = (h, w) if vertical else (w, h)
            self.assertLessEqual(math.hypot(x + bw / 2 - size / 2, y + bh / 2 - size / 2), size / 2)
        html = wc.render(records, {"열수력·유체": "var(--s2)"}, english)
        self.assertIn('data-trend="소형모듈원자로"', html)
        self.assertIn(">SMR</text>", html)                       # English sphere
        self.assertIn(">소형모듈원자로</text>", html)              # Korean sphere
        self.assertIn('data-wc-lang="en"', html)
        self.assertNotIn("neutron", html.lower())

    def test_home_screen_app_files(self):
        import json
        from app import build_app
        manifest = json.loads(Path(build_app.build_app()).read_text(encoding="utf-8"))
        self.assertEqual(manifest["display"], "standalone")
        self.assertEqual(manifest["start_url"], "./index.html")
        for icon in manifest["icons"]:
            self.assertTrue((config.DOCS_DIR / icon["src"]).exists(), icon["src"])
        self.assertTrue((config.DOCS_DIR / "sw.js").exists())
        self.assertIn('href="../../manifest.webmanifest"', site_theme.head("t", "d", "", "../../"))


    def test_install_page(self):
        from app import build_install
        html = Path(build_install.build_install()).read_text(encoding="utf-8")
        for text in ("앱 설치하기", "홈 화면에 추가", "beforeinstallprompt", "icons/icon-192.png"):
            self.assertIn(text, html)
        self.assertIn('href="../../install.html"', site_theme.site_header("news", "../../"))


if __name__ == "__main__":
    unittest.main()
