"""Cumulative database page (docs/database.html): every stored paper, searchable and filterable.

Static single file: paper data is embedded as JSON and filtered in the browser (no external libraries).
"""
import html
import json
from collections import Counter, defaultdict
from datetime import date, timedelta

from .. import site_theme
from .common import SETTINGS, watchlists_for

def week_of(value):
    day = date.fromisoformat(value[:10])
    return (day - timedelta(days=day.weekday())).isoformat()


def render(payload, archive_ids):
    papers = payload["papers"]
    topics_by_doi = defaultdict(list)
    for link in payload["paper_topics"]:
        topics_by_doi[link["doi"]].append(link["topic_ko"])
    rows = []
    for p in papers:
        registered = p.get("doi_registered_date") or ""
        rows.append({
            "d": p["doi"], "t": p["title_en"], "k": p.get("title_ko") or "", "j": p["journal"],
            "a": p.get("authors") or "", "r": registered, "w": week_of(registered) if registered else "",
            "p": p["primary_topic"], "tp": topics_by_doi.get(p["doi"], [p["primary_topic"]]),
            "c": [c for c in (p.get("countries") or "").split(";") if c], "o": int(bool(p.get("open_access"))),
            "y": p["document_type"], "ab": p.get("abstract") or "",
            # interest areas (config/site.json "interests"), same rule as the weekly tracker: keyword in title or abstract
            "iw": watchlists_for({"title": p["title_en"], "abstract": p.get("abstract") or ""}),
        })

    weeks = sorted({r["w"] for r in rows if r["w"]})
    topic_order = list(SETTINGS["topics"]) + [SETTINGS["fallback_topic"]]
    journals = [j for j, _ in Counter(r["j"] for r in rows).most_common()]
    countries = [c for c, _ in Counter(c for r in rows for c in r["c"]).most_common()]
    first, last = (min(r["r"] for r in rows), max(r["r"] for r in rows)) if rows else ("", "")
    meta = {
        "weeks": weeks, "topics": topic_order, "journals": journals, "countries": countries,
        "countryNames": SETTINGS["country_names"], "archives": sorted(archive_ids, reverse=True),
        "interests": SETTINGS["watchlists"],
    }
    data_json = json.dumps({"rows": rows, "meta": meta}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    esc = lambda v: html.escape(str(v), quote=True)
    oa = sum(r["o"] for r in rows)
    with_abstract = sum(bool(r["ab"]) for r in rows)
    with_country = sum(bool(r["c"]) for r in rows)

    css = """
.filters{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.5rem;margin-bottom:.75rem}
@media(max-width:640px){.filters{grid-template-columns:1fr 1fr}}
.filters input,.filters select,.filters2 input[type=date],.filters2 select{width:100%;padding:.6rem .7rem;border:1px solid var(--color-line);border-radius:0;
  background:var(--color-card);color:var(--color-neutral-800);font:inherit;font-size:.8125rem}
.filters2{display:flex;flex-wrap:wrap;gap:.5rem .75rem;align-items:center;font-size:.8125rem;color:var(--color-neutral-600)}
.filters2 input[type=date]{width:auto}.filters2 select{width:auto}
.filters2 label{display:inline-flex;gap:.35rem;align-items:center}
.kw-label{margin:0 0 .6rem;font-size:.8125rem;color:var(--color-neutral-600)}
.kw-chips{display:flex;flex-wrap:wrap;gap:.45rem;margin:0 0 1.25rem}
.kw-chips .chip small{font-size:.6875rem;opacity:.75;font-variant-numeric:tabular-nums}
.kw-help{margin:.35rem 0 1.25rem;font-size:.75rem;color:var(--color-neutral-500)}
.kw-help[hidden]{display:none}
.qrow{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:.5rem;margin-bottom:.5rem}
.qrow input,.qrow select{padding:.6rem .7rem;border:1px solid var(--color-line);border-radius:0;background:var(--color-card);color:var(--color-neutral-800);font:inherit;font-size:.875rem}
.qrow input{font-size:.9375rem}
@media(max-width:640px){.qrow{grid-template-columns:1fr 1fr}.qrow input{grid-column:1/-1}}
mark{background:color-mix(in srgb,var(--color-accent) 22%,transparent);color:inherit;padding:0 .1em}
.date-head{margin:1.5rem 0 0;padding:.5rem 0;border-bottom:1px solid var(--color-line-strong);font-size:.8125rem;font-weight:600;color:var(--color-accent);font-variant-numeric:tabular-nums}
.date-head small{margin-left:.5rem;font-weight:400;color:var(--color-neutral-500)}
.status{margin:1rem 0 0;padding:.7rem 1rem;background:var(--color-accent-soft);border-left:3px solid var(--color-accent);font-size:.875rem;color:var(--color-neutral-800)}
.bars{display:flex;align-items:flex-end;gap:.4rem;height:12rem;padding-top:1.25rem;border-bottom:1px solid var(--color-line-strong)}
.bar{flex:1;min-width:.9rem;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;height:100%;cursor:pointer;border:0;background:none;padding:0;font:inherit}
.bar i{display:block;width:100%;max-width:2.4rem;background:var(--chart);border-radius:4px 4px 0 0;min-height:2px}
.bar b{font-size:.6875rem;font-weight:600;color:var(--color-ink);margin-bottom:.2rem;font-variant-numeric:tabular-nums}
.bar:hover i{background:var(--color-accent-mid)}.bar.on i{background:var(--color-accent)}
.xlabels{display:flex;gap:.4rem}.xlabels span{flex:1;min-width:.9rem;text-align:center;font-size:.625rem;color:var(--color-neutral-500);white-space:nowrap;overflow:hidden;padding-top:.3rem}
.heat-wrap{overflow-x:auto}table.heat{border-collapse:separate;border-spacing:2px;font-size:.75rem;width:100%}
.heat th{font-weight:500;color:var(--color-neutral-500);font-size:.6875rem;padding:.15rem .3rem;white-space:nowrap;font-variant-numeric:tabular-nums}
.heat th.row{text-align:left;color:var(--color-neutral-700);font-size:.75rem}
.heat td{text-align:center;padding:.4rem .15rem;cursor:pointer;min-width:2.2rem;color:var(--color-ink);font-variant-numeric:tabular-nums}
.heat td.hi{color:var(--color-canvas)}.heat td.z{color:var(--color-neutral-400);background:var(--color-surface)}
.heat td:hover{outline:2px solid var(--color-accent);outline-offset:-2px}
#list{border-top:1px solid var(--color-line-strong);margin-top:1rem}
.paper{padding:1.2rem 0;border-bottom:1px solid var(--color-line)}
.top{display:flex;flex-wrap:wrap;gap:.6rem;font-size:.75rem;color:var(--color-neutral-500);font-variant-numeric:tabular-nums}.top .jr{color:var(--color-neutral-700);font-weight:500}
.top .oa{color:var(--color-accent);font-weight:500}
.paper h3{margin:.4rem 0 .2rem;font-size:1rem;line-height:1.45;font-weight:600;letter-spacing:-.01em}.paper h3 a{color:var(--color-ink)}
.ko{color:var(--color-neutral-700);font-size:.9rem;line-height:1.6}.au{color:var(--color-neutral-500);font-size:.75rem;margin-top:.3rem;line-height:1.7}
.tags{margin-top:.5rem;display:flex;flex-wrap:wrap;gap:.35rem}
details{margin-top:.5rem;font-size:.875rem}summary{cursor:pointer;color:var(--color-accent);font-size:.75rem}
details p{margin:.5rem 0 0;line-height:1.9;color:var(--color-neutral-700);max-width:48rem}
.pager{display:flex;justify-content:center;align-items:center;gap:.75rem;margin:1.5rem 0 0;font-size:.8125rem;color:var(--color-neutral-600)}
.btn[disabled]{opacity:.4;cursor:default}
.archive{display:grid;grid-template-columns:repeat(auto-fill,minmax(9rem,1fr));gap:1px;border:1px solid var(--color-line);background:var(--color-line)}
.archive a{display:block;padding:.8rem 1rem;background:var(--color-card);color:var(--color-neutral-800);text-decoration:none;font-size:.875rem;font-variant-numeric:tabular-nums}
.archive a:hover{color:var(--color-accent)}
@media(max-width:760px){.filters{grid-template-columns:1fr 1fr}.filters input{grid-column:1/-1}}
"""
    stats = "".join(
        f"<div><strong>{value}</strong><span>{label}</span></div>"
        for value, label in [
            (len(rows), "누적 논문"), (len(payload["runs"]), "수집 회차"), (len(weeks), "주간 (DOI 등록일 기준)"),
            (with_abstract, "초록 보유"), (oa, "Open Access"), (f"{round(with_country / max(len(rows), 1) * 100)}%", "국가 정보 보유"),
        ]
    )
    return f"""<!doctype html>
<html lang="ko"><head>
{site_theme.head("원자력공학 문헌 누적 데이터베이스 · " + site_theme.SITE["title"], f"원자력공학 주요 {len(SETTINGS['journals'])}개 저널 누적 논문 데이터베이스 — 검색, 필터, 주간 추세", css, "../")}
</head><body>
{site_theme.site_header("database", "../")}
{site_theme.page_header("Literature Database", "원자력공학 문헌 누적 데이터베이스",
    f"<b>{len(journals)}개 저널 · DOI 등록일 {esc(first)} ~ {esc(last)}</b> · DOI 기준 중복 제거. 검색·필터 결과는 CSV로, 전체 DB는 Excel로 내려받을 수 있습니다.")}
<main class="page"><div class="container-page">
<section class="section"><div class="stats" style="grid-template-columns:repeat(auto-fit,minmax(9rem,1fr))">{stats}</div></section>

<section class="section sec-grid"><div class="sec-side"><p class="eyebrow">01</p><h2>주간 신규 논문 수</h2>
<p class="note">DOI 등록일이 속한 주(월요일 시작). 막대를 누르면 그 주 논문만 아래 목록에 남습니다.</p></div>
<div class="sec-body"><div class="bars" id="bars"></div><div class="xlabels" id="xlabels"></div></div></section>

<section class="section sec-grid"><div class="sec-side"><p class="eyebrow">02</p><h2>주간 토픽 분포</h2>
<p class="note">숫자는 논문 수, 색이 진할수록 그 주 전체에서 차지하는 비중이 큽니다. 한 논문이 여러 토픽에 해당하면 각각 집계됩니다. 칸을 누르면 해당 토픽·주간으로 필터합니다.</p></div>
<div class="sec-body"><div class="heat-wrap"><table class="heat" id="heat"></table></div></div></section>

<section class="section" id="search"><p class="eyebrow eyebrow-mark eyebrow-accent">Search</p>
<h2 style="margin:1rem 0 1.25rem;font-size:1.375rem;font-weight:600;letter-spacing:-.015em;color:var(--color-ink)">논문 검색</h2>
<p class="kw-label">관심 분야 키워드로 찾기 <small style="color:var(--color-neutral-500)">(config/site.json의 interests · 제목·초록 기준)</small></p>
<div class="kw-chips" id="kw" role="group" aria-label="관심 분야 키워드"></div>
<p class="kw-help" id="kwhelp" hidden></p>
<div class="qrow">
<input id="q" type="search" placeholder="키워드 검색 (여러 단어는 띄어쓰기, 구절은 &quot;따옴표&quot;)" aria-label="검색어">
<select id="qf" aria-label="검색 범위"><option value="all">전체</option><option value="title">제목(영/한)</option><option value="author">저자</option><option value="abstract">초록</option></select>
<select id="qm" aria-label="여러 단어"><option value="and">모두 포함</option><option value="or">하나라도 포함</option></select>
</div>
<div class="filters">
<select id="fj" aria-label="저널"><option value="">전체 저널</option></select>
<select id="ft" aria-label="토픽"><option value="">전체 토픽</option></select>
<select id="fc" aria-label="국가"><option value="">전체 국가</option></select>
<select id="fy" aria-label="문서 유형"><option value="">전체 문서유형</option></select>
</div>
<div class="filters2">DOI 등록일 <input type="date" id="d1" aria-label="시작일"> ~ <input type="date" id="d2" aria-label="종료일">
<label><input type="checkbox" id="fo"> Open Access만</label>
<label><input type="checkbox" id="fa"> 초록 있는 논문만</label>
<select id="sort" aria-label="정렬"><option value="new">날짜순 (최신 먼저)</option><option value="old">날짜순 (오래된 먼저)</option><option value="journal">저널순</option></select>
<button class="btn" id="reset" type="button">필터 초기화</button>
<button class="btn" id="csv" type="button">검색 결과 CSV</button></div>
<div class="status" id="status" aria-live="polite"></div>
<div id="list"></div>
<div class="pager"><button class="btn" id="prev" type="button">이전</button><span id="page" class="tabular"></span><button class="btn" id="next" type="button">다음</button></div>
</section>

<section class="section sec-grid"><div class="sec-side"><p class="eyebrow">Archive</p><h2>회차별 동향</h2>
<p class="note">매주 발행된 동향 페이지 원본입니다.</p></div><div class="sec-body"><div class="archive" id="archive"></div></div></section>
</div></main>
{site_theme.site_footer("papers", "../")}
<script id="data" type="application/json">{data_json}</script>
<script>
(() => {{
const D = JSON.parse(document.getElementById('data').textContent), R = D.rows, M = D.meta;
const $ = id => document.getElementById(id), PER = 50;
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
const cname = c => (M.countryNames[c] || c) + ' (' + c + ')';
const endOf = w => {{ const d = new Date(w + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() + 6); return d.toISOString().slice(0, 10); }};
let page = 0, weekSel = '', kwSel = '';
R.forEach(r => {{
  r.st = (r.t + ' ' + r.k).toLowerCase(); r.sa = r.a.toLowerCase(); r.sb = r.ab.toLowerCase();
  r.s = r.st + ' ' + r.sa + ' ' + r.sb + ' ' + r.d.toLowerCase();
}});
// Search terms: words split by spaces, "quoted phrases" kept whole.
const terms = () => [...$('q').value.toLowerCase().matchAll(/"([^"]+)"|(\\S+)/g)].map(m => (m[1] || m[2]).trim()).filter(Boolean);
const field = r => ({{title: r.st, author: r.sa, abstract: r.sb}})[$('qf').value] || r.s;
const reEsc = s => s.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&');
function hl(text, words) {{
  const safe = esc(text); if (!words.length) return safe;
  const re = new RegExp('(' + words.map(w => reEsc(esc(w))).sort((a, b) => b.length - a.length).join('|') + ')', 'gi');
  return safe.replace(re, '<mark>$1</mark>');
}}

// Interest-area keyword chips
const kwCount = {{}}; R.forEach(r => r.iw.forEach(n => kwCount[n] = (kwCount[n] || 0) + 1));
$('kw').innerHTML = Object.keys(M.interests).map(n => `<button type="button" class="chip" aria-pressed="false" data-kw="${{esc(n)}}" title="${{esc(M.interests[n].join(', '))}}">${{esc(n)}} <small>${{kwCount[n] || 0}}</small></button>`).join('');
$('kw').addEventListener('click', e => {{
  const b = e.target.closest('.chip'); if (!b) return;
  kwSel = kwSel === b.dataset.kw ? '' : b.dataset.kw;
  document.querySelectorAll('#kw .chip').forEach(x => x.setAttribute('aria-pressed', x.dataset.kw === kwSel ? 'true' : 'false'));
  $('kwhelp').hidden = !kwSel;
  $('kwhelp').textContent = kwSel ? `「${{kwSel}}」 키워드: ${{M.interests[kwSel].join(', ')}}` : '';
  page = 0; draw();
}});

const fill = (id, vals, label) => $(id).insertAdjacentHTML('beforeend', vals.map(v => `<option value="${{esc(v)}}">${{esc(label ? label(v) : v)}}</option>`).join(''));
fill('fj', M.journals); fill('ft', M.topics); fill('fc', M.countries, cname);
fill('fy', [...new Set(R.map(r => r.y))]);
$('archive').innerHTML = M.archives.map(a => `<a href="./archive/${{a}}.html">${{a}}</a>`).join('') || '<span class="caption">아직 없음</span>';

// Weekly bars (single series: no legend; value label on top, native tooltip on hover)
const wc = {{}}; R.forEach(r => wc[r.w] = (wc[r.w] || 0) + 1);
const wmax = Math.max(1, ...M.weeks.map(w => wc[w] || 0));
$('bars').innerHTML = M.weeks.map(w => `<button class="bar" data-w="${{w}}" title="${{w}} ~ ${{endOf(w)}}: ${{wc[w] || 0}}편"><b>${{wc[w] || 0}}</b><i style="height:${{(wc[w] || 0) / wmax * 150}}px"></i></button>`).join('');
$('xlabels').innerHTML = M.weeks.map(w => `<span>${{w.slice(5)}}</span>`).join('');
$('bars').addEventListener('click', e => {{ const b = e.target.closest('.bar'); if (!b) return; setWeek(weekSel === b.dataset.w ? '' : b.dataset.w); }});

// Topic x week heatmap: one hue, lightness by within-week share; counts printed in every cell
const tw = {{}}; R.forEach(r => r.tp.forEach(t => {{ const k = t + '|' + r.w; tw[k] = (tw[k] || 0) + 1; }}));
const shade = f => `color-mix(in srgb, var(--chart) ${{Math.round((0.12 + 0.88 * f) * 100)}}%, var(--color-surface))`;
$('heat').innerHTML = '<tr><th></th>' + M.weeks.map(w => `<th>${{w.slice(5)}}</th>`).join('') + '<th>합계</th></tr>' +
  M.topics.map(t => {{
    let total = 0;
    const cells = M.weeks.map(w => {{
      const n = tw[t + '|' + w] || 0, f = n / Math.max(1, wc[w] || 0); total += n;
      return n ? `<td data-t="${{esc(t)}}" data-w="${{w}}" class="${{Math.min(1, f / 0.5) > 0.45 ? 'hi' : ''}}" style="background:${{shade(Math.min(1, f / 0.5))}}" title="${{esc(t)}} · ${{w}}주: ${{n}}편 (${{Math.round(f * 100)}}%)">${{n}}</td>` : `<td class="z" data-t="${{esc(t)}}" data-w="${{w}}">·</td>`;
    }}).join('');
    return `<tr><th class="row">${{esc(t)}}</th>${{cells}}<th>${{total}}</th></tr>`;
  }}).join('');
$('heat').addEventListener('click', e => {{ const c = e.target.closest('td'); if (!c) return; $('ft').value = c.dataset.t; setWeek(c.dataset.w); }});

function setWeek(w) {{ weekSel = w; $('d1').value = w; $('d2').value = w ? endOf(w) : ''; page = 0; draw(); $('search').scrollIntoView({{behavior: 'smooth', block: 'start'}}); }}

function filtered() {{
  const q = terms(), any = $('qm').value === 'or';
  const j = $('fj').value, t = $('ft').value, c = $('fc').value, y = $('fy').value, d1 = $('d1').value, d2 = $('d2').value;
  const out = R.filter(r => (!j || r.j === j) && (!t || r.tp.includes(t)) && (!c || r.c.includes(c)) && (!y || r.y === y)
    && (!d1 || r.r >= d1) && (!d2 || r.r <= d2) && (!$('fo').checked || r.o) && (!$('fa').checked || r.ab)
    && (!kwSel || r.iw.includes(kwSel))
    && (!q.length || (any ? q.some(x => field(r).includes(x)) : q.every(x => field(r).includes(x)))));
  const s = $('sort').value;
  out.sort((a, b) => s === 'old' ? a.r.localeCompare(b.r) : s === 'journal' ? a.j.localeCompare(b.j) || b.r.localeCompare(a.r) : b.r.localeCompare(a.r));
  return out;
}}

function draw() {{
  const rows = filtered(), pages = Math.max(1, Math.ceil(rows.length / PER));
  page = Math.min(page, pages - 1);
  document.querySelectorAll('.bar').forEach(b => b.classList.toggle('on', b.dataset.w === weekSel));
  $('status').textContent = `${{rows.length}}편 / 전체 ${{R.length}}편`;
  $('page').textContent = `${{page + 1}} / ${{pages}}`;
  $('prev').disabled = page === 0; $('next').disabled = page >= pages - 1;
  const q = terms(), f = $('qf').value, byDate = $('sort').value !== 'journal';
  const words = [...q, ...(kwSel ? M.interests[kwSel] : [])];
  const tw = f === 'all' || f === 'title' ? words : [], aw = f === 'all' || f === 'author' ? q : [], bw = f === 'all' || f === 'abstract' ? words : [];
  const perDay = {{}}; rows.forEach(r => perDay[r.r] = (perDay[r.r] || 0) + 1);
  let lastDay = null;
  $('list').innerHTML = rows.slice(page * PER, page * PER + PER).map(r => {{
    const au = r.a.split('; ').filter(Boolean), auText = au.slice(0, 6).join(', ') + (au.length > 6 ? ' et al.' : '');
    const head = byDate && r.r !== lastDay ? `<h3 class="date-head">${{r.r || '날짜 없음'}}<small>${{perDay[r.r]}}편</small></h3>` : '';
    lastDay = r.r;
    const openAbs = bw.length && q.length && r.ab && bw.some(w => r.sb.includes(w)) ? ' open' : '';
    return `${{head}}<article class="paper"><div class="top"><span>${{r.r}}</span><span class="jr">${{esc(r.j)}}</span><span>${{esc(r.y)}}</span>${{r.o ? '<span class="oa">Open Access</span>' : ''}}</div>
<h3><a class="link-wipe" href="https://doi.org/${{esc(r.d)}}" target="_blank" rel="noopener">${{hl(r.t, tw)}}</a></h3><div class="ko">${{hl(r.k, tw)}}</div>
<div class="au">${{hl(auText, aw)}}${{r.c.length ? ' · ' + r.c.map(cname).join(', ') : ''}}</div>
<div class="tags">${{r.tp.map(t => `<span class="pill">${{esc(t)}}</span>`).join('')}}${{r.iw.map(n => `<span class="pill" style="background:var(--color-surface);border-color:var(--color-line)">${{esc(n)}}</span>`).join('')}}</div>
${{r.ab ? `<details${{openAbs}}><summary>초록 보기</summary><p>${{hl(r.ab, bw)}}</p></details>` : ''}}</article>`;
  }}).join('') || '<p class="caption">조건에 맞는 논문이 없습니다.</p>';
}}

['q', 'qf', 'qm', 'fj', 'ft', 'fc', 'fy', 'd1', 'd2', 'fo', 'fa', 'sort'].forEach(id => $(id).addEventListener('input', () => {{ page = 0; if (id === 'd1' || id === 'd2') weekSel = ''; draw(); }}));
$('prev').onclick = () => {{ page--; draw(); $('search').scrollIntoView(); }};
$('next').onclick = () => {{ page++; draw(); $('search').scrollIntoView(); }};
$('reset').onclick = () => {{
  ['q', 'fj', 'ft', 'fc', 'fy', 'd1', 'd2'].forEach(id => $(id).value = ''); $('qf').value = 'all'; $('qm').value = 'and'; $('sort').value = 'new';
  $('fo').checked = $('fa').checked = false; weekSel = ''; kwSel = ''; $('kwhelp').hidden = true;
  document.querySelectorAll('#kw .chip').forEach(x => x.setAttribute('aria-pressed', 'false')); page = 0; draw();
}};
$('csv').onclick = () => {{
  const cols = [['doi', 'd'], ['title_en', 't'], ['title_ko', 'k'], ['journal', 'j'], ['authors', 'a'], ['doi_registered', 'r'], ['primary_topic', 'p'], ['countries', 'c'], ['open_access', 'o'], ['abstract', 'ab']];
  const cell = v => '"' + String(Array.isArray(v) ? v.join(';') : v ?? '').replace(/"/g, '""') + '"';
  const text = '\\ufeff' + [cols.map(c => c[0]).join(','), ...filtered().map(r => cols.map(c => cell(r[c[1]])).join(','))].join('\\r\\n');
  const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([text], {{type: 'text/csv;charset=utf-8'}}));
  a.download = 'nuclear-literature-filtered.csv'; a.click(); URL.revokeObjectURL(a.href);
}};
draw();
}})();
</script></body></html>"""
