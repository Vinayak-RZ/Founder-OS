/* Canvas charts — no external deps */
window.FOSCharts = {
  bar(el, labels, values, opts = {}) {
    const c = typeof el === "string" ? document.getElementById(el) : el;
    if (!c) return;
    const ctx = c.getContext("2d");
    if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;
    const w = c.clientWidth || 320;
    const h = c.clientHeight || 160;
    c.width = w * dpr;
    c.height = h * dpr;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, w, h);

    const n = values.length || 1;
    const bw = (w - 44) / n;
    const rotate = bw < 42;
    const pad = { t: 8, r: 8, b: rotate ? 52 : 32, l: 36 };
    const max = Math.max(...values, 1);
    const colors = opts.colors || ["#f75440", "#00666b", "#03904a", "#051f13", "#5a403c", "#8f706b"];

    values.forEach((v, i) => {
      const bh = ((h - pad.t - pad.b) * v) / max;
      const x = pad.l + i * bw + bw * 0.12;
      const barW = bw * 0.76;
      ctx.fillStyle = colors[i % colors.length];
      ctx.fillRect(x, h - pad.b - bh, barW, bh);
      ctx.fillStyle = "#5a403c";
      ctx.font = "10px Inter, sans-serif";
      const lbl = (labels[i] || "").slice(0, rotate ? 6 : 10);
      if (rotate) {
        ctx.save();
        ctx.translate(x + barW / 2, h - 6);
        ctx.rotate(-0.65);
        ctx.textAlign = "right";
        ctx.fillText(lbl, 0, 0);
        ctx.restore();
      } else {
        ctx.textAlign = "center";
        ctx.fillText(lbl, x + barW / 2, h - 8);
      }
    });
  },

  donut(el, segments, opts = {}) {
    const c = typeof el === "string" ? document.getElementById(el) : el;
    if (!c || !segments.length) return;
    const ctx = c.getContext("2d");
    if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;
    const size = Math.min(c.clientWidth || 200, c.clientHeight || 200);
    c.width = size * dpr;
    c.height = size * dpr;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, size, size);

    const cx = size / 2;
    const cy = size / 2;
    const r = size * 0.38;
    const ir = size * 0.24;
    const total = segments.reduce((s, x) => s + x.value, 0) || 1;
    const colors = opts.colors || ["#f75440", "#00666b", "#03904a", "#051f13", "#5a403c", "#8f706b"];
    let a = -Math.PI / 2;

    segments.forEach((seg, i) => {
      const slice = (seg.value / total) * Math.PI * 2;
      ctx.beginPath();
      ctx.arc(cx, cy, r, a, a + slice);
      ctx.arc(cx, cy, ir, a + slice, a, true);
      ctx.closePath();
      ctx.fillStyle = colors[i % colors.length];
      ctx.fill();
      a += slice;
    });

    ctx.fillStyle = "#fff";
    ctx.font = "600 18px Inter, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(String(total), cx, cy - 4);
    ctx.fillStyle = "#5a403c";
    ctx.font = "10px Inter, sans-serif";
    ctx.fillText(opts.centerLabel || "total", cx, cy + 12);
  },

  spark(el, points) {
    const c = typeof el === "string" ? document.getElementById(el) : el;
    if (!c || !points.length) return;
    const ctx = c.getContext("2d");
    if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;
    const w = c.clientWidth || 280;
    const h = c.clientHeight || 56;
    c.width = w * dpr;
    c.height = h * dpr;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, w, h);

    const max = Math.max(...points, 1);
    const min = Math.min(...points, 0);
    const range = max - min || 1;
    const pad = 4;

    ctx.strokeStyle = "#f75440";
    ctx.lineWidth = 2;
    ctx.beginPath();
    points.forEach((p, i) => {
      const x = pad + (i / Math.max(points.length - 1, 1)) * (w - pad * 2);
      const y = h - pad - ((p - min) / range) * (h - pad * 2);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
  },
};
