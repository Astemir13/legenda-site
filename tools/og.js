/* Картинка для превью ссылки в мессенджерах и соцсетях: tools/og.html → src/static/img/og.jpg (1200×630).
   Запуск из корня репозитория: node tools/og.js (нужен Playwright с Chromium). */
const { chromium } = require('playwright');
const { pathToFileURL } = require('url');
const path = require('path');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1200, height: 630 } });
  await p.goto(pathToFileURL(path.join(__dirname, 'og.html')).href);
  await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(300);
  const out = path.join(__dirname, '..', 'src', 'static', 'img', 'og.jpg');
  await p.locator('#B').screenshot({ path: out, type: 'jpeg', quality: 84 });
  await b.close();
  console.log('готово:', out, Math.round(require('fs').statSync(out).size / 1024) + ' КБ');
})();
