(function(){
  function initHybridCamera(){
    var container = document.getElementById('camera-capture');
    if(!container) return;

    container.innerHTML = '';

    var info = document.createElement('div');
    info.style.fontSize = '0.8rem';
    info.style.color = '#9ca3af';
    info.textContent = 'Hybrid capture: simple UI + category + GPS tagging.';
    container.appendChild(info);

    var video = document.createElement('video');
    video.setAttribute('playsinline', true);
    video.style.width = '100%';
    video.style.maxHeight = '260px';
    video.style.borderRadius = '0.75rem';
    video.style.marginTop = '0.5rem';
    container.appendChild(video);

    var canvas = document.createElement('canvas');
    canvas.style.display = 'none';
    container.appendChild(canvas);

    var category = document.createElement('select');
    category.style.width = '100%';
    category.style.marginTop = '0.5rem';
    category.style.padding = '0.4rem';
    category.style.borderRadius = '0.5rem';
    category.style.border = '1px solid #374151';
    category.style.background = '#020617';
    category.style.color = '#e5e7eb';
    ['Before','During','After','Documentation'].forEach(function(opt){
      var o = document.createElement('option');
      o.value = opt;
      o.textContent = opt;
      category.appendChild(o);
    });
    container.appendChild(category);

    var gpsInfo = document.createElement('div');
    gpsInfo.style.marginTop = '0.25rem';
    gpsInfo.style.fontSize = '0.75rem';
    gpsInfo.style.color = '#9ca3af';
    gpsInfo.textContent = 'GPS: locating...';
    container.appendChild(gpsInfo);

    var controls = document.createElement('div');
    controls.style.marginTop = '0.5rem';
    controls.style.display = 'flex';
    controls.style.gap = '0.5rem';
    container.appendChild(controls);

    var startBtn = document.createElement('button');
    startBtn.className = 'btn btn-outline';
    startBtn.textContent = 'Start Camera';
    controls.appendChild(startBtn);

    var captureBtn = document.createElement('button');
    captureBtn.className = 'btn btn-primary';
    captureBtn.textContent = 'Capture Photo';
    captureBtn.disabled = true;
    controls.appendChild(captureBtn);

    var result = document.createElement('div');
    result.style.marginTop = '0.5rem';
    result.style.fontSize = '0.8rem';
    result.style.color = '#e5e7eb';
    container.appendChild(result);

    let stream = null;
    let gps = { lat: null, lon: null };

    if(navigator.geolocation){
      navigator.geolocation.getCurrentPosition(function(pos){
        gps.lat = pos.coords.latitude;
        gps.lon = pos.coords.longitude;
        gpsInfo.textContent = 'GPS: ' + gps.lat.toFixed(5) + ', ' + gps.lon.toFixed(5);
      }, function(){
        gpsInfo.textContent = 'GPS: unavailable';
      });
    }else{
      gpsInfo.textContent = 'GPS: not supported';
    }

    startBtn.addEventListener('click', async function(){
      try{
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
        video.srcObject = stream;
        await video.play();
        captureBtn.disabled = false;
        result.textContent = 'Camera ready. Choose category and capture.';
      }catch(e){
        result.textContent = 'Camera access failed: ' + e.message;
      }
    });

    captureBtn.addEventListener('click', function(){
      if(!video.videoWidth){
        result.textContent = 'Camera not ready yet.';
        return;
      }
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      var ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0);
      var dataUrl = canvas.toDataURL('image/jpeg');
      result.textContent = 'Captured photo (placeholder). Category: ' +
        category.value + ', GPS: ' +
        (gps.lat ? gps.lat.toFixed(5) : 'n/a') + ', ' +
        (gps.lon ? gps.lon.toFixed(5) : 'n/a');
      // Here you would POST dataUrl + category + gps to your upload endpoint.
    });

    window.addEventListener('beforeunload', function(){
      if(stream){
        stream.getTracks().forEach(t => t.stop());
      }
    });
  }

  document.addEventListener('DOMContentLoaded', initHybridCamera);
})();
