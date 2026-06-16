const CACHE_NAME = 'pcrrg-fieldops-v1';
const OFFLINE_URLS = [
  '/',
  '/dashboard',
  '/inventory',
  '/static/css/theme.css',
  '/static/js/pwa.js'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(OFFLINE_URLS))
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  event.respondWith(
    caches.match(event.request).then(resp => {
      return resp || fetch(event.request).catch(() => caches.match('/'));
    })
  );
});
