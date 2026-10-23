"""Paths and settings shared by the news and paper sections.

config/site.json   personal settings (title, site address, email, interests)
config/news.json   news section details (feeds, keywords, categories, reference links)
config/papers.json paper section details (journals, topics, glossary)
"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
DOCS_DIR = ROOT / "docs"


def _load(name):
    data = json.loads((CONFIG_DIR / name).read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


SITE = _load("site.json")
# Repository variables override the committed defaults without code changes.
if os.environ.get("SITE_URL"):
    SITE["site_url"] = os.environ["SITE_URL"].strip()
if not SITE["site_url"].endswith("/"):
    SITE["site_url"] += "/"


def section_url(section):
    return f"{SITE['site_url']}{section}/"
