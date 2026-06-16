(function(){
  function isMobile(){
    return window.innerWidth < 768;
  }

  function initHybridScanner(){
    var container = document.getElementById('barcode-scanner');
    if(!container) return;

    container.innerHTML = '';

    var info = document.createElement('div');
    info.style.fontSize = '0.8rem';
    info.style.color = '#9ca3af';
    info.textContent = 'Hybrid scanner: fullscreen on mobile, inline on desktop.';
    container.appendChild(info);

    var video = document.createElement('video');
    video.setAttribute('playsinline', true);
    video.style.width = isMobile() ? '100%' : '320px';
    video.style.maxHeight = '260px';
    video.style.borderRadius = '0.75rem';
    video.style.marginTop = '0.5rem';
    container.appendChild(video);

    var resultBox = document.createElement('div');
    resultBox.style.marginTop = '0.5rem';
    resultBox.style.fontSize = '0.85rem';
    resultBox.style.color = '#e5e7eb';
    container.appendChild(resultBox);

    var button = document.createElement('button');
    button.className = 'btn btn-outline';
    button.textContent = 'Start Scanner';
    button.style.marginTop = '0.5rem';
    container.appendChild(button);

    let stream = null;

    button.addEventListener('click', async function(){
      try{
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
        video.srcObject = stream;
        await video.play();
        resultBox.textContent = 'Scanning... (placeholder, integrate real decoder later)';
      }catch(e){
        resultBox.textContent = 'Camera access failed: ' + e.message;
      }
    });

    window.addEventListener('beforeunload', function(){
      if(stream){
        stream.getTracks().forEach(t => t.stop());
      }
    });
  }

  document.addEventListener('DOMContentLoaded', initHybridScanner);
})();
