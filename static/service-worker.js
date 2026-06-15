self.addEventListener('install', event => {
  event.waitUntil(
    caches.open('pcrrg-shell-v1').then(cache => {
      return cache.addAll([
        '/',
        '/login',
        '/static/manifest.json',
        'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css'
      ]);
    })
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request).then(resp => {
      return resp || fetch(event.request);
    })
  );
});
