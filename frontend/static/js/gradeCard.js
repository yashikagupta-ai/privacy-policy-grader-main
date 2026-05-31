/**
 * gradeCard.js — Animated circular grade canvas with DM Serif Display font.
 */

class GradeCard {
  constructor(canvas, gradeLetter, score) {
    this.canvas = canvas;
    this.ctx    = canvas.getContext('2d');

    const dpr  = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    const w = rect.width  || 160;
    const h = rect.height || 160;

    canvas.width  = w * dpr;
    canvas.height = h * dpr;
    this.ctx.scale(dpr, dpr);
    canvas.style.width  = `${w}px`;
    canvas.style.height = `${h}px`;

    this.gradeLetter = gradeLetter;
    this.score       = score;
    this.color       = GradeCard.gradeColor(gradeLetter);
    this._animStart  = null;
    this._duration   = 1000;
    this._frame      = 0;
    this._render     = this._render.bind(this);
  }

  static gradeColor(grade) {
    return { A:'#1E6838', B:'#1048A0', C:'#845800', D:'#A84800', F:'#A82818' }[grade] || '#4A7A58';
  }

  draw() {
    this._animStart = null;
    cancelAnimationFrame(this._frame);
    this._frame = requestAnimationFrame(this._render);
  }

  _easeOutCubic(t) { return 1 - Math.pow(1 - t, 3); }

  _render(ts) {
    if (!this._animStart) this._animStart = ts;
    const progress = Math.min(1, (ts - this._animStart) / this._duration);
    this._drawFrame(this._easeOutCubic(progress));
    if (progress < 1) this._frame = requestAnimationFrame(this._render);
  }

  _drawFrame(ease) {
    const { canvas, ctx, score, color } = this;
    const dpr = window.devicePixelRatio || 1;
    const W   = canvas.width / dpr;
    const H   = canvas.height / dpr;
    ctx.clearRect(0, 0, W, H);

    const cx = W / 2, cy = H / 2;
    const R  = Math.min(cx, cy) - 14;
    const startAngle = -Math.PI / 2;
    const endAngle   = startAngle + Math.PI * 2 * (score / 100) * ease;

    // Background track
    ctx.beginPath();
    ctx.arc(cx, cy, R, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(0,0,0,0.07)';
    ctx.lineWidth   = 11;
    ctx.stroke();

    // Progress arc
    if (score > 0) {
      const grad = ctx.createLinearGradient(0, 0, W, H);
      grad.addColorStop(0, color);
      grad.addColorStop(1, color + 'BB');
      ctx.beginPath();
      ctx.arc(cx, cy, R, startAngle, endAngle);
      ctx.strokeStyle = grad;
      ctx.lineWidth   = 11;
      ctx.lineCap     = 'round';
      ctx.stroke();
    }

    // Grade letter in center
    ctx.fillStyle    = color;
    ctx.font         = `400 ${Math.round(R * 0.82)}px 'DM Serif Display', serif`;
    ctx.textAlign    = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(this.gradeLetter, cx, cy - 4);

    // Score below letter
    const displayScore = Math.round(score * ease);
    ctx.fillStyle = 'rgba(35,32,24,0.42)';
    ctx.font      = `500 11px 'DM Sans', sans-serif`;
    ctx.fillText(`${displayScore}/100`, cx, cy + R * 0.52);
  }
}

window.GradeCard = GradeCard;
