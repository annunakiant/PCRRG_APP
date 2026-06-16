if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/static/js/service-worker.js')
    .then(function(reg){ console.log('SW registered', reg); })
    .catch(function(err){ console.log('SW registration failed', err); });
}
