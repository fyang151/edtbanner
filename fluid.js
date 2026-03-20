function startFluidSim() {
  const canvas = document.getElementById("fluidCanvas");
  const ctx = canvas.getContext("2d");

  const SCALE = 4;
  const COOLING = 2;
  const OFFSCREEN_ROWS = 0;

  let cols, rows, buf, imageData, pixels;

  const palette = new Uint32Array(256);
  for (let i = 0; i < 256; i++) {
    let r, g, b;
    if (i < 64) {
      r = 0;
      g = 0;
      b = Math.round((i / 64) * 120);
    } else if (i < 128) {
      const t = (i - 64) / 64;
      r = 0;
      g = Math.round(t * 60);
      b = Math.round(120 + t * 100);
    } else if (i < 200) {
      const t = (i - 128) / 72;
      r = 0;
      g = Math.round(60 + t * 140);
      b = Math.round(220 + t * 35);
    } else {
      const t = (i - 200) / 55;
      r = Math.round(t * 255);
      g = Math.round(200 + t * 55);
      b = 255;
    }
    palette[i] = (255 << 24) | (b << 16) | (g << 8) | r;
  }

  function resize() {
    canvas.width = Math.ceil(window.innerWidth / SCALE);
    canvas.height = Math.ceil(canvas.clientHeight / SCALE) + OFFSCREEN_ROWS;
    cols = canvas.width;
    rows = canvas.height;
    buf = new Uint8Array(cols * rows);
    imageData = ctx.createImageData(cols, rows);
    pixels = new Uint32Array(imageData.data.buffer);

    for (let x = 0; x < cols; x++) {
      buf[(rows - 1) * cols + x] = 255;
    }
  }

  function step() {
    for (let x = 0; x < cols; x++) {
      buf[(rows - 1) * cols + x] = Math.random() > 0.05 ? 255 : 0;
    }

    for (let y = 0; y < rows - 1; y++) {
      for (let x = 0; x < cols; x++) {
        const below = buf[(y + 1) * cols + x];
        const belowLeft = buf[(y + 1) * cols + Math.max(x - 1, 0)];
        const belowRight = buf[(y + 1) * cols + Math.min(x + 1, cols - 1)];
        const sameRow = buf[y * cols + x];
        const avg = (below + belowLeft + belowRight + sameRow) >> 2;
        buf[y * cols + x] = avg > COOLING ? avg - COOLING : 0;
      }
    }

    for (let i = 0; i < cols * rows; i++) {
      pixels[i] = palette[buf[i]];
    }

    ctx.putImageData(imageData, 0, 0);

    ctx.save();
    ctx.imageSmoothingEnabled = false;
    ctx.translate(0, canvas.clientHeight);
    ctx.scale(1, -1);
    const visibleRows = rows - OFFSCREEN_ROWS;
    ctx.drawImage(
      canvas,
      0,
      0,
      cols,
      visibleRows,
      0,
      0,
      cols * SCALE,
      visibleRows * SCALE,
    );
    ctx.restore();
  }

  resize();
  window.addEventListener("resize", resize);

  const loop = () => {
    step();
    requestAnimationFrame(loop);
  };
  loop();
}
