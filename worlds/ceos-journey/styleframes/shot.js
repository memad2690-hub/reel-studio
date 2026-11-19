const path = require('path');
const { chromium } = require(path.join(__dirname, '..', '..', '..', 'node_modules', 'playwright'));
(async () => { const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  for (const n of ['exterior', 'cabin', 'chamber']) { await p.goto('file://' + path.join(__dirname, `frame_${n}.html`)); await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(300);
    await p.screenshot({ path: path.join(__dirname, `frame_${n}.png`) }); }
  await b.close(); })();
