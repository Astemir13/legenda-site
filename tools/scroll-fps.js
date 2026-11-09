// Плавность прокрутки всей страницы: node tools/scroll-fps.js [m|d] [замедление процессора] [адрес]
// Прокручивает страницу сверху донизу колёсиком и меряет кадры; печатает FPS, долю рывков (>33 мс) и где они были (раздел).
const {chromium} = require('playwright');
const mob = process.argv[2] !== 'd', RATE = +(process.argv[3] || 4), URL = process.argv[4] || 'https://hotellegenda.ru/';
(async () => { const b = await chromium.launch({args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader']});
  const ctx = await b.newContext({viewport: mob ? {width: 402, height: 874} : {width: 1440, height: 900}, deviceScaleFactor: mob ? 3 : 1, isMobile: mob, hasTouch: mob});
  const p = await ctx.newPage(); const cdp = await ctx.newCDPSession(p);
  await p.route(/mc\.yandex/, r => r.abort());
  await p.goto(URL, {waitUntil: 'networkidle'}); await p.waitForTimeout(3000);
  await cdp.send('Emulation.setCPUThrottlingRate', {rate: RATE});
  await p.evaluate(() => { window.__f = []; let last = performance.now();
    const sec = () => { const y = innerHeight/2; const el = document.elementFromPoint(innerWidth/2, y); const s = el && el.closest('section[id],footer'); return s ? (s.id || 'footer') : '?'; };
    (function f(t){ window.__f.push([t - last, sec()]); last = t; requestAnimationFrame(f); })(performance.now()); });
  const H = await p.evaluate(() => document.documentElement.scrollHeight - innerHeight);
  for (let y = 0; y < H; y += 120) { await p.mouse.wheel(0, 120); await p.waitForTimeout(40); }
  await p.waitForTimeout(800);
  const r = await p.evaluate(() => { const f = window.__f.slice(2), d = f.map(x => x[0]); const long = f.filter(x => x[0] > 33);
    const by = {}; long.forEach(x => by[x[1]] = (by[x[1]] || 0) + 1);
    return {frames: d.length, fps: Math.round(1000*d.length/d.reduce((a, b) => a + b, 0)), long: long.length, pct: (100*long.length/d.length).toFixed(1), worst: Math.round(Math.max(...d)), where: by}; });
  console.log(mob ? 'телефон' : 'компьютер', 'x' + RATE, JSON.stringify(r)); await b.close(); })();
