// Network first for pages and data (new briefs appear immediately), cache as offline fallback.
const CACHE = 'nuclear-digest-v1';
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
