// Проверка сайта: node tools/site-check.js — собранный site/ локально; или с адресом: node tools/site-check.js https://preview.hotellegenda.ru
// Ошибки скриптов, битые картинки и запросы, обращения к Тильде и шрифтам Google, незагруженные шрифты, просмотр фото, политика, горизонтальная прокрутка, снимки.
const pw = require('playwright'), path = require('path'), fs = require('fs'), serve = require('./serve');
(async () => {
  const srv = process.argv[2] ? null : await serve(), BASE = process.argv[2] || srv.url;
  const b = await pw.chromium.launch(); fs.mkdirSync('shots', { recursive: true }); let bad = 0;
  for (const [w, h, t] of [[1440, 900, 'd'], [390, 844, 'm'], [320, 640, 's']]) {
    const p = await b.newPage({ viewport: { width: w, height: h }, hasTouch: w < 700 });
    const errs = [], fails = [], tilda = [];
    p.on('pageerror', e => errs.push(e.message));
    // чужие запросы (Метрика, модуль бронирования, погода) не считаем — у них свои ошибки, и на Тильде тоже
    const ext = /yandex\.(ru|net)|homereserve|realtycalendar|open-meteo/;
    p.on('requestfailed', r => { if (!ext.test(r.url())) fails.push(r.url()); });
    p.on('response', r => { if (r.status() >= 400 && !ext.test(r.url())) fails.push(r.status() + ' ' + r.url()); });
    // шрифт Inter с Google подгружает сам модуль HomeReserve — это не наш запрос
    p.on('request', r => { if (/tildacdn|tilda\.ws|fonts\.googleapis|fonts\.gstatic/.test(r.url()) && !/family=Inter|\/s\/inter\//.test(r.url())) tilda.push(r.url()); });
    await p.goto(BASE + '/', { waitUntil: 'networkidle' }).catch(() => {});
    for (let y = 0; y < 9000; y += 700) { await p.evaluate(y => scrollTo(0, y), y); await p.waitForTimeout(150); }
    await p.evaluate(() => scrollTo(0, 0)); await p.waitForTimeout(1500);
    const info = await p.evaluate(() => ({
      title: document.title, h1: document.querySelector('h1').textContent, lang: document.documentElement.lang,
      hscroll: document.documentElement.scrollWidth > innerWidth, ld: !!document.querySelector('script[type="application/ld+json"]'),
      brokenImg: [...document.images].filter(i => i.complete && i.naturalWidth === 0 && i.getAttribute('src')).map(i => i.getAttribute('src')),
      // панель «Погода» видна только на preview.* и локально, на рабочем домене спрятана
      panelOk: (p => !!p && p.hidden === !/^(preview\.|localhost$|127\.)/.test(location.hostname))(document.getElementById('wxPanel')), ym: typeof window.ym,
      fonts: ['Lora', 'Golos Text', 'Geologica'].filter(f => !document.fonts.check('600 20px "' + f + '"', 'Тест')) }));
    await p.screenshot({ path: `shots/site_${t}.png` });
    // просмотр фото номера: открыть, перейти на миниатюру, проверить, что фото загрузилось
    const im = p.locator('img[data-i]').first(); await im.scrollIntoViewIfNeeded(); await im.click(); await p.waitForTimeout(1500);
    const th = p.locator('#galTh button'); if (await th.count() > 2) { await th.nth(2).click(); await p.waitForTimeout(1200); }
    const gal = await p.evaluate(() => { const i = document.querySelectorAll('#galS img')[2] || document.querySelector('#galS img'); return { n: document.getElementById('galN').textContent, ok: !!i && i.complete && i.naturalWidth > 0 }; });
    if (t === 'm') await p.screenshot({ path: 'shots/site_gal.png' });
    console.log(t, JSON.stringify({ ...info, gal, errs, fails: fails.slice(0, 5), tilda: tilda.slice(0, 3) }));
    if (errs.length || fails.length || tilda.length || info.hscroll || info.brokenImg.length || !info.panelOk || !gal.ok || info.fonts.length) bad++;
    await p.close();
  }
  const p = await b.newPage({ viewport: { width: 390, height: 844 } });
  const r = await p.goto(BASE + '/privacypolicy/'); await p.screenshot({ path: 'shots/site_privacy.png' });
  const pv = await p.evaluate(() => ({ h1: document.querySelector('h1').textContent, h2: document.querySelectorAll('h2').length, p: document.querySelectorAll('p').length, hscroll: document.documentElement.scrollWidth > innerWidth }));
  console.log('privacy', r.status(), JSON.stringify(pv)); if (r.status() !== 200 || pv.hscroll) bad++;
  for (const f of ['/robots.txt', '/sitemap.xml', '/404.html', '/img/og.jpg', '/favicon.svg', '/fonts/lora-cyrillic.woff2']) { const x = await p.request.get(BASE + f); console.log(f, x.status(), x.headers()['content-type']); if (x.status() !== 200) bad++; }
  await b.close(); if (srv) srv.close(); console.log(bad ? 'ПРОБЛЕМЫ: ' + bad : 'ВСЁ ХОРОШО'); process.exit(bad ? 1 : 0);
})();
