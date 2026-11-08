#!/usr/bin/env node
// Render a built page to MP4 (or still frames) with Playwright + ffmpeg.
// node engine/render.js --build projects/x/build --out out.mp4 [--audio a.mp3] [--from 0 --to 10]
// node engine/render.js --build projects/x/build --stills dir --times 1.2,5,9.4
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const { pathToFileURL } = require('url');

let chromium;
try { ({ chromium } = require('playwright')); }
catch (e) {
  try { ({ chromium } = require(path.join(__dirname, '..', 'node_modules', 'playwright'))); }
  catch (e2) { console.error('Playwright not found. Run: npm install && npx playwright install chromium'); process.exit(2); }
}

const args = {};
for (let i = 2; i < process.argv.length; i++) {
  const k = process.argv[i];
  if (k.startsWith('--')) { const v = process.argv[i + 1]; if (!v || v.startsWith('--')) args[k.slice(2)] = true; else { args[k.slice(2)] = v; i++; } }
}
const build = path.resolve(args.build);
const meta = JSON.parse(fs.readFileSync(path.join(build, 'meta.json'), 'utf8'));
const fps = meta.fps;
const lossless = meta.mode === 'B' || !!args.lossless;

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: meta.W, height: meta.H }, deviceScaleFactor: meta.scale });
  page.on('pageerror', e => console.error('page error:', e.message));
  await page.goto(pathToFileURL(path.join(build, 'page.html')).href);  // works on Windows paths too
  await page.evaluate(() => window.ready);
  const hasCard = meta.mode === 'B' && fs.existsSync(path.join(build, 'cf'));
  const cfCount = hasCard ? fs.readdirSync(path.join(build, 'cf')).filter(f => f.endsWith('.png')).length : 0;
  const hasCut = hasCard && fs.existsSync(path.join(build, 'cut'));

  async function draw(t) {
    if (hasCard) {
      const n = Math.min(cfCount, Math.floor(t * fps + 1e-6) + 1);
      await page.evaluate(async src => {
        const img = document.getElementById('cardimg');
        if (img.getAttribute('src') !== src) { img.src = src; await img.decode().catch(() => {}); }
      }, 'cf/' + String(n).padStart(5, '0') + '.png');
      if (hasCut) {
        const kind = await page.evaluate(t => window.cutKind(t), t);
        const rel = kind + '/' + String(n).padStart(5, '0') + '.png';
        const src = fs.existsSync(path.join(build, rel)) ? rel : '';
        await page.evaluate(async src => {
          const img = document.getElementById('cutimg');
          if (!img) return;
          if (!src) { img.removeAttribute('src'); return; }
          if (img.getAttribute('src') !== src) { img.src = src; await img.decode().catch(() => {}); }
        }, src);
      }
    }
    await page.evaluate(t => window.setTime(t), t);
  }
  const shot = () => page.screenshot(lossless ? { type: 'png' } : { type: 'jpeg', quality: 95 });

  if (args.stills) {
    fs.mkdirSync(args.stills, { recursive: true });
    const times = String(args.times).split(',').map(Number);
    for (let i = 0; i < times.length; i++) {
      await draw(times[i]);
      await page.screenshot({ path: path.join(args.stills, `f${String(i + 1).padStart(2, '0')}.png`), type: 'png' });
    }
    await browser.close();
    console.log(JSON.stringify({ stills: times.length, dir: args.stills }));
    return;
  }

  const from = +(args.from || 0);
  const to = Math.min(+(args.to || meta.duration), meta.duration);
  const f0 = Math.round(from * fps), f1 = Math.round(to * fps);
  const ff = ['-y', '-hide_banner', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps),
    '-c:v', lossless ? 'png' : 'mjpeg', '-i', '-'];
  if (args.audio) ff.push('-ss', String(from), '-t', String(to - from), '-i', args.audio);
  ff.push('-map', '0:v');
  if (args.audio) ff.push('-map', '1:a', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000');
  ff.push('-c:v', 'libx264', '-preset', args.preset || 'slow', '-crf', String(args.crf || (meta.mode === 'A' ? 16 : 15)),
    '-profile:v', 'high', '-pix_fmt', 'yuv420p', '-r', String(fps), '-movflags', '+faststart', '-shortest', args.out);
  const proc = spawn('ffmpeg', ff, { stdio: ['pipe', 'inherit', 'inherit'] });
  const done = new Promise((res, rej) => proc.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));
  const t0 = Date.now();
  for (let f = f0; f < f1; f++) {
    await draw(f / fps);
    const buf = await shot();
    if (!proc.stdin.write(buf)) await new Promise(r => proc.stdin.once('drain', r));
    if ((f - f0) % (fps * 5) === 0) process.stderr.write(`\r${((f - f0) / fps).toFixed(0)}s / ${(to - from).toFixed(0)}s`);
  }
  proc.stdin.end();
  await done;
  await browser.close();
  console.error(`\nrendered ${f1 - f0} frames in ${((Date.now() - t0) / 1000).toFixed(0)}s`);
})().catch(e => { console.error(e); process.exit(1); });
