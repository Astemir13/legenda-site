// Плавность погод на обложке: node tools/wx-fps.js [m|d] [замедление процессора, по умолчанию 4]
// Для каждой погоды 4 с меряет кадры: средний FPS, доля «длинных» кадров (>33 мс, заметный рывок) и худший кадр.
const {chromium} = require('playwright'); const {spawn} = require('child_process');
const [w, h] = process.argv[2] === 'd' ? [1440, 900] : [402, 874], RATE = +(process.argv[3] || 4);
(async () => { const srv = spawn('node', ['tools/serve.js']); await new Promise(r => setTimeout(r, 800));
  const b = await chromium.launch({args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader']});
  const ctx = await b.newContext({viewport: {width: w, height: h}, deviceScaleFactor: w < 768 ? 3 : 1, isMobile: w < 768, hasTouch: w < 768});
  const p = await ctx.newPage(); const cdp = await ctx.newCDPSession(p);
  await p.route(/open-meteo|wx\.php|homereserve|mc\.yandex/, r => r.abort());
  await p.goto('http://127.0.0.1:8765/', {waitUntil: 'load'}); await p.waitForTimeout(1500);
  await cdp.send('Emulation.setCPUThrottlingRate', {rate: RATE});
  const kinds = await p.evaluate(() => [...document.querySelectorAll('#wxKinds [data-k]')].map(b => b.dataset.k));
  for (const k of kinds) {
    await p.evaluate(k => document.querySelector('#wxKinds [data-k="' + k + '"]').click(), k); await p.waitForTimeout(1500);
    const r = await p.evaluate(() => new Promise(res => { const t = []; let last = performance.now(); const end = last + 4000;
      (function f(now){ t.push(now - last); last = now; if (now < end) requestAnimationFrame(f); else { t.shift(); const avg = t.reduce((a, b) => a + b, 0) / t.length;
        res({fps: Math.round(1000 / avg), long: Math.round(100 * t.filter(x => x > 33).length / t.length), worst: Math.round(Math.max(...t))}); } })(last); }));
    console.log(k.padEnd(10), 'FPS', String(r.fps).padStart(3), ' рывков', String(r.long).padStart(3) + '%', ' худший кадр', r.worst, 'мс');
  }
  await b.close(); srv.kill(); })();
