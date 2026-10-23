"""Cumulative SQLite database keyed by lower-case DOI."""
import sqlite3
from datetime import datetime

from .common import DB_PATH, DUMP_PATH, SETTINGS, document_type, strip_markup, topics_for

SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
  doi TEXT PRIMARY KEY,
  title_en TEXT NOT NULL,
  title_ko TEXT,
  journal TEXT NOT NULL,
  issn TEXT,
  authors TEXT,
  doi_registered_date TEXT,
  published_online TEXT,
  issue_date TEXT,
  document_type TEXT NOT NULL,
  primary_topic TEXT NOT NULL,
  abstract TEXT,
  abstract_source TEXT NOT NULL DEFAULT '',
  abstract_url TEXT,
  doi_url TEXT NOT NULL,
  open_access INTEGER NOT NULL DEFAULT 0,
  first_seen TEXT NOT NULL,
  last_checked TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  source TEXT NOT NULL,
  countries TEXT NOT NULL DEFAULT '',
  primary_country TEXT NOT NULL DEFAULT '',
  country_source TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS collection_runs (
  run_id TEXT PRIMARY KEY,
  period_start TEXT NOT NULL,
  period_end TEXT NOT NULL,
  executed_at TEXT NOT NULL,
  found_count INTEGER NOT NULL,
  new_count INTEGER NOT NULL,
  updated_count INTEGER NOT NULL,
  error_count INTEGER NOT NULL,
  source_note TEXT
);
CREATE TABLE IF NOT EXISTS paper_runs (
  doi TEXT NOT NULL REFERENCES papers(doi),
  run_id TEXT NOT NULL REFERENCES collection_runs(run_id),
  PRIMARY KEY (doi, run_id)
);
CREATE TABLE IF NOT EXISTS topics (
  topic_id INTEGER PRIMARY KEY,
  topic_ko TEXT UNIQUE NOT NULL,
  keywords TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS paper_topics (
  doi TEXT NOT NULL REFERENCES papers(doi),
  topic_ko TEXT NOT NULL REFERENCES topics(topic_ko),
  is_primary INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (doi, topic_ko)
);
CREATE INDEX IF NOT EXISTS idx_papers_journal ON papers(journal);
CREATE INDEX IF NOT EXISTS idx_papers_registered ON papers(doi_registered_date);
CREATE INDEX IF NOT EXISTS idx_papers_topic ON papers(primary_topic);
"""

SOURCE_NOTE = "Crossref DOI created date; weekly window; OpenAlex countries/abstracts"


def connect(path=DB_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    # The SQL dump in git is the source of truth; rebuild the local file whenever the dump is newer (e.g. after git pull).
    if DUMP_PATH.exists() and (not path.exists() or DUMP_PATH.stat().st_mtime > path.stat().st_mtime):
        path.unlink(missing_ok=True)
        restore = sqlite3.connect(path)
        restore.executescript(DUMP_PATH.read_text(encoding="utf-8"))
        restore.close()
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript(SCHEMA)
    columns = {row[1] for row in con.execute("PRAGMA table_info(papers)")}
    if "abstract_source" not in columns:
        con.execute("ALTER TABLE papers ADD COLUMN abstract_source TEXT NOT NULL DEFAULT ''")
    sync_topics(con)
    return con


def sync_topics(con):
    names = list(SETTINGS["topics"].items()) + [(SETTINGS["fallback_topic"], [])]
    with con:
        for i, (topic, terms) in enumerate(names, 1):
            con.execute(
                "INSERT INTO topics(topic_id,topic_ko,keywords,active) VALUES(?,?,?,1) "
                "ON CONFLICT(topic_ko) DO UPDATE SET keywords=excluded.keywords,active=1",
                (i, topic, "; ".join(terms)),
            )


def set_topics(con, doi, record):
    areas = topics_for(record)
    con.execute("DELETE FROM paper_topics WHERE doi=?", (doi,))
    for j, area in enumerate(areas):
        con.execute("INSERT INTO paper_topics(doi,topic_ko,is_primary) VALUES(?,?,?)", (doi, area, int(j == 0)))
    return areas[0]


def reclassify_all(con):
    """Re-apply the current topic rules to every stored paper, so a change to papers.json topics or
    keyword_exceptions (or to the matching rule) also fixes papers collected earlier. Returns papers changed."""
    changed = 0
    with con:
        for row in con.execute("SELECT doi, title_en, abstract, primary_topic FROM papers").fetchall():
            areas = topics_for({"title": row["title_en"], "abstract": row["abstract"]})
            stored = [r["topic_ko"] for r in con.execute(
                "SELECT topic_ko FROM paper_topics WHERE doi=? ORDER BY is_primary DESC, rowid", (row["doi"],))]
            if stored == areas and row["primary_topic"] == areas[0]:
                continue
            set_topics(con, row["doi"], {"title": row["title_en"], "abstract": row["abstract"]})
            con.execute("UPDATE papers SET primary_topic=? WHERE doi=?", (areas[0], row["doi"]))
            changed += 1
    return changed


def upsert_run(con, period, records, additive=False):
    """Insert/update one week's records. Returns (found, new).

    additive=True adds to an existing run's counts instead of replacing them (backfilling a newly added journal).
    """
    run_id = period.run_id
    now = datetime.now().isoformat(timespec="seconds")
    before = con.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    with con:
        con.execute(
            "INSERT INTO collection_runs(run_id,period_start,period_end,executed_at,found_count,new_count,updated_count,error_count,source_note) "
            "VALUES(?,?,?,?,0,0,0,0,?) ON CONFLICT(run_id) DO UPDATE SET executed_at=excluded.executed_at,source_note=excluded.source_note",
            (run_id, period.start.isoformat(), period.end.isoformat(), now, SOURCE_NOTE),
        )
        for r in records:
            doi = r["doi"].lower()
            con.execute(
                """INSERT INTO papers(doi,title_en,title_ko,journal,issn,authors,doi_registered_date,published_online,issue_date,
                document_type,primary_topic,abstract,abstract_source,abstract_url,doi_url,open_access,first_seen,last_checked,status,source,
                countries,primary_country,country_source)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'active',?,?,?,?)
                ON CONFLICT(doi) DO UPDATE SET title_en=excluded.title_en,
                  title_ko=COALESCE(NULLIF(excluded.title_ko,''),papers.title_ko),
                  journal=excluded.journal,issn=excluded.issn,
                  authors=CASE WHEN excluded.authors<>'' THEN excluded.authors ELSE papers.authors END,
                  published_online=COALESCE(NULLIF(excluded.published_online,''),papers.published_online),
                  issue_date=COALESCE(NULLIF(excluded.issue_date,''),papers.issue_date),
                  document_type=excluded.document_type,
                  abstract=COALESCE(NULLIF(excluded.abstract,''),papers.abstract),
                  abstract_source=COALESCE(NULLIF(excluded.abstract_source,''),papers.abstract_source),
                  abstract_url=excluded.abstract_url,doi_url=excluded.doi_url,
                  open_access=MAX(excluded.open_access,papers.open_access),
                  last_checked=excluded.last_checked,status='active',source=excluded.source,
                  countries=COALESCE(NULLIF(excluded.countries,''),papers.countries),
                  primary_country=COALESCE(NULLIF(excluded.primary_country,''),papers.primary_country),
                  country_source=COALESCE(NULLIF(excluded.country_source,''),papers.country_source)""",
                (
                    doi, r["title"], r.get("title_ko", ""), r["journal"], r.get("issn", ""), "; ".join(r.get("authors", [])),
                    r.get("registered_date", ""), r.get("published_online", ""), r.get("issued", ""), document_type(r["title"]),
                    topics_for(r)[0], strip_markup(r.get("abstract", "")), r.get("abstract_source", ""),
                    r.get("publisher_url") or r["doi_url"], r["doi_url"], int(bool(r.get("open_access"))),
                    period.end.isoformat(), period.run_id, "Crossref + OpenAlex",
                    ";".join(r.get("countries", [])), r.get("primary_country", ""), r.get("country_source", ""),
                ),
            )
            row = con.execute("SELECT title_en, abstract FROM papers WHERE doi=?", (doi,)).fetchone()
            primary = set_topics(con, doi, {"title": row["title_en"], "abstract": row["abstract"]})
            con.execute("UPDATE papers SET primary_topic=? WHERE doi=?", (primary, doi))
            con.execute("INSERT OR IGNORE INTO paper_runs(doi,run_id) VALUES(?,?)", (doi, run_id))
        after = con.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
        new = after - before
        if additive:
            con.execute(
                "UPDATE collection_runs SET found_count=found_count+?,new_count=new_count+? WHERE run_id=?",
                (new, new, run_id),
            )
        else:
            con.execute(
                "UPDATE collection_runs SET found_count=?,new_count=?,updated_count=?,error_count=0 WHERE run_id=?",
                (len(records), new, len(records) - new, run_id),
            )
    return len(records), new


def validate(con):
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    foreign = con.execute("PRAGMA foreign_key_check").fetchall()
    if integrity != "ok" or foreign:
        raise RuntimeError(f"database validation failed: integrity={integrity}, foreign_key_issues={len(foreign)}")
    return integrity


def last_run_id(con):
    row = con.execute("SELECT MAX(run_id) FROM collection_runs").fetchone()
    return row[0]


def papers_between(con, start, end):
    rows = con.execute(
        "SELECT * FROM papers WHERE doi_registered_date BETWEEN ? AND ? ORDER BY doi_registered_date DESC, journal, title_en",
        (str(start), str(end)),
    )
    return [dict(row) for row in rows]


def export_payload(con):
    q = lambda sql: [dict(row) for row in con.execute(sql)]
    return {
        "papers": q("SELECT * FROM papers ORDER BY doi_registered_date DESC,journal,title_en"),
        "runs": q("SELECT * FROM collection_runs ORDER BY period_end DESC"),
        "topics": q("SELECT * FROM topics ORDER BY topic_id"),
        "paper_topics": q("SELECT * FROM paper_topics ORDER BY doi,is_primary DESC,topic_ko"),
    }


def as_record(row):
    """DB row -> the record shape used by the dashboard/email builders."""
    record = dict(row)
    record["title"] = record["title_en"]
    record["title_ko"] = record.get("title_ko") or record["title_en"]
    record["authors"] = [a for a in (record.get("authors") or "").split("; ") if a]
    record["registered_date"] = record["doi_registered_date"]
    record["publisher_url"] = record.get("abstract_url") or record["doi_url"]
    record["issued"] = record.get("issue_date") or ""
    record["cover_date"] = ""
    record["countries"] = [c for c in (record.get("countries") or "").split(";") if c]
    record["abstract"] = record.get("abstract") or ""
    record["abstract_source"] = record.get("abstract_source") or ""
    return record


def sync_titles(con, cache):
    """Push the (possibly corrected) translation cache into papers.title_ko."""
    with con:
        for doi, entry in cache.items():
            if entry.get("ko"):
                con.execute("UPDATE papers SET title_ko=? WHERE doi=? AND IFNULL(title_ko,'')<>?", (entry["ko"], doi, entry["ko"]))


def dump(con):
    """Write the DB as SQL text. Git stores only the changed lines each week instead of a new binary copy."""
    DUMP_PATH.write_text("\n".join(con.iterdump()) + "\n", encoding="utf-8")
