"""Collect DOI-registered papers for one weekly window.

Sources
- Crossref: papers whose DOI was *created* in the window (the "new paper" criterion).
- OpenAlex: author countries, open-access flag, and an abstract when OpenAlex has one.
- Elsevier Article API (optional, needs ELSEVIER_API_KEY): PII / ScienceDirect link / cover date.
"""
import argparse
import json
import os
import time
from datetime import date
from urllib.parse import quote

import requests

from .common import HEADERS, SETTINGS, Period, raw_path, write_json

session = requests.Session()
session.headers.update(HEADERS)


def get_json(url, params=None, headers=None, allow_404=False, attempts=5):
    """GET with retry on rate limits / server errors. Raises on other failures."""
    for attempt in range(attempts):
        try:
            response = session.get(url, params=params, headers=headers, timeout=60)
        except requests.RequestException:
            if attempt == attempts - 1:
                raise
            time.sleep(2 ** attempt)
            continue
        if response.status_code == 200:
            return response.json()
        if allow_404 and response.status_code in (401, 403, 404):
            return None
        if response.status_code in (429, 500, 502, 503, 504) and attempt < attempts - 1:
            time.sleep(float(response.headers.get("Retry-After", 2 ** attempt)))
            continue
        response.raise_for_status()
    return None


def date_parts(value):
    parts = (value or {}).get("date-parts", [[]])[0] or []
    return "-".join(f"{p:02d}" if i else str(p) for i, p in enumerate(parts) if p is not None)


def author_name(author):
    return " ".join(filter(None, [author.get("given", ""), author.get("family", "")])).strip() or author.get("name", "")


def crossref_items(issn, start, end):
    cursor = "*"
    while cursor:
        payload = get_json(
            f"https://api.crossref.org/journals/{issn}/works",
            params={
                "filter": f"from-created-date:{start},until-created-date:{end}",
                "select": "DOI,title,author,created,published-online,published-print,issued,type,abstract,URL",
                "rows": 500,
                "cursor": cursor,
                "mailto": SETTINGS["contact_email"],
            },
        )
        message = payload["message"]
        items = message.get("items", [])
        yield from items
        next_cursor = message.get("next-cursor")
        if not items or not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor


def openalex_work(doi):
    params = {"select": "doi,authorships,open_access,abstract_inverted_index", "mailto": SETTINGS["contact_email"]}
    if os.environ.get("OPENALEX_API_KEY"):
        params["api_key"] = os.environ["OPENALEX_API_KEY"]
    return get_json("https://api.openalex.org/works/https://doi.org/" + quote(doi, safe="/()"), params=params, allow_404=True) or {}


def countries_from(work):
    countries, corresponding = [], []
    for authorship in work.get("authorships") or []:
        codes = authorship.get("countries") or [
            inst.get("country_code") for inst in authorship.get("institutions", []) if inst.get("country_code")
        ]
        for code in codes:
            code = (code or "").upper()
            if code and code not in countries:
                countries.append(code)
            if authorship.get("is_corresponding") and code and code not in corresponding:
                corresponding.append(code)
    return countries, (corresponding or countries or [""])[0]


def abstract_from(work):
    index = work.get("abstract_inverted_index")
    if not index:
        return ""
    positions = [(pos, word) for word, places in index.items() for pos in places]
    return " ".join(word for _, word in sorted(positions))


def elsevier_core(doi):
    key = os.environ.get("ELSEVIER_API_KEY")
    if not key:
        return {}
    payload = get_json(
        "https://api.elsevier.com/content/article/doi/" + quote(doi, safe=""),
        headers={"Accept": "application/json", "X-ELS-APIKey": key},
        allow_404=True,
    )
    return (payload or {}).get("full-text-retrieval-response", {}).get("coredata", {})


def collect(period: Period, journals=None, start=None, end=None):
    """journals: subset of SETTINGS["journals"] names (default all). start/end override the period window."""
    start, end = start or period.start.isoformat(), end or period.end.isoformat()
    records = {}
    for journal, issns in SETTINGS["journals"].items():
        if journals and journal not in journals:
            continue
        # A journal may list print and electronic ISSNs ("print,electronic"); both are queried, DOIs deduplicated.
        issn = issns.split(",")[0].strip()
        items = [item for value in issns.split(",") for item in crossref_items(value.strip(), start, end)]
        for item in items:
            registered = (item.get("created") or {}).get("date-time", "")[:10]
            doi = (item.get("DOI") or "").lower()
            if not doi or not start <= registered <= end:
                continue
            doi_url = "https://doi.org/" + doi
            record = {
                "journal": journal,
                "issn": issn,
                "title": ((item.get("title") or [""])[0] or "").strip(),
                "authors": [author_name(a) for a in item.get("author", [])],
                "doi": doi,
                "doi_url": doi_url,
                "registered_date": registered,
                "published_online": date_parts(item.get("published-online")),
                "published_print": date_parts(item.get("published-print")),
                "issued": date_parts(item.get("issued")),
                "abstract": item.get("abstract", ""),
                "abstract_source": "Crossref" if item.get("abstract") else "",
                "publisher_url": doi_url,
                "pii": "",
                "cover_date": "",
            }
            work = openalex_work(doi)
            record["countries"], record["primary_country"] = countries_from(work)
            record["country_source"] = "OpenAlex authorship institutions" if record["countries"] else "OpenAlex: country unavailable"
            record["open_access"] = bool((work.get("open_access") or {}).get("is_oa"))
            if not record["abstract"]:
                record["abstract"] = abstract_from(work)
                record["abstract_source"] = "OpenAlex" if record["abstract"] else ""
            if doi.startswith("10.1016/"):
                core = elsevier_core(doi)
                if core:
                    record["pii"] = core.get("pii", "")
                    record["cover_date"] = core.get("prism:coverDate", "")
                    link = next((l.get("@href", "") for l in core.get("link", []) if l.get("@rel") == "scidir"), "")
                    record["publisher_url"] = link or doi_url
            records[doi] = record
            time.sleep(0.05)
    ordered = sorted(records.values(), key=lambda r: (r["registered_date"], r["journal"], r["title"]), reverse=True)
    return ordered


def enrich_recent(con, since, limit=800):
    """Fill abstracts/countries/OA from OpenAlex for stored papers that lack them.

    Keeps week-to-week comparisons fair: topic rules read title+abstract, so a week with abstracts
    must not be compared against a week without them. Topics are recomputed after the update.
    """
    from .database import set_topics

    rows = con.execute(
        "SELECT doi, title_en, abstract, countries FROM papers WHERE doi_registered_date >= ? "
        "AND (IFNULL(abstract,'')='' OR IFNULL(countries,'')='') ORDER BY doi_registered_date DESC LIMIT ?",
        (str(since), limit),
    ).fetchall()
    filled = {"checked": len(rows), "abstract": 0, "countries": 0}
    with con:
        for row in rows:
            work = openalex_work(row["doi"])
            if not work:
                continue
            abstract = row["abstract"] or abstract_from(work)
            countries, primary = countries_from(work)
            if abstract and not row["abstract"]:
                filled["abstract"] += 1
                con.execute("UPDATE papers SET abstract=?, abstract_source='OpenAlex' WHERE doi=?", (abstract, row["doi"]))
            if countries and not row["countries"]:
                filled["countries"] += 1
                con.execute("UPDATE papers SET countries=?, primary_country=?, country_source='OpenAlex authorship institutions' WHERE doi=?",
                            (";".join(countries), primary, row["doi"]))
            if (work.get("open_access") or {}).get("is_oa"):
                con.execute("UPDATE papers SET open_access=1 WHERE doi=?", (row["doi"],))
            primary_topic = set_topics(con, row["doi"], {"title": row["title_en"], "abstract": abstract})
            con.execute("UPDATE papers SET primary_topic=? WHERE doi=?", (primary_topic, row["doi"]))
            time.sleep(0.05)
    return filled


def main():
    parser = argparse.ArgumentParser(description="Collect one weekly window into data/raw/")
    parser.add_argument("--run-date", default=date.today().isoformat(), help="Any date; snapped to that week's Monday")
    args = parser.parse_args()
    period = Period.for_date(date.fromisoformat(args.run_date))
    records = collect(period)
    write_json(raw_path(period, "current"), records)
    by_journal = {j: sum(r["journal"] == j for r in records) for j in SETTINGS["journals"]}
    print(json.dumps({"run_id": period.run_id, "start": str(period.start), "end": str(period.end), "count": len(records), "by_journal": by_journal}, ensure_ascii=False))


if __name__ == "__main__":
    main()

