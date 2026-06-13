self.addEventListener('install', event => {
  console.log('Service worker installed');
});
self.addEventListener('fetch', event => {
  // basic passthrough; can be extended for offline caching
});
