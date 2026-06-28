document.addEventListener('DOMContentLoaded', function () {
  var mapEl = document.getElementById('job-map');

  var map = L.map('job-map').setView([39.0, -76.7], 11);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19
  }).addTo(map);

  fetch(mapEl.getAttribute('data-url'))
    .then(r => r.json())
    .then(data => {
      var bounds = [];

      (data.photos || []).forEach(function (p) {
        var m = L.marker([p.lat, p.lon], { icon: L.icon({ iconUrl: '/static/icons/photo.png', iconSize: [28, 28] }) }).addTo(map);
        m.bindPopup('<strong>' + p.label + '</strong><br>' + p.filename);
        bounds.push([p.lat, p.lon]);
      });

      (data.contracts || []).forEach(function (c) {
        var m = L.marker([c.lat, c.lon], { icon: L.icon({ iconUrl: c.label.includes('Signed') ? '/static/icons/contract_signed.png' : '/static/icons/contract_pending.png', iconSize: [28, 28] }) }).addTo(map);
        m.bindPopup('<strong>' + c.label + '</strong><br>' + c.signer);
        bounds.push([c.lat, c.lon]);
      });

      if (bounds.length) map.fitBounds(bounds);
    })
    .catch(console.error);
});