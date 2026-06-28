
document.addEventListener('DOMContentLoaded', function () {
  const canvas = document.getElementById('sig-canvas');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  let drawing = false;

  function start(e) {
    drawing = true;
    ctx.beginPath();
    ctx.moveTo(e.offsetX, e.offsetY);
  }

  function draw(e) {
    if (!drawing) return;
    ctx.lineWidth = 3;
    ctx.lineCap = 'round';
    ctx.strokeStyle = '#000';
    ctx.lineTo(e.offsetX, e.offsetY);
    ctx.stroke();
  }

  function end() {
    drawing = false;
  }

  canvas.addEventListener('mousedown', start);
  canvas.addEventListener('mousemove', draw);
  canvas.addEventListener('mouseup', end);
  canvas.addEventListener('mouseleave', end);

  document.getElementById('sig-clear').addEventListener('click', function () {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  });

  document.getElementById('sig-submit').addEventListener('click', function () {
    const dataURL = canvas.toDataURL('image/png');
    document.getElementById('signature_data').value = dataURL;
    document.getElementById('sig-form').submit();
  });
});
