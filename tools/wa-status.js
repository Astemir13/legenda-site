/* Картинка для статуса WhatsApp про новый сайт: tools/wa-status.html → shots/wa-status.png (1080×1920).
   Запуск из корня репозитория: node tools/wa-status.js (нужен Playwright с Chromium). */
const { chromium } = require('playwright');
const { pathToFileURL } = require('url');
const path = require('path');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  await p.goto(pathToFileURL(path.join(__dirname, 'wa-status.html')).href);
  await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(400);
  require('fs').mkdirSync(path.join(__dirname, '..', 'shots'), { recursive: true });
  const out = path.join(__dirname, '..', 'shots', 'wa-status.png');
  await p.locator('#S').screenshot({ path: out });
  await b.close();
  console.log('готово:', out, Math.round(require('fs').statSync(out).size / 1024) + ' КБ');
})();
