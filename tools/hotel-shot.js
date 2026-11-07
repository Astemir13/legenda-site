// Снимки блока «Об отеле»: node tools/hotel-shot.js → shots/hotel-d.png, shots/hotel-m.png
const {chromium} = require('playwright'); const {spawn} = require('child_process');
(async () => {
  const srv = spawn('node', ['tools/serve.js']); await new Promise(r => setTimeout(r, 800));
  const b = await chromium.launch(); const errs = [];
  for (const [w, tag] of [[1440, 'd'], [402, 'm']]) {
    const p = await b.newPage({viewport: {width: w, height: 900}, deviceScaleFactor: 2}); p.on('pageerror', e => errs.push(e.message));
    await p.goto('http://127.0.0.1:8765/', {waitUntil: 'networkidle'});
    await p.evaluate(() => document.querySelector('#hotel').scrollIntoView()); await p.waitForTimeout(800);
    await (await p.$('#hotel .panel')).screenshot({path: `shots/hotel-${tag}.png`});
  }
  console.log('errors:', errs); await b.close(); srv.kill();
})();
