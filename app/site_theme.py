"""One look for every page of the site (news + papers).

Design tokens come from the original Nuclear_News / PaperCollection pages: light/dark via <html data-theme>,
no shadows or rounded corners (pill tags are the exception), one accent color, Pretendard.
Branding (title, subtitle, links) comes from config/site.json.

Every page passes `root`, the relative path from that page to the docs/ folder ("./", "../", "../../"),
so the same menu works from any depth.
"""
import html

from .config import SITE

THEME_STORAGE_KEY = "nuclear-digest-theme"

# Categorical series for topic identity (dataviz reference palette, validated for light #ffffff and
# dark #161b23 surfaces with scripts/validate_palette.js). "기타 원자력" is the Other bucket -> neutral.
TOPIC_SERIES = ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8"]

TOKENS_CSS = """
:root{
  --color-neutral-50:#f7f8fa;--color-neutral-100:#eef0f3;--color-neutral-200:#dcdfe4;--color-neutral-300:#c3c8d1;
  --color-neutral-400:#9aa3b2;--color-neutral-500:#666d7b;--color-neutral-600:#4b5462;--color-neutral-700:#3c414b;
  --color-neutral-800:#262b34;--color-neutral-900:#16181d;
  --color-line:#dcdfe4;--color-line-strong:#c3c8d1;--color-surface:#f5f6f8;--color-surface-deep:#eef0f3;
  --color-canvas:#ffffff;--color-card:#ffffff;--color-ink:#1b2a41;
  --color-navy:#1b2a41;--color-navy-deep:#121c2b;--color-navy-mid:#2e4365;
  --color-accent:#007a45;--color-accent-mid:#00a35c;--color-accent-soft:#d6ffed;
  --veil-line:rgba(27,42,65,.045);
  --chart:#2e4365;
  --s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;--s5:#e87ba4;--s6:#008300;--s7:#4a3aa7;--s8:#e34948;--s-other:#9aa3b2;
  --font-sans:"Pretendard Variable",Pretendard,-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Segoe UI",Roboto,"Noto Sans KR","Malgun Gothic",sans-serif;
  --ease:cubic-bezier(.16,1,.3,1);
}
:root[data-theme="dark"]{color-scheme:dark;
  --color-neutral-50:#1a1f28;--color-neutral-100:#212734;--color-neutral-200:#2a313d;--color-neutral-300:#444e5d;
  --color-neutral-400:#7f8a9c;--color-neutral-500:#98a2b3;--color-neutral-600:#b4bdca;--color-neutral-700:#c9d1dc;
  --color-neutral-800:#dde3ea;--color-neutral-900:#eef1f5;
  --color-line:#2a313d;--color-line-strong:#3a4452;--color-surface:#1b212b;--color-surface-deep:#222a35;
  --color-canvas:#0f1319;--color-card:#161b23;--color-ink:#e9eef6;
  --color-accent:#2ce68f;--color-accent-mid:#00c46f;--color-accent-soft:#0e2f22;
  --veil-line:rgba(255,255,255,.05);
  --chart:#98a2b3;
  --s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181;--s6:#008300;--s7:#9085e9;--s8:#e66767;--s-other:#7f8a9c;
}
"""

BASE_CSS = """
*{box-sizing:border-box}
html{scroll-padding-top:5rem;-webkit-text-size-adjust:100%}
body{margin:0;background:var(--color-canvas);color:var(--color-neutral-900);font-family:var(--font-sans);
  line-height:1.6;-webkit-font-smoothing:antialiased;word-break:keep-all;overflow-wrap:break-word}
::selection{background:var(--color-navy);color:#fff}
:focus-visible{outline:2px solid var(--color-accent);outline-offset:3px;border-radius:2px}
a{color:inherit}
time,.tabular{font-variant-numeric:tabular-nums}
.container-page{width:100%;max-width:72rem;margin-inline:auto;padding-inline:1.25rem}
@media(min-width:768px){.container-page{padding-inline:2rem}}
@media(min-width:1280px){.container-page{padding-inline:2.5rem}}
.eyebrow{font-size:.6875rem;line-height:1;letter-spacing:.18em;text-transform:uppercase;font-weight:500;color:var(--color-neutral-500);margin:0}
.eyebrow-accent{color:var(--color-accent)}
.eyebrow-mark::before{content:"";display:inline-block;width:2rem;height:3px;margin-right:.75rem;vertical-align:.2em;background:var(--color-accent)}
.grid-veil-light{background-image:linear-gradient(to right,var(--veil-line) 1px,transparent 1px),linear-gradient(to bottom,var(--veil-line) 1px,transparent 1px);background-size:34px 34px}
.link-underline{text-decoration:underline;text-underline-offset:3px;text-decoration-thickness:1px;
  text-decoration-color:color-mix(in srgb,var(--color-accent) 45%,transparent);transition:text-decoration-color 150ms ease}
.link-underline:hover{text-decoration-color:var(--color-accent)}
.link-wipe{text-decoration:none;background-image:linear-gradient(var(--color-accent),var(--color-accent));background-repeat:no-repeat;
  background-position:0 100%;background-size:0% 1.5px;transition:background-size 320ms var(--ease)}
.link-wipe:hover,.group:hover .link-wipe{background-size:100% 1.5px}

/* site header — same geometry as the homepage (h-16 / md:h-20, sticky, 85% canvas + blur) */
.site-header{position:sticky;top:0;z-index:50;border-bottom:1px solid var(--color-line);
  background:color-mix(in srgb,var(--color-canvas) 85%,transparent);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px)}
.site-bar{display:flex;align-items:center;justify-content:space-between;gap:1rem;height:4rem}
@media(min-width:768px){.site-bar{height:5rem}}
.wordmark{display:flex;flex-direction:column;text-decoration:none;min-width:0}
.wordmark b{font-size:.9375rem;line-height:1;font-weight:700;letter-spacing:.02em;color:var(--color-neutral-900)}
.wordmark span{margin-top:.375rem;font-size:.6875rem;line-height:1;color:var(--color-neutral-500);white-space:nowrap}
.site-nav{display:flex;align-items:center;gap:1.5rem}
.site-nav a.item{position:relative;font-size:.875rem;font-weight:500;color:var(--color-neutral-600);text-decoration:none;padding:.25rem 0;white-space:nowrap}
.site-nav a.item:hover{color:var(--color-neutral-900)}
.site-nav a.item[aria-current="page"]{color:var(--color-neutral-900)}
.site-nav a.item[aria-current="page"]::after{content:"";position:absolute;left:0;right:0;bottom:-.35rem;height:2px;background:var(--color-accent)}
.site-nav .home{font-size:.75rem;color:var(--color-neutral-500);text-decoration:none;border:1px solid var(--color-line);padding:.45rem .7rem;white-space:nowrap}
.site-nav .home:hover{color:var(--color-neutral-900);border-color:var(--color-line-strong)}
.site-nav a.subscribe{font-size:.8125rem;font-weight:600;color:var(--color-accent);text-decoration:none;border:1px solid var(--color-accent);padding:.45rem .75rem;white-space:nowrap}
.site-nav a.subscribe:hover,.site-nav a.subscribe[aria-current="page"]{background:var(--color-accent-soft)}
.theme-toggle{display:inline-flex;align-items:center;justify-content:center;width:2rem;height:2rem;border:1px solid var(--color-line);
  background:transparent;color:var(--color-neutral-600);cursor:pointer;padding:0}
.theme-toggle:hover{color:var(--color-neutral-900);border-color:var(--color-line-strong)}
.theme-toggle svg{width:15px;height:15px}
.theme-toggle .sun{display:none}:root[data-theme="dark"] .theme-toggle .sun{display:block}:root[data-theme="dark"] .theme-toggle .moon{display:none}
@media(max-width:767px){.site-bar{height:auto;padding-block:.75rem;flex-wrap:wrap}.site-nav{gap:1rem;flex-wrap:wrap;width:100%}
  .site-nav .home{margin-left:auto}.wordmark span{white-space:normal}}

/* page header (6-5): eyebrow, title, 64x4 accent bar, veil fading to the top-right */
.page-head{position:relative;overflow:hidden;border-bottom:1px solid var(--color-line);padding:3rem 0 2.5rem}
@media(min-width:768px){.page-head{padding:4rem 0 3rem}}
.page-head .veil{position:absolute;inset:0;pointer-events:none;-webkit-mask-image:radial-gradient(90% 120% at 100% 0%,#000,transparent 65%);mask-image:radial-gradient(90% 120% at 100% 0%,#000,transparent 65%)}
.page-head .inner{position:relative}
.page-head h1{margin:1.25rem 0 0;max-width:48rem;font-size:1.875rem;line-height:1.25;font-weight:600;letter-spacing:-.02em;color:var(--color-ink);text-wrap:balance}
@media(min-width:768px){.page-head h1{font-size:3rem}}
.page-head .rule{display:block;margin-top:1.5rem;width:4rem;height:4px;background:var(--color-accent)}
.page-head .lead{margin:1.5rem 0 0;max-width:42rem;font-size:.975rem;line-height:1.9;color:var(--color-neutral-700)}
.page-head .lead b{font-weight:600;color:var(--color-ink)}

/* building blocks */
main.page{padding:2.5rem 0 5rem}
.section{border-top:1px solid var(--color-line);padding:2.5rem 0}
.section:first-child{border-top:0;padding-top:0}
.sec-grid{display:grid;gap:1.5rem;grid-template-columns:minmax(0,1fr)}
@media(min-width:900px){.sec-grid{grid-template-columns:repeat(12,minmax(0,1fr));gap:2.5rem}.sec-grid>.sec-side{grid-column:span 4}.sec-grid>.sec-body{grid-column:span 8;min-width:0}}
.sec-side h2{margin:1rem 0 0;font-size:1.375rem;line-height:1.3;font-weight:600;letter-spacing:-.015em;color:var(--color-ink);text-wrap:balance}
.sec-side p.note{margin:.75rem 0 0;font-size:.875rem;line-height:1.7;color:var(--color-neutral-600)}
.stats{display:grid;gap:1px;border:1px solid var(--color-line);background:var(--color-line);grid-template-columns:repeat(3,minmax(0,1fr))}
.stats>div{background:var(--color-card);padding:1.25rem 1.25rem 1.1rem}
.stats strong{display:block;font-size:1.75rem;line-height:1.1;font-weight:600;letter-spacing:-.02em;color:var(--color-ink);font-variant-numeric:tabular-nums}
.stats span{display:block;margin-top:.5rem;font-size:.75rem;color:var(--color-neutral-500)}
.pill{display:inline-flex;align-items:center;gap:.4rem;border:1px solid color-mix(in srgb,var(--color-accent) 25%,transparent);background:var(--color-accent-soft);
  border-radius:999px;padding:.3rem .65rem;font-size:.75rem;line-height:1;color:var(--color-neutral-700)}
.chip{display:inline-flex;align-items:center;gap:.45rem;border:1px solid var(--color-line);background:var(--color-card);border-radius:999px;
  padding:.45rem .8rem;font:inherit;font-size:.8125rem;line-height:1;color:var(--color-neutral-700);cursor:pointer;transition:border-color 150ms,color 150ms}
.chip:hover{border-color:var(--color-accent);color:var(--color-accent)}
.chip.active,.chip[aria-pressed="true"]{background:var(--color-navy);border-color:var(--color-navy);color:#fff}
:root[data-theme="dark"] .chip.active,:root[data-theme="dark"] .chip[aria-pressed="true"]{background:var(--color-ink);border-color:var(--color-ink);color:var(--color-canvas)}
.chip strong{font-weight:600;font-variant-numeric:tabular-nums}
.chip[disabled]{opacity:.45;cursor:default}.chip[disabled]:hover{border-color:var(--color-line);color:var(--color-neutral-700)}
.btn{display:inline-flex;align-items:center;border:1px solid var(--color-line);background:var(--color-card);color:var(--color-neutral-700);
  padding:.55rem .85rem;font:inherit;font-size:.8125rem;cursor:pointer}
.btn:hover{border-color:var(--color-line-strong);color:var(--color-neutral-900)}
.caption{margin:.75rem 0 0;font-size:.75rem;line-height:1.7;color:var(--color-neutral-500)}
.chart-note{margin:.75rem 0 0;font-size:.75rem;line-height:1.7;color:var(--color-neutral-500)}
.chart-note strong{color:var(--color-neutral-700)}
.site-footer{border-top:1px solid var(--color-line);padding:3.5rem 0}
.site-footer .cols{display:grid;gap:2rem}
@media(min-width:768px){.site-footer .cols{grid-template-columns:5fr 4fr 3fr}}
.site-footer p{margin:0;font-size:.875rem;line-height:1.7;color:var(--color-neutral-600)}
.site-footer .name{font-weight:700;letter-spacing:.02em;color:var(--color-neutral-900);margin-bottom:.75rem}
.site-footer .eyebrow{margin-bottom:1rem}
.site-footer a{color:var(--color-neutral-600)}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{transition-duration:.001ms!important;animation-duration:.001ms!important}}
@media print{.site-header,.theme-toggle,.site-footer{display:none}}
"""

THEME_INIT = (
    "(function(){try{var v=localStorage.getItem(%r);var d=v==='dark'||(v!=='light'&&"
    "window.matchMedia('(prefers-color-scheme: dark)').matches);document.documentElement.dataset.theme=d?'dark':'light'}"
    "catch(e){document.documentElement.dataset.theme='light'}})();" % THEME_STORAGE_KEY
)

THEME_TOGGLE_JS = (
    "(function(){var b=document.getElementById('theme-toggle');if(!b)return;b.addEventListener('click',function(){"
    "var r=document.documentElement,n=r.dataset.theme==='dark'?'light':'dark';r.dataset.theme=n;"
    "try{localStorage.setItem(%r,n)}catch(e){}});})();" % THEME_STORAGE_KEY
)

SUN = '<svg class="sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>'
MOON = '<svg class="moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>'

# (key, label, path from docs/). One menu for the whole site, so news and papers feel like one app.
NAV = [("home", "홈", "index.html"), ("news", "오늘의 뉴스", "news/index.html"), ("news-archive", "뉴스 모아보기", "news/archive.html"),
       ("papers", "이번 주 논문", "papers/index.html"), ("database", "논문 DB", "papers/database.html"),
       ("jobs", "취업", "jobs/index.html")]


def esc(value):
    return html.escape(str(value or ""), quote=True)


def app_tags(root):
    """Home-screen app: manifest, icons, theme colour and the offline service worker (docs/sw.js)."""
    return (
        f'<link rel="manifest" href="{root}manifest.webmanifest">'
        '<meta name="theme-color" content="#1b2a41">'
        f'<link rel="icon" href="{root}icon.svg" type="image/svg+xml">'
        f'<link rel="apple-touch-icon" href="{root}icons/apple-touch-icon.png">'
        '<meta name="apple-mobile-web-app-capable" content="yes">'
        '<meta name="mobile-web-app-capable" content="yes">'
        f'<meta name="apple-mobile-web-app-title" content="{esc(SITE.get("app_name") or SITE["title"])}">'
        '<meta name="apple-mobile-web-app-status-bar-style" content="default">'
        "<script>if('serviceWorker' in navigator&&(location.protocol==='https:'||location.hostname==='localhost')){addEventListener('load',function(){"
        f"navigator.serviceWorker.register('{root}sw.js').catch(function(){{}});}});}}</script>"
    )


def head(title, description, extra_css="", root="./"):
    """`root` is the relative path from the page to docs/ (as in site_header)."""
    return f"""<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{esc(title)}</title><meta name="description" content="{esc(description)}">
{app_tags(root)}
<script>{THEME_INIT}</script>
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<style>{TOKENS_CSS}{BASE_CSS}{extra_css}</style>"""


def subscribe_button(active, root):
    newsletter = SITE.get("newsletter") or {}
    if newsletter.get("enabled", True) is False:
        return ""
    current = " aria-current=page" if active == "subscribe" else ""
    return f'<a class="subscribe" href="{root}subscribe.html"{current}>이메일로 받기</a>'


def install_button(active, root):
    current = " aria-current=page" if active == "install" else ""
    return f'<a class="subscribe" href="{root}install.html"{current}>앱 설치</a>'


def site_header(active, root="./"):
    items = "".join(
        f'<a class="item" href="{root}{href}"{" aria-current=page" if key == active else ""}>{label}</a>'
        for key, label, href in NAV
    )
    return f"""<header class="site-header"><div class="container-page site-bar">
<a class="wordmark" href="{root}index.html"><b>{esc(SITE["title"])}</b><span>{esc(SITE.get("subtitle", ""))}</span></a>
<nav class="site-nav" aria-label="사이트 메뉴">{items}
{subscribe_button(active, root)}{install_button(active, root)}
<button type="button" class="theme-toggle" id="theme-toggle" aria-label="밝은 화면/어두운 화면 전환">{SUN}{MOON}</button></nav>
</div></header>"""


def page_header(eyebrow, title, lead_html=""):
    lead = f'<p class="lead">{lead_html}</p>' if lead_html else ""
    return f"""<section class="page-head"><div class="veil grid-veil-light" aria-hidden="true"></div>
<div class="container-page inner"><p class="eyebrow eyebrow-mark eyebrow-accent">{eyebrow}</p>
<h1>{title}</h1><span class="rule" aria-hidden="true"></span>{lead}</div></section>"""


FOOTER_NOTES = {
    "news": ("만드는 방법 · 저작권", "매일 아침 국내외 뉴스 RSS에서 제목·매체·링크만 모으고, 해설은 Claude(AI)로 새로 씁니다. "
             "기사 본문·사진은 싣지 않으며 저작권은 각 언론사에 있습니다. AI 해설은 틀릴 수 있으니 중요한 내용은 원문으로 확인하세요."),
    "papers": ("수집 기준", "Crossref DOI 등록일(created) 기준 주간 수집 · 국가·Open Access·초록은 OpenAlex · "
               "토픽은 제목·초록 키워드 규칙 분류 · 한글 제목은 기계번역"),
    "jobs": ("수집 기준", "공공기관 공고는 공공데이터포털 「공공기관 채용정보 조회서비스」(잡알리오)에서 매주 월요일 아침 모읍니다. "
             "마감일·응시 자격은 바뀔 수 있으니 지원 전에 반드시 원문 공고를 확인하세요. 뉴스는 제목·링크만 싣습니다."),
    "home": ("구성", "매일 아침 원자력 뉴스 해설, 매주 월요일 주요 저널 신규 논문 동향을 한곳에서 봅니다."),
}


CREDIT_CSS = """
.site-credit{margin-top:2.5rem;border-top:1px solid var(--color-line);padding:1.25rem 0 1.5rem;font-size:.8125rem;line-height:1.9;color:var(--color-neutral-500)}
.site-credit a{color:var(--color-neutral-700)}
"""


def _linked(item):
    text = esc(item["text"])
    if item.get("url"):
        text = f'<a class="link-underline" href="{esc(item["url"])}" target="_blank" rel="noopener">{text}</a>'
    return text


def credit_line():
    """Bottom lines on the front pages: original source (credit) and current maintainer (maintainer)."""
    lines = [_linked(SITE[key]) for key in ("credit", "maintainer") if (SITE.get(key) or {}).get("text")]
    if not lines:
        return ""
    return (f'<style>{CREDIT_CSS}</style><div class="site-credit"><div class="container-page">'
            f'{"<br>".join(lines)}</div></div>')


def site_footer(section="home", root="./", credit=False):
    eyebrow, note = FOOTER_NOTES.get(section, FOOTER_NOTES["home"])
    owner = f"<br>{esc(SITE['owner'])}" if SITE.get("owner") else ""
    repo = SITE.get("repo_url", "")
    repo_link = f'<br><a class="link-underline" href="{esc(repo)}">수집 코드 (GitHub)</a>' if repo and "YOUR-GITHUB-ID" not in repo else ""
    return f"""<footer class="site-footer"><div class="container-page cols">
<div><p class="name">{esc(SITE["title"])}</p><p>{esc(SITE.get("subtitle", ""))}{owner}</p></div>
<div><p class="eyebrow">{eyebrow}</p><p>{note}</p></div>
<div><p class="eyebrow">바로 가기</p><p><a class="link-underline" href="{root}news/index.html">오늘의 뉴스</a><br>
<a class="link-underline" href="{root}papers/index.html">이번 주 논문</a><br>
<a class="link-underline" href="{root}jobs/index.html">원자력 취업</a><br>
<a class="link-underline" href="{root}papers/nuclear-literature-database.xlsx">논문 DB Excel</a>{repo_link}</p></div>
</div>{credit_line() if credit else ""}</footer><script>{THEME_TOGGLE_JS}</script>"""


DASHBOARD_CSS = """
.stats.four{grid-template-columns:repeat(4,minmax(0,1fr))}
@media(max-width:700px){.stats,.stats.four{grid-template-columns:repeat(2,minmax(0,1fr))}}
.journal-filters{display:flex;flex-wrap:wrap;gap:.5rem}

.type-summary,.type-tag,.tag{display:inline-flex;align-items:center;margin:0 .35rem .35rem 0;border-radius:999px;padding:.3rem .65rem;font-size:.75rem;line-height:1}
.tag{border:1px solid color-mix(in srgb,var(--color-accent) 25%,transparent);background:var(--color-accent-soft);color:var(--color-neutral-700)}
.type-tag,.type-summary{border:1px solid var(--color-line);background:var(--color-surface);color:var(--color-neutral-600)}
.type-summary strong{margin-right:.35rem;font-weight:600;color:var(--color-neutral-800)}
.bar-row{width:100%;display:grid;grid-template-columns:10rem 1fr 2.25rem;gap:.75rem;align-items:center;margin:0;padding:.45rem 0;border:0;border-bottom:1px solid var(--color-line);
  background:transparent;color:var(--color-neutral-700);font:inherit;font-size:.875rem;text-align:left}
.bar-row strong{text-align:right;font-weight:600;color:var(--color-ink);font-variant-numeric:tabular-nums}
.bar-track{height:.5rem;background:var(--color-surface-deep)}.bar-fill{height:100%;background:var(--chart)}
button.bar-row{cursor:pointer}button.bar-row:hover{color:var(--color-neutral-900)}button.bar-row:hover .bar-fill{background:var(--color-accent-mid)}
.trend-head{display:grid;grid-template-columns:9rem 1fr 1fr 4rem;gap:.75rem;color:var(--color-neutral-500);font-size:.6875rem;padding:0 0 .5rem;border-bottom:1px solid var(--color-line-strong)}
.trend-grid{display:grid}
.trend-row{width:100%;display:grid;grid-template-columns:9rem 1fr 1fr 4rem;gap:.75rem;align-items:center;padding:.55rem 0;border:0;border-bottom:1px solid var(--color-line);
  background:transparent;color:var(--color-neutral-800);font:inherit;font-size:.875rem;text-align:left;cursor:pointer}
.trend-row:hover .trend-name{color:var(--color-accent)}
.trend-period{position:relative;display:grid;grid-template-columns:1fr 1.75rem 2.75rem;gap:.35rem;align-items:center;font-size:.6875rem;color:var(--color-neutral-600);font-variant-numeric:tabular-nums}
.trend-period::before{content:"";position:absolute;left:0;right:4.85rem;height:.45rem;background:var(--color-surface-deep)}
.trend-period i{height:.45rem;background:var(--color-neutral-300);z-index:1}.trend-period.current i{background:var(--chart)}
.trend-period b,.trend-period small{z-index:1;text-align:right;font-weight:600}
.trend-delta{text-align:right;font-weight:600;font-size:.8125rem;font-variant-numeric:tabular-nums}
.trend-delta.up{color:var(--color-accent)}.trend-delta.down{color:var(--color-neutral-500)}
.keyword-grid{display:grid;grid-template-columns:1fr 1fr;gap:0 1.5rem}
.keyword-item{display:grid;grid-template-columns:7rem 1fr 1.75rem;gap:.5rem;align-items:center;padding:.35rem 0;font-size:.8125rem;color:var(--color-neutral-700);border-bottom:1px solid var(--color-line)}
.keyword-item strong{text-align:right;font-weight:600;color:var(--color-ink)}
.keyword-track{height:.4rem;background:var(--color-surface-deep)}.keyword-fill{height:100%;background:var(--chart)}
.surge-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1px;border:1px solid var(--color-line);background:var(--color-line)}
.surge-keyword{display:grid;grid-template-columns:1fr auto auto;gap:.5rem;width:100%;padding:.8rem .9rem;border:0;background:var(--color-card);color:var(--color-neutral-800);font:inherit;text-align:left;cursor:pointer}
.surge-keyword:hover .surge-word{color:var(--color-accent)}
.surge-word{font-weight:600}.surge-count{color:var(--color-neutral-600);font-size:.75rem}.surge-delta{color:var(--color-accent);font-size:.75rem;font-weight:600}
.surge-context{grid-column:1/-1;color:var(--color-neutral-500);font-size:.6875rem}
.watch-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1px;border:1px solid var(--color-line);background:var(--color-line)}
.watch-card{display:grid;grid-template-columns:1fr auto;gap:.35rem .75rem;padding:1rem 1.1rem;border:0;background:var(--color-card);color:var(--color-neutral-800);font:inherit;text-align:left;cursor:pointer}
.watch-card:hover .watch-name{color:var(--color-accent)}
.watch-name{font-weight:600;color:var(--color-ink)}.watch-total{font-size:.75rem;color:var(--color-neutral-500)}.watch-total strong{color:var(--color-neutral-800)}
.watch-change{font-size:.75rem;color:var(--color-neutral-600);font-variant-numeric:tabular-nums}
.watch-change em{margin-left:.5rem;font-style:normal;font-weight:600}.watch-change em.up{color:var(--color-accent)}.watch-change em.down,.watch-change em.flat{color:var(--color-neutral-500)}
.watch-paper{grid-column:1/-1;color:var(--color-neutral-500);font-size:.6875rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.timeline{display:flex;gap:.5rem;height:11rem;align-items:flex-end}
.day{flex:1;min-width:1.25rem;text-align:center;font-size:.6875rem;color:var(--color-neutral-500)}
.day-track{height:7.5rem;display:flex;align-items:flex-end;margin:.2rem 0;border-bottom:1px solid var(--color-line-strong)}
.day-fill{width:100%;background:var(--chart);border-radius:3px 3px 0 0}.day-value{color:var(--color-ink);font-weight:600}
.matrix-wrap{overflow-x:auto}.matrix{border-collapse:collapse;width:100%;font-size:.6875rem}
.matrix th,.matrix td{padding:0;border:1px solid var(--color-canvas);text-align:center}
.matrix thead th{padding:.4rem .2rem;vertical-align:bottom;min-width:3rem;font-size:.625rem;line-height:1.35;font-weight:500;color:var(--color-neutral-600)}
.matrix tbody th{padding:.4rem .6rem;text-align:left;min-width:11rem;font-weight:500;color:var(--color-neutral-700)}
.matrix td{background:color-mix(in srgb,var(--chart) calc(var(--cell-opacity)*100%),var(--color-surface))}
.matrix-cell{width:100%;min-height:2.6rem;border:0;background:transparent;color:var(--color-ink);cursor:pointer;font:inherit;font-variant-numeric:tabular-nums}
.matrix td.hi .matrix-cell{color:var(--color-canvas)}
.matrix-cell:hover{outline:2px solid var(--color-accent);outline-offset:-2px}
.matrix-cell strong,.matrix-cell small{display:block}.matrix-cell small{opacity:.75}
.topic-scatter{display:block;width:100%;height:auto}
.topic-scatter text{fill:var(--color-neutral-500);font-size:12px}
.topic-scatter .plot-bg{fill:var(--color-surface);stroke:var(--color-line)}.topic-scatter .axis{stroke:var(--color-line-strong)}
.topic-scatter circle{cursor:pointer;stroke:var(--color-card);stroke-width:2;transition:opacity .18s}
.topic-scatter circle:hover{r:8}
.topic-scatter .cluster-label{fill:var(--color-ink);font-size:11px;font-weight:600;paint-order:stroke;stroke:var(--color-surface);stroke-width:4px;stroke-linejoin:round;pointer-events:none}
.topic-scatter circle.is-dimmed{opacity:.1}.topic-scatter circle.is-selected{opacity:1;stroke:var(--color-ink);stroke-width:1.7}
.scatter-legend{display:flex;flex-wrap:wrap;gap:.5rem 1rem;margin-bottom:.75rem;font-size:.75rem;color:var(--color-neutral-700)}
.scatter-legend span{display:inline-flex;align-items:center;gap:.35rem}.scatter-legend i{width:.6rem;height:.6rem;border-radius:50%;display:inline-block}
.filter-status{position:sticky;top:5.5rem;z-index:5;display:flex;align-items:center;justify-content:space-between;gap:.75rem;margin:0 0 1rem;padding:.75rem 1rem;
  background:var(--color-accent-soft);border-left:3px solid var(--color-accent);font-size:.875rem;color:var(--color-neutral-800)}
.filter-status button{border:1px solid var(--color-line);background:var(--color-card);color:var(--color-neutral-700);padding:.35rem .7rem;font:inherit;font-size:.75rem;cursor:pointer}
.filter-status[hidden]{display:none}
#papers{border-top:1px solid var(--color-line-strong)}
.paper{padding:1.4rem 0;border-bottom:1px solid var(--color-line)}.paper[hidden]{display:none}
.paper-top{display:flex;gap:.6rem;align-items:center;flex-wrap:wrap;font-size:.75rem;color:var(--color-neutral-500)}
.paper-top .num{font-weight:600;color:var(--color-accent);font-variant-numeric:tabular-nums}
.paper-top .journal{color:var(--color-neutral-700);font-weight:500}
.paper h2{margin:.5rem 0 .25rem;font-size:1.0625rem;line-height:1.45;font-weight:600;letter-spacing:-.01em}
.paper h2 a{color:var(--color-ink)}
.paper .title-ko{margin:0 0 .5rem;font-size:.9375rem;font-weight:500;line-height:1.6;color:var(--color-neutral-700)}
.paper .authors,.paper .basis{margin:.25rem 0;color:var(--color-neutral-500);font-size:.75rem;line-height:1.7}
.paper .basis a{color:var(--color-neutral-600)}
.paper .summary{margin:.5rem 0;font-size:.875rem;line-height:1.8;color:var(--color-neutral-700)}
.paper .tags{margin-top:.5rem}
@media(max-width:700px){.bar-row{grid-template-columns:7rem 1fr 2rem}.trend-head,.trend-row{grid-template-columns:6.5rem 1fr 1fr 3.25rem;gap:.4rem}
  .keyword-grid,.surge-grid,.watch-grid{grid-template-columns:1fr}.timeline{gap:.2rem}}
"""
