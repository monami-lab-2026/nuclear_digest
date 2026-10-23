"""Render the public site from data/days/*.json.

docs/news/index.html           latest day
docs/news/days/YYYY-MM-DD.html one page per day (all re-rendered each run so the date picker stays current)
docs/news/archive.html         every day, grouped by month
docs/news/dates.json           available dates (for other tools and the home page)
"""
import json
from datetime import date, datetime

from .common import DAYS_DIR, KST, SETTINGS, SITE, SITE_DIR, date_label, read_json, write_json
from ..site_theme import esc, head, page_header, site_footer, site_header

NEWS_CSS = """
.notice{margin:0 0 2rem;padding:.9rem 1.1rem;border-left:3px solid var(--color-accent);background:var(--color-accent-soft);
  font-size:.875rem;line-height:1.7;color:var(--color-neutral-800)}
.day-nav{display:flex;flex-wrap:wrap;align-items:center;gap:.75rem 1rem;margin:0 0 2rem;padding:1rem 0;border-bottom:1px solid var(--color-line)}
.day-nav a{font-size:.8125rem;color:var(--color-neutral-600);text-decoration:none;border:1px solid var(--color-line);padding:.5rem .8rem;white-space:nowrap}
.day-nav a:hover{color:var(--color-neutral-900);border-color:var(--color-line-strong)}
.day-nav input{font:inherit;font-size:.9375rem;height:2.75rem;padding:0 .7rem;border:1px solid var(--color-line-strong);background:var(--color-card);color:var(--color-neutral-900)}
.stepper{display:inline-flex;align-items:stretch;gap:.5rem}
.day-nav .step{display:inline-flex;align-items:center;justify-content:center;width:2.75rem;height:2.75rem;padding:0;
  border:1px solid var(--color-line-strong);font-size:1.125rem;line-height:1;color:var(--color-accent);text-decoration:none}
.day-nav a.step:hover{background:var(--color-accent-soft);border-color:var(--color-accent);color:var(--color-accent)}
.day-nav .step[aria-disabled="true"]{color:var(--color-neutral-400);border-color:var(--color-line);cursor:default}
.day-nav .spacer{flex:1}
.day-msg{flex-basis:100%;margin:0;font-size:.8125rem;color:var(--color-accent)}
.day-msg[hidden]{display:none}
.filters{display:flex;flex-wrap:wrap;gap:.5rem;margin:0 0 1.5rem}
.story{padding:2rem 0;border-top:1px solid var(--color-line)}
.story:first-of-type{border-top:1px solid var(--color-line-strong)}
.story[hidden]{display:none}
.story-top{display:flex;flex-wrap:wrap;align-items:center;gap:.5rem;font-size:.75rem;color:var(--color-neutral-500)}
.story-top .num{font-weight:600;color:var(--color-accent);font-variant-numeric:tabular-nums}
.tag{display:inline-flex;align-items:center;border-radius:999px;padding:.3rem .65rem;font-size:.75rem;line-height:1;border:1px solid var(--color-line);background:var(--color-surface);color:var(--color-neutral-700)}
.tag.region{border-color:color-mix(in srgb,var(--color-accent) 25%,transparent);background:var(--color-accent-soft)}
.tag.key{background:var(--color-navy);border-color:var(--color-navy);color:#fff}
:root[data-theme="dark"] .tag.key{background:var(--color-ink);border-color:var(--color-ink);color:var(--color-canvas)}
.story h2{margin:.9rem 0 0;font-size:1.5rem;line-height:1.4;font-weight:700;letter-spacing:-.02em;color:var(--color-ink);text-wrap:balance}
@media(min-width:768px){.story h2{font-size:1.75rem}}
.story h3{display:flex;align-items:center;gap:.5rem;margin:1.6rem 0 .45rem;font-size:.875rem;letter-spacing:.02em;font-weight:700;color:var(--color-accent)}
.story h3::before{content:"";flex:none;width:1rem;height:3px;background:var(--color-accent)}
.story p{margin:0;font-size:.9375rem;line-height:1.9;color:var(--color-neutral-800)}
.concepts{margin:0;display:grid;gap:.5rem}
.concepts div{display:grid;grid-template-columns:9rem 1fr;gap:.75rem;padding:.6rem 0;border-bottom:1px solid var(--color-line);font-size:.875rem;line-height:1.75}
.concepts dt{font-weight:600;color:var(--color-ink)}.concepts dd{margin:0;color:var(--color-neutral-700)}
@media(max-width:640px){.concepts div{grid-template-columns:1fr;gap:.2rem}}
.question{padding:.9rem 1.1rem;border-left:3px solid var(--color-accent);background:var(--color-surface)}
.question p{font-size:.9375rem;color:var(--color-neutral-800)}
.study{display:flex;flex-wrap:wrap;gap:.4rem}
.refs,.sources{margin:.4rem 0 0;padding:0;list-style:none}
.refs li,.sources li{padding:.35rem 0;font-size:.8125rem;line-height:1.6;color:var(--color-neutral-600)}
.refs a,.sources a{color:var(--color-neutral-800)}
.sources .meta{color:var(--color-neutral-500);font-size:.75rem;white-space:nowrap}
.others{columns:2 22rem;column-gap:2.5rem;margin:0;padding:0;list-style:none}
.others li{break-inside:avoid;padding:.55rem 0;border-bottom:1px solid var(--color-line);font-size:.875rem;line-height:1.6}
.others a{color:var(--color-neutral-800)}
.others .meta{display:block;font-size:.75rem;color:var(--color-neutral-500)}
.month{margin:0 0 2.5rem}
.month h2{margin:0 0 .75rem;font-size:1.125rem;font-weight:600;color:var(--color-ink)}
.day-row{display:grid;grid-template-columns:11rem 1fr;gap:1rem;padding:1rem 0;border-top:1px solid var(--color-line);text-decoration:none;color:inherit}
.day-row:hover .d{color:var(--color-accent)}
.day-row .d{font-weight:600;color:var(--color-ink);font-size:.9375rem}
.day-row .d small{display:block;margin-top:.3rem;font-weight:400;font-size:.75rem;color:var(--color-neutral-500)}
.day-row ul{margin:0;padding:0;list-style:none}
.day-row li{font-size:.875rem;line-height:1.7;color:var(--color-neutral-700)}
@media(max-width:640px){.day-row{grid-template-columns:1fr;gap:.4rem}}
"""


def load_days():
    days = {}
    for path in sorted(DAYS_DIR.glob("*.json")):
        record = read_json(path)
        if record:
            days[record["date"]] = record
    return days


def kst_time(value):
    if not value:
        return ""
    moment = datetime.fromisoformat(value).astimezone(KST)
    return f"{moment.month}/{moment.day} {moment:%H:%M}"


def source_list(clusters):
    rows = []
    for cluster in clusters:
        for item in cluster["items"][:4]:
            rows.append(
                f'<li><a class="link-underline" href="{esc(item["url"])}" rel="noopener" target="_blank">{esc(item["title"])}</a> '
                f'<span class="meta">· {esc(item["publisher"])}{" · " + kst_time(item["published"]) if item["published"] else ""}</span></li>'
            )
    return f'<ul class="sources">{"".join(rows)}</ul>'


def story_html(number, story, clusters_by_id, library):
    clusters = [clusters_by_id[i] for i in story["source_ids"] if i in clusters_by_id]
    tags = [f'<span class="tag region">{esc(story["region"])}</span>', f'<span class="tag">{esc(story["category"])}</span>']
    if story.get("importance") == 3:
        tags.insert(0, '<span class="tag key">주요</span>')
    concepts = "".join(
        f'<div><dt>{esc(c["term"])}</dt><dd>{esc(c["explain"])}</dd></div>' for c in story.get("concepts", [])
    )
    study = "".join(f'<span class="tag">{esc(s)}</span>' for s in story.get("study", []))
    refs = "".join(
        f'<li><a class="link-underline" href="{esc(library[r]["url"])}" rel="noopener" target="_blank">{esc(library[r]["name"])}</a>'
        f' · {esc(library[r]["about"])}</li>'
        for r in story.get("reference_ids", []) if r in library
    )
    parts = [
        f'<article class="story" data-region="{esc(story["region"])}" data-category="{esc(story["category"])}">',
        f'<div class="story-top"><span class="num">{number:02d}</span>{"".join(tags)}</div>',
        f'<h2>{esc(story["headline"])}</h2>',
        f'<h3>무슨 일이 있었나</h3><p>{esc(story["summary"])}</p>',
        f'<h3>기술 배경</h3><p>{esc(story["background"])}</p>' if story.get("background") else "",
        f'<h3>공학도에게 왜 중요한가</h3><p>{esc(story["why_it_matters"])}</p>',
    ]
    if concepts:
        parts.append(f'<h3>개념 풀이</h3><dl class="concepts">{concepts}</dl>')
    if story.get("question"):
        parts.append(f'<h3>생각해 볼 질문</h3><div class="question"><p>{esc(story["question"])}</p></div>')
    if study or refs:
        parts.append("<h3>더 공부하기</h3>")
        if study:
            parts.append(f'<div class="study">{study}</div>')
        if refs:
            parts.append(f'<ul class="refs">{refs}</ul>')
    parts.append(f"<h3>원문 기사</h3>{source_list(clusters)}</article>")
    return "".join(parts)


def day_nav(current, dates, prefix):
    """← [date picker] →. Arrows stay in place and dim at either end; keyboard ←/→ does the same."""
    index = dates.index(current)
    prev_day = dates[index - 1] if index > 0 else None
    next_day = dates[index + 1] if index + 1 < len(dates) else None

    def arrow(day, symbol, rel, word):
        if not day:
            return f'<span class="step" aria-disabled="true" title="{word} 브리핑 없음">{symbol}</span>'
        d = date.fromisoformat(day)
        label = f"{word} 날 ({d.month}월 {d.day}일)"
        return (f'<a class="step" id="day-{rel}" href="{prefix}days/{day}.html" rel="{rel}" '
                f'title="{label}" aria-label="{label}">{symbol}</a>')

    script = (
        "(function(){var dates=%s,p=document.getElementById('day-picker'),m=document.getElementById('day-msg');"
        "if(!p)return;p.addEventListener('change',function(){var v=p.value;if(!v)return;"
        "if(dates.indexOf(v)>=0){location.href=%s+'days/'+v+'.html';return;}"
        "var earlier=dates.filter(function(d){return d<v;}).pop();m.hidden=false;"
        "m.innerHTML='그날은 브리핑이 없습니다.'+(earlier?' 가장 가까운 이전 날짜: <a href=\"'+%s+'days/'+earlier+'.html\">'+earlier+'</a>':'');});"
        "document.addEventListener('keydown',function(e){var t=e.target.tagName;"
        "if(e.altKey||e.ctrlKey||e.metaKey||t==='INPUT'||t==='TEXTAREA'||t==='SELECT')return;"
        "var a=e.key==='ArrowLeft'?document.getElementById('day-prev'):e.key==='ArrowRight'?document.getElementById('day-next'):null;"
        "if(a)location.href=a.href;});})();"
        % (json.dumps(dates), json.dumps(prefix), json.dumps(prefix))
    )
    return (
        f'<nav class="day-nav" aria-label="날짜 이동"><span class="stepper">{arrow(prev_day, "←", "prev", "이전")}'
        f'<input type="date" id="day-picker" aria-label="날짜 선택" value="{current}" min="{dates[0]}" max="{dates[-1]}">'
        f'{arrow(next_day, "→", "next", "다음")}</span><span class="spacer"></span><a href="{prefix}archive.html">전체 날짜 목록</a>'
        f'<p class="day-msg" id="day-msg" role="status" hidden></p></nav><script>{script}</script>'
    )


def filter_bar(stories):
    regions = [r for r in ("국내", "해외") if any(s["region"] == r for s in stories)]
    categories = list(dict.fromkeys(s["category"] for s in stories))
    if len(stories) < 3:
        return ""
    chips = ['<button type="button" class="chip" aria-pressed="true" data-f="all">전체</button>']
    chips += [f'<button type="button" class="chip" aria-pressed="false" data-f="region:{esc(r)}">{esc(r)}</button>' for r in regions]
    chips += [f'<button type="button" class="chip" aria-pressed="false" data-f="category:{esc(c)}">{esc(c)}</button>' for c in categories]
    script = (
        "(function(){var bs=document.querySelectorAll('.filters .chip'),ss=document.querySelectorAll('.story');"
        "bs.forEach(function(b){b.addEventListener('click',function(){var f=b.dataset.f;"
        "bs.forEach(function(x){x.setAttribute('aria-pressed',x===b?'true':'false')});"
        "ss.forEach(function(s){if(f==='all'){s.hidden=false;return;}var k=f.split(':');"
        "s.hidden=s.dataset[k[0]]!==k.slice(1).join(':');});});});})();"
    )
    return f'<div class="filters" role="group" aria-label="뉴스 거르기">{"".join(chips)}</div><script>{script}</script>'


def engine_notice(record):
    engine = record.get("engine", {}).get("engine")
    if engine not in ("pending", "failed") or not record.get("sources"):
        return ""
    if engine == "pending":
        return '<p class="notice">오늘의 해설을 준비하고 있습니다. 우선 수집한 기사 제목만 싣고, 해설은 오전 중에 추가됩니다.</p>'
    return '<p class="notice">오늘은 AI 해설을 만들지 못해 수집한 기사 제목만 싣습니다.</p>'


def render_day(record, dates, prefix, canonical=""):
    day = date.fromisoformat(record["date"])
    library = {r["id"]: r for r in SETTINGS["reference_library"]}
    clusters = record.get("sources", [])
    by_id = {c["id"]: c for c in clusters}
    stories = record.get("stories", [])
    used = {i for s in stories for i in s["source_ids"]}
    others = [c for c in clusters if c["id"] not in used][: SETTINGS["other_headlines_limit"]]
    n_articles = sum(len(c["items"]) for c in clusters)
    publishers = {i["publisher"] for c in clusters for i in c["items"]}

    lead = esc(record.get("overview")) if record.get("overview") else (
        "원자력공학을 배우는 학생을 위해 국내외 원자력 뉴스를 매일 아침 골라, 무슨 일이 있었는지와 공학적으로 왜 중요한지를 쉬운 말로 정리합니다."
    )
    body = [day_nav(record["date"], dates, prefix), engine_notice(record)]
    body.append(
        '<div class="stats">'
        f'<div><strong>{len(stories)}</strong><span>오늘의 해설 뉴스</span></div>'
        f'<div><strong>{n_articles}</strong><span>살펴본 기사</span></div>'
        f'<div><strong>{len(publishers)}</strong><span>매체·기관</span></div></div>'
    )
    if stories:
        body.append('<section class="section" style="padding-top:2.5rem;border-top:0">')
        body.append(filter_bar(stories))
        body.extend(story_html(n, s, by_id, library) for n, s in enumerate(stories, 1))
        body.append("</section>")
    if others:
        items = "".join(
            f'<li><a class="link-underline" href="{esc(c["items"][0]["url"])}" rel="noopener" target="_blank">{esc(c["items"][0]["title"])}</a>'
            f'<span class="meta">{esc(c["region"])} · {esc(c["items"][0]["publisher"])}'
            f'{" 외 " + str(len(c["items"]) - 1) + "곳" if len(c["items"]) > 1 else ""}</span></li>'
            for c in others
        )
        title = "그 밖의 기사" if stories else "수집한 기사"
        body.append(f'<section class="section"><div class="sec-side" style="margin-bottom:1.25rem"><p class="eyebrow eyebrow-mark">Headlines</p>'
                    f'<h2>{title}</h2><p class="note">해설 없이 제목과 링크만 모았습니다.</p></div><ul class="others">{items}</ul></section>')
    if not clusters:
        body.append('<p class="notice">이 날은 조건에 맞는 새 기사를 찾지 못했습니다.</p>')

    canonical_tag = f'<link rel="canonical" href="{esc(canonical)}">' if canonical else ""
    title = f"원자력 뉴스 브리핑 {record['date']} | {SITE['title']}"
    root = prefix + "../"
    return (
        f'<!doctype html><html lang="ko"><head>{head(title, "원자력공학도를 위한 국내외 원자력 뉴스 해설 " + record["date"], NEWS_CSS, root)}'
        f'{canonical_tag}</head><body>'
        f'{site_header("news", root)}'
        f'{page_header("Nuclear News Brief · " + esc(date_label(day)), "오늘의 원자력 뉴스", lead)}'
        f'<main class="page"><div class="container-page">{"".join(body)}</div></main>{site_footer("news", root, credit=bool(canonical))}</body></html>'
    )


def render_archive(days):
    dates = sorted(days, reverse=True)
    months = {}
    for d in dates:
        months.setdefault(d[:7], []).append(d)
    blocks = []
    for month, month_dates in months.items():
        rows = []
        for d in month_dates:
            record = days[d]
            stories = record.get("stories", [])
            heads = "".join(f"<li>{esc(s['headline'])}</li>" for s in stories[:3]) or "<li>해설 없이 제목만 수집한 날</li>"
            count = f"해설 {len(stories)}건" if stories else f"기사 {sum(len(c['items']) for c in record.get('sources', []))}건"
            rows.append(f'<a class="day-row" href="days/{d}.html"><span class="d">{esc(date_label(date.fromisoformat(d)))}'
                        f"<small>{count}</small></span><ul>{heads}</ul></a>")
        y, m = month.split("-")
        blocks.append(f'<section class="month"><h2>{int(y)}년 {int(m)}월</h2>{"".join(rows)}</section>')
    body = "".join(blocks) or '<p class="notice">아직 쌓인 브리핑이 없습니다.</p>'
    return (
        f'<!doctype html><html lang="ko"><head>{head(f"날짜별 모아보기 | 원자력 뉴스 브리핑 | {SITE['title']}", "지난 원자력 뉴스 브리핑 전체 목록", NEWS_CSS, "../")}'
        f'</head><body>{site_header("news-archive", "../")}'
        f'{page_header("Archive", "날짜별 모아보기", f"지금까지 쌓인 브리핑 {len(dates)}일치입니다. 날짜를 누르면 그날의 해설로 갑니다.")}'
        f'<main class="page"><div class="container-page">{body}</div></main>{site_footer("news", "../")}</body></html>'
    )


def build_site():
    days = load_days()
    dates = sorted(days)
    (SITE_DIR / "days").mkdir(parents=True, exist_ok=True)
    for d in dates:
        (SITE_DIR / "days" / f"{d}.html").write_text(render_day(days[d], dates, "../"), encoding="utf-8")
    if dates:
        latest = dates[-1]
        canonical = f"{SETTINGS['site_url']}days/{latest}.html"
        (SITE_DIR / "index.html").write_text(render_day(days[latest], dates, "./", canonical), encoding="utf-8")
    archive = render_archive(days)
    (SITE_DIR / "archive.html").write_text(archive, encoding="utf-8")
    if not dates:  # before the first run the site root still needs a page
        (SITE_DIR / "index.html").write_text(archive, encoding="utf-8")
    write_json(SITE_DIR / "dates.json", dates)
    return len(dates)


if __name__ == "__main__":
    print(build_site())
