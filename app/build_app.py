"""Home-screen app files: docs/manifest.webmanifest and docs/sw.js (rebuilt with the home page).

Installing: Android/desktop Chrome or Edge -> "앱 설치"; iPhone Safari -> 공유 -> "홈 화면에 추가".
The service worker keeps the last-seen pages so the app still opens without a connection; when online it
always fetches fresh pages first, so new daily/weekly content shows up without any app update.
"""
import json

from .config import DOCS_DIR, SITE

SW_VERSION = "v1"  # bump to drop old caches if the caching rules below change

SERVICE_WORKER = """// Network first for pages and data (new briefs appear immediately), cache as offline fallback.
const CACHE = 'nuclear-digest-%(version)s';
const CORE = ['./', './index.html', './news/index.html', './papers/index.html', './install.html', './icon.svg', './manifest.webmanifest'];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(CORE)).catch(() => {}).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== location.origin) return;  // fonts/CDN: browser default
  e.respondWith(
    fetch(req).then(res => {
      if (res.ok && !req.url.endsWith('.xlsx')) {
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put(req, copy));
      }
      return res;
    }).catch(() => caches.match(req).then(hit => hit || (req.mode === 'navigate' ? caches.match('./index.html') : undefined)))
  );
});
"""


def build_app():
    name = SITE.get("app_name") or SITE["title"]
    manifest = {
        "name": SITE["title"],
        "short_name": name,
        "description": "매일 원자력 뉴스 해설과 매주 원자력공학 논문 동향",
        "lang": "ko",
        "start_url": "./index.html",
        "scope": "./",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#1b2a41",
        "icons": [
            {"src": "icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "icons/maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
            {"src": "icon.svg", "sizes": "any", "type": "image/svg+xml"},
        ],
        "shortcuts": [
            {"name": "오늘의 뉴스", "url": "./news/index.html", "icons": [{"src": "icons/icon-192.png", "sizes": "192x192"}]},
            {"name": "이번 주 논문", "url": "./papers/index.html", "icons": [{"src": "icons/icon-192.png", "sizes": "192x192"}]},
            {"name": "논문 DB", "url": "./papers/database.html", "icons": [{"src": "icons/icon-192.png", "sizes": "192x192"}]},
        ],
    }
    (DOCS_DIR / "manifest.webmanifest").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (DOCS_DIR / "sw.js").write_text(SERVICE_WORKER % {"version": SW_VERSION}, encoding="utf-8")
    return DOCS_DIR / "manifest.webmanifest"


if __name__ == "__main__":
    print(build_app())
