// Deterministic frame runtime: window.setTime(t) draws any moment.
(function () {
  const D = window.D;
  const easeOutBack = p => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(p - 1, 3) + c1 * Math.pow(p - 1, 2); };
  const easeOut = p => 1 - Math.pow(1 - p, 3);
  const easeInOut = p => p < .5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2;
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  let scenes, anims, counts, cap, card, cardImg;

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
    anims = [...document.querySelectorAll('.a')].map(g => ({ g, i: +g.dataset.in, o: +g.dataset.out, k: g.dataset.k, x: g.dataset.x || 'fade' }));
    counts = [...document.querySelectorAll('.count')].map(t => ({ t, from: +t.dataset.from, to: +t.dataset.to, dur: +t.dataset.dur,
      pre: t.dataset.prefix || '', suf: t.dataset.suffix || '', g: t.closest('.a') }));
    cap = document.getElementById('cap'); card = document.getElementById('card');
    cardImg = document.getElementById('cardimg');
  }

  // deterministic damped spring (0 → 1), no state between frames
  const spring = (p, z = 0.55, w = 13) => {
    const t = p * 0.9; if (t <= 0) return 0;
    const wd = w * Math.sqrt(1 - z * z);
    return 1 - Math.exp(-z * w * t) * (Math.cos(wd * t) + (z * w / wd) * Math.sin(wd * t));
  };
  const SLIDE = D.slide || 0.45;
  const L = name => (D.layouts && D.layouts[name]) || { x: D.card.x, y: D.card[name] ?? D.card.top, w: D.card.w, h: D.card.h, r: 44, b: 7 };

  function cardRect(t) {
    const sc = D.scenes; if (!sc.length) return L('top');
    let idx = sc.findIndex(s => t >= s.start && t < s.end); if (idx < 0) idx = t < sc[0].start ? 0 : sc.length - 1;
    const target = L(sc[idx].card || 'top');
    const prev = idx > 0 ? L(sc[idx - 1].card || 'top') : target;
    const p = easeInOut(clamp((t - sc[idx].start) / SLIDE, 0, 1));
    const out = { target };
    ['x', 'y', 'w', 'h', 'r', 'b'].forEach(k => { out[k] = prev[k] + (target[k] - prev[k]) * p; });
    return out;
  }

  function placeCard(rc) {
    const st = card.style;
    st.left = rc.x + 'px'; st.top = rc.y + 'px'; st.width = rc.w + 'px'; st.height = rc.h + 'px';
    st.borderRadius = rc.r + 'px'; st.borderWidth = rc.b + 'px';
    st.boxShadow = rc.b > 0.5 ? '12px 14px 0 rgba(34,34,34,.22)' : 'none';
    if (D.cf && D.cf.full && cardImg) {
      // full-frame (1080x1920) card frames: cover the card, keep the face focus point near the centre
      const iw = rc.w - 2 * rc.b, ih = rc.h - 2 * rc.b;
      const s = Math.max(iw / 1080, ih / 1920);
      const W = 1080 * s, H = 1920 * s;
      const fx = D.focus[0] * W, fy = D.focus[1] * H;
      const left = clamp(iw / 2 - fx, iw - W, 0), top = clamp(ih * 0.5 - fy, ih - H, 0);
      const is = cardImg.style;
      is.objectFit = 'fill'; is.width = W + 'px'; is.height = H + 'px'; is.left = left + 'px'; is.top = top + 'px';
    }
  }

  function entrance(a, t) {
    const p = clamp((t - a.i) / 0.4, 0, 1);
    let op = Math.min(1, 3 * p), sc = 1, rot = 0, tx = 0, ty = 0, clip = '';
    const k = a.k;
    if (k === 'pop') sc = easeOutBack(p);
    else if (k === 'stamp') { sc = 1.8 - 0.8 * easeOut(p); op = Math.min(1, 4 * p); }
    else if (k === 'shake') { sc = easeOutBack(p); const q = (t - a.i); rot = 9 * Math.sin(q * 28) * Math.exp(-q * 4); }
    else if (k === 'fade') op = p;
    else if (k === 'slide' || k === 'slide-up') { ty = 50 * (1 - easeOut(p)); op = p; }
    else if (k === 'slide-down') { ty = -60 * (1 - easeOut(p)); op = p; }
    else if (k === 'slide-left') { tx = 90 * (1 - easeOut(p)); op = p; }      // comes in from the right (RTL reading start)
    else if (k === 'slide-right') { tx = -90 * (1 - easeOut(p)); op = p; }
    else if (k === 'spring') { const q = clamp((t - a.i) / 0.7, 0, 1); sc = 0.4 + 0.6 * spring(q); op = Math.min(1, 4 * q); }
    else if (k === 'wipe') { const q = easeOut(clamp((t - a.i) / 0.5, 0, 1)); clip = `inset(-20% -20% -20% ${(1 - q) * 120 - 20}%)`; op = 1; }
    else if (k === 'none') op = 1;
    return { op, sc, rot, tx, ty, clip };
  }

  function exitFx(a, t, v) {
    const left = a.o - t;
    if (!(left < 0.3 && a.o - a.i > 0.5)) return v;
    const q = 1 - left / 0.3;                       // 0 → 1 over the last 0.3 s
    if (a.x === 'none') return v;
    if (a.x === 'shrink') { v.sc *= 1 - 0.6 * easeInOut(q); v.op *= 1 - q; }
    else if (a.x === 'slide-left') { v.tx -= 90 * easeInOut(q); v.op *= 1 - q; }
    else if (a.x === 'slide-right') { v.tx += 90 * easeInOut(q); v.op *= 1 - q; }
    else if (a.x === 'slide-down') { v.ty += 60 * easeInOut(q); v.op *= 1 - q; }
    else v.op *= 1 - q;                             // fade (default)
    return v;
  }

  function showCaption(c, rc) {
    const style = D.capStyle || 'box';
    if (style === 'box' && !(c.hl && c.hl.length)) cap.textContent = c.text;
    else {
      const esc = s => s.replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]));
      cap.innerHTML = c.text.split(' ').map((w, j) => (c.hl || []).includes(j)
        ? `<span style="background:${D.hlColor};color:#111;padding:0 10px;border-radius:8px">${esc(w)}</span>` : esc(w)).join(' ');
    }
    cap.style.display = 'block';
    if (!card) return;
    // placement follows the scene's target layout, so the caption never rides a shrinking card
    const tg = rc.target || rc, big = tg.h >= 600;
    cap.style.left = (big ? rc.x + rc.w / 2 : 540) + 'px';
    cap.style.top = (big ? rc.y + rc.h - 110 : 1560) + 'px';
    if (style === 'clean') { cap.style.background = 'none'; cap.style.textShadow = '0 3px 0 #000, 0 0 14px rgba(0,0,0,.7)'; }
  }

  window.setTime = function (t) {
    scenes.forEach(s => { s.g.style.display = (t >= s.s && t < s.e) ? '' : 'none'; });
    anims.forEach(a => {
      const st = a.g.style;
      if (t < a.i || t >= a.o) { st.opacity = 0; return; }
      const v = exitFx(a, t, entrance(a, t));
      st.opacity = v.op; st.transform = `translate(${v.tx}px, ${v.ty}px) rotate(${v.rot}deg) scale(${v.sc})`;
      st.clipPath = v.clip || '';
    });
    counts.forEach(c => {
      const t0 = c.g ? +c.g.dataset.in : 0; const p = clamp((t - t0) / c.dur, 0, 1);
      c.t.textContent = c.pre + fmt(c.from + (c.to - c.from) * easeOut(p)) + c.suf;
    });
    let rc = null;
    if (card) { rc = cardRect(t); placeCard(rc); }
    const c = D.captions.find(c => t >= c.start && t < c.end);
    if (c) showCaption(c, rc || {}); else cap.style.display = 'none';
  };

  window.cardFrame = t => Math.floor(t * D.fps + 1e-6) + 1;
  window.ready = (document.fonts ? Promise.all([document.fonts.load('900 60px Cairo'), document.fonts.load('800 40px Cairo')]).then(() => document.fonts.ready) : Promise.resolve())
    .then(() => { init(); window.setTime(0); return true; });
})();
