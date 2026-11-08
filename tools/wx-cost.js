// Сколько времени скрипт анимации тратит на кадр в каждой погоде: node tools/wx-cost.js [m|d]
// Меряет все колбэки requestAnimationFrame страницы (среднее и 95-й перцентиль, мс). Бюджет кадра — 16,7 мс; на iPhone 16 Pro процессор в 3–4 раза быстрее, чем тут при замедлении 4.
const {chromium} = require('playwright'); const {spawn} = require('child_process');
const [w, h] = process.argv[2] === 'd' ? [1440, 900] : [402, 874];
(async () => { const srv = spawn('node', ['tools/serve.js']); await new Promise(r => setTimeout(r, 800));
  const b = await chromium.launch();
  const ctx = await b.newContext({viewport: {width: w, height: h}, deviceScaleFactor: w < 768 ? 3 : 1, isMobile: w < 768, hasTouch: w < 768});
  await ctx.addInitScript(() => { const raf = window.requestAnimationFrame.bind(window); window.__cost = [];
    window.requestAnimationFrame = cb => raf(t => { const s = performance.now(); cb(t); window.__cost.push(performance.now() - s); }); });
  const p = await ctx.newPage();
  await p.route(/open-meteo|wx\.php|homereserve|mc\.yandex/, r => r.abort());
  await p.goto('http://127.0.0.1:8765/', {waitUntil: 'load'}); await p.waitForTimeout(1500);
  const kinds = await p.evaluate(() => [...document.querySelectorAll('#wxKinds [data-k]')].map(b => b.dataset.k));
  for (const k of kinds) {
    await p.evaluate(k => document.querySelector('#wxKinds [data-k="' + k + '"]').click(), k); await p.waitForTimeout(2500);
    await p.evaluate(() => { window.__cost = []; }); await p.waitForTimeout(4000);
    const r = await p.evaluate(() => { const c = window.__cost.slice().sort((a, b) => a - b), n = c.length; return {n, avg: (c.reduce((a, b) => a + b, 0) / n).toFixed(2), p95: c[Math.floor(n * .95)].toFixed(2), max: c[n - 1].toFixed(1)}; });
    console.log(k.padEnd(10), 'кадров', String(r.n).padStart(4), ' среднее', r.avg.padStart(6), 'мс  95%', r.p95.padStart(6), 'мс  макс', r.max, 'мс');
  }
  await b.close(); srv.kill(); })();
