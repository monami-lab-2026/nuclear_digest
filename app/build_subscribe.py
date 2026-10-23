"""Subscribe page (docs/subscribe.html), opened by the "이메일로 받기" button at the top of every page.

The form posts straight to Buttondown, which stores the address, sends the confirmation email and
handles unsubscribing. Nothing is stored on this site.

    python -m app.build_subscribe
"""
from .config import DOCS_DIR, SITE
from .newsletter import LISTS, settings, turned_on
from .site_theme import esc, head, page_header, site_footer, site_header

SUBSCRIBE_CSS = """
.sub-wrap{max-width:36rem}
.sub-form{display:grid;gap:1.25rem;padding:1.75rem;border:1px solid var(--color-line-strong);background:var(--color-card)}
.sub-form label.field{display:grid;gap:.5rem;font-size:.875rem;font-weight:600;color:var(--color-ink)}
.sub-form input[type=email]{font:inherit;font-size:1rem;height:3rem;padding:0 .9rem;border:1px solid var(--color-line-strong);background:var(--color-canvas);color:var(--color-neutral-900)}
.sub-form input[type=email]:focus{outline:2px solid var(--color-accent);outline-offset:1px}
.sub-form fieldset{margin:0;padding:0;border:0;display:grid;gap:.6rem}
.sub-form legend{margin-bottom:.6rem;font-size:.875rem;font-weight:600;color:var(--color-ink)}
.sub-form .opt{display:grid;grid-template-columns:auto 1fr;gap:.25rem .7rem;align-items:start;padding:.85rem 1rem;border:1px solid var(--color-line);cursor:pointer}
.sub-form .opt:has(input:checked){border-color:var(--color-accent);background:var(--color-accent-soft)}
.sub-form .opt input{margin:.2rem 0 0;width:1.05rem;height:1.05rem;accent-color:var(--color-accent)}
.sub-form .opt b{font-size:.9375rem;color:var(--color-ink)}
.sub-form .opt small{grid-column:2;font-size:.8125rem;color:var(--color-neutral-600)}
.sub-form button{height:3rem;border:0;background:var(--color-navy);color:#fff;font:inherit;font-weight:600;font-size:.9375rem;cursor:pointer}
:root[data-theme="dark"] .sub-form button{background:var(--color-accent);color:var(--color-canvas)}
.sub-form button[disabled]{opacity:.5;cursor:default}
.sub-msg{margin:0;font-size:.8125rem;color:var(--color-accent)}.sub-msg[hidden]{display:none}
.sub-notes{margin:1.5rem 0 0;padding:0;list-style:none;font-size:.8125rem;line-height:1.8;color:var(--color-neutral-600)}
.sub-notes li::before{content:"· ";color:var(--color-accent)}
.notice{margin:0 0 1.5rem;padding:.9rem 1.1rem;border-left:3px solid var(--color-accent);background:var(--color-accent-soft);font-size:.875rem;line-height:1.7;color:var(--color-neutral-800)}
"""

DESCRIPTIONS = {
    "news": "해설이 올라오는 날 아침, 그날의 원자력 뉴스와 공학적 의미",
    "papers": "월요일 아침, 주요 저널 신규 논문 동향과 관심 분야별 논문",
}


def form_html():
    config = settings()
    username = config.get("username", "").strip()
    choose = config.get("choose_lists", False)
    disabled = "" if username else " disabled"
    action = f"https://buttondown.com/api/emails/embed-subscribe/{esc(username)}" if username else "#"
    if choose:
        options = "".join(
            f'<label class="opt"><input type="checkbox" name="tag" value="{key}" checked><b>{esc(label)}</b>'
            f"<small>{esc(DESCRIPTIONS[key])}</small></label>"
            for key, label in LISTS.items()
        )
        lists = f'<fieldset><legend>받을 내용 (하나 이상)</legend>{options}</fieldset>'
    else:
        items = "".join(f"<li>{esc(label)}: {esc(DESCRIPTIONS[key])}</li>" for key, label in LISTS.items())
        lists = f'<div><p class="eyebrow" style="margin-bottom:.75rem">받는 내용</p><ul class="sub-notes" style="margin:0">{items}</ul></div>'
    script = (
        "(function(){var f=document.getElementById('sub-form');if(!f)return;var m=document.getElementById('sub-msg');"
        "f.addEventListener('submit',function(e){var boxes=f.querySelectorAll('input[name=tag]');"
        "if(boxes.length&&!Array.prototype.some.call(boxes,function(b){return b.checked})){e.preventDefault();"
        "m.hidden=false;m.textContent='받을 내용을 하나 이상 골라 주세요.';return;}"
        "m.hidden=false;m.textContent='새 창에서 신청이 진행됩니다. 받은편지함의 확인 메일을 눌러야 구독이 완료됩니다.';});})();"
    )
    pending = "" if username else '<p class="notice">구독 기능을 준비하고 있습니다. 곧 신청할 수 있습니다.</p>'
    return (
        f'{pending}<form class="sub-form" id="sub-form" action="{action}" method="post" target="_blank">'
        f'<label class="field">이메일 주소<input type="email" name="email" required autocomplete="email" placeholder="you@example.com"{disabled}></label>'
        f'{lists}<input type="hidden" name="embed" value="1">'
        f'<button type="submit"{disabled}>구독 신청</button><p class="sub-msg" id="sub-msg" role="status" hidden></p></form>'
        f"<script>{script}</script>"
    )


REDIRECT = ('<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta http-equiv="refresh" content="0; url=index.html">'
            '<title>이동 중</title></head><body><a href="index.html">홈으로</a></body></html>')


def build_subscribe():
    if not turned_on():
        # Feature off: no page to subscribe on. A redirect (not a deletion) keeps old links working.
        (DOCS_DIR / "subscribe.html").write_text(REDIRECT, encoding="utf-8")
        return DOCS_DIR / "subscribe.html"
    lead = "새 브리핑과 논문 동향이 올라오면 메일로 알려 드립니다. 언제든 메일 하단의 링크로 구독을 끊을 수 있습니다."
    notes = (
        '<ul class="sub-notes"><li>신청하면 확인 메일이 갑니다. 그 메일의 링크를 눌러야 구독이 시작됩니다.</li>'
        "<li>이메일 주소는 뉴스레터 서비스(Buttondown)에만 저장되며, 이 사이트에는 저장되지 않습니다.</li>"
        "<li>뉴스 메일은 AI 해설이 올라온 날에만 보냅니다.</li></ul>"
    )
    page = (
        f'<!doctype html><html lang="ko"><head>{head("이메일로 받기 | " + SITE["title"], lead, SUBSCRIBE_CSS)}'
        f'</head><body>'
        f'{site_header("subscribe", "./")}{page_header("Subscribe", "이메일로 받기", lead)}'
        f'<main class="page"><div class="container-page"><div class="sub-wrap">{form_html()}{notes}</div></div></main>'
        f'{site_footer("home", "./")}</body></html>'
    )
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "subscribe.html").write_text(page, encoding="utf-8")
    return DOCS_DIR / "subscribe.html"


if __name__ == "__main__":
    print(build_subscribe())
