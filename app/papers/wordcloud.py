"""Trend-keyword sphere for the weekly paper page (pure Python -> inline SVG, no extra library).

Plain word frequency puts "neutron", "thermal", "design" on top every week, which says nothing about what is
new. Instead the cloud shows the curated trend keywords in config/papers.json "trend_keywords"
(SMR, MSR, MMR, Digital Twin, AI, Multiphysics ...). Each keyword lists its synonyms; a paper counts once
per keyword if its title or abstract contains any synonym (same word-aware matching as the topic rules).

Every keyword has a Korean name and an English label; the page has a 한글 / EN switch (two spheres, one shown).
Size = number of this week's papers with the keyword. Color = the research area most of those papers fall in.
The sphere shrinks to fit however many keywords appear, so a quiet week still looks like a full ball.
Clicking a keyword filters the paper list to the papers tagged with it (data-trend on each paper).
"""
import html
import math
from collections import Counter

FONT_MIN, FONT_MAX = 13, 54
FILL = 0.60            # share of the circle's area covered by word boxes (sets the sphere size)
MARGIN = 14


def split_config(config):
    """papers.json trend_keywords -> ({korean name: synonyms}, {korean name: english name}).
    Accepts {"이름": {"en": "...", "terms": [...]}} or the plain {"이름": [...]} form."""
    terms, english = {}, {}
    for name, value in config.items():
        if name.startswith("_"):
            continue
        if isinstance(value, dict):
            terms[name] = value.get("terms", [])
            english[name] = value.get("en") or name
        else:
            terms[name] = value
            english[name] = name
    return terms, english


def tag_trends(records, trends, text_of, matcher):
    """Store record["trends"] = [keyword names found in the paper]."""
    for record in records:
        text = text_of(record)
        record["trends"] = [label for label, synonyms in trends.items() if matcher(text, synonyms)]


def _text_width(term, size):
    width = 0.0
    for ch in term:
        if ord(ch) > 0x3000:        # Hangul / CJK: full width
            width += 0.98
        elif ch.isupper() or ch.isdigit():
            width += 0.68
        else:
            width += 0.34 if ch in "-il .,'·" else 0.84 if ch in "mw" else 0.6
    return width * size


def _font(count, top, low):
    share = 1.0 if top == low else (count - low) / (top - low)
    return FONT_MIN + (FONT_MAX - FONT_MIN) * share ** 0.6


def layout(terms):
    """Place words largest-first on an occupancy grid inside a circle sized to the words.
    Each word goes to the free spot nearest the centre (all spots tested at once with an integral image).
    Returns (size, [(term, count, font, x, y, vertical)])."""
    import numpy as np

    if not terms:
        return 0, []
    top, low = terms[0][1], terms[-1][1]
    area = sum(_text_width(t, _font(c, top, low)) * _font(c, top, low) * 1.1 for t, c in terms)
    radius = min(280.0, max(110.0, math.sqrt(area / (FILL * math.pi))))
    size = int(2 * (radius + MARGIN))
    cell = 2
    n = size // cell
    yy, xx = np.mgrid[0:n, 0:n]
    centre = n / 2
    blocked = (np.hypot(xx + 0.5 - centre, yy + 0.5 - centre) > radius / cell).astype(np.int32)
    placed = []
    for index, (term, count) in enumerate(terms):
        font = _font(count, top, low)
        vertical = index >= 4 and index % 5 == 4 and len(term) <= 12 and font < 30 and term.isascii()   # only small Latin words turn sideways (Hangul reads badly rotated)
        integral = np.pad(blocked.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
        while font >= FONT_MIN * 0.75:
            w = int(np.ceil((_text_width(term, font) + 8 + font * 0.35) / cell))   # side gap so neighbours never read as one word
            h = int(np.ceil((font * 1.1 + 4) / cell))
            bw, bh = (h, w) if vertical else (w, h)
            if bw >= n or bh >= n:
                font *= 0.88
                continue
            window = integral[bh:, bw:] - integral[:-bh, bw:] - integral[bh:, :-bw] + integral[:-bh, :-bw]
            ys, xs = np.nonzero(window == 0)
            if len(ys):
                dist = np.hypot((xs + bw / 2 - centre) * 0.9, ys + bh / 2 - centre)
                k = int(np.argmin(dist))
                y0, x0 = int(ys[k]), int(xs[k])
                blocked[y0:y0 + bh, x0:x0 + bw] = 1
                placed.append((term, count, font, (x0 + bw / 2) * cell, (y0 + bh / 2) * cell, vertical))
                break
            font *= 0.88
    return size, placed


def _svg(words, size, key_of, colors, counts, english, lang):
    esc = lambda v: html.escape(str(v), quote=True)
    items = []
    for shown, count, font, x, y, vertical in words:
        key = key_of[shown]
        rotate = f' transform="rotate(-90 {x:.1f} {y:.1f})"' if vertical else ""
        tip = f"{key} ({english[key]})" if english[key] != key else key
        items.append(
            f'<text class="wc-word trend-trigger" data-trend="{esc(key)}" tabindex="0" role="button" '
            f'x="{x:.1f}" y="{y:.1f}" font-size="{font:.1f}" style="fill:{colors[key]}"{rotate}>'
            f'<title>{esc(tip)}: {counts[key]}편</title>{esc(shown)}</text>'
        )
    c = size / 2
    label = "이번 주 논문 트렌드 키워드" if lang == "ko" else "Trend keywords in this week's papers"
    return (
        f'<svg class="wordcloud" viewBox="0 0 {size} {size}" role="img" aria-label="{label}, {len(words)}">'
        # faint sphere behind the words: lighter top-left, so the cloud reads as a ball
        f'<defs><radialGradient id="wc-sphere-{lang}" cx="38%" cy="34%" r="70%">'
        f'<stop offset="0%" style="stop-color:var(--color-card)"/><stop offset="100%" style="stop-color:var(--color-surface-deep)"/></radialGradient></defs>'
        f'<circle cx="{c}" cy="{c}" r="{c - 1}" fill="url(#wc-sphere-{lang})" style="stroke:var(--color-line)"/>'
        f'{"".join(items)}</svg>'
    )


def render(records, area_colors, english=None):
    """HTML for the cloud section body: a 한글 / EN switch and one sphere per language.
    Needs record["trends"] (tag_trends) and record["primary_area"]; `english` maps name -> English label."""
    counts = Counter(label for r in records for label in r.get("trends", []))
    if not counts:
        return '<p class="chart-note">이번 주 논문에는 트렌드 키워드가 없습니다. config/papers.json의 trend_keywords에 키워드를 추가할 수 있습니다.</p>'
    english = {k: (english or {}).get(k) or k for k in counts}
    esc = lambda v: html.escape(str(v), quote=True)
    colors, used_areas = {}, Counter()
    for key, count in counts.items():
        areas = Counter(r["primary_area"] for r in records if key in r.get("trends", []))
        area = areas.most_common(1)[0][0] if areas else ""
        colors[key] = area_colors.get(area, "var(--s-other)")
        used_areas[area] += count
    spheres = []
    for lang in ("ko", "en"):
        key_of = {(k if lang == "ko" else english[k]): k for k in counts}
        terms = sorted(((shown, counts[k]) for shown, k in key_of.items()), key=lambda kv: (-kv[1], kv[0]))
        size, words = layout(terms)
        hidden = "" if lang == "ko" else " hidden"
        spheres.append(f'<div class="wc-lang-view" data-lang="{lang}"{hidden}>{_svg(words, size, key_of, colors, counts, english, lang)}</div>')
    legend = "".join(
        f'<span><i style="background:{area_colors.get(area, "var(--s-other)")}"></i>{esc(area)}</span>'
        for area, _ in used_areas.most_common() if area
    )
    switch = ('<div class="wc-switch" role="group" aria-label="키워드 표기 언어">'
              '<button type="button" class="chip" data-wc-lang="ko" aria-pressed="true">한글</button>'
              '<button type="button" class="chip" data-wc-lang="en" aria-pressed="false">EN</button></div>')
    return f'{switch}<div class="wc-wrap">{"".join(spheres)}</div><div class="wc-legend">{legend}</div>'


CSS = """
.wc-wrap{max-width:32rem;margin:0 auto}
.wc-switch{display:flex;justify-content:center;gap:.4rem;margin:0 0 .75rem}
.wc-lang-view[hidden]{display:none}
.wordcloud{display:block;width:100%;height:auto}
.wc-word{font-family:var(--font-sans);font-weight:700;letter-spacing:-.01em;text-anchor:middle;dominant-baseline:central;cursor:pointer;transition:opacity 150ms}
.wordcloud:hover .wc-word{opacity:.45}.wordcloud .wc-word:hover,.wordcloud .wc-word:focus{opacity:1}
.wc-word:focus{outline:none;text-decoration:underline}
.wc-legend{display:flex;flex-wrap:wrap;justify-content:center;gap:.4rem 1rem;margin-top:1rem;font-size:.75rem;color:var(--color-neutral-600)}
.wc-legend span{display:inline-flex;align-items:center;gap:.35rem}
.wc-legend i{width:.65rem;height:.65rem;border-radius:999px;display:inline-block}
"""

KEY_JS = (
    # 한글 / EN switch; the choice is remembered in this browser only
    "(function(){var KEY='nuclear-digest-wc-lang';function show(l){document.querySelectorAll('.wc-lang-view').forEach(function(v){v.hidden=v.dataset.lang!==l;});"
    "document.querySelectorAll('[data-wc-lang]').forEach(function(b){b.setAttribute('aria-pressed',b.dataset.wcLang===l?'true':'false');});}"
    "var saved=null;try{saved=localStorage.getItem(KEY);}catch(e){}if(saved==='en'||saved==='ko')show(saved);"
    "document.querySelectorAll('[data-wc-lang]').forEach(function(b){b.addEventListener('click',function(){show(b.dataset.wcLang);"
    "try{localStorage.setItem(KEY,b.dataset.wcLang);}catch(e){}});});})();"
    "document.querySelectorAll('.wc-word').forEach(function(w){w.addEventListener('keydown',function(e){"
    "if(e.key==='Enter'||e.key===' '){e.preventDefault();w.dispatchEvent(new MouseEvent('click',{bubbles:true}));}});});"
)
