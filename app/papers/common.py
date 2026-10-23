"""Shared paths, settings, and classification rules for the weekly pipeline."""
import json
import os
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from ..config import DOCS_DIR, ROOT, SITE, _load, section_url

DATA_DIR = ROOT / "data" / "papers"
RAW_DIR = DATA_DIR / "raw"
DB_PATH = DATA_DIR / "literature.sqlite"
DUMP_PATH = DATA_DIR / "literature.sql"  # text form kept in git; the .sqlite is rebuilt from it
TRANSLATIONS_PATH = DATA_DIR / "translations_ko.json"
STATE_DIR = ROOT / "state" / "papers"
OUTPUT_DIR = ROOT / "outputs" / "papers"
SITE_DIR = DOCS_DIR / "papers"

USER_AGENT = "NuclearDailyDigest/1.0 (mailto:{contact})"


def load_settings():
    settings = _load("papers.json")
    settings.update(recipients=SITE["email"]["recipients"], email_subject=SITE["email"]["subject"],
                    dashboard_url=section_url("papers"), contact_email=SITE["contact_email"],
                    watchlists=SITE.get("interests", {}))
    # Repository variables override the committed defaults without code changes.
    if os.environ.get("DASHBOARD_URL"):
        settings["dashboard_url"] = os.environ["DASHBOARD_URL"].strip()
    if os.environ.get("DIGEST_RECIPIENTS"):
        settings["recipients"] = [v.strip() for v in os.environ["DIGEST_RECIPIENTS"].split(",") if v.strip()]
    return settings


SETTINGS = load_settings()
HEADERS = {"User-Agent": USER_AGENT.format(contact=SETTINGS["contact_email"])}


@dataclass(frozen=True)
class Period:
    """A weekly window: run on Monday, collect the previous Monday..Sunday."""

    run_date: date

    @classmethod
    def for_date(cls, value: date):
        return cls(value - timedelta(days=value.weekday()))

    @property
    def start(self):
        return self.run_date - timedelta(days=7)

    @property
    def end(self):
        return self.run_date - timedelta(days=1)

    @property
    def previous(self):
        return Period(self.run_date - timedelta(days=7))

    @property
    def run_id(self):
        return self.run_date.isoformat()


def strip_markup(value):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value or "")).strip()


def paper_text(record):
    title = record.get("title") or record.get("title_en") or ""
    return f"{title} {strip_markup(record.get('abstract', ''))}".lower()


_TERM_RE = {}


def _term_pattern(term):
    """A keyword must start a word ("fusion" does not match "diffusion", "flow" not "workflow").
    Longer keywords may continue ("neutron" -> "neutronics", "dosim" -> "dosimetry").
    Keywords of 4 letters or fewer must also end the word, apart from a plural/verb ending
    ("loca" -> "LOCAs" but not "local"; "heat" -> "heating")."""
    if term not in _TERM_RE:
        body = re.escape(term)
        if len(term) <= 4 and re.fullmatch(r"[a-z0-9]+", term):
            body += r"(?:s|es|ed|ing)?(?![a-z0-9])"
        _TERM_RE[term] = re.compile(r"(?<![a-z0-9])" + body)
    return _TERM_RE[term]


def term_hit(text, term):
    """True if `term` occurs in `text` as a word, outside the phrases listed for it in
    papers.json "keyword_exceptions" (e.g. "thermal" inside "thermal neutron" is reactor physics,
    not thermal-hydraulics)."""
    term = term.lower()
    exceptions = SETTINGS.get("keyword_exceptions", {}).get(term, [])
    for match in _term_pattern(term).finditer(text):
        if not any(text.startswith(phrase, match.start()) for phrase in exceptions):
            return True
    return False


def matches_any(record_or_text, terms):
    text = record_or_text if isinstance(record_or_text, str) else paper_text(record_or_text)
    return any(term_hit(text, term) for term in terms)


def topics_for(record):
    text = paper_text(record)
    found = [name for name, terms in SETTINGS["topics"].items() if matches_any(text, terms)]
    return found or [SETTINGS["fallback_topic"]]


def watchlists_for(record):
    text = paper_text(record)
    return [name for name, terms in SETTINGS["watchlists"].items() if matches_any(text, terms)]


def document_type(title):
    value = (title or "").lower().strip()
    for label, rule in SETTINGS["document_types"].items():
        if value in rule.get("equals", []):
            return label
        if any(value.startswith(prefix) for prefix in rule.get("startswith", [])):
            return label
        if any(term in value for term in rule.get("contains", [])):
            return label
    return SETTINGS["default_document_type"]


def read_json(path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def raw_path(period: Period, kind: str):
    """kind: 'current' (full metadata) for the run's own window."""
    return RAW_DIR / f"{period.run_id}-{kind}.json"
