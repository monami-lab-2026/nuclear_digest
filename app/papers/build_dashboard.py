"""Interactive single-file HTML dashboard (ported from the Codex build_digest.py).

Layout, charts and filters are unchanged; data now comes from the SQLite DB and config/settings.json.
"""
import html
from collections import Counter
from datetime import date, timedelta

from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer

from .. import site_theme
from . import wordcloud
from .common import SETTINGS, document_type, matches_any, paper_text, topics_for

from .wordcloud import split_config as _split_trends
TRENDS, TRENDS_EN = _split_trends(SETTINGS.get("trend_keywords", {}))

WATCHLISTS = SETTINGS["watchlists"]
COUNTRY_NAMES = SETTINGS["country_names"]
FALLBACK_TOPIC = SETTINGS["fallback_topic"]


def topic_tags(title):
    return topics_for({"title": title})

def country_codes(record):
    values = record.get("countries") or []
    if isinstance(values, str):
        values = values.split(";")
    return [value for value in values if value]

def country_label(code):
    return f"{COUNTRY_NAMES.get(code, code)} ({code})"


def provisional_intro(title, tags):
    lowered = title.lower()
    if "machine learning" in lowered or "artificial intelligence" in lowered or "ai-driven" in lowered or "reinforcement learning" in lowered:
        return "AI·기계학습을 이용해 원자력 계통의 예측, 진단 또는 최적화 문제를 다룬 연구입니다."
    if "cfd" in lowered or "computational fluid" in lowered or "eulerian" in lowered:
        return "전산유체역학 모델을 이용해 원자로 내부 유동과 열전달 현상을 해석한 연구입니다."
    if "boiling" in lowered or "critical heat flux" in lowered or "chf" in lowered:
        return "비등 열전달 또는 임계열유속과 관련된 모델·실험·안전여유를 검토한 연구입니다."
    if "condensation" in lowered:
        return "응축 열전달과 비응축성 기체 등 원전 안전계통의 주요 열수력 현상을 다룬 연구입니다."
    if "smr" in lowered or "microreactor" in lowered:
        return "SMR 또는 마이크로리액터의 설계·성능·안전 특성을 평가한 연구입니다."
    if "accident" in lowered or "loca" in lowered or "corium" in lowered:
        return "사고 조건에서의 원전 거동과 안전성 평가 또는 완화 전략을 다룬 연구입니다."
    if tags:
        return f"{', '.join(tags)} 관점에서 원자력 시스템의 성능 또는 해석 방법을 다룬 연구입니다."
    return "제목상 원자력 시스템의 설계, 해석, 운전 또는 기반 기술을 다룬 연구입니다."



def render(period, records, previous_records, cumulative_records, run_count, nav_prefix="./"):
    """records / previous_records / cumulative_records: dicts from database.as_record()."""
    RUN_DATE = period.run_id
    PERIOD_START, PERIOD_END = period.start.isoformat(), period.end.isoformat()
    PREVIOUS_START, PREVIOUS_END = period.previous.start.isoformat(), period.previous.end.isoformat()
    if not records:
        raise ValueError(f"no papers in {PERIOD_START}~{PERIOD_END}; refusing to publish an empty dashboard")
    for record in records:
        tags = topics_for(record)
        record["areas"] = tags
        record["primary_area"] = tags[0]
        record["document_type"] = document_type(record["title"])
        record["summary"] = ""
        record["summary_basis"] = f"{record['abstract_source']} Abstract 확인" if record.get("abstract") else "제목·서지정보 확인"
    wordcloud.tag_trends(records, TRENDS, paper_text, matches_any)

    # Every configured journal is listed, including ones with no papers this week (shown as 0).
    by_journal = Counter({name: 0 for name in SETTINGS["journals"]})
    by_journal.update(record["journal"] for record in records)
    area_counts = Counter(record["primary_area"] for record in records)
    date_counts = Counter(record["registered_date"] for record in records)
    previous_area_counts = Counter(topics_for(record)[0] for record in previous_records)
    type_counts = Counter(record["document_type"] for record in records)
    country_counts = Counter(code for record in records for code in country_codes(record))
    cumulative_country_counts = Counter(code for record in cumulative_records for code in country_codes(record))
    country_coverage = sum(bool(country_codes(record)) for record in records)

    # Title-based semantic map: TF-IDF (unigrams+bigrams) projected to two dimensions.
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=2 if len(records) >= 10 else 1)
    title_matrix = vectorizer.fit_transform(record["title"] for record in records)
    topic_xy = TruncatedSVD(n_components=2, random_state=42).fit_transform(title_matrix)
    for record, (x_value, y_value) in zip(records, topic_xy):
        record["topic_x"] = float(x_value)
        record["topic_y"] = float(y_value)

    n_clusters = max(1, min(7, len(records) // 3))
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=20).fit(title_matrix)
    terms = vectorizer.get_feature_names_out()
    cluster_names = {}
    for cluster_id in range(n_clusters):
        member_indices = [i for i, label in enumerate(kmeans.labels_) if label == cluster_id]
        if not member_indices:
            continue
        dominant_area = Counter(records[i]["primary_area"] for i in member_indices).most_common(1)[0][0]
        center_terms = [terms[i] for i in kmeans.cluster_centers_[cluster_id].argsort()[::-1] if len(terms[i]) > 3][:1] or [""]
        cluster_names[cluster_id] = f"{dominant_area} · {center_terms[0]}".rstrip(" ·")
        for i in member_indices:
            records[i]["cluster"] = cluster_id

    keyword_stop = list(TfidfVectorizer(stop_words="english").get_stop_words()) + [
        "nuclear", "reactor", "study", "analysis", "model", "modeling", "development", "assessment", "using", "based", "system", "systems",
        "characteristics", "approach", "condition", "conditions", "case", "effect", "effects", "performance", "method", "methods", "experimental",
        "numerical", "evaluation", "investigation", "results", "application", "new", "integrated", "energy", "implications"
    ]
    keyword_vectorizer = CountVectorizer(stop_words=keyword_stop, ngram_range=(1, 1), token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9-]{2,}\b")
    keyword_matrix = keyword_vectorizer.fit_transform(record["title"].lower() for record in records)
    keyword_totals = keyword_matrix.sum(axis=0).A1
    keyword_names = keyword_vectorizer.get_feature_names_out()
    top_keywords = sorted(zip(keyword_names, keyword_totals), key=lambda item: (-item[1], item[0]))[:18]


    def count_keywords(items):
        texts = [paper_text(item) for item in items]
        if not texts:
            return Counter()
        vectorizer = CountVectorizer(stop_words=keyword_stop, ngram_range=(1, 2), token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9-]{2,}\b")
        matrix = vectorizer.fit_transform(texts)
        totals = matrix.sum(axis=0).A1
        return Counter({word: int(value) for word, value in zip(vectorizer.get_feature_names_out(), totals)})


    current_keyword_counts = count_keywords(records)
    previous_keyword_counts = count_keywords(previous_records)
    keyword_candidates = []
    for word, current_count in current_keyword_counts.items():
        if current_count < 2 or word in {"nuclear energy", "nuclear engineering", "reactor system"}:
            continue
        previous_count = previous_keyword_counts[word]
        current_rate = current_count / len(records) * 100
        previous_rate = previous_count / max(len(previous_records), 1) * 100
        delta_rate = current_rate - previous_rate
        if delta_rate > 0:
            keyword_candidates.append((word, current_count, previous_count, current_rate, previous_rate, delta_rate))
    emerging_keywords = sorted(keyword_candidates, key=lambda item: (-item[5], -item[1], item[0]))[:14]

    cumulative_area_counts = Counter(record.get("primary_topic") or FALLBACK_TOPIC for record in cumulative_records)


    def watch_matches(record, terms):
        return matches_any(record, terms)


    watch_stats = []
    for watch_name, watch_terms in WATCHLISTS.items():
        current_matches = [record for record in records if watch_matches(record, watch_terms)]
        previous_matches = [record for record in previous_records if watch_matches(record, watch_terms)]
        cumulative_matches = [record for record in cumulative_records if watch_matches(record, watch_terms)]
        representative = next(iter(current_matches), None)
        if representative is None and cumulative_matches:
            representative = max(cumulative_matches, key=lambda item: item.get("doi_registered_date", ""))
        watch_stats.append({
            "name": watch_name,
            "current": len(current_matches),
            "previous": len(previous_matches),
            "cumulative": len(cumulative_matches),
            "delta": len(current_matches) - len(previous_matches),
            "representative": representative,
        })


    def esc(value):
        return html.escape(str(value or ""), quote=True)


    cards = []
    for number, record in enumerate(records, 1):
        tags_html = "".join(f'<span class="tag">{esc(tag)}</span>' for tag in record["areas"])
        author_text = ", ".join(record["authors"][:8])
        if len(record["authors"]) > 8:
            author_text += " et al."
        date_text = record.get("published_online") or record.get("issued") or record.get("cover_date") or "미확인"
        summary_html = f'<p class="summary">{esc(record["summary"])}</p>' if record["summary"] else ""
        abstract_link_label = "Abstract 확인" if record["publisher_url"] else "DOI 확인"
        watch_names = "|".join(name for name, terms in WATCHLISTS.items() if watch_matches(record, terms))
        countries = country_codes(record)
        country_text = ", ".join(country_label(code) for code in countries) if countries else "소속 국가 미확인"
        cards.append(f"""
          <article class="paper" data-journal="{esc(record['journal'])}" data-topic="{esc(record['primary_area'])}" data-title="{esc(paper_text(record))}" data-watch="{esc(watch_names)}" data-trend="{esc('|'.join(record['trends']))}" data-country="{esc('|'.join(countries))}" data-type="{esc(record['document_type'])}">
            <div class="paper-top"><span class="num">{number:03d}</span><span class="journal">{esc(record['journal'])}</span><span class="date">DOI 등록 {esc(record['registered_date'])}</span></div>
            <h2><a class="link-wipe" href="{esc(record['doi_url'])}" target="_blank" rel="noopener noreferrer">{esc(record['title'])}</a></h2>
            <h3 class="title-ko">{esc(record['title_ko'])}</h3>
            <p class="authors">{esc(author_text)}</p>
            <div class="tags"><span class="type-tag">{esc(record['document_type'])}</span>{tags_html}</div>
            {summary_html}
            <p class="basis">저자 소속 국가: {esc(country_text)} · {esc(record['summary_basis'])} · 온라인/권호일 {esc(date_text)} · <a class="abstract-link" href="{esc(record['publisher_url'] or record['doi_url'])}" target="_blank" rel="noopener noreferrer">{abstract_link_label}</a> · <a href="{esc(record['doi_url'])}" target="_blank" rel="noopener noreferrer">DOI</a></p>
          </article>""")

    journal_rows = f'<button type="button" class="chip journal-filter active" data-journal="all" aria-pressed="true">전체 <strong>{len(records)}</strong></button>' + "".join(
        f'<button type="button" class="chip journal-filter" data-journal="{esc(name)}" aria-pressed="false"{" disabled" if not count else ""}><span>{esc(name)}</span> <strong>{count}</strong></button>'
        for name, count in by_journal.most_common()
    )
    type_rows = "".join(f'<span class="type-summary"><strong>{esc(name)}</strong> {count}</span>' for name, count in type_counts.items())
    max_area = max(area_counts.values())
    area_order = [name for name, _ in area_counts.most_common()]
    area_bars = "".join(
        f'<div class="bar-row"><span>{esc(name)}</span><div class="bar-track"><div class="bar-fill" style="width:{count/max_area*100:.1f}%"></div></div><strong>{count}</strong></div>'
        for name, count in area_counts.most_common()
    )
    country_max = max(country_counts.values(), default=1)
    country_bars = "".join(
        f'<button type="button" class="bar-row country-trigger" data-country="{esc(code)}"><span>{esc(country_label(code))}</span><div class="bar-track"><div class="bar-fill country-fill" style="width:{count/country_max*100:.1f}%"></div></div><strong>{count}</strong></button>'
        for code, count in country_counts.most_common(15)
    )

    top_country_codes = [code for code, _ in country_counts.most_common(10)]
    country_matrix_rows = []
    for journal in by_journal:
        cells = []
        for code in top_country_codes:
            count = sum(r["journal"] == journal and code in country_codes(r) for r in records)
            cell_opacity = 0.08 + min(count/5, 0.75)
            cells.append(f'<td class="{"hi" if cell_opacity > 0.5 else ""}" style="--cell-opacity:{cell_opacity:.2f}"><button type="button" class="matrix-cell journal-country-trigger" data-journal="{esc(journal)}" data-country="{esc(code)}"><strong>{count}</strong></button></td>')
        country_matrix_rows.append(f'<tr><th>{esc(journal)}</th>{"".join(cells)}</tr>')
    country_matrix_header = "".join(f'<th title="{esc(country_label(code))}">{esc(COUNTRY_NAMES.get(code, code))}</th>' for code in top_country_codes)
    country_matrix_html = f'<div class="matrix-wrap"><table class="matrix"><thead><tr><th>저널</th>{country_matrix_header}</tr></thead><tbody>{"".join(country_matrix_rows)}</tbody></table></div><p class="chart-note">저자 소속기관 기준입니다. 국제공동연구는 참여 국가마다 1편으로 집계되어 국가별 합계가 전체 논문 수보다 클 수 있습니다.</p>'
    trend_rows = "".join(
        f'''<button type="button" class="trend-row topic-trigger" data-topic="{esc(area)}">
          <span class="trend-name">{esc(area)}</span>
          <span class="trend-period"><i style="width:{previous_area_counts[area]/len(previous_records)*100:.1f}%"></i><b>{previous_area_counts[area]}</b><small>{previous_area_counts[area]/len(previous_records)*100:.1f}%</small></span>
          <span class="trend-period current"><i style="width:{area_counts[area]/len(records)*100:.1f}%"></i><b>{area_counts[area]}</b><small>{area_counts[area]/len(records)*100:.1f}%</small></span>
          <span class="trend-delta {"up" if area_counts[area]/len(records)-previous_area_counts[area]/len(previous_records) > 0 else "down"}">{(area_counts[area]/len(records)-previous_area_counts[area]/len(previous_records))*100:+.1f}%p</span>
        </button>'''
        for area in area_order
    )
    keyword_max = max((count for _, count in top_keywords), default=1)
    keyword_bars = "".join(
        f'<div class="keyword-item"><span>{esc(word)}</span><div class="keyword-track"><div class="keyword-fill" style="width:{count/keyword_max*100:.1f}%"></div></div><strong>{int(count)}</strong></div>'
        for word, count in top_keywords
    )
    emerging_keyword_html = "".join(
        f'''<button type="button" class="surge-keyword keyword-trigger" data-keyword="{esc(word)}">
          <span class="surge-word">{esc(word)}</span>
          <span class="surge-count">{current_count}편</span>
          <span class="surge-delta">+{delta_rate:.1f}편/100편</span>
          <span class="surge-context">직전 {previous_count} → 현재 {current_count}{" · 신규" if previous_count == 0 else ""}</span>
        </button>'''
        for word, current_count, previous_count, current_rate, previous_rate, delta_rate in emerging_keywords
    )
    watchlist_html = "".join(
        f'''<button type="button" class="watch-card watch-trigger" data-watch="{esc(item['name'])}">
          <span class="watch-name">{esc(item['name'])}</span>
          <span class="watch-total">누적 <strong>{item['cumulative']}</strong>편</span>
          <span class="watch-change"><b>{item['previous']}</b> → <b>{item['current']}</b><em class="{'up' if item['delta'] > 0 else 'down' if item['delta'] < 0 else 'flat'}">{item['delta']:+d}</em></span>
          <span class="watch-paper">{esc((item['representative'] or {}).get('title_ko') or (item['representative'] or {}).get('title') or (item['representative'] or {}).get('title_en') or '관련 논문 없음')}</span>
        </button>'''
        for item in watch_stats
    )
    start_day = date.fromisoformat(PERIOD_START)
    end_day = date.fromisoformat(PERIOD_END)
    all_dates = [(start_day + timedelta(days=offset)).isoformat() for offset in range((end_day-start_day).days + 1)]
    max_date = max(date_counts.values())
    timeline_bars = "".join(
        f'<div class="day"><div class="day-value">{date_counts[date]}</div><div class="day-track"><div class="day-fill" style="height:{(date_counts[date]/max_date*100) if max_date else 0:.1f}%"></div></div><span>{date[-2:]}</span></div>'
        for date in all_dates
    )
    matrix_rows = []
    for journal in by_journal:
        cells = []
        for area in area_order:
            current_count = sum(r["journal"] == journal and r["primary_area"] == area for r in records)
            cumulative_count = sum(r["journal"] == journal and (r.get("primary_topic") or FALLBACK_TOPIC) == area for r in cumulative_records)
            journal_total = sum(r["journal"] == journal for r in cumulative_records)
            opacity = 0.08 + (cumulative_count / max(journal_total, 1)) * 1.5
            cells.append(f'<td class="{"hi" if min(opacity, 0.85) > 0.5 else ""}" style="--cell-opacity:{min(opacity,0.85):.2f}"><button type="button" class="matrix-cell matrix-trigger" data-journal="{esc(journal)}" data-topic="{esc(area)}" aria-label="{esc(journal)}, {esc(area)}, 현재 {current_count}편, 누적 {cumulative_count}편"><strong>{current_count}</strong><small>{cumulative_count}</small></button></td>')
        matrix_rows.append(f'<tr><th>{esc(journal)}</th>{"".join(cells)}</tr>')
    matrix_header = "".join(f'<th>{esc(area)}</th>' for area in area_order)
    matrix_html = f'<div class="matrix-wrap"><table class="matrix"><thead><tr><th>저널</th>{matrix_header}</tr></thead><tbody>{"".join(matrix_rows)}</tbody></table></div><p class="chart-note">각 셀은 <strong>현재 기간</strong> / 누적 순서입니다. 셀을 누르면 해당 조합의 최신 논문만 표시합니다.</p>'

    topic_names = list(SETTINGS["topics"])
    area_colors = {name: f"var(--s{i + 1})" for i, name in enumerate(topic_names[:8])}
    area_colors.update({name: "var(--s-other)" for name in topic_names[8:]})
    area_colors[FALLBACK_TOPIC] = "var(--s-other)"
    wordcloud_html = wordcloud.render(records, area_colors, TRENDS_EN)
    x_values = [record["topic_x"] for record in records]
    y_values = [record["topic_y"] for record in records]
    x_min, x_max = min(x_values), max(x_values)
    y_min, y_max = min(y_values), max(y_values)

    def map_value(value, low, high, out_low, out_high):
        return out_low + (value - low) / max(high - low, 1e-9) * (out_high - out_low)

    scatter_points = []
    for index, record in enumerate(records, 1):
        cx = map_value(record["topic_x"], x_min, x_max, 62, 798)
        cy = map_value(record["topic_y"], y_min, y_max, 448, 28)
        color = area_colors[record["primary_area"]]
        tooltip = f"{index:03d} · {record['title_ko']} · {record['primary_area']}"
        point_watches = "|".join(name for name, terms in WATCHLISTS.items() if watch_matches(record, terms))
        scatter_points.append(
            f'<a href="{esc(record["doi_url"])}" target="_blank" rel="noopener noreferrer"><circle data-journal="{esc(record["journal"])}" data-topic="{esc(record["primary_area"])}" data-title="{esc(paper_text(record))}" data-watch="{esc(point_watches)}" data-country="{esc("|".join(country_codes(record)))}" cx="{cx:.1f}" cy="{cy:.1f}" r="5.2" style="fill:{color}" fill-opacity="0.85"><title>{esc(tooltip)}</title></circle></a>'
        )
    cluster_labels = []
    for cluster_id, cluster_name in cluster_names.items():
        members = [record for record in records if record["cluster"] == cluster_id]
        label_x = sum(map_value(record["topic_x"], x_min, x_max, 62, 798) for record in members) / len(members)
        label_y = sum(map_value(record["topic_y"], y_min, y_max, 448, 28) for record in members) / len(members)
        cluster_labels.append(f'<text class="cluster-label" x="{label_x:.1f}" y="{label_y:.1f}" text-anchor="middle">{esc(cluster_name)}</text>')
    scatter_legend = "".join(
        f'<span><i style="background:{area_colors[area]}"></i>{esc(area)} {area_counts[area]}</span>'
        for area in area_order
    )
    scatter_html = f'''<div class="scatter-legend">{scatter_legend}</div>
    <svg class="topic-scatter" viewBox="0 0 840 500" role="img" aria-labelledby="topic-map-title topic-map-desc">
      <title id="topic-map-title">제목 기반 연구 토픽 산점도</title>
      <desc id="topic-map-desc">영문 제목의 TF-IDF 유사도를 SVD로 2차원에 투영한 지도입니다. 가까운 점일수록 제목에서 사용하는 연구 용어가 유사합니다.</desc>
      <rect class="plot-bg" x="54" y="18" width="754" height="440"/>
      <line class="axis" x1="54" y1="458" x2="808" y2="458"/><line class="axis" x1="54" y1="18" x2="54" y2="458"/>
      <text x="431" y="490" text-anchor="middle">토픽 성분 1</text><text x="16" y="238" text-anchor="middle" transform="rotate(-90 16 238)">토픽 성분 2</text>
      {''.join(scatter_points)}
      {''.join(cluster_labels)}
    </svg>
    <p class="chart-note">점 하나는 논문 한 편입니다. 가까울수록 제목에 등장하는 용어가 유사하며, 점을 가리키면 한글 제목을 확인하고 클릭하면 DOI로 이동합니다.</p>'''

    head_html = site_theme.head(f"원자력공학 최근 논문 동향 · {RUN_DATE}", f"{PERIOD_START}~{PERIOD_END} 원자력공학 주요 {len(SETTINGS['journals'])}개 저널 신규 논문 동향", site_theme.DASHBOARD_CSS + wordcloud.CSS, nav_prefix + "../")
    header_html = site_theme.site_header("papers", nav_prefix + "../")
    page_head_html = site_theme.page_header(
        f"Weekly Literature Watch · {RUN_DATE}",
        "원자력공학 최근 논문 동향",
        f"<b>{PERIOD_START} ~ {PERIOD_END}</b> DOI 신규 등록 논문 {len(records)}편 · {len(SETTINGS['journals'])}개 원자력공학 저널. "
        f"동향 지표 일부는 누적 {len(cumulative_records)}편({run_count}회 수집)을 함께 씁니다.",
    )
    stats_html = (
        f'<div class="stats four"><div><strong id="visible-count">{len(records)}</strong><span>이번 주 표시 논문</span></div>'
        f'<div><strong>{len(previous_records)}</strong><span>직전 주 논문</span></div>'
        f'<div><strong>{len(cumulative_records)}</strong><span>누적 논문</span></div>'
        f'<div><strong>{run_count}</strong><span>수집 회차</span></div></div>'
    )
    document = f"""<!doctype html>
    <html lang="ko">
    <head>
    {head_html}
    </head>
    <body>
    {header_html}
    {page_head_html}
    <main class="page"><div class="container-page">
      <section class="section sec-grid"><div class="sec-side"><p class="eyebrow eyebrow-mark eyebrow-accent">Keywords</p><h2>이번 주 트렌드 키워드</h2>
        <p class="note">이번 주 새 논문 {len(records)}편의 제목·초록에서 소형모듈원자로, 용융염원자로, 디지털트윈, 인공지능 같은 트렌드 키워드가 나온 논문 수입니다(영문 표기·약어도 함께 찾습니다). 글자가 클수록 많이 나왔고, 색은 그 논문들이 주로 속한 연구 영역입니다. 키워드를 누르면 해당 논문만 아래 목록에 남습니다.</p></div>
        <div class="sec-body">{wordcloud_html}</div></section>
      <section class="section">{stats_html}</section>
      <section class="section sec-grid"><div class="sec-side"><p class="eyebrow">01</p><h2>저널 필터</h2></div><div class="sec-body"><div class="journal-filters" aria-label="저널별 논문 필터">{journal_rows}</div></div></section>
      <div id="filter-status" class="filter-status" aria-live="polite" hidden><span id="filter-label"></span><button type="button" id="reset-filter">필터 초기화</button></div>
      <section class="section sec-grid"><div class="sec-side"><p class="eyebrow">02</p><h2>문서 유형</h2></div><div class="sec-body"><div>{type_rows}</div></div></section>
      <section class="section sec-grid"><div class="sec-side"><p class="eyebrow">03</p><h2>연구 영역 분포</h2></div><div class="sec-body">{area_bars}</div></section>
      <section class="section sec-grid"><div class="sec-side"><p class="eyebrow">04</p><h2>국가별 논문 분포</h2></div><div class="sec-body">{country_bars}<p class="chart-note">이번 주 {len(records)}편 중 소속 국가를 확인한 논문은 {country_coverage}편입니다. 막대를 누르면 해당 국가의 논문만 표시합니다.</p></div></section>
      <section class="section sec-grid"><div class="sec-side"><p class="eyebrow">05</p><h2>저널 × 국가 히트맵</h2></div><div class="sec-body">{country_matrix_html}</div></section>
      <section class="section sec-grid"><div class="sec-side"><p class="eyebrow">06</p><h2>제목 기반 연구 토픽 지도</h2></div><div class="sec-body">{scatter_html}</div></section>
      <section class="section sec-grid"><div class="sec-side"><p class="eyebrow">07</p><h2>주간 연구 토픽 추세</h2></div><div class="sec-body"><div class="trend-head"><span>토픽</span><span>{PREVIOUS_START[5:]}–{PREVIOUS_END[5:]} · {len(previous_records)}편</span><span>{PERIOD_START[5:]}–{PERIOD_END[5:]} · {len(records)}편</span><span>비중 변화</span></div><div class="trend-grid">{trend_rows}</div><p class="chart-note">주별 전체 논문 수가 다르므로 건수와 함께 점유율 변화를 표시합니다. 행을 누르면 최신 논문을 필터링합니다.</p></div></section>
      <section class="section sec-grid"><div class="sec-side"><p class="eyebrow">08</p><h2>급상승 연구 키워드</h2></div><div class="sec-body"><div class="surge-grid">{emerging_keyword_html}</div><p class="chart-note">제목·공개 초록에서 기간별 100편당 출현 빈도가 증가한 단어와 구문입니다. 키워드를 누르면 최신 관련 논문만 표시합니다.</p></div></section>
      <section class="section sec-grid"><div class="sec-side"><p class="eyebrow">09</p><h2>내 관심 분야 추적기</h2></div><div class="sec-body"><div class="watch-grid">{watchlist_html}</div><p class="chart-note">누적 건수와 직전 주→현재 주 변화를 함께 표시합니다. 항목을 누르면 관련 최신 논문으로 이동합니다.</p></div></section>
      <section class="section sec-grid"><div class="sec-side"><p class="eyebrow">10</p><h2>상위 연구 키워드</h2></div><div class="sec-body"><div class="keyword-grid">{keyword_bars}</div></div></section>
      <section class="section sec-grid"><div class="sec-side"><p class="eyebrow">11</p><h2>최근 1주 DOI 등록 추이</h2></div><div class="sec-body"><div class="timeline" role="img" aria-label="{PERIOD_START}부터 {PERIOD_END}까지 일별 DOI 등록 논문 수">{timeline_bars}</div></div></section>
      <section class="section sec-grid"><div class="sec-side"><p class="eyebrow">12</p><h2>저널 × 연구 토픽 히트맵</h2></div><div class="sec-body">{matrix_html}</div></section>
      <section class="section sec-grid" id="paper-list"><div class="sec-side"><p class="eyebrow eyebrow-mark eyebrow-accent">Papers</p><h2>이번 주 논문</h2>
        <p class="note">제목은 DOI(출판사) 페이지로 연결됩니다. 위의 그래프·표를 누르면 해당 조건의 논문만 남습니다. 날짜는 Crossref DOI 등록일이며 온라인 공개일·권호일과 다를 수 있습니다.</p></div>
        <div class="sec-body" id="papers">{''.join(cards)}</div></section>
    </div></main>
    {site_theme.site_footer("papers", nav_prefix + "../", credit=nav_prefix == "./")}
    <script>
    (() => {{
      const buttons = [...document.querySelectorAll('.journal-filter')];
      const papers = [...document.querySelectorAll('.paper')];
      const points = [...document.querySelectorAll('.topic-scatter circle[data-journal]')];
      const visibleCount = document.getElementById('visible-count');
      const status = document.getElementById('filter-status');
      const statusLabel = document.getElementById('filter-label');
      const state = {{ journal: 'all', topic: '', keyword: '', watch: '', country: '', trend: '' }};
      function matches(item) {{
        return (state.journal === 'all' || item.dataset.journal === state.journal)
          && (!state.topic || item.dataset.topic === state.topic)
          && (!state.keyword || (item.dataset.title || '').includes(state.keyword))
          && (!state.watch || (item.dataset.watch || '').split('|').includes(state.watch))
          && (!state.trend || (item.dataset.trend || '').split('|').includes(state.trend))
          && (!state.country || (item.dataset.country || '').split('|').includes(state.country));
      }}
      function applyFilters(scrollToPapers = false) {{
        let count = 0;
        papers.forEach(paper => {{
          const show = matches(paper);
          paper.hidden = !show;
          if (show) count += 1;
        }});
        points.forEach(point => {{
          const selected = matches(point);
          const filtering = state.journal !== 'all' || state.topic || state.keyword || state.watch || state.country || state.trend;
          point.classList.toggle('is-dimmed', filtering && !selected);
          point.classList.toggle('is-selected', filtering && selected);
        }});
        buttons.forEach(button => {{
          const selected = button.dataset.journal === state.journal;
          button.classList.toggle('active', selected);
          button.setAttribute('aria-pressed', String(selected));
        }});
        visibleCount.textContent = count;
        const labels = [];
        if (state.journal !== 'all') labels.push(state.journal);
        if (state.topic) labels.push(state.topic);
        if (state.keyword) labels.push(`키워드: ${{state.keyword}}`);
        if (state.watch) labels.push(`관심 분야: ${{state.watch}}`);
        if (state.trend) labels.push(`트렌드: ${{state.trend}}`);
        if (state.country) labels.push(`국가: ${{state.country}}`);
        status.hidden = labels.length === 0;
        statusLabel.textContent = labels.length ? `${{labels.join(' · ')}} — ${{count}}편 표시` : '';
        if (scrollToPapers) document.getElementById('papers').scrollIntoView({{ behavior: 'smooth', block: 'start' }});
      }}
      function resetSecondaryFilters() {{ state.topic = ''; state.keyword = ''; state.watch = ''; state.country = ''; state.trend = ''; }}
      buttons.forEach(button => button.addEventListener('click', () => {{ state.journal = button.dataset.journal; applyFilters(); }}));
      document.querySelectorAll('.topic-trigger').forEach(button => button.addEventListener('click', () => {{ resetSecondaryFilters(); state.topic = button.dataset.topic; applyFilters(true); }}));
      document.querySelectorAll('.keyword-trigger').forEach(button => button.addEventListener('click', () => {{ resetSecondaryFilters(); state.keyword = button.dataset.keyword.toLowerCase(); applyFilters(true); }}));
      document.querySelectorAll('.trend-trigger').forEach(button => button.addEventListener('click', () => {{ resetSecondaryFilters(); state.trend = button.dataset.trend; applyFilters(true); }}));
      document.querySelectorAll('.watch-trigger').forEach(button => button.addEventListener('click', () => {{ resetSecondaryFilters(); state.watch = button.dataset.watch; applyFilters(true); }}));
      document.querySelectorAll('.country-trigger').forEach(button => button.addEventListener('click', () => {{ resetSecondaryFilters(); state.country = button.dataset.country; applyFilters(true); }}));
      document.querySelectorAll('.journal-country-trigger').forEach(button => button.addEventListener('click', () => {{ resetSecondaryFilters(); state.journal = button.dataset.journal; state.country = button.dataset.country; applyFilters(true); }}));
      document.querySelectorAll('.matrix-trigger').forEach(button => button.addEventListener('click', () => {{ resetSecondaryFilters(); state.journal = button.dataset.journal; state.topic = button.dataset.topic; applyFilters(true); }}));
      {wordcloud.KEY_JS}
      document.getElementById('reset-filter').addEventListener('click', () => {{ state.journal = 'all'; resetSecondaryFilters(); applyFilters(); }});
    }})();
    </script>
    </body></html>"""

    return document
