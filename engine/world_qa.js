// QA for a Story World episode page: shaping/RTL of every caption word, HUD values at given times, and a visible
// state change for each line (frame difference outside the caption band, before vs after the line's key event).
// node engine/world_qa.js <build dir> '<json: {"hud": [[t, "100 / 10,000"], ...]}>'
const path = require('path');
const { pathToFileURL } = require('url');
const { chromium } = require(path.join(__dirname, '..', 'node_modules', 'playwright'));
const PNG = (() => { try { return require(path.join(__dirname, '..', 'node_modules', 'pngjs')).PNG; } catch (e) { return null; } })();

(async () => {
  const build = path.resolve(process.argv[2]);
  const want = JSON.parse(process.argv[3] || '{}');
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  await p.goto(pathToFileURL(path.join(build, 'page.html')).href); await p.evaluate(() => window.ready);
  const res = { shaping: [], rtl: [], hud: [], change: [] };

  // 1. shaping + RTL order of every caption chunk
  const caps = await p.evaluate(() => {
    const out = [];
    const probe = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    probe.setAttribute('font-size', 70); probe.setAttribute('font-weight', 900); probe.setAttribute('direction', 'rtl');
    document.getElementById('caps').appendChild(probe);
    const w = s => { probe.textContent = s; return probe.getComputedTextLength(); };
    document.querySelectorAll('#caps > g').forEach(chunk => {
      const words = [...chunk.querySelectorAll('g > text')].map(t => ({ text: t.textContent, x: +t.parentNode.getAttribute('transform').match(/translate\(([-\d.]+)/)[1] }));
      if (!words.length) return;
      // only words with a pair that must join: a dual-joining letter followed by another Arabic letter (marks skipped)
      const NONJOIN = 'اأإآدذرزوؤةىء';
      words.forEach(o => {
        const L = [...o.text].filter(c => /[ء-ي]/.test(c));
        o.arabic = L.some((c, i) => i < L.length - 1 && !NONJOIN.includes(c));
        o.joined = w(o.text);
        o.isolated = w([...o.text].join('‌'));           // zero-width non-joiner between every character: no joining
      });
      out.push(words);
    });
    probe.remove();
    return out;
  });
  // width ties: compare pixels of the word vs the same word with joining broken (ZWNJ between letters)
  const ties = [...new Set(caps.flat().filter(o => o.arabic && Math.abs(o.joined - o.isolated) <= 1).map(o => o.text))];
  const pix = {};
  for (const word of ties) {
    const img = async s => { await p.evaluate(s => { let el = document.getElementById('qaProbe');
      if (!el) { el = document.createElementNS('http://www.w3.org/2000/svg', 'text'); el.id = 'qaProbe'; document.getElementById('stage').appendChild(el); }
      el.setAttribute('x', 540); el.setAttribute('y', 960); el.setAttribute('text-anchor', 'middle'); el.setAttribute('font-size', 140);
      el.setAttribute('font-weight', 900); el.setAttribute('fill', '#fff'); el.setAttribute('direction', 'rtl'); el.textContent = s; }, s);
      return p.screenshot({ type: 'png', clip: { x: 140, y: 800, width: 800, height: 240 } }); };
    const A = PNG.sync.read(await img(word)), B = PNG.sync.read(await img([...word].join('\u200C')));
    let d = 0; for (let i = 0; i < A.data.length; i += 4) if (Math.abs(A.data[i] - B.data[i]) > 80) d++;
    pix[word] = d;
  }
  await p.evaluate(() => { const el = document.getElementById('qaProbe'); if (el) el.remove(); });
  caps.forEach(words => {
    words.forEach(o => { if (o.arabic) res.shaping.push({ word: o.text, ok: Math.abs(o.joined - o.isolated) > 1 || (pix[o.text] || 0) > 200, pixels: pix[o.text], joined: Math.round(o.joined), isolated: Math.round(o.isolated) }); });
    const xs = words.map(o => o.x);
    res.rtl.push({ chunk: words.map(o => o.text).join(' '), ok: xs.every((x, i) => i === 0 || x < xs[i - 1]) });
  });

  // 2. HUD values
  for (const [t, expect] of (want.hud || [])) {
    const s = await p.evaluate(t => { window.setTime(t); return window.stateAt(t).hud; }, t);
    res.hud.push({ t, expect, got: s, ok: s === expect });
  }

  // 3. a visible change on each line's key moment (caption band y 1360–1520 masked)
  const shot = async t => { await p.evaluate(t => window.setTime(t), t); return p.screenshot({ type: 'png', clip: { x: 0, y: 0, width: 1080, height: 1920 } }); };
  const diff = (a, bb) => {
    const A = PNG.sync.read(a), B = PNG.sync.read(bb); let n = 0, tot = 0;
    for (let y = 0; y < 1920; y += 4) { if (y > 1340 && y < 1530) continue; for (let x = 0; x < 1080; x += 4) {
      const i = (y * 1080 + x) * 4; const d = Math.abs(A.data[i] - B.data[i]) + Math.abs(A.data[i + 1] - B.data[i + 1]) + Math.abs(A.data[i + 2] - B.data[i + 2]);
      tot++; if (d > 60) n++; } }
    return n / tot;
  };
  for (const k of (want.keys || [])) {
    const a = await shot(k.t - 0.12), c = await shot(k.t + (k.after || 0.7));
    const d = PNG ? diff(a, c) : null;
    res.change.push({ line: k.line, what: k.what, t: k.t, changed: d === null ? null : +(d * 100).toFixed(2), ok: d === null ? null : d > 0.004 });
  }
  await b.close();
  const sum = { shaping_ok: res.shaping.every(x => x.ok), shaping_words: res.shaping.length, rtl_ok: res.rtl.every(x => x.ok), rtl_chunks: res.rtl.length,
    hud_ok: res.hud.every(x => x.ok), change_ok: res.change.every(x => x.ok !== false) };
  console.log(JSON.stringify({ summary: sum, fails: { shaping: res.shaping.filter(x => !x.ok), rtl: res.rtl.filter(x => !x.ok), hud: res.hud.filter(x => !x.ok) }, change: res.change }, null, 1));
})();
