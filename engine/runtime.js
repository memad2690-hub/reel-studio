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
    anims = [...document.querySelectorAll('.a')].map(g => ({ g, i: +g.dataset.in, o: +g.dataset.out, k: g.dataset.k, x: g.dataset.x || 'fade',
      fx: +(g.dataset.fx || 0), fy: +(g.dataset.fy || 0) }));
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
        // look 2: a run of English words inside a right-to-left line keeps its English order
        // ("apples to oranges" must not read "to apples" when placed right to left)
        let place = ln;
        if ((D.look || 1) >= 2) {
          const lat = o => /^[A-Za-z0-9][A-Za-z0-9.%$'&+-]*$/.test((o.t.textContent || '').trim());
          place = []; let i = 0;
          while (i < ln.length) { if (lat(ln[i])) { let j = i; while (j < ln.length && lat(ln[j])) j++; place.push(...ln.slice(i, j).reverse()); i = j; }
            else place.push(ln[i++]); }
        }
        place.forEach(o => {
          const cx = x - o.w / 2; x -= o.w + gap;
          o.g.setAttribute('transform', `translate(${cx.toFixed(1)},${(y0 + li * size * lh).toFixed(1)})`);
          const bg = o.g.querySelector('.kwbg');
          if (bg) { const fs = +o.t.getAttribute('font-size'); bg.setAttribute('x', -o.w / 2 - 14); bg.setAttribute('y', -fs * 0.42);
            bg.setAttribute('width', o.w + 28); bg.setAttribute('height', fs * 0.8); }
          kws.push({ g: o.g, inner: o.t, bg, t0: +o.g.dataset.t0, int: o.g.dataset.int, emph: o.g.dataset.emph === '1' });
        });
      });
      // look 2: a long phrase must not run off its region or the frame. Shrink the block around its centre line to the
      // region's room (data-room) and keep it inside 90…1770 px of the frame; never under the 46 px readable floor.
      if ((D.look || 1) >= 2 && lines.length > 1) {
        const need = (lines.length - 1) * size * lh + size * 1.5;
        let f = k.dataset.room ? +k.dataset.room / need : 1;
        const m = k.getCTM(); if (m) { const half = need / 2 * (m.d || 1); f = Math.min(f, (1770 - m.f) / half, (m.f - 90) / half); }
        f = Math.max(Math.min(1, f), 46 / size);
        if (f < 0.999) k.setAttribute('transform', `scale(${f.toFixed(3)})`);
      }
    });
    dims = [...document.querySelectorAll('.dim')].map(el => ({ el, t0: +el.dataset.t0 }));
    kbs = [...document.querySelectorAll('.kb')].map(el => ({ el, z: +el.dataset.z, d: +el.dataset.d,
      t0: el.closest('.a') ? +el.closest('.a').dataset.in : 0 }));
    kbs.forEach(o => { o.el.style.transformBox = 'fill-box'; o.el.style.transformOrigin = '50% 50%'; });
    mainEl = document.getElementById('main'); flashEl = document.getElementById('flash');
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
    const cur = sc[idx], before = idx > 0 ? sc[idx - 1] : null;
    let target = L(cur.card || 'top');
    let prev = before ? L(before.pre && before.pre[1] >= before.end - 1e-3 ? before.pre[0] : (before.card || 'top')) : target;
    let t0 = cur.start;
    if (cur.pre) {                                  // speaker-first: big until the scene's graphics arrive
      if (t < cur.pre[1]) { target = L(cur.pre[0]); if (!before) prev = target; }
      else { prev = L(cur.pre[0]); t0 = cur.pre[1]; }
    }
    const p = easeInOut(clamp((t - t0) / SLIDE, 0, 1));
    const out = { target, scene: sc[idx] };
    ['x', 'y', 'w', 'h', 'r', 'b'].forEach(k => { out[k] = prev[k] + (target[k] - prev[k]) * p; });
    out.rot = (prev.rot || 0) + ((target.rot || 0) - (prev.rot || 0)) * p;
    out.sticker = target.sticker ? p : (prev.sticker ? 1 - p : 0);
    return out;
  }

  const maskOK = t => { if (!D.cut) return false;
    const sc = D.scenes.find(s => t >= s.start && t < s.end);
    if (sc && sc.cutok !== undefined) return sc.cutok;          // decided per scene by the build (no flicker)
    const q = D.maskq[Math.floor(t * D.fps + 1e-6)]; return q === undefined || q >= D.maskMin; };
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
    let op = Math.min(1, 3 * p), sc = 1, rot = 0, tx = 0, ty = 0, clip = '', blur = 0;
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
    else if (k === 'blur-in') { op = easeOut(p); blur = 14 * (1 - easeOut(p)); sc = 0.96 + 0.04 * easeOut(p); }   // text swap
    else if (k === 'rise') { const q = clamp((t - a.i) / 0.5, 0, 1); ty = 44 * (1 - easeOut(q)); op = Math.min(1, 2.5 * q);
      blur = 6 * (1 - easeOut(q)); sc = 0.94 + 0.06 * easeOut(q); }                                                   // toast rise
    else if (k === 'burst') { const q = clamp((t - a.i) / 0.55, 0, 1), e = easeOutBack(q);   // out of a point to its place
      tx = a.fx * (1 - easeOut(q)); ty = a.fy * (1 - easeOut(q)); sc = 0.35 + 0.65 * e; op = Math.min(1, 4 * q); }
    else if (k === 'none') op = 1;
    return { op, sc, rot, tx, ty, clip, blur };
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
    else if (a.x === 'blur') { v.blur = (v.blur || 0) + 12 * easeInOut(q); v.op *= 1 - q; }
    else v.op *= 1 - q;                             // fade (default)
    return v;
  }

  const CAPS = {   // caption presets: container style, active-word style (null = no active word)
    box: null, highlight: null, clean: null,
    kinetic:   { box: 'background:none;color:#fff;font-size:74px;text-shadow:0 4px 0 #000,0 0 18px rgba(0,0,0,.8)', act: 'color:HL' },
    editorial: { box: 'background:#fff;color:#111;border:5px solid #111;border-radius:0;box-shadow:8px 8px 0 #111', act: null },
    energy:    { box: 'background:HL;color:#111;border-radius:16px;font-size:64px', act: 'background:#d64541;color:#fff;padding:0 10px;border-radius:10px' },
    minimal:   { box: (D.look >= 2 ? 'background:none;color:#fff;font-size:56px;font-weight:800;text-shadow:0 2px 3px rgba(0,0,0,.9),0 0 14px rgba(0,0,0,.75)'
                                     : 'background:none;color:#fff;font-size:42px;font-weight:700;text-shadow:0 2px 6px rgba(0,0,0,.85)'), act: null },
  };
  // Animated presets: every word is its own inline-block (Arabic letters keep joining), motion is driven by the word's
  // spoken time so preview and render match; c.k = the line's key word (build.py key_word), RTL lines move right→left.
  const AR = /[؀-ۿ]/;
  const pad2 = n => String(n).padStart(2, '0');
  const SHADOW = 'text-shadow:0 3px 4px rgba(0,0,0,.85),0 0 16px rgba(0,0,0,.55)';
  const STICK = ['★', '✦', '♥', '✸'], POP_BG = [['#c6f432', '#111'], ['#ff8fc7', '#111'], ['#ffffff', '#111'], ['#7cc4ff', '#111']];
  const ANIM = {
    'editorial-highlight': {
      box: `background:none;padding:0;color:#fff;font:700 66px/1.25 Amiri,Cairo,serif;${SHADOW}`,
      html(c, t, e, w) {
        const ci = D.captions.indexOf(c), n = D.captions.length;
        const num = `<div style="font:700 20px Cairo;letter-spacing:3px;opacity:.75;direction:ltr;margin-bottom:6px">${pad2(ci + 1)} / ${pad2(n)}</div>`;
        return num + w.map((x, j) => {
          const q = clamp((t - c.wt[j] + 0.06) / 0.28, 0, 1), y = 16 * (1 - easeOut(q));
          let st = `display:inline-block;opacity:${q.toFixed(3)};transform:translateY(${y.toFixed(1)}px)`;
          if (j === c.k) {
            const g = easeOut(clamp((t - c.wt[j] - 0.05) / 0.32, 0, 1));
            st += `;padding:0 12px;transform:translateY(${y.toFixed(1)}px) rotate(-1.5deg);background:linear-gradient(#b3261e,#b3261e) no-repeat ${c.rtl ? 'right' : 'left'} 58%/${(g * 100).toFixed(1)}% 78%`;
          }
          return `<span style="${st}">${e(x)}</span>`;
        }).join(' ');
      },
    },
    'pop-sticker': {
      box: 'background:none;padding:0;color:#111;font:900 54px/1.15 Cairo;text-shadow:none;white-space:normal;width:max-content;max-width:900px;text-align:center',
      html(c, t, e, w) {
        const ci = D.captions.indexOf(c);
        let out = w.map((x, j) => {
          const q = clamp((t - c.wt[j] + 0.04) / 0.34, 0, 1);
          const sc = q <= 0 ? 0 : spring(q), rot = ((ci + j) % 2 ? 2.5 : -2.5) * (j === c.k ? 1.6 : 1);
          const [bg, fg] = j === c.k ? ['#7c3aed', '#fff'] : POP_BG[(ci * 3 + j) % POP_BG.length];
          return `<span style="display:inline-block;margin:6px 5px;padding:0 18px 8px;background:${bg};color:${fg};border:4px solid #111;`
            + `border-radius:14px;box-shadow:6px 6px 0 #111;opacity:${q > 0 ? 1 : 0};transform:rotate(${rot}deg) scale(${sc.toFixed(3)})">${e(x)}</span>`;
        }).join('');
        [[-34, 8], [-18, 88]].forEach(([top, left], s) => {         // two stickers pop just after the line starts
          const q = clamp((t - c.start - 0.15 - 0.12 * s) / 0.3, 0, 1);
          out += `<span style="position:absolute;top:${s ? 'auto' : top + 'px'};bottom:${s ? top + 'px' : 'auto'};left:${left}%;`
            + `font:900 ${s ? 34 : 42}px Cairo;color:${s ? '#ff4f9a' : D.hlColor};-webkit-text-stroke:2px #111;`
            + `transform:scale(${(q > 0 ? spring(q) : 0).toFixed(3)}) rotate(${s ? 14 : -12}deg)">${STICK[(ci + s) % STICK.length]}</span>`;
        });
        return out;
      },
    },
    'paper-plane': {
      box: `background:none;padding:0 20px;color:#fff;font:800 58px/1.3 Cairo;${SHADOW}`,
      html(c, t, e, w) {
        const p = easeInOut(clamp((t - c.start + 0.05) / 0.55, 0, 1));
        const fly = clamp((t - c.start + 0.05) / 0.75, 0, 1.4), px = c.rtl ? 100 - fly * 100 : fly * 100;
        const clip = c.rtl ? `inset(-40px 0 -40px ${((1 - p) * 100).toFixed(1)}%)` : `inset(-40px ${((1 - p) * 100).toFixed(1)}% -40px 0)`;
        const words = w.map((x, j) => `<span style="display:inline-block${j === c.k ? ';color:' + D.hlColor : ''}">${e(x)}</span>`).join(' ');
        const plane = fly >= 1.4 ? '' : `<svg width="70" height="70" viewBox="0 0 24 24" style="position:absolute;top:50%;left:${px.toFixed(1)}%;`
          + `transform:translate(-50%,-62%) scaleX(${c.rtl ? -1 : 1}) rotate(-8deg);opacity:${(1 - clamp((fly - 1.1) / 0.3, 0, 1)).toFixed(3)};`
          + `filter:drop-shadow(0 3px 3px rgba(0,0,0,.6))"><path d="M2 12 22 3 15 21 11 13Z" fill="${D.hlColor}" stroke="#111" stroke-width="1.3" `
          + `stroke-linejoin="round"/><path d="M11 13 22 3" stroke="#111" stroke-width="1.3"/></svg>`;
        return `<span style="display:inline-block;clip-path:${clip}">${words}</span>${plane}`;
      },
    },
    'rolodex-flip': {
      box: `background:none;padding:0;color:#fff;font:900 60px/1.25 Cairo;${SHADOW};perspective:600px`,
      html(c, t, e, w) {
        return w.map((x, j) => {
          const q = clamp((t - c.wt[j] + 0.03) / 0.3, 0, 1), r = -95 * (1 - easeOut(q));
          const key = j === c.k ? `;background:${D.hlColor};color:#111;text-shadow:none;padding:0 12px 6px;border-radius:10px` : '';
          return `<span style="display:inline-block;transform-origin:50% 0;transform:rotateX(${r.toFixed(1)}deg);opacity:${q > 0 ? Math.min(1, q * 3).toFixed(3) : 0}${key}">${e(x)}</span>`;
        }).join(' ');
      },
    },
  };
  let capBase = null;
  const sceneAt = t => D.scenes.find(s => t >= s.start && t < s.end);
  function showCaption(c, rc, t) {
    const sc0 = sceneAt(c.start);
    const style = (sc0 && sc0.cap) || D.capStyle || 'box';
    const P = CAPS[style];
    if (capBase === null) capBase = cap.getAttribute('style') || '';
    const AN = ANIM[style];
    if (AN) cap.setAttribute('style', capBase + ';' + AN.box);
    else if (P) cap.setAttribute('style', capBase + ';' + P.box.replace(/HL/g, D.hlColor));
    else if (cap.dataset.st && cap.dataset.st !== style) cap.setAttribute('style', capBase);   // back from a styled preset
    cap.dataset.st = style;
    const esc = s => s.replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]));
    const tg0 = (rc && (rc.target || rc)) || {}, onPage = card && !(tg0.h >= 600);
    let act = -1;
    if (P && P.act && c.wt) c.wt.forEach((s0, j) => { if (t >= s0) act = j; });
    if (AN) {
      if (c.rtl === undefined) c.rtl = AR.test(c.text);
      cap.style.direction = c.rtl ? 'rtl' : 'ltr';
      cap.innerHTML = AN.html(c, t, esc, c.text.split(' '));
      cap.style.opacity = clamp((c.end - t) / 0.12, 0, 1).toFixed(3);     // quick fade at the end of the line
    } else if (style === 'box' && !(c.hl && c.hl.length)) cap.textContent = c.text;
    else {
      cap.innerHTML = c.text.split(' ').map((w, j) => (c.hl || []).includes(j) && !(P && P.act)
        ? `<span style="background:${D.hlColor};color:#111;padding:0 10px;border-radius:8px">${esc(w)}</span>`
        : j === act ? `<span style="${(onPage && style === 'kinetic' ? 'background:HL;color:#111;padding:0 8px;border-radius:8px;text-shadow:none' : P.act).replace(/HL/g, D.hlColor)}">${esc(w)}</span>` : esc(w)).join(' ');
    }
    cap.style.display = 'block';
    if (!card) return;
    // placement follows the scene's target layout, so the caption never rides a shrinking card
    const tg = rc.target || rc;
    let big = tg.h >= 600, cx = rc.x + rc.w / 2;
    if (D.look >= 2 && big && tg.w < 700) {
      // look 2 PiP (480×600): the caption stays on the card's bottom edge (not on the graphics area); if it is wider
      // than the card it is shifted sideways so it stays on screen
      const half = cap.offsetWidth / 2 + 24;
      cx = Math.max(half, Math.min(1080 - half, cx));
    } else if (tg.w < 700) big = false;
    cap.style.left = (big ? cx : 540) + 'px';
    const mb = (D.cap && D.cap.max_bottom) || 0;                // keep captions above platform buttons/captions
    let top = big ? rc.y + rc.h - 110 : 1560;
    if (mb && big) top = Math.min(top, mb - 120);
    if (AN && big) top = Math.min(top, rc.y + rc.h - cap.offsetHeight - 34);   // taller animated lines stay inside the card
    if (D.cap && D.cap.safe && mb) {                            // safe-zone captions: the whole box ends above max_bottom;
      const hc = cap.offsetHeight;                              // a small card at the top carries its caption right under it
      if (!big && tg.y + tg.h < 640) { top = tg.y + tg.h + 14; cap.style.left = (tg.x + tg.w / 2) + 'px'; }
      else top = Math.min(top, mb - hc);
    }
    cap.style.top = top + 'px';
    if (style === 'clean') { cap.style.background = 'none'; cap.style.textShadow = '0 3px 0 #000, 0 0 14px rgba(0,0,0,.7)'; }
    // light-on-dark presets sitting on the page (not on the video card) switch to dark text for contrast
    if (!big && (style === 'kinetic' || style === 'minimal' || style === 'clean' || style === 'editorial-highlight'
                 || style === 'paper-plane' || style === 'rolodex-flip')) { cap.style.color = '#111'; cap.style.textShadow = 'none'; }
  }

  // scene transitions on the main layer (footage + graphics; captions, film and page background stay put)
  let mainEl, flashEl;
  function transition(t) {
    if (!mainEl) return;
    let fil = '', tf = '', fl = 0;
    for (const s of D.scenes) {
      if (!s.tr) continue;
      const [k, h] = s.tr, d = t - s.start;
      if (d < -h || d > h) continue;
      const u = clamp(d / h, -1, 1), near = 1 - Math.abs(u);
      if (k === 'blur') fil = `blur(${(12 * near).toFixed(2)}px) brightness(${(1 + 0.08 * near).toFixed(3)})`;
      else if (k === 'whip') { const sg = u < 0 ? -1 : 1; tf = `translateX(${(sg * 180 * near * near).toFixed(1)}px)`;
        fil = `blur(${(16 * near).toFixed(2)}px)`; }
      else if (k === 'zoom' && d >= 0) { const q = easeOut(clamp(d / h, 0, 1)); tf = `scale(${(1.1 - 0.1 * q).toFixed(4)})`;
        fil = d < 0.1 ? `blur(${(6 * (1 - d / 0.1)).toFixed(2)}px)` : ''; }
      else if (k === 'flash') fl = d < 0 ? clamp(1 + d / 0.06, 0, 1) : Math.max(0, 1 - d / h);
    }
    mainEl.style.filter = fil; mainEl.style.transform = tf;
    if (flashEl) flashEl.style.opacity = fl.toFixed(3);
  }

  window.setTime = function (t) {
    scenes.forEach(s => { s.g.style.display = (t >= s.s && t < s.e) ? '' : 'none'; });
    anims.forEach(a => {
      const st = a.g.style;
      if (t < a.i || t >= a.o) { st.opacity = 0; return; }
      const v = exitFx(a, t, entrance(a, t));
      st.opacity = v.op; st.transform = `translate(${v.tx}px, ${v.ty}px) rotate(${v.rot}deg) scale(${v.sc})`;
      st.clipPath = v.clip || '';
      st.filter = v.blur > 0.05 ? `blur(${v.blur.toFixed(2)}px)` : '';
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
      let v = c.from + (c.to - c.from) * easeOut(p);
      if (D.look >= 2 && p < 1) {                     // count in round steps (no odd values like 99,103 mid-count)
        const step = Math.pow(10, Math.max(0, Math.floor(Math.log10(Math.max(1, Math.abs(c.to)))) - 2));
        v = Math.round(v / step) * step;
      }
      c.t.textContent = c.pre + fmt(v) + c.suf;
    });
    let rc = null;
    if (card) { rc = cardRect(t); placeCard(rc, t); }
    kbs.forEach(o => { o.el.style.transform = `scale(${1 + (o.z - 1) * clamp((t - o.t0) / o.d, 0, 1)})`; });
    if (grainT) grainT.setAttribute('seed', String(Math.floor(t * D.fps) % 997 + 1));
    const c = D.captions.find(c => t >= c.start && t < c.end);
    const muted = (D.capMute || []).some(w => t >= w[0] && t < w[1]);   // kinetic text shows these words already
    if (c && !muted) showCaption(c, rc || {}, t); else cap.style.display = 'none';
    transition(t);
  };

  window.cardFrame = t => Math.floor(t * D.fps + 1e-6) + 1;
  window.ready = (document.fonts ? Promise.all([document.fonts.load('900 60px Cairo'), document.fonts.load('800 40px Cairo'), document.fonts.load('700 60px Amiri', 'ب'), document.fonts.load('700 60px Amiri', 'A')]).then(() => document.fonts.ready) : Promise.resolve())
    .then(() => { init(); window.setTime(0); return true; });
})();
