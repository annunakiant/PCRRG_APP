(function(){
  function initHybridCamera(){
    var container = document.getElementById('camera-capture');
    if(!container) return;

    // Retrieve backend data
    var jobId = container.getAttribute('data-job-id');
    var username = container.getAttribute('data-username') || 'Unknown User';
    var uploadUrl = container.getAttribute('data-upload-url');

    container.innerHTML = '';

    // UI Setup
    var video = document.createElement('video');
    video.setAttribute('playsinline', 'true');
    video.style.width = '100%';
    video.style.maxHeight = '400px';
    video.style.borderRadius = '0.75rem';
    video.style.backgroundColor = '#000';
    container.appendChild(video);

    var canvas = document.createElement('canvas');
    canvas.style.display = 'none';
    container.appendChild(canvas);

    var controlsRow = document.createElement('div');
    controlsRow.style.marginTop = '0.5rem';
    controlsRow.style.display = 'flex';
    controlsRow.style.gap = '0.5rem';
    controlsRow.style.flexWrap = 'wrap';
    container.appendChild(controlsRow);

    var category = document.createElement('select');
    category.className = 'form-select';
    category.style.flex = '1';
    category.style.minWidth = '150px';
    ['Before', 'During', 'After', 'Documentation', 'Damage'].forEach(function(opt){
      var o = document.createElement('option');
      o.value = opt;
      o.textContent = opt;
      category.appendChild(o);
    });
    controlsRow.appendChild(category);

    var startBtn = document.createElement('button');
    startBtn.className = 'btn btn-outline-primary';
    startBtn.textContent = 'Open Camera';
    controlsRow.appendChild(startBtn);

    var captureBtn = document.createElement('button');
    captureBtn.className = 'btn btn-primary';
    captureBtn.textContent = 'Snap Photo';
    captureBtn.disabled = true;
    controlsRow.appendChild(captureBtn);

    var uploadBtn = document.createElement('button');
    uploadBtn.className = 'btn btn-success';
    uploadBtn.textContent = 'Upload Batch (0)';
    uploadBtn.style.display = 'none';
    controlsRow.appendChild(uploadBtn);

    var gpsInfo = document.createElement('div');
    gpsInfo.style.marginTop = '0.5rem';
    gpsInfo.style.fontSize = '0.75rem';
    gpsInfo.style.color = '#9ca3af';
    gpsInfo.textContent = 'GPS: Locating...';
    container.appendChild(gpsInfo);

    // Gallery for unsaved photos
    var previewGallery = document.createElement('div');
    previewGallery.style.display = 'flex';
    previewGallery.style.gap = '10px';
    previewGallery.style.overflowX = 'auto';
    previewGallery.style.marginTop = '1rem';
    previewGallery.style.paddingBottom = '0.5rem';
    container.appendChild(previewGallery);

    let stream = null;
    let gps = { lat: null, lon: null };
    let capturedBatch = []; // Array to hold images before upload

    // 1. Fetch GPS
    if(navigator.geolocation){
      navigator.geolocation.getCurrentPosition(function(pos){
        gps.lat = pos.coords.latitude;
        gps.lon = pos.coords.longitude;
        gpsInfo.textContent = 'GPS: ' + gps.lat.toFixed(5) + ', ' + gps.lon.toFixed(5);
      }, function(){
        gpsInfo.textContent = 'GPS: Unavailable';
      });
    }

    // 2. Start Camera
    startBtn.addEventListener('click', async function(e){
      e.preventDefault();
      try{
        if(stream) {
            // If already running, stop it (Toggle behavior)
            stream.getTracks().forEach(t => t.stop());
            stream = null;
            video.srcObject = null;
            startBtn.textContent = 'Open Camera';
            captureBtn.disabled = true;
            return;
        }
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
        video.srcObject = stream;
        await video.play();
        startBtn.textContent = 'Close Camera';
        captureBtn.disabled = false;
      } catch(err){
        alert('Camera access failed: ' + err.message);
      }
    });

    // 3. Capture & Stamp Photo (Looping mechanism)
    captureBtn.addEventListener('click', function(e){
      e.preventDefault();
      if(!video.videoWidth) return;

      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      var ctx = canvas.getContext('2d');
      
      // Draw actual picture
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

      // Setup Text Stamping
      const timestamp = new Date().toLocaleString();
      const currentCategory = category.value;
      const gpsString = gps.lat ? `GPS: ${gps.lat.toFixed(4)}, ${gps.lon.toFixed(4)}` : 'GPS: N/A';
      
      // Draw semi-transparent background for text legibility
      ctx.fillStyle = "rgba(0, 0, 0, 0.5)";
      ctx.fillRect(0, canvas.height - 100, canvas.width, 100);

      // Burn text onto image
      ctx.font = "20px Arial";
      ctx.fillStyle = "white";
      ctx.fillText(`Tech: ${username} | Date: ${timestamp}`, 20, canvas.height - 65);
      ctx.fillText(`Category: ${currentCategory} | ${gpsString}`, 20, canvas.height - 30);

      // Convert to Blob instead of DataURL for smaller upload size
      canvas.toBlob(function(blob){
        const file = new File([blob], `snap_${Date.now()}.jpg`, { type: "image/jpeg" });
        capturedBatch.push({ file: file, category: currentCategory, lat: gps.lat, lon: gps.lon });
        
        // Update UI
        uploadBtn.style.display = 'block';
        uploadBtn.textContent = `Upload Batch (${capturedBatch.length})`;
        
        // Create Thumbnail
        const thumb = document.createElement('img');
        thumb.src = URL.createObjectURL(blob);
        thumb.style.height = '80px';
        thumb.style.borderRadius = '6px';
        thumb.style.border = '2px solid #1E88E5';
        previewGallery.appendChild(thumb);
      }, 'image/jpeg', 0.85);
    });

    // 4. Batch Upload
    uploadBtn.addEventListener('click', async function(e){
      e.preventDefault();
      if(capturedBatch.length === 0) return;

      uploadBtn.disabled = true;
      uploadBtn.textContent = 'Uploading...';

      // We send them one by one to your existing /upload_photo route to prevent payload size errors
      for(let i = 0; i < capturedBatch.length; i++) {
          const item = capturedBatch[i];
          const formData = new FormData();
const category = document.getElementById('photo-category')?.value || '';
formData.append('category', category);
          formData.append('photo', item.file);
          formData.append('category', item.category);
          if(item.lat) formData.append('lat', item.lat);
          if(item.lon) formData.append('lon', item.lon);
          
          try {
              await fetch(uploadUrl, { method: 'POST', body: formData });
          } catch(err) {
              console.error('Upload failed for item', i, err);
          }
      }

      // Refresh page to show uploaded images in the standard gallery
      window.location.reload();
    });

    // Cleanup on exit
    window.addEventListener('beforeunload', function(){
      if(stream){ stream.getTracks().forEach(t => t.stop()); }
    });
  }

  document.addEventListener('DOMContentLoaded', initHybridCamera);
})();
