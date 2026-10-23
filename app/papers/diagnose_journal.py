"""Compare how a journal's papers fall on Crossref date fields (created vs online vs issue).

    python -m app.papers.diagnose_journal 1001-8042 --days 90

Used to decide whether "DOI created date" is a sound weekly criterion for a journal.
"""
import argparse
from collections import Counter
from datetime import date, timedelta

from .collect import get_json
from .common import SETTINGS


def works(issn, filter_):
    cursor, out = "*", []
    while cursor:
        message = get_json(f"https://api.crossref.org/journals/{issn}/works",
                           params={"filter": filter_, "select": "DOI,created,published-online,published-print,issued,type",
                                   "rows": 500, "cursor": cursor, "mailto": SETTINGS["contact_email"]})["message"]
        items = message.get("items", [])
        out += items
        if not items or message.get("next-cursor") in (None, cursor):
            break
        cursor = message["next-cursor"]
    return out


def month(parts):
    p = (parts or {}).get("date-parts", [[None]])[0]
    return f"{p[0]}-{p[1]:02d}" if p and len(p) > 1 and p[0] else "none"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("issn")
    parser.add_argument("--days", type=int, default=90)
    args = parser.parse_args()
    since = (date.today() - timedelta(days=args.days)).isoformat()
    by_created = works(args.issn, f"from-created-date:{since}")
    by_online = works(args.issn, f"from-online-pub-date:{since}")
    print(f"ISSN {args.issn}, since {since}")
    print(f"  DOIs created since: {len(by_created)}   published online since: {len(by_online)}")
    print("  created (by week):", sorted(Counter((w.get('created') or {}).get('date-time', '')[:10] for w in by_created).items()))
    print("  online-pub month of online set:", sorted(Counter(month(w.get('published-online')) for w in by_online).items()))
    print("  created month of online set:", sorted(Counter((w.get('created') or {}).get('date-time', '')[:7] for w in by_online).items()))
    lag = [(date.fromisoformat(w['created']['date-time'][:10]) - date(*w['published-online']['date-parts'][0][:3])).days
           for w in by_online if len((w.get('published-online') or {}).get('date-parts', [[]])[0]) == 3]
    if lag:
        lag.sort()
        print(f"  created minus online-pub (days): median {lag[len(lag)//2]}, min {lag[0]}, max {lag[-1]}, n={len(lag)}")


if __name__ == "__main__":
    main()
