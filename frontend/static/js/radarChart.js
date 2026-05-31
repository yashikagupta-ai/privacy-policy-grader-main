/**
 * radarChart.js — Polished radar/spider chart for dimension scores.
 */

class RadarChart {
  constructor(canvas, labels, values) {
    this.canvas = canvas;
    this.ctx    = canvas.getContext('2d');
    this.labels = labels;
    this.values = values.map(v => Math.min(Math.max(v, 0), 100));

    const dpr  = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    const w = rect.width  || 380;
    const h = rect.height || 340;

    canvas.width  = w * dpr;
    canvas.height = h * dpr;
    this.ctx.scale(dpr, dpr);
    canvas.style.width  = `${w}px`;
    canvas.style.height = `${h}px`;

    this.W = w; this.H = h;
  }

  draw() {
    const { ctx, labels, values, W, H } = this;
    const cx = W / 2;
    const cy = H / 2 + 4;
    const R  = Math.min(cx, cy) - 52;
    const n  = labels.length;

    ctx.clearRect(0, 0, W, H);

    // Grid rings
    const rings = [20, 40, 60, 80, 100];
    rings.forEach(ring => {
      ctx.beginPath();
      for (let i = 0; i < n; i++) {
        const angle = (Math.PI * 2 * i / n) - Math.PI / 2;
        const r = (ring / 100) * R;
        const x = cx + r * Math.cos(angle);
        const y = cy + r * Math.sin(angle);
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      }
      ctx.closePath();
      ctx.strokeStyle = ring === 100 ? 'rgba(74,122,88,0.2)' : 'rgba(0,0,0,0.07)';
      ctx.lineWidth   = ring === 100 ? 1.5 : 1;
      ctx.stroke();
      ctx.fillStyle = ring % 40 === 0 ? 'rgba(74,122,88,0.03)' : 'transparent';
      ctx.fill();

      // Ring label
      if (ring > 0 && ring < 100) {
        ctx.fillStyle = 'rgba(0,0,0,0.3)';
        ctx.font      = '10px DM Sans, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(ring, cx + 4, cy - (ring / 100) * R + 3);
      }
    });

    // Spokes
    for (let i = 0; i < n; i++) {
      const angle = (Math.PI * 2 * i / n) - Math.PI / 2;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + R * Math.cos(angle), cy + R * Math.sin(angle));
      ctx.strokeStyle = 'rgba(0,0,0,0.1)';
      ctx.lineWidth   = 1;
      ctx.stroke();
    }

    // Data polygon
    ctx.beginPath();
    values.forEach((v, i) => {
      const angle = (Math.PI * 2 * i / n) - Math.PI / 2;
      const r = (v / 100) * R;
      const x = cx + r * Math.cos(angle);
      const y = cy + r * Math.sin(angle);
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.closePath();
    ctx.fillStyle   = 'rgba(74,122,88,0.18)';
    ctx.fill();
    ctx.strokeStyle = 'rgba(74,122,88,0.85)';
    ctx.lineWidth   = 2.5;
    ctx.lineJoin    = 'round';
    ctx.stroke();

    // Data points
    values.forEach((v, i) => {
      const angle = (Math.PI * 2 * i / n) - Math.PI / 2;
      const r = (v / 100) * R;
      const x = cx + r * Math.cos(angle);
      const y = cy + r * Math.sin(angle);
      ctx.beginPath();
      ctx.arc(x, y, 5, 0, Math.PI * 2);
      ctx.fillStyle   = '#4A7A58';
      ctx.fill();
      ctx.strokeStyle = '#fff';
      ctx.lineWidth   = 2;
      ctx.stroke();
    });

    // Labels
    labels.forEach((label, i) => {
      const angle    = (Math.PI * 2 * i / n) - Math.PI / 2;
      const labelR   = R + 38;
      const lx       = cx + labelR * Math.cos(angle);
      const ly       = cy + labelR * Math.sin(angle);
      const parts    = label.split('\n');
      const score    = Math.round(values[i]);

      ctx.font      = '600 11.5px DM Sans, sans-serif';
      ctx.fillStyle = '#232018';
      ctx.textAlign = 'center';

      parts.forEach((part, pi) => {
        const lineH = 14;
        const totalH = (parts.length + 1) * lineH;
        const startY = ly - totalH / 2 + lineH / 2;
        ctx.fillText(part, lx, startY + pi * lineH);
      });

      // Score below label
      const scoreY = ly + (parts.length) * 14 - (parts.length * 7) + 2;
      ctx.font      = '700 12px JetBrains Mono, monospace';
      ctx.fillStyle = '#4A7A58';
      ctx.fillText(score, lx, scoreY);
    });
  }
}

window.RadarChart = RadarChart;
