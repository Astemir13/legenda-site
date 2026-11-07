const {chromium} = require('playwright'); const {spawn} = require('child_process');
(async () => {
  const srv = spawn('node', ['tools/serve.js']); await new Promise(r => setTimeout(r, 800));
  const b = await chromium.launch(); const errs = [];
  for (const [w, h, tag] of [[1440, 900, 'd'], [402, 874, 'm']]) {
    const p = await b.newPage({viewport: {width: w, height: h}, deviceScaleFactor: 2});
    p.on('pageerror', e => errs.push(e.message));
    await p.goto('http://127.0.0.1:8765/', {waitUntil: 'networkidle'});
    for (const v of [0, 1]) {
      await p.evaluate(() => document.querySelector('#r-std2 .pl').click());
      await p.waitForTimeout(400);
      if (v) { await p.evaluate(() => [...document.querySelectorAll('button')].find(x => x.textContent.trim() === 'Две кровати').click()); }
      await p.waitForTimeout(2500);
      await p.screenshot({path: `shots/plan-std2-${tag}${v}.png`});
      await p.keyboard.press('Escape'); await p.waitForTimeout(300);
    }
  }
  console.log('errors:', errs); await b.close(); srv.kill();
})();
