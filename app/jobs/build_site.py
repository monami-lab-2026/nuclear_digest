"""Render docs/jobs/index.html (원자력 취업) and the small jobs panel on the home page.

    python -m app.jobs.build_site
"""
import json
from collections import Counter
from datetime import date, timedelta

from ..config import DOCS_DIR, SITE
from ..site_theme import esc, head, page_header, site_footer, site_header
from .collect import HISTORY_PATH, LATEST_RUN_PATH, NEWS_PATH, OTHER_GROUP, SETTINGS, read_json

SITE_DIR = DOCS_DIR / "jobs"
WEEKDAYS_KO = "월화수목금토일"
HIRE_FILTERS = ["정규직", "무기계약직", "비정규직", "청년인턴"]

JOBS_CSS = """
.stats.four{grid-template-columns:repeat(4,minmax(0,1fr))}
@media(max-width:700px){.stats.four{grid-template-columns:repeat(2,minmax(0,1fr))}}
.notice{margin:0 0 1.5rem;padding:.9rem 1.1rem;border-left:3px solid var(--color-accent);background:var(--color-accent-soft);font-size:.875rem;line-height:1.75;color:var(--color-neutral-800)}
.notice a{color:inherit}
.filters{display:flex;flex-wrap:wrap;gap:.5rem;margin:0 0 .75rem}
.filters .label{width:100%;font-size:.6875rem;letter-spacing:.12em;color:var(--color-neutral-500);margin:.25rem 0 0}
.search{width:100%;margin:.5rem 0 1rem;padding:.7rem .9rem;border:1px solid var(--color-line-strong);background:var(--color-card);color:var(--color-neutral-900);font:inherit;font-size:.9375rem}
.search:focus{outline:2px solid var(--color-accent);outline-offset:-1px}
.job-count{font-size:.8125rem;color:var(--color-neutral-500);margin:0 0 .5rem}
.jobs{border-top:1px solid var(--color-line-strong)}
.job{display:grid;grid-template-columns:4.75rem minmax(0,1fr);gap:1rem;padding:1.1rem 0;border-bottom:1px solid var(--color-line)}
.job[hidden]{display:none}
.job.closed{opacity:.5}
.dday{align-self:start;text-align:center;border:1px solid var(--color-line-strong);padding:.5rem .25rem .45rem}
.dday b{display:block;font-size:1.0625rem;line-height:1.1;font-weight:700;color:var(--color-ink);font-variant-numeric:tabular-nums}
.dday small{display:block;margin-top:.3rem;font-size:.6875rem;color:var(--color-neutral-500);font-variant-numeric:tabular-nums}
.dday.soon{border-color:var(--color-accent);background:var(--color-accent-soft)}
.dday.soon b{color:var(--color-accent)}
.job .inst{margin:0;font-size:.75rem;color:var(--color-neutral-500)}
.job .inst b{font-weight:600;color:var(--color-neutral-700)}
.job .new{display:inline-block;margin-left:.4rem;padding:.1rem .4rem;border-radius:999px;background:var(--color-accent);color:var(--color-canvas);font-size:.625rem;font-weight:700;letter-spacing:.04em;vertical-align:.1em}
.job h3{margin:.3rem 0 .35rem;font-size:1rem;line-height:1.5;font-weight:600}
.job h3 a{color:var(--color-ink);text-decoration:none}
.job h3 a:hover{color:var(--color-accent)}
.job .meta{margin:0;font-size:.8125rem;line-height:1.7;color:var(--color-neutral-600)}
.job .meta a{color:var(--color-neutral-700)}
.empty{padding:2rem 0;color:var(--color-neutral-500);font-size:.875rem}
.chart-block{margin:0 0 2rem}
.chart-block h3{margin:0 0 .75rem;font-size:.9375rem;font-weight:600;color:var(--color-ink)}
.cols{display:flex;gap:.35rem;height:10rem;align-items:flex-end;border-bottom:1px solid var(--color-line-strong)}
.col{flex:1;min-width:0;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;height:100%}
.col i{display:block;width:100%;background:var(--chart);min-height:1px}
.col.now i{background:var(--color-accent-mid)}
.col span{font-size:.6875rem;font-weight:600;color:var(--color-ink);font-variant-numeric:tabular-nums;margin-bottom:.2rem}
.col-labels{display:flex;gap:.35rem;margin-top:.35rem}
.col-labels span{flex:1;min-width:0;text-align:center;font-size:.625rem;color:var(--color-neutral-500);font-variant-numeric:tabular-nums;overflow:hidden}
.bar-row{display:grid;grid-template-columns:11rem 1fr 2.25rem;gap:.75rem;align-items:center;padding:.45rem 0;border-bottom:1px solid var(--color-line);font-size:.8125rem;color:var(--color-neutral-700)}
.bar-row strong{text-align:right;font-weight:600;color:var(--color-ink);font-variant-numeric:tabular-nums}
.bar-track{height:.5rem;background:var(--color-surface-deep)}.bar-fill{height:100%;background:var(--chart)}
@media(max-width:700px){.bar-row{grid-template-columns:7.5rem 1fr 2rem}.col-labels span:nth-child(even){visibility:hidden}}
.news-cols{display:grid;gap:2rem;grid-template-columns:minmax(0,1fr)}
@media(min-width:900px){.news-cols{grid-template-columns:1fr 1fr}}
.news-cols h3{margin:0 0 .5rem;font-size:.875rem;font-weight:600;color:var(--color-neutral-600)}
.news-list{margin:0;padding:0;list-style:none;border-top:1px solid var(--color-line)}
.news-list li{padding:.75rem 0;border-bottom:1px solid var(--color-line)}
.news-list a{font-size:.9375rem;line-height:1.55;font-weight:500;color:var(--color-ink);text-decoration:none}
.news-list a:hover{color:var(--color-accent)}
.news-list small{display:block;margin-top:.2rem;font-size:.75rem;color:var(--color-neutral-500)}
.link-groups{display:grid;gap:1px;border:1px solid var(--color-line);background:var(--color-line);grid-template-columns:minmax(0,1fr)}
@media(min-width:900px){.link-groups{grid-template-columns:1fr 1fr}}
.link-group{background:var(--color-card);padding:1.4rem 1.4rem 1rem}
.link-group h3{margin:0 0 .5rem;font-size:1rem;font-weight:600;color:var(--color-ink)}
.link-group ul{margin:0;padding:0;list-style:none}
.link-group li{padding:.55rem 0;border-top:1px solid var(--color-line)}
.link-group a{font-size:.875rem;font-weight:500;color:var(--color-ink);text-decoration:none}
.link-group a:hover{color:var(--color-accent)}
.link-group a::after{content:" ↗";color:var(--color-neutral-400);font-size:.75rem}
.link-group small{display:block;margin-top:.15rem;font-size:.75rem;color:var(--color-neutral-500)}
"""

FILTER_JS = """
(function(){
var jobs=[].slice.call(document.querySelectorAll('.job')),q=document.getElementById('job-q'),out=document.getElementById('job-count');
var state={group:'',hire:''};
var today=new Date();today.setHours(0,0,0,0);
jobs.forEach(function(j){var e=j.dataset.end,b=j.querySelector('.dday b'),box=j.querySelector('.dday');if(!e){b.textContent='상시';return}
  var d=new Date(e+'T00:00:00'),n=Math.round((d-today)/864e5);
  if(n<0){b.textContent='마감';j.classList.add('closed');j.dataset.closed='1'}else if(n===0){b.textContent='오늘';box.classList.add('soon')}
  else{b.textContent='D-'+n;if(n<=7)box.classList.add('soon')}});
function apply(){var t=(q.value||'').trim().toLowerCase(),shown=0;
  jobs.forEach(function(j){var ok=(!state.group||j.dataset.group===state.group)&&(!state.hire||j.dataset.hire.indexOf(state.hire)>=0)&&(!t||j.dataset.text.indexOf(t)>=0)&&!j.dataset.closed;
    j.hidden=!ok;if(ok)shown++});
  out.textContent=shown+'건 표시';}
[].forEach.call(document.querySelectorAll('[data-filter]'),function(btn){btn.addEventListener('click',function(){
  var k=btn.dataset.filter;state[k]=btn.dataset.value;
  [].forEach.call(document.querySelectorAll('[data-filter="'+k+'"]'),function(o){o.setAttribute('aria-pressed',o===btn?'true':'false')});apply()})});
if(q)q.addEventListener('input',apply);apply();
})();
"""


def short(iso):
    if not iso:
        return ""
    d = date.fromisoformat(iso)
    return f"{d.month}/{d.day}"


def load():
    history = read_json(HISTORY_PATH, {}) or {}
    news = read_json(NEWS_PATH, {}) or {}
    status = read_json(LATEST_RUN_PATH, {}) or {}
    return history, news, status


def open_postings(history, today):
    iso = today.isoformat()
    items = [r for r in history.values() if r.get("open") and (not r.get("end") or r["end"] >= iso)]
    return sorted(items, key=lambda r: (r.get("end") or "9999", r.get("inst", ""), r.get("title", "")))


def summary(history, today):
    opened = open_postings(history, today)
    week_ago = (today - timedelta(days=7)).isoformat()
    soon = (today + timedelta(days=7)).isoformat()
    return {
        "open": opened,
        "new_week": [r for r in history.values() if (r.get("start") or r.get("first_seen") or "") >= week_ago],
        "closing": [r for r in opened if r.get("end") and r["end"] <= soon],
        "insts": sorted({r["inst"] for r in opened}),
    }


def job_card(record, today):
    hire = " · ".join(record.get("hire") or [])
    region = ", ".join((record.get("region") or [])[:3]) + (" 외" if len(record.get("region") or []) > 3 else "")
    period = f'{short(record.get("start"))}~{short(record.get("end"))}' if record.get("end") else f'{short(record.get("start"))}~'
    meta = [x for x in (hire, record.get("kind"), region, f"접수 {period}") if x]
    if record.get("count"):
        meta.insert(0, f'{record["count"]}명')
    src = f' · <a class="link-underline" href="{esc(record["src"])}" target="_blank" rel="noopener">기관 공고</a>' if record.get("src", "").startswith("http") else ""
    new = '<span class="new">NEW</span>' if (record.get("first_seen") or "") >= (today - timedelta(days=7)).isoformat() else ""
    text = " ".join([record["inst"], record["title"], hire, record.get("kind", ""), region]).lower()
    return (f'<article class="job" data-group="{esc(record["group"])}" data-hire="{esc(hire)}" data-end="{esc(record.get("end") or "")}" '
            f'data-text="{esc(text)}"><div class="dday"><b>&nbsp;</b><small>{esc(short(record.get("end")) or "-")}</small></div>'
            f'<div><p class="inst"><b>{esc(record["inst"])}</b> · {esc(record["group"])}{new}</p>'
            f'<h3><a href="{esc(record["url"])}" target="_blank" rel="noopener">{esc(record["title"])}</a></h3>'
            f'<p class="meta">{esc(" · ".join(meta))}{src}</p></div></article>')


def chip(kind, value, label, count=None, pressed=False):
    num = f" <strong>{count}</strong>" if count is not None else ""
    return (f'<button type="button" class="chip" data-filter="{kind}" data-value="{esc(value)}" '
            f'aria-pressed="{"true" if pressed else "false"}">{esc(label)}{num}</button>')


def open_section(history, today, status):
    opened = open_postings(history, today)
    notice = ""
    alio = status.get("alio")
    if alio == "no_key" and not history:
        notice = ('<p class="notice">공공기관 공고 자동 수집은 <b>공공데이터포털 인증키</b>를 저장소에 등록하면 시작됩니다 '
                  '(<code>DATA_GO_KR_KEY</code>). 그 전까지는 <a class="link-underline" href="https://job.alio.go.kr" target="_blank" rel="noopener">잡알리오</a>에서 직접 확인하세요.</p>')
    elif alio == "error":
        notice = f'<p class="notice">오늘 공고 수집에 실패해 마지막으로 받은 목록({esc(status.get("alio_date", ""))})을 보여 줍니다.</p>'
    groups = Counter(r["group"] for r in opened)
    order = [g["group"] for g in SETTINGS["institutions"]] + [OTHER_GROUP]
    group_chips = chip("group", "", "전체", len(opened), True) + "".join(
        chip("group", g, g, groups[g]) for g in order if groups.get(g))
    hire_chips = chip("hire", "", "전체", pressed=True) + "".join(
        chip("hire", h, h, sum(1 for r in opened if any(h in x for x in r.get("hire") or []))) for h in HIRE_FILTERS)
    cards = "".join(job_card(r, today) for r in opened)
    body = (f'{notice}<div class="filters"><p class="label">기관</p>{group_chips}</div>'
            f'<div class="filters"><p class="label">고용 형태</p>{hire_chips}</div>'
            '<input id="job-q" class="search" type="search" placeholder="기관·제목·지역 검색 (예: 연구직, 경주, 기계)" aria-label="공고 검색">'
            f'<p class="job-count" id="job-count"></p>'
            f'<div class="jobs">{cards or "<p class=empty>지금 접수 중인 원자력 공공기관 공고가 없습니다.</p>"}</div>')
    return ('<section class="section" id="open"><div class="sec-grid"><div class="sec-side"><p class="eyebrow eyebrow-mark">Open now</p>'
            '<h2>지금 열린 공고</h2><p class="note">원자력 공공기관(한수원·한전기술·한전KPS·원자력연구원·KINS 등)과 제목에 원자력·방사선·핵융합이 들어간 공공기관 공고입니다. '
            '마감이 가까운 순서이며, 제목을 누르면 잡알리오 원문이 열립니다.</p>'
            '<p class="note">민간 기업·해외·대학원 공고는 아래 <a class="link-underline" href="#links">바로 가기</a>에서 찾아보세요.</p></div>'
            f'<div class="sec-body">{body}</div></div></section>')


def weekly_counts(history, today, weeks=12):
    monday = today - timedelta(days=today.weekday())
    starts = [monday - timedelta(weeks=i) for i in range(weeks - 1, -1, -1)]
    counts = Counter()
    for r in history.values():
        day = r.get("start") or r.get("first_seen")
        if not day:
            continue
        d = date.fromisoformat(day)
        wk = d - timedelta(days=d.weekday())
        counts[wk] += 1
    return [(s, counts.get(s, 0)) for s in starts]


def bars(rows):
    top = max((n for _, n in rows), default=0) or 1
    return "".join(f'<div class="bar-row"><span>{esc(name)}</span><div class="bar-track"><div class="bar-fill" style="width:{n / top * 100:.1f}%"></div></div>'
                   f'<strong>{n}</strong></div>' for name, n in rows)


def trend_section(history, today):
    if not history:
        return ""
    weeks = weekly_counts(history, today)
    top = max(n for _, n in weeks) or 1
    cols = "".join(f'<div class="col{" now" if i == len(weeks) - 1 else ""}"><span>{n or ""}</span><i style="height:{n / top * 85:.1f}%"></i></div>'
                   for i, (_, n) in enumerate(weeks))
    labels = "".join(f"<span>{s.month}/{s.day}</span>" for s, _ in weeks)
    opened = open_postings(history, today)
    by_inst = Counter(r["inst"] for r in opened).most_common(10)
    since = (today - timedelta(days=90)).isoformat()
    recent = [r for r in history.values() if (r.get("start") or r.get("first_seen") or "") >= since]
    by_hire = Counter(h for r in recent for h in (r.get("hire") or ["미기재"])).most_common(6)
    by_group = Counter(r["group"] for r in recent).most_common()
    first = min((r.get("first_seen") for r in history.values() if r.get("first_seen")), default="")
    blocks = [f'<div class="chart-block"><h3>주별 새 공고 (공고 시작일 기준, 최근 12주)</h3><div class="cols">{cols}</div>'
              f'<div class="col-labels">{labels}</div></div>']
    if by_inst:
        blocks.append(f'<div class="chart-block"><h3>기관별 접수 중 공고</h3>{bars(by_inst)}</div>')
    if by_group:
        blocks.append(f'<div class="chart-block"><h3>분야별 공고 (최근 90일)</h3>{bars(by_group)}</div>')
    if by_hire:
        blocks.append(f'<div class="chart-block"><h3>고용 형태 (최근 90일, 공고 하나에 여러 형태 가능)</h3>{bars(by_hire)}</div>')
    note = f"매주 수집한 기록이 쌓일수록 정확해집니다. 기록 시작: {esc(first)}." if first else ""
    return ('<section class="section" id="trend"><div class="sec-grid"><div class="sec-side"><p class="eyebrow eyebrow-mark">Trend</p>'
            f'<h2>채용 동향</h2><p class="note">원자력 공공기관 공고 수의 흐름입니다. 상·하반기 공채 시즌(대개 3~5월, 8~10월)에 몰립니다. {note}</p></div>'
            f'<div class="sec-body">{"".join(blocks)}</div></div></section>')


def news_section(news):
    items = news.get("items") or []
    if not items:
        return ""
    limit = SETTINGS["news"]["limit"]

    def column(region, title):
        rows = [i for i in items if (i.get("region") == "국내") == (region == "국내")][: limit // 2 + 2]
        if not rows:
            return ""
        lis = "".join(f'<li><a href="{esc(i["url"])}" target="_blank" rel="noopener">{esc(i["title"])}</a>'
                      f'<small>{esc(i["publisher"])} · {esc((i.get("published") or "")[:10])}</small></li>' for i in rows)
        return f'<div><h3>{title}</h3><ul class="news-list">{lis}</ul></div>'

    return ('<section class="section" id="news"><div class="sec-grid"><div class="sec-side"><p class="eyebrow eyebrow-mark">News</p>'
            f'<h2>채용·인력 뉴스</h2><p class="note">최근 {SETTINGS["news"]["lookback_days"]}일 원자력 채용·인력 관련 기사 제목입니다. 본문은 각 언론사에서 보세요.</p></div>'
            f'<div class="sec-body"><div class="news-cols">{column("국내", "국내")}{column("해외", "해외")}</div></div></div></section>')


def links_section():
    groups = "".join(
        f'<div class="link-group"><h3>{esc(g["group"])}</h3><ul>'
        + "".join(f'<li><a href="{esc(i["url"])}" target="_blank" rel="noopener">{esc(i["name"])}</a><small>{esc(i.get("note", ""))}</small></li>'
                  for i in g["items"])
        + "</ul></div>" for g in SETTINGS["links"])
    return ('<section class="section" id="links"><div style="margin-bottom:1.25rem"><p class="eyebrow eyebrow-mark">Directory</p>'
            '<h2 style="margin:1rem 0 0;font-size:1.375rem;font-weight:600;color:var(--color-ink)">바로 가기 · 기관 채용 링크</h2>'
            '<p class="caption">민간 기업·해외·대학원 공고는 공개 수집 경로가 없어 각 채용 페이지로 연결합니다. 목록은 config/jobs.json에서 고칠 수 있습니다.</p></div>'
            f'<div class="link-groups">{groups}</div></section>')


def build_site(today=None):
    today = today or date.today()
    history, news, status = load()
    s = summary(history, today)
    updated = status.get("run_date") or today.isoformat()
    lead = ("원자력 공공기관 공고는 매주 월요일 아침 잡알리오(공공데이터포털)에서 자동으로 모으고, "
            "민간 기업·해외·대학원·박사후 정보는 바로 가기로 정리했습니다. "
            f"<b>마지막 갱신 {esc(updated)}</b>")
    stats = ('<div class="stats four">'
             f'<div><strong>{len(s["open"])}</strong><span>지금 접수 중</span></div>'
             f'<div><strong>{len(s["new_week"])}</strong><span>최근 7일 새 공고</span></div>'
             f'<div><strong>{len(s["closing"])}</strong><span>7일 안에 마감</span></div>'
             f'<div><strong>{len(s["insts"])}</strong><span>채용 중인 기관</span></div></div>')
    body = (f'<section class="section">{stats}</section>{open_section(history, today, status)}'
            f'{trend_section(history, today)}{news_section(news)}{links_section()}')
    page = (f'<!doctype html><html lang="ko"><head>{head("원자력 취업 · " + SITE["title"], "원자력 공공기관 채용 공고, 채용 동향, 관련 뉴스, 기관 채용 링크", JOBS_CSS, "../")}'
            f'</head><body>{site_header("jobs", "../")}{page_header("Careers · 원자력 취업", "원자력 취업 시장", lead)}'
            f'<main class="page"><div class="container-page">{body}</div></main>{site_footer("jobs", "../", credit=True)}'
            f'<script>{FILTER_JS}</script></body></html>')
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    path = SITE_DIR / "index.html"
    path.write_text(page, encoding="utf-8")
    return path


def home_panel(today=None):
    """Full-width strip for the home page: counts + the three nearest deadlines."""
    today = today or date.today()
    history, _, _ = load()
    s = summary(history, today)
    head_html = ('<article class="panel"><p class="eyebrow eyebrow-mark eyebrow-accent">Careers · Jobs</p>'
                 '<h2>원자력 취업</h2>')
    if not history:
        return (head_html + '<p class="notice">공공기관 공고 자동 수집을 준비하고 있습니다. 기관별 채용 링크는 바로 볼 수 있습니다.</p>'
                '<div class="more"><a class="primary" href="jobs/index.html">취업 정보 보기</a></div></article>')
    soon = s["open"][:3]
    items = "".join(
        f'<li><div><a href="{esc(r["url"])}" target="_blank" rel="noopener">{esc(r["title"])}</a>'
        f'<small>{esc(r["inst"])} · 마감 {esc(short(r.get("end")) or "상시")}</small></div></li>' for r in soon)
    return (head_html + '<div class="mini-stats">'
            f'<div><strong>{len(s["open"])}</strong><span>지금 접수 중</span></div>'
            f'<div><strong>{len(s["new_week"])}</strong><span>최근 7일 새 공고</span></div>'
            f'<div><strong>{len(s["closing"])}</strong><span>7일 안에 마감</span></div></div>'
            + (f'<ol class="heads">{items}</ol>' if items else "")
            + '<div class="more"><a class="primary" href="jobs/index.html">공고 전체 보기</a><a href="jobs/index.html#links">기관 채용 링크</a></div></article>')


if __name__ == "__main__":
    print(build_site())
