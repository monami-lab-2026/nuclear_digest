"""Inline-HTML email body (no attachments). Ported from the Codex build_email_digest.py."""
import html
from collections import Counter

from .common import SETTINGS, topics_for


def esc(value):
    return html.escape(str(value or ""), quote=True)


def render(period, records, previous_records, total_papers, total_runs):
    fallback = SETTINGS["fallback_topic"]
    current_topics = Counter(topics_for(r)[0] for r in records)
    previous_topics = Counter(topics_for(r)[0] for r in previous_records)
    journals = Counter({name: 0 for name in SETTINGS["journals"]})
    journals.update(r["journal"] for r in records)
    all_topics = sorted(set(current_topics) | set(previous_topics), key=lambda t: (-current_topics[t], -previous_topics[t], t == fallback, t))

    def delta_cell(delta):
        color = "#087f5b" if delta > 0 else "#c92a2a" if delta < 0 else "#627d98"
        return f'<td style="padding:7px 8px;border-bottom:1px solid #e6edf3;text-align:right;font-weight:700;color:{color}">{delta:+d}</td>'

    td = 'style="padding:7px 8px;border-bottom:1px solid #e6edf3"'
    tdr = 'style="padding:7px 8px;border-bottom:1px solid #e6edf3;text-align:right"'
    topic_rows = "".join(
        f"<tr><td {td}>{esc(t)}</td><td {tdr}><span style=\"color:#627d98\">{previous_topics[t]}</span></td>"
        f"<td {tdr}><strong>{current_topics[t]}</strong></td>{delta_cell(current_topics[t] - previous_topics[t])}</tr>"
        for t in all_topics
    )
    journal_rows = "".join(f"<tr><td {td}>{esc(j)}</td><td {tdr}><strong>{c}</strong></td></tr>" for j, c in journals.most_common())

    paper_rows = []
    for i, r in enumerate(records, 1):
        authors = ", ".join(r["authors"][:5]) + (" et al." if len(r["authors"]) > 5 else "")
        paper_rows.append(
            f'<tr><td style="padding:12px 8px;border-bottom:1px solid #d9e2ec;vertical-align:top;color:#0b6bcb;font-weight:700">{i:03d}</td>'
            f'<td style="padding:12px 8px;border-bottom:1px solid #d9e2ec;vertical-align:top">'
            f'<a href="{esc(r["doi_url"])}" style="color:#075985;font-weight:700;text-decoration:none">{esc(r["title"])}</a>'
            f'<div style="margin-top:4px;color:#102a43">{esc(r["title_ko"])}</div>'
            f'<div style="margin-top:6px;font-size:12px;color:#627d98">{esc(authors)}</div>'
            f'<div style="margin-top:5px;font-size:12px;color:#52677b">{esc(r["journal"])} · {esc(topics_for(r)[0])} · DOI 등록 {esc(r["registered_date"])}</div>'
            f"</td></tr>"
        )

    url = SETTINGS.get("dashboard_url")
    button = (
        f'<div style="margin-top:16px"><a href="{esc(url)}" style="display:inline-block;background:#ffffff;color:#075985;'
        f'text-decoration:none;font-weight:700;padding:10px 16px;border-radius:7px">대화형 대시보드 열기</a></div>'
        if url else ""
    )
    card = 'style="background:#ffffff;border:1px solid #d9e2ec;padding:16px;margin:12px 0"'
    h2 = 'style="margin:0 0 9px;font-size:18px;color:#102a43"'
    stat = 'style="width:33%;background:#ffffff;border:1px solid #d9e2ec;padding:13px;text-align:center"'
    big = 'style="display:block;font-size:24px;color:#102a43"'
    th = 'style="padding:7px 8px;background:#eaf4ff'
    p, pp = period, period.previous
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;background:#f5f8fb;color:#243b53;font-family:Arial,'Noto Sans KR','Malgun Gothic',sans-serif;line-height:1.55">
<div style="max-width:760px;margin:0 auto;padding:22px 12px">
  <div style="background:#102a43;color:#ffffff;padding:24px;border-radius:12px">
    <h1 style="margin:0 0 8px;font-size:25px">원자력공학 최근 논문 다이제스트</h1>
    <div style="color:#d9edff">{p.start} ~ {p.end} · 최근 1주 DOI 신규 등록 기준</div>{button}
  </div>
  <table role="presentation" style="width:100%;border-collapse:separate;border-spacing:8px;margin:12px 0"><tr>
    <td {stat}><strong {big}>{total_papers}</strong>누적 논문</td>
    <td {stat}><strong {big}>{len(records)}</strong>이번 주 신규 논문</td>
    <td {stat}><strong {big}>{total_runs}</strong>수집 회차</td>
  </tr></table>
  <div {card}><h2 {h2}>주간 연구 토픽 변화</h2>
    <p style="margin:0 0 8px;color:#627d98;font-size:12px">{pp.start}~{pp.end} 대비 {p.start}~{p.end}</p>
    <table style="width:100%;border-collapse:collapse;font-size:13px"><thead><tr><th {th};text-align:left">토픽</th><th {th};text-align:right">직전</th><th {th};text-align:right">현재</th><th {th};text-align:right">변화</th></tr></thead><tbody>{topic_rows}</tbody></table>
  </div>
  <div {card}><h2 {h2}>저널별 신규 논문</h2><table style="width:100%;border-collapse:collapse;font-size:13px">{journal_rows}</table></div>
  <div {card}><h2 style="margin:0 0 4px;font-size:18px;color:#102a43">최신 논문 {len(records)}편</h2>
    <p style="margin:0 0 8px;color:#627d98;font-size:12px">제목을 누르면 DOI 페이지(출판사)로 이동합니다.</p>
    <table style="width:100%;border-collapse:collapse;font-size:13px">{''.join(paper_rows)}</table>
  </div>
  <p style="color:#627d98;font-size:11px;text-align:center">수집 기준: Crossref DOI created date. 온라인 공개일·권호일과 다를 수 있습니다. 토픽은 제목·초록 키워드 규칙으로 분류합니다.</p>
</div></body></html>"""
