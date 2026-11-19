// CEOS Engine world runtime. Everything is a pure function of time t (window.setTime), so renders are deterministic.
(() => {
  const E = window.EP, W = E.W, H = E.H, A = E.anchors, D = E.data || {};
  const LIME = '#D1FE17', AMBER = '#FFB547', NS = 'http://www.w3.org/2000/svg';
  const $ = id => document.getElementById(id);
  const mk = (tag, attrs = {}, parent) => { const el = document.createElementNS(NS, tag); for (const k in attrs) el.setAttribute(k, attrs[k]); if (parent) parent.appendChild(el); return el; };
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const ease = p => p < .5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2;
  const easeOut = p => 1 - Math.pow(1 - p, 3);
  const back = p => { const c = 1.6; return 1 + (c + 1) * Math.pow(p - 1, 3) + c * Math.pow(p - 1, 2); };
  const evs = (name) => E.events.filter(e => e.do === name);
  const last = (names, t) => { let r = null; for (const e of E.events) if (e.t <= t && names.includes(e.do)) r = e; return r; };
  const fmt = n => Math.round(n).toLocaleString('en-US');

  // ---------------------------------------------------------------- camera
  const MOVE_DUR = { cut: 0, push: 1.3, pull: 1.6, drift: 2.4, travel: null };
  const cams = E.cams.map((c, i) => ({ ...c, dur: c.move === 'cut' ? 0 : (c.dur || MOVE_DUR[c.move] ||
    ((E.cams[i + 1] ? E.cams[i + 1].t : E.duration) - c.t)) }));
  function camAt(t) {
    let cur = cams.length ? cams[0].to.slice() : [540, 960, 1], since = 0;
    for (let i = 0; i < cams.length; i++) {
      const c = cams[i];
      if (t < c.t) break;
      const from = cur.slice();
      if (c.dur <= 0 || t >= c.t + c.dur) { cur = c.to.slice(); since = c.t + c.dur; continue; }
      const p = (t - c.t) / c.dur, e = c.move === 'travel' ? (p < .1 ? 5 * p * p : p < .9 ? .05 + (p - .1) * 1.125 : 1 - 5 * (1 - p) * (1 - p)) : ease(p);
      const z = Math.exp(Math.log(from[2]) + (Math.log(c.to[2]) - Math.log(from[2])) * e);
      return [from[0] + (c.to[0] - from[0]) * e, from[1] + (c.to[1] - from[1]) * e, z];
    }
    const hold = Math.max(0, t - since);                       // slow breathing push while holding a shot
    return [cur[0], cur[1], cur[2] * (1 + Math.min(.035, hold * .012))];
  }
  const camG = $('cam');
  function applyCam(t) {
    const [cx, cy, z] = camAt(t);
    camG.setAttribute('transform', `translate(${W / 2},${H * .47}) scale(${z.toFixed(5)}) translate(${(-cx).toFixed(2)},${(-cy).toFixed(2)})`);
    return z;
  }

  // ---------------------------------------------------------------- core (always running)
  const coreHalo = $('coreHalo'), coreRing = $('coreRing'), coreEye = $('coreEye');
  function core(t) {
    const act = last(['core.active', 'core.idle'], t), active = act && act.do === 'core.active';
    let flash = 0;
    for (const e of evs('core.pulse')) if (t >= e.t) flash = Math.max(flash, Math.exp(-(t - e.t) * 3.2));
    const breathe = .5 + .5 * Math.sin(t * 2 * Math.PI * .7);
    coreHalo.setAttribute('opacity', (.42 + .14 * breathe + (active ? .22 : 0) + .4 * flash).toFixed(3));
    coreEye.setAttribute('opacity', (.7 + .2 * breathe + .1 * flash).toFixed(3));
    coreRing.setAttribute('stroke-dashoffset', (-(t * (active ? 160 : 45))).toFixed(1));
    coreHalo.setAttribute('transform', `scale(${(1 + .25 * flash + (active ? .08 : 0)).toFixed(3)})`);
  }

  // ---------------------------------------------------------------- slot grid
  const gridLit = $('gridLit'), gridLitRect = $('gridLitRect'), GW = +gridLitRect.getAttribute('width');
  const queueG = $('queueSlots'), fx = $('worldFx');
  const SW = GW / A.grid_cols, SH = +gridLitRect.getAttribute('height') / A.grid_rows;
  const YOU = [47, 52];
  const youRect = mk('rect', { x: YOU[0] * SW, y: YOU[1] * SH, width: SW, height: SH, rx: 1.5, fill: LIME, opacity: 0 }, queueG);
  const youGlow = mk('rect', { x: YOU[0] * SW - SW, y: YOU[1] * SH - SH, width: SW * 3, height: SH * 3, rx: 3, fill: LIME, opacity: 0, filter: 'url(#soft)' }, queueG);
  // queue brands (episode data): lit slots in order, each with its name (empty in episode 1)
  (D.queue || []).forEach((name, i) => mk('rect', { x: (i % A.grid_cols) * SW, y: Math.floor(i / A.grid_cols) * SH, width: SW, height: SH, rx: 1.2, fill: LIME, class: 'qslot' }, queueG));
  const youLabel = mk('g', { opacity: 0 }, fx);
  mk('rect', { x: -34, y: -15, width: 68, height: 24, rx: 12, fill: '#000', stroke: LIME, 'stroke-width': 1.6 }, youLabel);
  const yl = mk('text', { y: 1.5, 'text-anchor': 'middle', 'dominant-baseline': 'middle', 'font-size': 14, 'font-weight': 900, fill: '#fff', direction: 'rtl' }, youLabel);
  yl.textContent = 'براندك';
  const ylLine = mk('line', { stroke: LIME, 'stroke-width': 1.2, opacity: 0 }, fx);
  function grid(t, z) {
    const g = last(['grid.lit', 'grid.dim'], t);
    let op = 0, w = 0;
    if (g && g.do === 'grid.lit') { const p = clamp((t - g.t) / (g.dur || 1.1), 0, 1); op = .92; w = GW * easeOut(p); }
    for (const e of evs('grid.scan')) if (t >= e.t && t < e.t + 1.6 && !(g && g.do === 'grid.lit')) {
      const p = (t - e.t) / 1.6; op = .38 * Math.sin(Math.PI * p); w = GW * Math.min(1, p * 1.6);
    }
    gridLit.setAttribute('opacity', op); gridLitRect.setAttribute('width', w.toFixed(1));
    const y = last(['you.on', 'you.off'], t);
    const on = y && y.do === 'you.on' ? clamp((t - y.t) / .35, 0, 1) : 0;
    const merge = (() => { let m = 0; for (const e of evs('bubble.fly')) if (t >= e.t + 1.0) m = Math.max(m, Math.exp(-(t - e.t - 1.0) * 2.5)); return m; })();
    youRect.setAttribute('opacity', (on * (.85 + .15 * Math.sin(t * 6))).toFixed(3));
    youGlow.setAttribute('opacity', (on * (.35 + .5 * merge)).toFixed(3));
    const [ux, uy] = A.you;
    const lift = 26;
    youLabel.setAttribute('opacity', on.toFixed(3));
    const k = 3.0 / z;                                         // ≈ the same size on screen at any zoom
    youLabel.setAttribute('transform', `translate(${ux},${uy - (lift + 14 * (1 - easeOut(on))) * k}) scale(${((.6 + .4 * back(Math.min(1, on))) * k).toFixed(3)})`);
    ylLine.setAttribute('x1', ux); ylLine.setAttribute('y1', uy - 5); ylLine.setAttribute('x2', ux); ylLine.setAttribute('y2', uy - (lift - 9) * k);
    ylLine.setAttribute('stroke-width', (1.2 * k).toFixed(2));
    ylLine.setAttribute('opacity', on.toFixed(3));
  }

  // ---------------------------------------------------------------- experiment module
  const modGlow = $('moduleGlow'), modFire = $('moduleFire'), pipe = $('pipeFlow'), flames = [...document.querySelectorAll('.flame')];
  function module(t) {
    const e = last(['module.ignite', 'module.off'], t);
    const p = e && e.do === 'module.ignite' ? clamp((t - e.t) / .5, 0, 1) : 0;
    const flick = p ? .85 + .15 * Math.sin(t * 31) * Math.sin(t * 17) : 0;
    const burst = e && e.do === 'module.ignite' ? Math.exp(-(t - e.t) * 2.2) : 0;
    modGlow.setAttribute('opacity', (p * (.55 + .25 * flick) + .4 * burst).toFixed(3));
    modFire.setAttribute('opacity', (p * flick).toFixed(3));
    pipe.setAttribute('opacity', (.25 + .7 * p).toFixed(3));
    pipe.setAttribute('stroke-dashoffset', (-(t * (p ? 220 : 30))).toFixed(1));
    let lp = 0; for (const e2 of evs('module.label')) if (t >= e2.t) lp = Math.max(lp, Math.exp(-(t - e2.t) * 1.6));
    const lab = $('moduleLabel'), base = lab.dataset.base || (lab.dataset.base = lab.getAttribute('transform'));
    lab.setAttribute('transform', `${base} scale(${(1 + .18 * lp).toFixed(3)})`);
    lab.querySelector('rect').setAttribute('stroke-opacity', (.5 + .5 * lp + .4 * p).toFixed(3));
    flames.forEach((f, k) => { f.setAttribute('transform', `translate(0,${(-6 * Math.sin(t * 9 + k)).toFixed(1)}) scale(1,${(.8 + .25 * Math.sin(t * 11 + k * 1.7)).toFixed(3)})`); f.style.transformOrigin = 'center bottom'; });
  }

  // ---------------------------------------------------------------- output tray: ad cards (placeholders, no brands)
  const cardsG = $('cards'), slotGlow = $('slotGlow');
  const launches = [];
  for (const e of evs('tray.emit')) for (let i = 0; i < (e.n || 1); i++) launches.push(e.t + i * (e.interval || .2));
  launches.sort((a, b) => a - b);
  const VARIANT = ['#D1FE17', '#ffffff', '#D1FE17', '#cfcfc6', '#D1FE17', '#ffffff', '#D1FE17', '#e9e9e2'];
  const cards = launches.map((t0, k) => {
    const g = mk('g', { opacity: 0 }, cardsG);
    mk('rect', { x: -44, y: -58, width: 88, height: 116, rx: 9, fill: '#fff', stroke: '#000', 'stroke-width': 2 }, g);
    mk('rect', { x: -36, y: -50, width: 72, height: 54, rx: 5, fill: VARIANT[k % VARIANT.length] === '#ffffff' ? '#1b1d14' : VARIANT[k % VARIANT.length] }, g);
    mk('path', { d: 'M-20,-10 l12,-18 l10,12 l8,-8 l12,14 z', fill: '#000', opacity: .55 }, g);
    mk('rect', { x: -36, y: 12, width: 58, height: 8, rx: 4, fill: '#222' }, g);
    mk('rect', { x: -36, y: 26, width: 42, height: 7, rx: 3.5, fill: '#999' }, g);
    mk('rect', { x: -36, y: 40, width: 30, height: 10, rx: 5, fill: LIME, stroke: '#000', 'stroke-width': 1.2 }, g);
    return { g, t0, k };
  });
  function tray(t) {
    let glow = 0;
    const [ex, ey] = A.emit, [tx, ty] = A.tray0;
    cards.forEach(c => {
      if (t < c.t0) { c.g.setAttribute('opacity', 0); return; }
      glow = Math.max(glow, Math.exp(-(t - c.t0) * 6));
      const p = clamp((t - c.t0) / .45, 0, 1), e = back(p);
      const col = c.k % 4, row = Math.floor(c.k / 4);
      const fx2 = tx + col * 62 - row * 18, fy = ty + 40 + row * 34 + col * 20;
      const x = ex + (fx2 - ex) * e, y = ey + (fy - ey) * easeOut(p) - 60 * Math.sin(Math.PI * p);
      c.g.setAttribute('opacity', Math.min(1, p * 4).toFixed(3));
      c.g.setAttribute('transform', `translate(${x.toFixed(1)},${y.toFixed(1)}) rotate(${(-8 + (c.k % 3) * 8).toFixed(1)}) scale(${(.55 + .45 * e).toFixed(3)})`);
    });
    slotGlow.setAttribute('opacity', glow.toFixed(3));
  }

  // ---------------------------------------------------------------- comment bubble flying into the "you" slot (world space)
  const flies = evs('bubble.fly').map(e => {
    const g = mk('g', { opacity: 0 }, fx);
    mk('rect', { x: -170, y: -40, width: 340, height: 80, rx: 24, fill: '#fff', stroke: '#000', 'stroke-width': 2.5 }, g);
    mk('circle', { cx: 132, cy: 0, r: 22, fill: '#111', stroke: LIME, 'stroke-width': 4 }, g);
    const tx = mk('text', { x: 98, y: 2, 'text-anchor': 'start', 'dominant-baseline': 'middle', 'font-size': 27, 'font-weight': 800, fill: '#111', direction: 'rtl' }, g);
    tx.textContent = e.text;
    return { g, e };
  });
  function bubbles(t, z) {
    const [ux, uy] = A.you;
    flies.forEach(({ g, e }) => {
      const p = clamp((t - e.t) / 1.0, 0, 1);
      if (t < e.t || p >= 1) { g.setAttribute('opacity', 0); return; }
      const k = 1.5 / z, sx = ux + 220 * k, sy = uy + 520 * k, q = ease(p);   // rises from below, like a new comment
      const x = sx + (ux - sx) * q, y = sy + (uy - sy) * q, s = k * (1 - .95 * Math.pow(p, 2.2));
      g.setAttribute('opacity', (p < .1 ? p * 10 : p > .85 ? (1 - p) / .15 : 1).toFixed(3));
      g.setAttribute('transform', `translate(${x.toFixed(1)},${y.toFixed(1)}) scale(${s.toFixed(3)})`);
    });
  }

  // ---------------------------------------------------------------- corridor of frameworks + drawer 135
  const drawers = [...document.querySelectorAll('.drawer')].map(g => ({ i: +g.dataset.i, body: g.querySelector('.dbody'), edge: g.querySelector('.dedge'), handle: g.querySelector('.dhandle') }));
  const nums = {}; document.querySelectorAll('.dnum').forEach(n => { nums[n.dataset.i] = n; });
  function corridor(t) {
    const dark = last(['corridor.dark', 'corridor.light', 'corridor.lit'], t);
    drawers.forEach(d => {
      let lit = .25;
      if (dark && dark.do === 'corridor.dark') lit = .1;
      if (dark && dark.do === 'corridor.lit') lit = 1;
      if (dark && dark.do === 'corridor.light') {
        const n = (dark.to || 134) - (dark.from || 1);
        const ti = dark.t + (dark.over || 3) * clamp((d.i - (dark.from || 1)) / Math.max(1, n), 0, 1);
        lit = t < ti ? .1 : .1 + .9 * clamp((t - ti) / .25, 0, 1);
      }
      d.edge.setAttribute('opacity', (lit).toFixed(3));
      d.handle.setAttribute('opacity', (lit).toFixed(3));
      d.body.setAttribute('fill', lit > .5 ? '#1a1f0c' : '#121410');
      nums[d.i].setAttribute('opacity', (.25 + .75 * clamp((lit - .1) / .9, 0, 1)).toFixed(3));
      nums[d.i].setAttribute('fill', lit > .5 ? '#ffffff' : LIME);
    });
    // drawer 135: sealed → pulsing (grows) → label / lines (later episodes)
    const pl = evs('d135.pulse').filter(e => e.t <= t);
    let level = 0;
    if (pl.length) { const e = pl[pl.length - 1], prev = pl.length > 1 ? pl[pl.length - 2].level : 0; level = prev + (e.level - prev) * clamp((t - e.t) / (e.grow || 1.6), 0, 1); }
    const beat = .55 + .45 * Math.pow(.5 + .5 * Math.sin(t * 2 * Math.PI * .85 - 1.2), 3);
    $('d135Glow').setAttribute('opacity', (level * beat * .85).toFixed(3));
    $('d135Edge').setAttribute('opacity', (level * (.35 + .65 * beat)).toFixed(3));
    const lab = last(['d135.label', 'd135.label_off'], t);
    $('d135Label').setAttribute('opacity', lab ? (lab.do === 'd135.label' ? clamp((t - lab.t) / .4, 0, 1) : 1 - clamp((t - lab.t) / .3, 0, 1)).toFixed(3) : 0);
    if (lab && lab.do === 'd135.label' && lab.text) $('d135LabelText').textContent = lab.text;
  }
  // persistent episode state for drawer 135 (lines written so far)
  const linesG = $('d135Lines');
  for (let i = 0; i < ((D.drawer135 || {}).lines || 0); i++) mk('rect', { x: 14, y: 16 + i * 14, width: 72 - (i % 3) * 14, height: 5, rx: 2.5, fill: AMBER, opacity: .8 }, linesG);

  // ---------------------------------------------------------------- lights (screen dim)
  const dimRect = $('dimRect');
  function lights(t) {
    const e = last(['lights.dim', 'lights.up', 'lights.drop'], t);
    let v = 0;
    if (e) {
      const prev = (() => { const ps = E.events.filter(x => x.t < e.t && ['lights.dim', 'lights.up', 'lights.drop'].includes(x.do)); const p = ps[ps.length - 1]; return p ? (p.do === 'lights.up' ? 0 : p.level ?? .82) : 0; })();
      const target = e.do === 'lights.up' ? 0 : (e.level ?? (e.do === 'lights.drop' ? .82 : .55));
      const dur = e.do === 'lights.drop' ? 0 : (e.dur || .6);
      v = dur ? prev + (target - prev) * ease(clamp((t - e.t) / dur, 0, 1)) : target;
    }
    dimRect.setAttribute('opacity', v.toFixed(3));
  }

  // ---------------------------------------------------------------- HUD (screen space, Western digits, log bar)
  const hud = $('hud');
  const HY = 268, BW = 760, BX = (W - BW) / 2;
  mk('rect', { x: BX - 40, y: HY - 78, width: BW + 80, height: 196, rx: 26, fill: '#000', 'fill-opacity': .72, stroke: LIME, 'stroke-opacity': .35, 'stroke-width': 2 }, hud);
  const ht = mk('text', { x: W / 2 + BW / 2, y: HY - 30, 'text-anchor': 'start', 'font-size': 34, 'font-weight': 800, fill: '#fff', direction: 'rtl' }, hud);
  ht.textContent = 'براندات في المحرّك';
  const hv = mk('text', { x: BX, y: HY - 22, 'text-anchor': 'start', 'font-size': 52, 'font-weight': 900, fill: LIME, direction: 'ltr' }, hud);
  mk('rect', { x: BX, y: HY + 12, width: BW, height: 18, rx: 9, fill: '#1c1e15' }, hud);
  const bar = mk('rect', { x: BX, y: HY + 12, width: 0, height: 18, rx: 9, fill: LIME }, hud);
  const CAP = D.capacity || 10000, LOGMAX = Math.log10(CAP);
  const pos = v => v <= 1 ? 0 : Math.log10(v) / LOGMAX;
  [[100, '100'], [1000, '1K'], [10000, '10K']].forEach(([v, s]) => {
    const x = BX + BW * pos(v);
    mk('line', { x1: x, y1: HY + 6, x2: x, y2: HY + 36, stroke: '#fff', 'stroke-opacity': .6, 'stroke-width': 3 }, hud);
    const tt = mk('text', { x: Math.min(x, BX + BW - 4), y: HY + 70, 'text-anchor': v === CAP ? 'end' : 'middle', 'font-size': 28, 'font-weight': 800, fill: '#fff', 'fill-opacity': .75, direction: 'ltr' }, hud);
    tt.textContent = s;
  });
  const hline = mk('text', { x: W / 2, y: HY + 168, 'text-anchor': 'middle', 'font-size': 40, 'font-weight': 900, fill: '#fff', opacity: 0, direction: 'rtl' }, hud);
  function hudAt(t) {
    let v = D.counter || 0;
    for (const e of E.events) {
      if (e.t > t) break;
      if (e.do === 'hud.to') {
        const from = v, p = e.instant ? 1 : clamp((t - e.t) / (e.dur || 1.0), 0, 1);
        const lf = Math.log10(from + 1), lt = Math.log10(e.value + 1);
        v = Math.pow(10, lf + (lt - lf) * easeOut(p)) - 1;
        if (p >= 1) v = e.value;
      }
    }
    hv.textContent = `${fmt(v)} / ${fmt(CAP)}`;
    let hp = 0; for (const e of evs('hud.pulse')) if (t >= e.t) hp = Math.max(hp, Math.exp(-(t - e.t) * 2.4));
    hv.setAttribute('fill', hp > .3 ? '#ffffff' : LIME);
    hv.setAttribute('transform', `translate(${BX},${HY - 22}) scale(${(1 + .14 * hp).toFixed(3)}) translate(${-BX},${-(HY - 22)})`);
    bar.setAttribute('width', (BW * pos(v)).toFixed(1));
    const hl = last(['hud.line', 'hud.line_off'], t);
    if (hl && hl.do === 'hud.line') { hline.textContent = hl.text; hline.setAttribute('opacity', clamp((t - hl.t) / .3, 0, 1)); }
    else hline.setAttribute('opacity', 0);
    const hh = last(['hud.hide', 'hud.show'], t);
    hud.setAttribute('opacity', hh && hh.do === 'hud.hide' ? (1 - clamp((t - hh.t) / .4, 0, 1)).toFixed(3) : 1);
  }

  // ---------------------------------------------------------------- mock comments (screen space)
  const sfxG = $('screenFx');
  const comments = [];
  for (const e of evs('comments.show')) (e.items || []).forEach((txt, k) => {
    const g = mk('g', { opacity: 0 }, sfxG);
    const w = 640, h = 104;
    mk('rect', { x: -w / 2, y: -h / 2, width: w, height: h, rx: 30, fill: '#fff', stroke: '#000', 'stroke-width': 3 }, g);
    mk('circle', { cx: w / 2 - 56, cy: 0, r: 30, fill: '#111', stroke: LIME, 'stroke-width': 5 }, g);
    const tx = mk('text', { x: w / 2 - 104, y: 3, 'text-anchor': 'start', 'dominant-baseline': 'middle', 'font-size': 44, 'font-weight': 800, fill: '#111', direction: 'rtl' }, g);
    tx.textContent = txt;
    if (k === 0 && e.highlight) { mk('rect', { x: -w / 2 - 6, y: -h / 2 - 6, width: w + 12, height: h + 12, rx: 34, fill: 'none', stroke: AMBER, 'stroke-width': 5 }, g); }
    comments.push({ g, t0: e.t + k * (e.interval || .45), y: (e.y || 700) + k * 132, out: e.out });
  });
  function commentsAt(t) {
    const off = last(['comments.hide'], t);
    comments.forEach(c => {
      const p = clamp((t - c.t0) / .35, 0, 1);
      let op = t < c.t0 ? 0 : Math.min(1, p * 2);
      if (off && off.t >= c.t0) op *= 1 - clamp((t - off.t) / .3, 0, 1);
      c.g.setAttribute('opacity', op.toFixed(3));
      c.g.setAttribute('transform', `translate(${W / 2 + 60 * (1 - easeOut(p))},${c.y}) scale(${(.85 + .15 * back(p)).toFixed(3)})`);
    });
  }

  // ---------------------------------------------------------------- end card
  const endG = $('endcard');
  const endE = evs('endcard.show')[0];
  if (endE) {
    mk('rect', { width: W, height: H, fill: '#000', opacity: .62, id: 'endBg' }, endG);
    const t1 = mk('text', { x: W / 2, y: 1060, 'text-anchor': 'middle', 'font-size': 84, 'font-weight': 900, fill: '#fff', direction: 'rtl' }, endG);
    (endE.lines || [endE.text]).forEach((ln, i) => {
      const ts = mk('tspan', { x: W / 2, dy: i ? 104 : 0 }, t1);
      ln.split(/(\*[^*]+\*)/).forEach(part => { if (!part) return; const s = mk('tspan', part.startsWith('*') ? { fill: LIME } : {}, ts); s.textContent = part.replace(/\*/g, ''); });
    });
    const hb = mk('g', { transform: `translate(${W / 2},1330)` }, endG);
    mk('rect', { x: -330, y: -52, width: 660, height: 104, rx: 52, fill: LIME }, hb);
    const htx = mk('text', { y: 4, 'text-anchor': 'middle', 'dominant-baseline': 'middle', 'font-size': 54, 'font-weight': 900, fill: '#000', direction: 'ltr' }, hb);
    htx.textContent = D.handle || '{{HANDLE}}';
  }
  function endAt(t) {
    if (!endE) return;
    const p = clamp((t - endE.t) / .5, 0, 1);
    endG.setAttribute('opacity', p.toFixed(3));
    endG.setAttribute('transform', `translate(0,${(30 * (1 - easeOut(p))).toFixed(1)})`);
  }

  // ---------------------------------------------------------------- captions: word by word, RTL, keys in lime
  const capG = $('caps');
  const CAP_Y = 1440, CAP_SIZE = 70, GAP = 20, MAXW = 940;
  const meas = mk('text', { 'font-size': CAP_SIZE, 'font-weight': 900, opacity: 0, direction: 'rtl' }, capG);
  const width = s => { meas.textContent = s; return meas.getComputedTextLength(); };
  const chunks = [];
  const layoutCaps = () => E.caps.forEach(line => {
    let cur = [], w = 0;
    const flush = () => { if (cur.length) chunks.push({ words: cur, whisper: line.whisper, line: line.line }); cur = []; w = 0; };
    line.words.forEach((wd, i) => {
      const ww = width(wd.text);
      if (cur.length && (w + GAP + ww > MAXW || cur.length >= 4)) flush();
      cur.push({ ...wd, w: ww }); w += (cur.length > 1 ? GAP : 0) + ww;
      if (/[.،,؟?…:!]$/.test(wd.text) && i < line.words.length - 1) flush();
    });
    flush();
  });
  const drawCaps = () => chunks.forEach((c, k) => {
    c.s = c.words[0].s; c.e = chunks[k + 1] && chunks[k + 1].line === c.line ? chunks[k + 1].words[0].s : c.words[c.words.length - 1].e + .35;
    const total = c.words.reduce((a, w) => a + w.w, 0) + GAP * (c.words.length - 1);
    let x = W / 2 + total / 2;                                   // right edge (RTL: first word on the right)
    c.g = mk('g', { opacity: 0 }, capG);
    c.words.forEach(w => {
      const cx = x - w.w / 2; x -= w.w + GAP;
      const g = mk('g', { transform: `translate(${cx.toFixed(1)},${CAP_Y})` }, c.g);
      const tx = mk('text', { 'text-anchor': 'middle', 'font-size': CAP_SIZE * (c.whisper ? .86 : 1), 'font-weight': 900, direction: 'rtl',
        fill: w.key ? LIME : '#fff', stroke: '#000', 'stroke-width': 12, 'paint-order': 'stroke', 'stroke-linejoin': 'round' }, g);
      tx.textContent = w.text.replace(/[.،,]$/, '');
      w.g = g; w.tx = tx;
    });
  });
  function capsAt(t) {
    const endT = endE ? endE.t : 1e9;
    chunks.forEach(c => {
      const vis = t >= c.s - .02 && t < c.e && t < endT + .1;
      c.g.setAttribute('opacity', vis ? (c.whisper ? .82 : 1) : 0);
      if (!vis) return;
      c.words.forEach(w => {
        const p = clamp((t - w.s + .03) / .14, 0, 1);
        w.g.setAttribute('opacity', p > 0 ? 1 : .0);
        w.tx.setAttribute('transform', `scale(${(.72 + .28 * back(p)).toFixed(3)})`);
      });
    });
  }

  // ---------------------------------------------------------------- frame
  window.setTime = t => {
    const z = applyCam(t); core(t); grid(t, z); module(t); tray(t); bubbles(t, z); corridor(t); lights(t); hudAt(t); commentsAt(t); endAt(t); capsAt(t);
  };
  window.ready = document.fonts.load('900 70px Cairo').then(() => document.fonts.ready).then(() => { layoutCaps(); drawCaps(); window.setTime(0); return true; });
  window.stateAt = t => ({ cam: camAt(t), dim: +dimRect.getAttribute('opacity'), hud: hv.textContent, hline: hline.textContent });
})();
