const CACHE = 'morning-brief-v3';
const PRE_CACHE = ['/index.html', '/favicon.svg', '/manifest.json', '/icon-192.png', '/icon-512.png', '/icon-180.png'];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE)
      .then(c => c.addAll(PRE_CACHE.map(u => new Request(u, { cache: 'reload' }))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (url.origin !== location.origin) return;

  // news*.json: ネットワーク優先（常に最新を取得）、オフライン時はキャッシュ
  if (url.pathname.match(/news.*\.json$/)) {
    e.respondWith(
      fetch(e.request)
        .then(r => {
          caches.open(CACHE).then(c => c.put(e.request, r.clone()));
          return r;
        })
        .catch(() => caches.match(e.request))
    );
    return;
  }

  // その他: キャッシュ優先、なければネットワーク取得してキャッシュ
  e.respondWith(
    caches.match(e.request).then(cached => {
      if (cached) return cached;
      return fetch(e.request).then(r => {
        caches.open(CACHE).then(c => c.put(e.request, r.clone()));
        return r;
      });
    })
  );
});

/* ── プッシュ通知 ── */
self.addEventListener('push', e => {
  const d = e.data ? e.data.json() : {};
  e.waitUntil(
    self.registration.showNotification(d.title || 'Morning Brief', {
      body:  d.body  || '今日のニュースが届きました',
      icon:  '/icon-192.png',
      badge: '/icon-192.png',
      data:  { url: d.url || '/' },
    })
  );
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  e.waitUntil(clients.openWindow(e.notification.data?.url || '/'));
});
