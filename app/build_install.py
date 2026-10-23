"""Install page (docs/install.html): how to open the site on the web and add it to the home screen as an app.

Chrome / Edge / Samsung Internet fire `beforeinstallprompt`, so the page shows a real 「앱 설치하기」 button there.
iPhone Safari has no such event, so the page shows the Share -> 「홈 화면에 추가」 steps instead.
Installing needs the site to be served over https (GitHub Pages); opened as a local file the page says so.
"""
from .config import DOCS_DIR, SITE
from .site_theme import esc, head, page_header, site_footer, site_header

INSTALL_CSS = """
.inst-hero{display:grid;gap:1px;border:1px solid var(--color-line);background:var(--color-line);grid-template-columns:minmax(0,1fr)}
@media(min-width:860px){.inst-hero{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}}
.inst-card{background:var(--color-card);padding:1.75rem 1.5rem}
.inst-card h2{margin:1rem 0 .4rem;font-size:1.25rem;font-weight:600;color:var(--color-ink)}
.inst-card p{margin:.4rem 0 0;font-size:.9375rem;line-height:1.8;color:var(--color-neutral-700)}
.inst-app{display:flex;align-items:center;gap:1rem;margin:1.25rem 0 0}
.inst-app img{width:64px;height:64px;border-radius:14px}
.inst-app b{display:block;font-size:1rem;color:var(--color-ink)}.inst-app small{font-size:.8125rem;color:var(--color-neutral-500)}
.inst-btn{display:inline-flex;align-items:center;justify-content:center;height:3rem;padding:0 1.4rem;margin-top:1.25rem;border:0;
  background:var(--color-navy);color:#fff;font:inherit;font-weight:600;font-size:.9375rem;cursor:pointer;text-decoration:none}
:root[data-theme="dark"] .inst-btn{background:var(--color-accent);color:var(--color-canvas)}
.inst-btn[hidden]{display:none}
.inst-url{display:flex;flex-wrap:wrap;gap:.5rem;align-items:center;margin-top:1rem}
.inst-url code{padding:.55rem .75rem;border:1px solid var(--color-line-strong);background:var(--color-surface);font-size:.875rem;word-break:break-all}
.inst-msg{margin:1rem 0 0;padding:.8rem 1rem;border-left:3px solid var(--color-accent);background:var(--color-accent-soft);font-size:.875rem;line-height:1.7;color:var(--color-neutral-800)}
.inst-msg[hidden]{display:none}
.steps{display:grid;gap:1px;border:1px solid var(--color-line);background:var(--color-line);grid-template-columns:minmax(0,1fr)}
@media(min-width:860px){.steps{grid-template-columns:repeat(3,minmax(0,1fr))}}
.step-card{background:var(--color-card);padding:1.5rem}
.step-card.here{outline:2px solid var(--color-accent);outline-offset:-2px}
.step-card h3{margin:0 0 .25rem;font-size:1rem;font-weight:700;color:var(--color-ink)}
.step-card .who{font-size:.75rem;color:var(--color-neutral-500)}
.step-card ol{margin:1rem 0 0;padding-left:1.2rem;font-size:.875rem;line-height:1.9;color:var(--color-neutral-800)}
.step-card .here-tag{display:none;margin-left:.4rem;font-size:.6875rem;font-weight:600;color:var(--color-accent)}
.step-card.here .here-tag{display:inline}
.faq{margin:0;padding:0;list-style:none}
.faq li{padding:1rem 0;border-top:1px solid var(--color-line);font-size:.875rem;line-height:1.8;color:var(--color-neutral-700)}
.faq b{display:block;color:var(--color-ink);font-size:.9375rem}
"""

SCRIPT = """
(function(){
  var btn=document.getElementById('inst-btn'), msg=document.getElementById('inst-msg'), deferred=null;
  var ua=navigator.userAgent, ios=/iPhone|iPad|iPod/.test(ua)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
  var android=/Android/.test(ua), standalone=matchMedia('(display-mode: standalone)').matches||navigator.standalone;
  var card=document.getElementById(ios?'step-ios':android?'step-android':'step-pc'); if(card) card.classList.add('here');
  function say(t){msg.hidden=false;msg.textContent=t;}
  if(standalone){say('지금 앱으로 열려 있습니다. 이미 설치되어 있어요.');return;}
  if(location.protocol==='file:'){say('지금은 컴퓨터의 파일로 열려 있어 설치할 수 없습니다. 사이트가 인터넷 주소(https)로 올라간 뒤 그 주소에서 설치하세요.');return;}
  if(ios){say('아이폰·아이패드는 아래 「아이폰」 방법대로 사파리의 공유 버튼에서 「홈 화면에 추가」를 누르세요.');return;}
  addEventListener('beforeinstallprompt',function(e){e.preventDefault();deferred=e;btn.hidden=false;msg.hidden=true;});
  addEventListener('appinstalled',function(){btn.hidden=true;say('설치되었습니다. 홈 화면이나 시작 메뉴에서 열 수 있어요.');});
  btn.addEventListener('click',function(){if(!deferred)return;deferred.prompt();deferred.userChoice.then(function(){deferred=null;btn.hidden=true;});});
  setTimeout(function(){if(!deferred&&btn.hidden)say('설치 버튼이 보이지 않으면 아래 방법대로 브라우저 메뉴에서 설치하세요. (이미 설치했거나, 지원하지 않는 브라우저일 수 있습니다)');},2500);
  var copy=document.getElementById('copy-url');
  if(copy&&navigator.clipboard)copy.addEventListener('click',function(){navigator.clipboard.writeText(copy.dataset.url).then(function(){copy.textContent='복사됨';});});
})();
"""


def build_install():
    url = SITE["site_url"]
    placeholder = "YOUR-GITHUB-ID" in url
    name = SITE.get("app_name") or SITE["title"]
    url_html = (
        '<p class="inst-msg">사이트 주소는 GitHub에 올린 뒤 정해집니다.</p>' if placeholder else
        f'<div class="inst-url"><code>{esc(url)}</code>'
        f'<button type="button" class="btn" id="copy-url" data-url="{esc(url)}">주소 복사</button></div>'
    )
    lead = "브라우저로 바로 보거나, 휴대폰·PC에 앱처럼 설치해 아이콘으로 열 수 있습니다. 설치 파일이나 앱스토어는 필요 없고 무료입니다."
    body = f"""
<section class="section"><div class="inst-hero">
  <div class="inst-card"><p class="eyebrow eyebrow-mark eyebrow-accent">Web</p><h2>웹으로 보기</h2>
    <p>어떤 브라우저든 아래 주소로 들어오면 됩니다. 즐겨찾기에 넣어 두세요.</p>{url_html}</div>
  <div class="inst-card"><p class="eyebrow eyebrow-mark eyebrow-accent">App</p><h2>앱으로 설치</h2>
    <div class="inst-app"><img src="icons/icon-192.png" alt=""><div><b>{esc(name)}</b><small>매일 원자력 뉴스 · 매주 논문 동향</small></div></div>
    <button type="button" class="inst-btn" id="inst-btn" hidden>앱 설치하기</button>
    <p class="inst-msg" id="inst-msg" role="status" hidden></p></div>
</div></section>

<section class="section"><p class="eyebrow eyebrow-mark">How to install</p>
<h2 style="margin:1rem 0 1.25rem;font-size:1.375rem;font-weight:600;color:var(--color-ink)">기기별 설치 방법</h2>
<div class="steps">
  <div class="step-card" id="step-android"><h3>안드로이드<span class="here-tag">지금 기기</span></h3><span class="who">크롬 · 삼성 인터넷</span><ol>
    <li>크롬에서 사이트 주소를 엽니다.</li><li>위의 「앱 설치하기」 버튼을 누르거나, 오른쪽 위 ⋮ 메뉴 → 「앱 설치」 (또는 「홈 화면에 추가」).</li>
    <li>「설치」를 누르면 홈 화면에 아이콘이 생깁니다.</li></ol></div>
  <div class="step-card" id="step-ios"><h3>아이폰 · 아이패드<span class="here-tag">지금 기기</span></h3><span class="who">사파리</span><ol>
    <li><b>사파리</b>에서 사이트 주소를 엽니다. (다른 브라우저 앱은 iOS 버전에 따라 안 될 수 있어요)</li>
    <li>아래쪽 가운데 <b>공유 버튼</b>(네모에 위 화살표)을 누릅니다.</li>
    <li>목록을 내려 「<b>홈 화면에 추가</b>」 → 오른쪽 위 「추가」.</li></ol></div>
  <div class="step-card" id="step-pc"><h3>PC · 맥<span class="here-tag">지금 기기</span></h3><span class="who">크롬 · 엣지</span><ol>
    <li>크롬이나 엣지에서 사이트 주소를 엽니다.</li>
    <li>위의 「앱 설치하기」 버튼을 누르거나, 주소창 오른쪽의 설치 아이콘(⊕ 또는 모니터 모양)을 누릅니다.</li>
    <li>시작 메뉴·바탕화면(맥은 Launchpad)에서 별도 창으로 열립니다.</li></ol></div>
</div></section>

<section class="section sec-grid"><div class="sec-side"><p class="eyebrow">FAQ</p><h2>자주 묻는 것</h2></div><div class="sec-body"><ul class="faq">
  <li><b>업데이트는 어떻게 하나요?</b>필요 없습니다. 뉴스는 매일, 논문은 매주 사이트에서 자동으로 바뀌고, 앱은 열 때마다 최신 내용을 받아옵니다.</li>
  <li><b>인터넷이 없을 때도 열리나요?</b>마지막으로 본 페이지는 열립니다. 새 내용은 다시 연결되면 받아옵니다.</li>
  <li><b>지우려면?</b>안드로이드·아이폰은 아이콘을 길게 눌러 삭제, PC는 앱 창의 ⋯ 메뉴 → 「제거」.</li>
  <li><b>개인정보를 모으나요?</b>아니요. 로그인·회원가입이 없고, 밝은/어두운 화면 선택만 기기 안에 저장됩니다.</li>
</ul></div></section>
"""
    page = (
        f'<!doctype html><html lang="ko"><head>{head("앱 설치 | " + SITE["title"], lead, INSTALL_CSS)}</head><body>'
        f'{site_header("install", "./")}{page_header("Install", "웹으로 보기 · 앱으로 설치", lead)}'
        f'<main class="page"><div class="container-page">{body}</div></main>{site_footer("home", "./")}'
        f"<script>{SCRIPT}</script></body></html>"
    )
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "install.html").write_text(page, encoding="utf-8")
    return DOCS_DIR / "install.html"


if __name__ == "__main__":
    print(build_install())
