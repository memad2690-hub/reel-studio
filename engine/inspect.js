#!/usr/bin/env node
// Layout inspection for acceptance checks: load the built page, sample times, measure what is on screen.
// node engine/inspect.js --build projects/x/build --times 1.2,5,9 --out report.json
// Reports per time: visible graphic boxes, caption box, card + footage rectangles; plus Arabic shaping and RTL
// checks on every distinct visible text, the font status and any page errors.
const path = require('path');
const fs = require('fs');
const { pathToFileURL } = require('url');
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require(path.join(__dirname, '..', 'node_modules', 'playwright'))); }

const args = {};
for (let i = 2; i < process.argv.length; i++) {
  const k = process.argv[i];
  if (k.startsWith('--')) { const v = process.argv[i + 1]; if (!v || v.startsWith('--')) args[k.slice(2)] = true; else { args[k.slice(2)] = v; i++; } }
}
const build = path.resolve(args.build);
const meta = JSON.parse(fs.readFileSync(path.join(build, 'meta.json'), 'utf8'));
const times = String(args.times).split(',').map(Number);

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: meta.W, height: meta.H }, deviceScaleFactor: 1 });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  await page.goto(pathToFileURL(path.join(build, 'page.html')).href);
  await page.evaluate(() => window.ready);
  const hasCard = meta.mode === 'B' && fs.existsSync(path.join(build, 'cf'));
  const cfCount = hasCard ? fs.readdirSync(path.join(build, 'cf')).filter(f => f.endsWith('.png')).length : 0;

  const samples = [];
  const texts = new Map();
  for (const t of times) {
    const n = Math.min(cfCount, Math.floor(t * meta.fps + 1e-6) + 1);
    if (hasCard) await page.evaluate(async src => { const img = document.getElementById('cardimg');
      if (img.getAttribute('src') !== src) { img.src = src; await new Promise(r => { if (img.complete && img.naturalWidth) r(); else { img.onload = img.onerror = () => r(); } }); await img.decode().catch(() => {}); } }, 'cf/' + String(n).padStart(5, '0') + '.png');
    await page.evaluate(t => window.setTime(t), t);
    const s = await page.evaluate(() => {
      const R = el => { const r = el.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom].map(v => Math.round(v)); };
      const vis = el => { let e = el; while (e && e !== document.body) { const cs = getComputedStyle(e);
        if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity < 0.05) return false; e = e.parentElement; } return true; };
      const els = [];
      document.querySelectorAll('#fg .a, #behind .a').forEach(g => {
        if (!vis(g)) return;
        const r = R(g); if (r[2] - r[0] < 2 || r[3] - r[1] < 2) return;
        const tx = [...g.querySelectorAll('text')].filter(x => x.textContent.trim());
        const txt = tx.map(x => x.textContent.trim()).join(' ').slice(0, 80);
        let tb = null;                                           // the text's own box (decorative backdrops excluded)
        tx.forEach(x => { const q = R(x); tb = tb ? [Math.min(tb[0], q[0]), Math.min(tb[1], q[1]), Math.max(tb[2], q[2]), Math.max(tb[3], q[3])] : q; });
        // rendered font size in canvas px (font-size × the element's on-screen scale), smallest text in the element
        let fpx = null, fmax = null;
        tx.forEach(x => { const m = x.getScreenCTM(); const f = parseFloat(getComputedStyle(x).fontSize) * (m ? Math.hypot(m.a, m.b) : 1);
          if (x.getBoundingClientRect().width > 2) { fpx = fpx == null ? f : Math.min(fpx, f); fmax = fmax == null ? f : Math.max(fmax, f); } });
        els.push({ box: r, tbox: tb, behind: !!g.closest('#behind'), text: txt, k: g.dataset.k || '', id: g.id || '',
                   fpx: fpx == null ? null : Math.round(fpx), fmax: fmax == null ? null : Math.round(fmax),
                   tin: +g.dataset.in || 0, type: g.dataset.type || '' });
      });
      const cap = document.getElementById('cap');
      const capBox = cap && getComputedStyle(cap).display !== 'none' ? R(cap) : null;
      const card = document.getElementById('card'), img = document.getElementById('cardimg');
      const capPx = capBox ? Math.round(parseFloat(getComputedStyle(cap).fontSize)) : null;
      return { els, cap: capBox, capPx, capText: capBox ? cap.textContent : '', card: card ? R(card) : null,
               img: img && img.getAttribute('src') ? R(img) : null };
    });
    s.t = t; s.frame = n; samples.push(s);
    // collect visible text nodes for shaping / RTL checks (by content)
    const tn = await page.evaluate(() => {
      const out = [];
      document.querySelectorAll('#fg text, #behind text').forEach(t => {
        const g = t.closest('.a') || t; const cs = getComputedStyle(g);
        let e = t, ok = true; while (e && e !== document.body) { const c = getComputedStyle(e); if (c.display === 'none' || +c.opacity < 0.05) { ok = false; break; } e = e.parentElement; }
        if (ok && t.textContent.trim()) out.push(getComputedStyle(t).direction + '|' + t.textContent.trim());
      });
      return out;
    });
    tn.forEach(x => texts.set(x, (texts.get(x) || 0) + 1));
    if (s.capText) texts.set('rtl|CAP:' + s.capText, 1);
  }

  // Arabic shaping: a shaped word is narrower/wider than the same letters forced apart with ZWNJ (isolated forms).
  // RTL: in an Arabic-first line the first character must sit to the right of the last; digit runs must read LTR.
  const checks = await page.evaluate(list => {
    const AR = /[؀-ۿ]/, LAT = /[A-Za-z]/;
    const svg = document.getElementById('fg');
    const cv = document.createElement('canvas').getContext('2d');
    const res = { shaping: [], rtl: [], digits: [], font: document.fonts.check('800 60px Cairo') };
    for (const item of list) {
      const bar = item.indexOf('|'), dir = item.slice(0, bar), raw = item.slice(bar + 1);
      const isCap = raw.startsWith('CAP:'), s = isCap ? raw.slice(4) : raw;
      if (!AR.test(s)) continue;
      cv.font = '800 60px Cairo';
      // each Arabic word with a joining pair (ا د ذ ر ز و never join to the next letter) must change width when its
      // letters are forced apart with ZWNJ; a word that does not was drawn unshaped (isolated letters or a fallback font)
      const JOIN = /[\u0626\u0628\u062a-\u062e\u0633-\u063a\u0641-\u0647\u064a\u06cc][\u0621-\u064a\u06cc]/;
      const jw = s.split(/\s+/).map(w => w.replace(/[^\u0621-\u06ff]/g, '')).filter(w => JOIN.test(w));
      const ink = w => { const c = cv.canvas; c.width = 900; c.height = 140; cv.font = '800 60px Cairo'; cv.fillStyle = '#000';
        cv.clearRect(0, 0, 900, 140); cv.fillText(w, 20, 95); return cv.getImageData(0, 0, 900, 140).data; };
      const flat = jw.filter(w => { const a = ink(w), b = ink([...w].join('\u200C'));
        let diff = 0; for (let i = 3; i < a.length; i += 4) if (Math.abs(a[i] - b[i]) > 60) diff++;
        return diff < 30; });                                     // same pixels → letters were not joined
      if (jw.length && flat.length === jw.length) res.shaping.push(s);
      if (isCap || !svg) continue;
      const t = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      t.setAttribute('font-size', '60'); t.setAttribute('font-weight', '800'); t.setAttribute('x', '540'); t.setAttribute('y', '-500');
      t.setAttribute('text-anchor', 'middle'); t.textContent = s; svg.appendChild(t);
      try {
        // every line with Arabic is set right-to-left (as kits.text does), so its first character must sit to the
        // right of its last one, whether it starts with an Arabic or a Latin word ("design ممتاز")
        t.setAttribute('direction', dir || 'rtl');                   // the element's own computed direction
        if (s.length > 2 && /\S\s+\S/.test(s)) {
          const n = t.getNumberOfChars();
          const cx = i => { const e = t.getExtentOfChar(i); return e.x + e.width / 2; };
          const x0 = cx(0), x1 = cx(n - 1);
          if (!(x0 > x1)) res.rtl.push(s);
        }
        const m = s.match(/\d[\d,.]*\d/g) || [];
        for (const run of m) {
          const i = s.indexOf(run);
          if (i < 0) continue;
          const ex = k => { const e = t.getExtentOfChar(k); return e.x + e.width / 2; };
          const a = ex(i), b = ex(i + run.length - 1);
          if (!(b > a)) res.digits.push(run + ' in ' + s);
        }
      } catch (e) { /* glyph positions unavailable for this string */ }
      svg.removeChild(t);
    }
    return res;
  }, [...texts.keys()]);
  await browser.close();
  const out = { samples, checks, errors, texts: texts.size };
  if (args.out) fs.writeFileSync(args.out, JSON.stringify(out));
  else console.log(JSON.stringify(out));
})().catch(e => { console.error(e); process.exit(1); });
