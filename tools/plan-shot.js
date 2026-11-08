// Снимки схемы номера: node tools/plan-shot.js [номер] [вариант,вариант] → shots/plan-<номер>-<d|m><i>.png
// По умолчанию — стандарт двухместный. Пример: node tools/plan-shot.js semi "Полулюкс" (у барнхауса один вариант — оба этажа: node tools/plan-shot.js barn "Оба этажа")
const {chromium} = require('playwright'); const {spawn} = require('child_process');
const id = process.argv[2] || 'std2', vars = (process.argv[3] || 'Большая кровать,Две кровати').split(',');
(async () => {
  const srv = spawn('node', ['tools/serve.js']); await new Promise(r => setTimeout(r, 800));
  const b = await chromium.launch(); const errs = [];
  for (const [w, h, tag] of [[1440, 900, 'd'], [402, 874, 'm']]) {
    const p = await b.newPage({viewport: {width: w, height: h}, deviceScaleFactor: 2});
    p.on('pageerror', e => errs.push(e.message));
    await p.goto('http://127.0.0.1:8765/', {waitUntil: 'networkidle'});
    for (let v = 0; v < vars.length; v++) {
      await p.evaluate(id => document.querySelector('#r-' + id + ' .pl').click(), id);
      await p.waitForTimeout(400);
      await p.evaluate(n => { const x = [...document.querySelectorAll('button')].find(x => x.textContent.trim() === n); if (x) x.click(); }, vars[v]);
      await p.waitForTimeout(2500);
      await p.screenshot({path: `shots/plan-${id}-${tag}${v}.png`});
      await p.keyboard.press('Escape'); await p.waitForTimeout(300);
    }
  }
  console.log('errors:', errs); await b.close(); srv.kill();
})();
