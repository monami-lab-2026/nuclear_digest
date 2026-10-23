"""Home page (docs/index.html): today's news brief and this week's papers on one screen.

Rebuilt at the end of every news and paper run, so it always shows the latest of both.

    python -m app.build_home
"""
import json
from datetime import date

from .config import DOCS_DIR, ROOT, SITE
from .site_theme import esc, head, page_header, site_footer, site_header

WEEKDAYS_KO = "월화수목금토일"

HOME_CSS = """
.home-grid{display:grid;gap:1px;border:1px solid var(--color-line);background:var(--color-line);grid-template-columns:minmax(0,1fr)}
@media(min-width:900px){.home-grid{grid-template-columns:minmax(0,7fr) minmax(0,5fr)}}
.panel{background:var(--color-card);padding:1.75rem 1.5rem 1.5rem;min-width:0}
@media(min-width:768px){.panel{padding:2.25rem 2rem 2rem}}
.panel h2{margin:1rem 0 0;font-size:1.5rem;line-height:1.3;font-weight:600;letter-spacing:-.015em;color:var(--color-ink)}
.panel .sub{margin:.4rem 0 0;font-size:.8125rem;color:var(--color-neutral-500)}
.panel .overview{margin:1.25rem 0 0;font-size:.9375rem;line-height:1.9;color:var(--color-neutral-800)}
.notice{margin:1.25rem 0 0;padding:.8rem 1rem;border-left:3px solid var(--color-accent);background:var(--color-accent-soft);font-size:.875rem;line-height:1.7;color:var(--color-neutral-800)}
.heads{margin:1.25rem 0 0;padding:0;list-style:none;counter-reset:h}
.heads li{counter-increment:h;display:grid;grid-template-columns:2rem 1fr;gap:.25rem;padding:.75rem 0;border-top:1px solid var(--color-line)}
.heads li::before{content:counter(h,decimal-leading-zero);font-weight:600;font-size:.8125rem;color:var(--color-accent);font-variant-numeric:tabular-nums;padding-top:.15rem}
.heads a{font-size:.9375rem;line-height:1.6;font-weight:500;color:var(--color-ink);text-decoration:none}
.heads a:hover{color:var(--color-accent)}
.heads small{display:block;margin-top:.2rem;font-size:.75rem;color:var(--color-neutral-500)}
.mini-stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;margin:1.25rem 0 0;border:1px solid var(--color-line);background:var(--color-line)}
.mini-stats div{background:var(--color-card);padding:.9rem .9rem .8rem}
.mini-stats strong{display:block;font-size:1.375rem;line-height:1.1;font-weight:600;color:var(--color-ink);font-variant-numeric:tabular-nums}
.mini-stats span{display:block;margin-top:.4rem;font-size:.6875rem;color:var(--color-neutral-500)}
.mini-stats em{font-style:normal;font-size:.75rem;font-weight:600;color:var(--color-accent);margin-left:.3rem}
.mini-stats em.down{color:var(--color-neutral-500)}
.interest{margin:1.25rem 0 0;padding:0;list-style:none}
.interest li{padding:.7rem 0;border-top:1px solid var(--color-line)}
.interest .row{display:flex;justify-content:space-between;gap:1rem;font-size:.875rem;font-weight:600;color:var(--color-ink)}
.interest .row span{font-weight:600;color:var(--color-accent);font-variant-numeric:tabular-nums}
.interest a{display:block;margin-top:.25rem;font-size:.8125rem;line-height:1.55;color:var(--color-neutral-700);text-decoration:none;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.interest a:hover{color:var(--color-accent)}
.more{display:flex;flex-wrap:wrap;gap:.5rem;margin:1.5rem 0 0}
.more a{font-size:.8125rem;color:var(--color-neutral-700);text-decoration:none;border:1px solid var(--color-line-strong);padding:.55rem .85rem}
.more a:hover{color:var(--color-accent);border-color:var(--color-accent)}
.more a.primary{background:var(--color-navy);border-color:var(--color-navy);color:#fff}
:root[data-theme="dark"] .more a.primary{background:var(--color-ink);border-color:var(--color-ink);color:var(--color-canvas)}
.week{margin:0;padding:0;list-style:none;display:grid;grid-template-columns:repeat(auto-fill,minmax(13rem,1fr));border-top:1px solid var(--color-line);border-left:1px solid var(--color-line)}
.week li{border-right:1px solid var(--color-line);border-bottom:1px solid var(--color-line)}
.week a{display:block;height:100%;background:var(--color-card);padding:1rem 1.1rem;text-decoration:none;color:inherit}
.week a:hover b{color:var(--color-accent)}
.week b{display:block;font-size:.875rem;font-weight:600;color:var(--color-ink)}
.week span{display:block;margin-top:.35rem;font-size:.8125rem;line-height:1.55;color:var(--color-neutral-600);
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
"""


def read_json(path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def day_label(value):
    d = date.fromisoformat(value)
    return f"{d.month}월 {d.day}일 ({WEEKDAYS_KO[d.weekday()]})"


def news_days():
    days = {}
    for path in sorted((ROOT / "data" / "news" / "days").glob("*.json")):
        record = read_json(path)
        if record:
            days[record["date"]] = record
    return days


def news_panel(days):
    if not days:
        return ('<article class="panel"><p class="eyebrow eyebrow-mark eyebrow-accent">Today · News</p><h2>오늘의 원자력 뉴스</h2>'
                '<p class="notice">아직 수집된 뉴스가 없습니다. 첫 수집이 끝나면 여기에 표시됩니다.</p></article>')
    latest = max(days)
    record = days[latest]
    stories = record.get("stories", [])
    engine = record.get("engine", {}).get("engine")
    parts = [f'<article class="panel"><p class="eyebrow eyebrow-mark eyebrow-accent">Today · News</p>',
             f'<h2>오늘의 원자력 뉴스</h2><p class="sub">{esc(day_label(latest))} · 해설 {len(stories)}건 · '
             f'살펴본 기사 {sum(len(c["items"]) for c in record.get("sources", []))}건</p>']
    if record.get("overview"):
        parts.append(f'<p class="overview">{esc(record["overview"])}</p>')
    elif engine == "pending":
        parts.append('<p class="notice">해설을 준비하고 있습니다. 우선 수집한 기사 제목만 볼 수 있습니다.</p>')
    if stories:
        items = "".join(
            f'<li><div><a href="news/index.html">{esc(s["headline"])}</a>'
            f'<small>{esc(s["region"])} · {esc(s["category"])}</small></div></li>'
            for s in stories
        )
        parts.append(f'<ol class="heads">{items}</ol>')
    else:
        heads = [c["items"][0] for c in record.get("sources", [])[:5]]
        items = "".join(
            f'<li><div><a href="{esc(h["url"])}" target="_blank" rel="noopener">{esc(h["title"])}</a>'
            f'<small>{esc(h["publisher"])}</small></div></li>' for h in heads
        )
        if items:
            parts.append(f'<ol class="heads">{items}</ol>')
    parts.append('<div class="more"><a class="primary" href="news/index.html">해설 전체 보기</a>'
                 '<a href="news/archive.html">지난 브리핑</a></div></article>')
    return "".join(parts)


def papers_panel():
    from .papers.common import RAW_DIR, STATE_DIR, watchlists_for

    status = read_json(STATE_DIR / "latest-run.json", {}) or {}
    run = status.get("run_date")
    records = read_json(RAW_DIR / f"{run}-current.json", []) if run else []
    if not run or status.get("status") != "success":
        # Fall back to the newest collected week on disk.
        raws = sorted(RAW_DIR.glob("*-current.json"))
        if raws:
            run = raws[-1].name[:10]
            records = read_json(raws[-1], []) or []
    head_html = '<article class="panel"><p class="eyebrow eyebrow-mark eyebrow-accent">This week · Papers</p><h2>이번 주 새 논문</h2>'
    if not records:
        return head_html + '<p class="notice">아직 수집된 논문이 없습니다. 매주 월요일 아침에 갱신됩니다.</p></article>'

    count = len(records)
    previous = status.get("previous_count") if status.get("run_date") == run else None
    delta = ""
    if isinstance(previous, int) and previous:
        diff = count - previous
        delta = f'<em class="{"up" if diff > 0 else "down"}" title="지난주 대비">{"+" if diff > 0 else ""}{diff}</em>' if diff else ""
    period = f'{status.get("period_start", "")} ~ {status.get("period_end", "")}' if status.get("run_date") == run else f"{run} 주"
    total = status.get("total_papers", "")

    matched = {}
    for record in records:
        for name in watchlists_for(record):
            matched.setdefault(name, []).append(record)
    ranked = sorted(matched.items(), key=lambda kv: -len(kv[1]))[:5]
    interest = "".join(
        f'<li><div class="row">{esc(name)}<span>{len(papers)}편</span></div>'
        f'<a href="{esc(papers[0]["doi_url"])}" target="_blank" rel="noopener" title="{esc(papers[0]["title"])}">'
        f'{esc(papers[0].get("title_ko") or papers[0]["title"])}</a></li>'
        for name, papers in ranked
    )
    parts = [head_html, f'<p class="sub">{esc(period)}</p>',
             '<div class="mini-stats">'
             f'<div><strong>{count}{delta}</strong><span>이번 주 신규</span></div>'
             f'<div><strong>{len(matched)}</strong><span>관심 분야 해당</span></div>'
             f'<div><strong>{total}</strong><span>누적 논문</span></div></div>']
    if interest:
        parts.append(f'<ul class="interest">{interest}</ul>')
    parts.append('<div class="more"><a class="primary" href="papers/index.html">이번 주 동향</a>'
                 '<a href="papers/database.html">논문 DB 검색</a></div></article>')
    return "".join(parts)


def recent_week(days):
    dates = sorted(days, reverse=True)[1:8]
    if not dates:
        return ""
    cells = []
    for d in dates:
        stories = days[d].get("stories", [])
        line = stories[0]["headline"] if stories else "해설 없이 제목만 수집한 날"
        cells.append(f'<li><a href="news/days/{d}.html"><b>{esc(day_label(d))}</b><span>{esc(line)}</span></a></li>')
    return ('<section class="section"><div style="margin-bottom:1.25rem"><p class="eyebrow eyebrow-mark">Recent</p>'
            f'<h2 style="margin:1rem 0 0;font-size:1.375rem;font-weight:600;color:var(--color-ink)">지난 일주일</h2></div>'
            f'<ul class="week">{"".join(cells)}</ul></section>')


def build_home():
    days = news_days()
    lead = "매일 아침 국내외 원자력 뉴스 해설과, 매주 주요 저널에 새로 나온 논문을 한곳에서 봅니다."
    body = (f'<section class="section"><div class="home-grid">{news_panel(days)}{papers_panel()}</div></section>'
            f'{recent_week(days)}')
    page = (
        f'<!doctype html><html lang="ko"><head>{head(SITE["title"], lead, HOME_CSS)}'
        f'</head><body>'
        f'{site_header("home", "./")}{page_header(esc(SITE.get("subtitle", "")), esc(SITE["title"]), lead)}'
        f'<main class="page"><div class="container-page">{body}</div></main>{site_footer("home", "./", credit=True)}</body></html>'
    )
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "index.html").write_text(page, encoding="utf-8")
    (DOCS_DIR / ".nojekyll").touch()
    from .build_subscribe import build_subscribe
    build_subscribe()
    from .build_app import build_app
    build_app()  # manifest + service worker for the home-screen app
    from .build_install import build_install
    build_install()  # "웹으로 보기 · 앱으로 설치" page linked from every header  # every page links to it, so keep it in step with config/site.json
    return DOCS_DIR / "index.html"


if __name__ == "__main__":
    print(build_home())
