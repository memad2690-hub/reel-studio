// Deterministic frame runtime: window.setTime(t) draws any moment.
(function () {
  const D = window.D;
  const easeOutBack = p => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(p - 1, 3) + c1 * Math.pow(p - 1, 2); };
  const easeOut = p => 1 - Math.pow(1 - p, 3);
  const easeInOut = p => p < .5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2;
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  let scenes, anims, counts, cap, card;

  function fitBoxes() {
    document.querySelectorAll('[data-fit]').forEach(g => {
      const pad = +g.dataset.fit;
      const texts = [...g.querySelectorAll(':scope > text')];
      if (!texts.length) return;
      let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
      texts.forEach(t => { const b = t.getBBox(); x0 = Math.min(x0, b.x); y0 = Math.min(y0, b.y); x1 = Math.max(x1, b.x + b.width); y1 = Math.max(y1, b.y + b.height); });
      const x = x0 - pad, y = y0 - pad * 0.55, w = x1 - x0 + 2 * pad, h = y1 - y0 + pad * 1.1;
      g.querySelectorAll(':scope > .fitbox').forEach(r => {
        r.setAttribute('x', x); r.setAttribute('y', y); r.setAttribute('width', w); r.setAttribute('height', h);
        if (g.dataset.fitround) r.setAttribute('rx', h / 2);
      });
      const tl = g.querySelector(':scope > .tapeL'), tr = g.querySelector(':scope > .tapeR');
      if (tl) { tl.setAttribute('x', x - 14); tl.setAttribute('y', y - 12); }
      if (tr) { tr.setAttribute('x', x + w - 40); tr.setAttribute('y', y - 10); }
    });
  }

  function layoutHeadlines() {
    document.querySelectorAll('.headline').forEach(g => {
      const size = +g.dataset.size, gap = 0.28 * size;
      const parts = [0, 1, 2].map(i => g.querySelector('.hp' + i));
      const widths = parts.map(p => p.textContent.trim() ? p.getComputedTextLength() : 0);
      const used = widths.filter(w => w > 0);
      const total = used.reduce((a, b) => a + b, 0) + gap * Math.max(0, used.length - 1);
      let x = total / 2; // RTL: start from the right edge
      const rect = g.querySelector('.hl-rect');
      parts.forEach((p, i) => {
        p.setAttribute('x', x); p.setAttribute('y', 0);
        if (i === 1) {
          if (widths[1] > 0) {
            const pad = size * 0.14;
            rect.setAttribute('x', x - widths[1] - pad); rect.setAttribute('width', widths[1] + 2 * pad);
            rect.setAttribute('y', -size * 0.5); rect.setAttribute('height', size * 1.02);
            rect.setAttribute('transform', `rotate(-2 ${x - widths[1] / 2} 0)`);
          } else rect.setAttribute('width', 0);
        }
        if (widths[i] > 0) x -= widths[i] + gap;
      });
    });
  }

  function fmt(n) { return Math.round(n).toLocaleString('en-US'); }

  function init() {
    fitBoxes(); layoutHeadlines();
    scenes = [...document.querySelectorAll('.scene')].map(g => ({ g, s: +g.dataset.start, e: +g.dataset.end }));
    anims = [...document.querySelectorAll('.a')].map(g => ({ g, i: +g.dataset.in, o: +g.dataset.out, k: g.dataset.k }));
    counts = [...document.querySelectorAll('.count')].map(t => ({ t, from: +t.dataset.from, to: +t.dataset.to, dur: +t.dataset.dur,
      pre: t.dataset.prefix || '', suf: t.dataset.suffix || '', g: t.closest('.a') }));
    cap = document.getElementById('cap'); card = document.getElementById('card');
  }

  function cardY(t) {
    const sc = D.scenes; if (!sc.length) return D.card.top;
    let idx = sc.findIndex(s => t >= s.start && t < s.end); if (idx < 0) idx = t < sc[0].start ? 0 : sc.length - 1;
    const target = D.card[sc[idx].card || 'top'];
    const prev = idx > 0 ? D.card[sc[idx - 1].card || 'top'] : target;
    const p = clamp((t - sc[idx].start) / 0.45, 0, 1);
    return prev + (target - prev) * easeInOut(p);
  }

  window.setTime = function (t) {
    scenes.forEach(s => { s.g.style.display = (t >= s.s && t < s.e) ? '' : 'none'; });
    anims.forEach(a => {
      const st = a.g.style;
      if (t < a.i || t >= a.o) { st.opacity = 0; return; }
      const p = clamp((t - a.i) / 0.4, 0, 1);
      let op = Math.min(1, 3 * p), sc = 1, rot = 0, ty = 0;
      if (a.k === 'pop') sc = easeOutBack(p);
      else if (a.k === 'stamp') { sc = 1.8 - 0.8 * easeOut(p); op = Math.min(1, 4 * p); }
      else if (a.k === 'shake') { sc = easeOutBack(p); const q = (t - a.i); rot = 9 * Math.sin(q * 28) * Math.exp(-q * 4); }
      else if (a.k === 'fade') op = p;
      else if (a.k === 'slide') { ty = 50 * (1 - easeOut(p)); op = p; }
      else if (a.k === 'none') op = 1;
      const left = a.o - t; if (left < 0.25 && a.o - a.i > 0.5) op *= left / 0.25;
      st.opacity = op; st.transform = `translateY(${ty}px) rotate(${rot}deg) scale(${sc})`;
    });
    counts.forEach(c => {
      const t0 = c.g ? +c.g.dataset.in : 0; const p = clamp((t - t0) / c.dur, 0, 1);
      c.t.textContent = c.pre + fmt(c.from + (c.to - c.from) * easeOut(p)) + c.suf;
    });
    let y = null;
    if (card) { y = cardY(t); card.style.top = y + 'px'; }
    const c = D.captions.find(c => t >= c.start && t < c.end);
    if (c) {
      cap.textContent = c.text; cap.style.display = 'block';
      if (card) cap.style.top = (y + D.card.h - 110) + 'px';
    } else cap.style.display = 'none';
  };

  window.cardFrame = t => Math.floor(t * D.fps + 1e-6) + 1;
  window.ready = (document.fonts ? Promise.all([document.fonts.load('900 60px Cairo'), document.fonts.load('800 40px Cairo')]).then(() => document.fonts.ready) : Promise.resolve())
    .then(() => { init(); window.setTime(0); return true; });
})();
