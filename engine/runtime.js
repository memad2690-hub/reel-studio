// Deterministic frame runtime: window.setTime(t) draws any moment.
(function () {
  const D = window.D;
  const easeOutBack = p => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(p - 1, 3) + c1 * Math.pow(p - 1, 2); };
  const easeOut = p => 1 - Math.pow(1 - p, 3);
  const easeInOut = p => p < .5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2;
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  let scenes, anims, counts, cap, card, cardImg, parts = [], kws = [], dims = [], kbs = [], cutDiv, cutImg, grainT;

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
    // chart parts animate on their own clocks (absolute data-t0 + optional delay data-dl)
    const T = el => +el.dataset.t0 + (+el.dataset.dl || 0);
    // kinetic phrases: measure each word, wrap into right-to-left lines inside data-w, centre each line
    kws = [];
    document.querySelectorAll('.kin').forEach(k => {
      const W = +k.dataset.w, size = +k.dataset.size, lh = +k.dataset.lh, gap = size * 0.28;
      const ws = [...k.querySelectorAll('.kw')].map(g => { const t = g.querySelector('text'); return { g, t, w: t.getComputedTextLength() }; });
      const lines = []; let cur = [], cw = 0;
      ws.forEach(o => { const add = (cur.length ? gap : 0) + o.w; if (cur.length && cw + add > W) { lines.push([cur, cw]); cur = []; cw = 0; }
        cw += (cur.length ? gap : 0) + o.w; cur.push(o); });
      if (cur.length) lines.push([cur, cw]);
      const y0 = -(lines.length - 1) * size * lh / 2;
      lines.forEach(([ln, lw], li) => {
        let x = lw / 2;                                           // start at the right edge (RTL)
        ln.forEach(o => {
          const cx = x - o.w / 2; x -= o.w + gap;
          o.g.setAttribute('transform', `translate(${cx.toFixed(1)},${(y0 + li * size * lh).toFixed(1)})`);
          const bg = o.g.querySelector('.kwbg');
          if (bg) { const fs = +o.t.getAttribute('font-size'); bg.setAttribute('x', -o.w / 2 - 14); bg.setAttribute('y', -fs * 0.42);
            bg.setAttribute('width', o.w + 28); bg.setAttribute('height', fs * 0.8); }
          kws.push({ g: o.g, inner: o.t, bg, t0: +o.g.dataset.t0, int: o.g.dataset.int, emph: o.g.dataset.emph === '1' });
        });
      });
    });
    dims = [...document.querySelectorAll('.dim')].map(el => ({ el, t0: +el.dataset.t0 }));
    kbs = [...document.querySelectorAll('.kb')].map(el => ({ el, z: +el.dataset.z, d: +el.dataset.d,
      t0: el.closest('.a') ? +el.closest('.a').dataset.in : 0 }));
    kbs.forEach(o => { o.el.style.transformBox = 'fill-box'; o.el.style.transformOrigin = '50% 50%'; });
    cutDiv = document.getElementById('cut'); cutImg = document.getElementById('cutimg'); grainT = document.getElementById('grt');
    parts = [...document.querySelectorAll('.grow,.draw,.arc,.tl')].map(el => {
      const k = el.classList.contains('grow') ? 'grow' : el.classList.contains('draw') ? 'draw' : el.classList.contains('arc') ? 'arc' : 'tl';
      const o = { el, k, t0: T(el), d: +el.dataset.d || 0.5 };
      if (k === 'grow') { el.style.transformBox = 'fill-box'; el.style.transformOrigin = el.dataset.o || '50% 100%'; }
      if (k === 'draw') { o.len = el.getTotalLength ? el.getTotalLength() : 1000; el.style.strokeDasharray = o.len; }
      if (k === 'arc') { o.len = +el.dataset.len; o.circ = +el.dataset.circ; }
      return o;
    });
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
    const out = { target, scene: sc[idx] };
    ['x', 'y', 'w', 'h', 'r', 'b'].forEach(k => { out[k] = prev[k] + (target[k] - prev[k]) * p; });
    out.rot = (prev.rot || 0) + ((target.rot || 0) - (prev.rot || 0)) * p;
    out.sticker = target.sticker ? p : (prev.sticker ? 1 - p : 0);
    return out;
  }

  const maskOK = t => { if (!D.cut) return false; const q = D.maskq[Math.floor(t * D.fps + 1e-6)]; return q === undefined || q >= D.maskMin; };
  function camZoom(sc, t) {
    let z = 1;
    if (!sc) return z;
    if (sc.zoom) z *= sc.zoom[0] + (sc.zoom[1] - sc.zoom[0]) * clamp((t - sc.start) / Math.max(0.1, sc.end - sc.start), 0, 1);
    if (sc.punch && t >= sc.punch[0]) z *= 1 + (sc.punch[1] - 1) * easeOut(clamp((t - sc.punch[0]) / 0.25, 0, 1));
    return z;
  }
  function fit(img, iw, ih, z) {
    // full-frame (1080x1920) card frames: cover the box, keep the face focus point near the centre, zoom z
    const s = Math.max(iw / 1080, ih / 1920) * z;
    const W = 1080 * s, H = 1920 * s;
    const left = clamp(iw / 2 - D.focus[0] * W, iw - W, 0), top = clamp(ih * 0.5 - D.focus[1] * H, ih - H, 0);
    const is = img.style;
    is.objectFit = 'fill'; is.width = W + 'px'; is.height = H + 'px'; is.left = left + 'px'; is.top = top + 'px';
  }
  function placeCard(rc, t) {
    const ok = maskOK(t);
    const stick = rc.sticker > 0.5 && ok;                      // sticker layout falls back to a normal card on a bad mask
    const b = stick ? 0 : (rc.sticker > 0.5 ? 6 : rc.b), r = stick ? 0 : (rc.sticker > 0.5 ? 40 : rc.r);
    const st = card.style;
    st.left = rc.x + 'px'; st.top = rc.y + 'px'; st.width = rc.w + 'px'; st.height = rc.h + 'px';
    st.borderRadius = r + 'px'; st.borderWidth = b + 'px'; st.transform = `rotate(${rc.rot || 0}deg)`;
    st.boxShadow = b > 0.5 ? '12px 14px 0 rgba(34,34,34,.22)' : 'none';
    st.background = stick ? 'transparent' : '#333';
    if (!(D.cf && D.cf.full && cardImg)) return;
    const sc = rc.scene, z = camZoom(sc, t);
    const par = sc && sc.parallax && ok ? sc.parallax * clamp((t - sc.start) / Math.max(0.1, sc.end - sc.start), 0, 1) : 0;
    const iw = rc.w - 2 * b, ih = rc.h - 2 * b;
    fit(cardImg, iw, ih, z * (1 + 0.035 * par));
    cardImg.style.opacity = stick ? 0 : 1;
    cardImg.style.filter = par > 0 ? `blur(${(2.5 * Math.min(1, par * 3)).toFixed(2)}px)` : 'none';  // soft depth of field hides ghosting
    if (cutDiv && cutImg) {
      const cs = cutDiv.style;
      cs.left = rc.x + 'px'; cs.top = rc.y + 'px'; cs.width = rc.w + 'px'; cs.height = rc.h + 'px';
      cs.borderRadius = r + 'px'; cs.borderWidth = b + 'px'; cs.transform = st.transform;
      cs.overflow = stick ? 'visible' : 'hidden';
      fit(cutImg, iw, ih, z * (1 + 0.012 * par));
      cutImg.style.visibility = ok ? 'visible' : 'hidden';
      if (par > 0) cutImg.style.top = (parseFloat(cutImg.style.top) - 8 * par) + 'px';
    }
  }
  window.cutKind = t => { const rc = card ? cardRect(t) : null; return rc && rc.sticker > 0.5 ? 'sticker' : 'cut'; };

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

  const CAPS = {   // caption presets: container style, active-word style (null = no active word)
    box: null, highlight: null, clean: null,
    kinetic:   { box: 'background:none;color:#fff;font-size:74px;text-shadow:0 4px 0 #000,0 0 18px rgba(0,0,0,.8)', act: 'color:HL' },
    editorial: { box: 'background:#fff;color:#111;border:5px solid #111;border-radius:0;box-shadow:8px 8px 0 #111', act: null },
    energy:    { box: 'background:HL;color:#111;border-radius:16px;font-size:64px', act: 'background:#d64541;color:#fff;padding:0 10px;border-radius:10px' },
    minimal:   { box: 'background:none;color:#fff;font-size:42px;font-weight:700;text-shadow:0 2px 6px rgba(0,0,0,.85)', act: null },
  };
  let capBase = null;
  function showCaption(c, rc, t) {
    const style = D.capStyle || 'box';
    const P = CAPS[style];
    if (capBase === null) capBase = cap.getAttribute('style') || '';
    if (P) cap.setAttribute('style', capBase + ';' + P.box.replace(/HL/g, D.hlColor));
    const esc = s => s.replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]));
    const tg0 = (rc && (rc.target || rc)) || {}, onPage = card && !(tg0.h >= 600);
    let act = -1;
    if (P && P.act && c.wt) c.wt.forEach((s0, j) => { if (t >= s0) act = j; });
    if (style === 'box' && !(c.hl && c.hl.length)) cap.textContent = c.text;
    else {
      cap.innerHTML = c.text.split(' ').map((w, j) => (c.hl || []).includes(j) && !(P && P.act)
        ? `<span style="background:${D.hlColor};color:#111;padding:0 10px;border-radius:8px">${esc(w)}</span>`
        : j === act ? `<span style="${(onPage && style === 'kinetic' ? 'background:HL;color:#111;padding:0 8px;border-radius:8px;text-shadow:none' : P.act).replace(/HL/g, D.hlColor)}">${esc(w)}</span>` : esc(w)).join(' ');
    }
    cap.style.display = 'block';
    if (!card) return;
    // placement follows the scene's target layout, so the caption never rides a shrinking card
    const tg = rc.target || rc, big = tg.h >= 600;
    cap.style.left = (big ? rc.x + rc.w / 2 : 540) + 'px';
    cap.style.top = (big ? rc.y + rc.h - 110 : 1560) + 'px';
    if (style === 'clean') { cap.style.background = 'none'; cap.style.textShadow = '0 3px 0 #000, 0 0 14px rgba(0,0,0,.7)'; }
    // light-on-dark presets sitting on the page (not on the video card) switch to dark text for contrast
    if (!big && (style === 'kinetic' || style === 'minimal' || style === 'clean')) { cap.style.color = '#111'; cap.style.textShadow = 'none'; }
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
    parts.forEach(o => {
      const p = clamp((t - o.t0) / o.d, 0, 1), e = easeOut(p), st = o.el.style;
      if (o.k === 'grow') { st.transform = `scaleY(${e})`; st.opacity = p > 0 ? 1 : 0; }
      else if (o.k === 'draw') st.strokeDashoffset = o.len * (1 - p);   // linear: reaches each point on time
      else if (o.k === 'arc') o.el.setAttribute('stroke-dasharray', `${(o.len * e).toFixed(2)} ${o.circ}`);
      else st.opacity = clamp((t - o.t0) / 0.25, 0, 1);
    });
    kws.forEach(o => {
      const q = clamp((t - o.t0) / (o.int === 'high' ? 0.35 : 0.45), 0, 1);
      let op = q > 0 ? Math.min(1, 3 * q) : 0, ty = 0, sc = 1, rot = 0;
      if (o.int === 'low') { ty = 18 * (1 - easeOut(q)); }
      else if (o.int === 'high') { sc = 1 + 0.9 * (1 - spring(q)); rot = -10 * (1 - easeOut(q)); }
      else { ty = 46 * (1 - easeOut(q)); sc = 0.82 + 0.18 * spring(q); }
      if (o.emph && q > 0) sc *= 1 + 0.06 * Math.exp(-6 * Math.max(0, t - o.t0 - 0.3)) ;
      o.inner.style.opacity = op; o.inner.style.transformBox = 'fill-box'; o.inner.style.transformOrigin = '50% 50%';
      o.inner.style.transform = `translateY(${ty}px) rotate(${rot}deg) scale(${sc})`;
      if (o.bg) { o.bg.style.transformBox = 'fill-box'; o.bg.style.transformOrigin = '100% 50%';
        o.bg.style.transform = `scaleX(${easeOut(clamp((t - o.t0 - 0.1) / 0.35, 0, 1))})`; }
    });
    dims.forEach(o => { o.el.style.opacity = 1 - 0.6 * clamp((t - o.t0) / 0.4, 0, 1); });
    counts.forEach(c => {
      const t0 = c.g ? +c.g.dataset.in : 0; const p = clamp((t - t0) / c.dur, 0, 1);
      c.t.textContent = c.pre + fmt(c.from + (c.to - c.from) * easeOut(p)) + c.suf;
    });
    let rc = null;
    if (card) { rc = cardRect(t); placeCard(rc, t); }
    kbs.forEach(o => { o.el.style.transform = `scale(${1 + (o.z - 1) * clamp((t - o.t0) / o.d, 0, 1)})`; });
    if (grainT) grainT.setAttribute('seed', String(Math.floor(t * D.fps) % 997 + 1));
    const c = D.captions.find(c => t >= c.start && t < c.end);
    if (c) showCaption(c, rc || {}, t); else cap.style.display = 'none';
  };

  window.cardFrame = t => Math.floor(t * D.fps + 1e-6) + 1;
  window.ready = (document.fonts ? Promise.all([document.fonts.load('900 60px Cairo'), document.fonts.load('800 40px Cairo')]).then(() => document.fonts.ready) : Promise.resolve())
    .then(() => { init(); window.setTime(0); return true; });
})();
