// Полная проверка интерфейса: проходит по всем кнопкам и окнам на трёх ширинах, собирает ошибки.
// BROWSER=webkit node tools/full-check.js — то же в движке Safari (как на iPhone).
// node tools/full-check.js [адрес]  — без адреса поднимает site/ локально (tools/serve.js).
// Что проверяет: ошибки скрипта и консоли, битые картинки, горизонтальную прокрутку,
// шапку и меню, ссылки разделов, карточки номеров (фото, листание, план), просмотр фото, окно схемы со всеми вариантами,
// альбом «Об отеле», меню ресторана, прогноз погоды, панель погод, «Сайт на телефоне», вопросы, ссылки бронирования.
const {chromium} = require('playwright'); const {spawn} = require('child_process');
const URL = process.argv[2] || 'http://127.0.0.1:8765/';
(async () => {
  const srv = process.argv[2] ? null : spawn('node', ['tools/serve.js']); if (srv) await new Promise(r => setTimeout(r, 800));
  const b = await (process.env.BROWSER === 'webkit' ? require('playwright').webkit : chromium).launch(); const bad = []; let bookOk = false;
  for (const [w, h, tag] of [[1440, 900, 'd'], [402, 874, 'm'], [320, 640, 's']]) {
    const p = await b.newPage({viewport: {width: w, height: h}, deviceScaleFactor: 1, hasTouch: w < 768, isMobile: w < 768});
    const errs = [];
    p.on('pageerror', e => errs.push('pageerror: ' + e.message));
    p.on('console', m => { if (m.type() === 'error' && !/Failed to load resource/.test(m.text())) errs.push('console: ' + m.text() + ' @ ' + (m.location() || {}).url); });  // сбои загрузки — через requestfailed/response, со сторонними сервисами
    p.on('requestfailed', r => { const u = r.url(); if (!/homereserve|realtycalendar|yandex|open-meteo|wx\.php/.test(u)) errs.push('failed: ' + u + ' ' + (r.failure() || {}).errorText); });
    p.on('response', r => { if (r.status() >= 400 && !/homereserve|realtycalendar|yandex|open-meteo|favicon/.test(r.url())) errs.push('http ' + r.status() + ': ' + r.url()); });
    const log = (ok, what) => { if (!ok) bad.push(tag + ': ' + what); };
    const hs = async (what) => log(await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'горизонтальная прокрутка — ' + what);
    await p.goto(URL, {waitUntil: 'networkidle'}); await p.waitForTimeout(1500);
    await hs('после загрузки');
    // вся страница: прокрутить до конца, чтобы подгрузились картинки
    const H = await p.evaluate(() => document.body.scrollHeight);
    for (let y = 0; y < H; y += h * 0.8) { await p.evaluate(y => scrollTo(0, y), y); await p.waitForTimeout(120); }
    await p.waitForTimeout(1200);
    const broken = await p.evaluate(() => [...document.images].filter(i => i.complete && i.naturalWidth === 0 && i.getAttribute('src')).map(i => i.getAttribute('src')));
    log(!broken.length, 'битые картинки ' + broken.join(', '));
    // шапка: после прокрутки — капсула
    await p.evaluate(() => scrollTo(0, 700)); await p.waitForTimeout(500);
    log(await p.evaluate(() => document.getElementById('hdr').classList.contains('solid')), 'шапка не стала капсулой');
    // меню логотипа
    await p.click('#logoBtn'); await p.waitForTimeout(400);
    log(await p.evaluate(() => document.getElementById('logoBtn').getAttribute('aria-expanded') === 'true'), 'меню не открылось');
    const menuLinks = await p.evaluate(() => [...document.querySelectorAll('#siteMenu a[href^="#"]')].map(a => a.getAttribute('href')));
    log(menuLinks.length > 0, 'в меню нет ссылок');
    await p.keyboard.press('Escape'); await p.waitForTimeout(400);
    log(await p.evaluate(() => document.getElementById('logoBtn').getAttribute('aria-expanded') !== 'true'), 'меню не закрылось по Escape');
    // ссылки разделов из меню: целевой раздел существует и прокручивается к нему
    for (const href of [...new Set(menuLinks)]) {
      const ex = await p.evaluate(h => !!document.querySelector(h), href); log(ex, 'ссылка меню ведёт в никуда: ' + href);
      if (!ex) continue;
      await p.click('#logoBtn'); await p.waitForTimeout(350);
      await p.evaluate(h => document.querySelector('#siteMenu a[href="' + h + '"]').click(), href); await p.waitForTimeout(1300);
      // «Ресторан» в меню открывает меню ресторана (data-food) — так задумано
      if (await p.evaluate(() => document.getElementById('fm').classList.contains('on'))) { await p.click('#fmX'); await p.waitForTimeout(400); continue; }
      const top = await p.evaluate(h => document.querySelector(h).getBoundingClientRect().top, href);
      log(Math.abs(top) < 160, 'после перехода по ' + href + ' раздел не наверху (' + Math.round(top) + ')');
      log(await p.evaluate(() => document.getElementById('logoBtn').getAttribute('aria-expanded') !== 'true'), 'меню не закрылось после перехода ' + href);
    }
    // все якорные ссылки страницы ведут на существующие разделы
    const deadA = await p.evaluate(() => [...document.querySelectorAll('a[href^="#"]')].map(a => a.getAttribute('href')).filter(h => h.length > 1 && !document.querySelector(h)));
    log(!deadA.length, 'якоря без раздела: ' + deadA.join(', '));
    // кнопки обложки
    await p.evaluate(() => scrollTo(0, 0)); await p.waitForTimeout(400);
    const heroBtn = await p.evaluate(() => { const a = [...document.querySelectorAll('#hero a, #top a')].find(x => /Выбрать номер/.test(x.textContent)); return a ? a.getAttribute('href') : null; });
    log(heroBtn === '#rooms', 'кнопка «Выбрать номер» на обложке: ' + heroBtn);
    // прогноз
    const hasDaily = await p.evaluate(() => !document.documentElement.classList.contains('nowx'));
    if (hasDaily) {
      await p.click('#hpWx'); await p.waitForTimeout(500);
      log(await p.evaluate(() => document.getElementById('hpWx').getAttribute('aria-expanded') === 'true'), 'прогноз не открылся');
      log(await p.evaluate(() => document.querySelectorAll('#hpFc .fd').length >= 3), 'в прогнозе меньше 3 дней');
      await hs('прогноз открыт');
      await p.click('#hpWx'); await p.waitForTimeout(400);
    } else bad.push(tag + ': погода не загрузилась (nowx)');
    // карточки номеров
    const ids = await p.evaluate(() => [...document.querySelectorAll('#roomGrid [id^="r-"]')].map(e => e.id.slice(2)));
    log(ids.length === 6, 'номеров на странице ' + ids.length);
    for (const id of ids) {
      const c = '#r-' + id;
      await p.evaluate(c => document.querySelector(c).scrollIntoView({block: 'center'}), c); await p.waitForTimeout(250);
      const n0 = await p.evaluate(c => { const n = document.querySelector(c + ' .mph-n'); return n ? n.textContent : ''; }, c);
      if (n0) { await p.evaluate(c => document.querySelector(c + ' .mph-a.n').click(), c); await p.waitForTimeout(1300);
        const n1 = await p.evaluate(c => document.querySelector(c + ' .mph-n').textContent, c); log(n1 !== n0, id + ': стрелка фото в карточке не листает (' + n0 + ')'); }
      // переключатель План/Фото
      await p.evaluate(c => document.querySelector(c + ' .mtog [data-v="plan"]').click(), c); await p.waitForTimeout(300);
      log(await p.evaluate(c => document.querySelector(c + ' .ph').dataset.view === 'plan', c), id + ': не переключается на план');
      log(await p.evaluate(c => document.querySelector(c + ' .pl svg').childElementCount > 3, c), id + ': мини-схема пустая');
      await p.evaluate(c => document.querySelector(c + ' .mtog [data-v="photo"]').click(), c); await p.waitForTimeout(300);
      log(await p.evaluate(c => document.querySelector(c + ' .ph').dataset.view === 'photo', c), id + ': не переключается на фото');
      // просмотр фото
      await p.evaluate(c => document.querySelector(c + ' .mph-s img').click(), c); await p.waitForTimeout(700);
      const g = await p.evaluate(() => ({open: !document.getElementById('gal').hidden, n: document.getElementById('galN').textContent, t: document.getElementById('galT').textContent}));
      log(g.open, id + ': просмотр фото не открылся');
      if (g.open) {
        const tot = +g.n.split('/')[1];
        await p.evaluate(() => document.querySelector('#gal .gal-a.n').click()); await p.waitForTimeout(600);
        const n2 = await p.evaluate(() => document.getElementById('galN').textContent); log(tot < 2 || n2 !== g.n, id + ': в просмотре стрелка не листает');
        if (tot > 2) { await p.evaluate(() => document.querySelector('#galTh button:last-child').click()); await p.waitForTimeout(600);
          log(await p.evaluate(() => document.getElementById('galN').textContent.startsWith(document.getElementById('galN').textContent.split('/')[1].trim() + ' ')), id + ': миниатюра не переключает'); }
        const gb = await p.evaluate(() => [...document.querySelectorAll('#galS img')].filter(i => i.complete && i.naturalWidth === 0).length); log(!gb, id + ': битые фото в просмотре');
        await hs(id + ' просмотр фото');
        await p.keyboard.press('Escape'); await p.waitForTimeout(400);
        log(await p.evaluate(() => document.getElementById('gal').hidden && document.documentElement.style.overflow === ''), id + ': просмотр не закрылся');
      }
      // окно схемы со всеми вариантами
      await p.evaluate(c => { document.querySelector(c + ' .mtog [data-v="plan"]').click(); }, c); await p.waitForTimeout(200);
      await p.evaluate(c => document.querySelector(c + ' .pl').click(), c); await p.waitForTimeout(600);
      log(await p.evaluate(() => document.getElementById('pm').classList.contains('on')), id + ': окно схемы не открылось');
      const vars = await p.evaluate(() => [...document.querySelectorAll('#pmVars button')].map(b => b.textContent));
      for (let i = 0; i < Math.max(1, vars.length); i++) {
        if (vars.length) { await p.evaluate(i => document.querySelectorAll('#pmVars button')[i].click(), i); await p.waitForTimeout(400); }
        const sv = await p.evaluate(() => { const s = document.querySelector('#pmBox svg'), r = s.getBoundingClientRect(), bb = s.getBBox(), vb = s.viewBox.baseVal; return {n: s.childElementCount, w: r.width, ok: bb.x >= -1 && bb.y >= -1 && bb.x + bb.width <= vb.width + 1 && bb.y + bb.height <= vb.height + 1}; });
        log(sv.n > 3 && sv.w > 100, id + ': схема «' + (vars[i] || '') + '» пустая');
        log(sv.ok, id + ': схема «' + (vars[i] || '') + '» вылезает за рамку');
      }
      await hs(id + ' окно схемы');
      if (id === ids[0]) { // «Забронировать» в окне схемы: окно закрывается, открывается бронирование
        await p.evaluate(() => document.getElementById('pmPick').click()); await p.waitForTimeout(900);
        log(await p.evaluate(() => !document.getElementById('pm').classList.contains('on')), 'кнопка «Забронировать» в окне схемы не закрыла окно');
        const hsh = await p.evaluate(() => location.hash); log(/^#\/detail\/\d+/.test(hsh) || hsh === '', 'бронирование из схемы: адрес ' + hsh);
        bookOk = /^#\/detail\//.test(hsh);
        await p.evaluate(() => { location.hash = '#/'; }); await p.waitForTimeout(800);
        await p.evaluate(c => document.querySelector(c).scrollIntoView({block: 'center'}), c);
        await p.evaluate(c => document.querySelector(c + ' .pl').click(), c); await p.waitForTimeout(500); }
      await p.click('#pmX'); await p.waitForTimeout(400);
      log(await p.evaluate(() => !document.getElementById('pm').classList.contains('on')), id + ': окно схемы не закрылось');
      await p.evaluate(c => document.querySelector(c + ' .mtog [data-v="photo"]').click(), c);
      const bk = await p.evaluate(c => { const a = document.querySelector(c + ' [data-book]'); return a && a.href; }, c); log(/homereserve\.ru/.test(bk || ''), id + ': ссылка «Свободные даты» ' + bk);
    }
    // альбом
    const alb = await p.evaluate(() => document.querySelectorAll('#alb button').length); log(alb === 5, 'плиток в альбоме ' + alb);
    for (let i = 0; i < alb; i++) {
      await p.evaluate(i => document.querySelectorAll('#alb button')[i].click(), i); await p.waitForTimeout(500);
      const g = await p.evaluate(() => ({open: !document.getElementById('gal').hidden, t: document.getElementById('galT').textContent}));
      log(g.open && g.t.length > 3, 'альбом: плитка ' + i + ' не открыла просмотр с подписью');
      await p.keyboard.press('Escape'); await p.waitForTimeout(300);
    }
    // меню ресторана
    for (const k of ['menu', 'set']) {
      await p.evaluate(k => document.querySelector('[data-food="' + k + '"]').click(), k); await p.waitForTimeout(500);
      log(await p.evaluate(() => document.getElementById('fm').classList.contains('on')), 'меню ресторана (' + k + ') не открылось');
      for (const t of ['set', 'menu']) { await p.evaluate(t => document.querySelector('#fmTabs [data-t="' + t + '"]').click(), t); await p.waitForTimeout(250);
        log(await p.evaluate(t => !document.getElementById(t === 'set' ? 'fmSet' : 'fmMenu').hidden, t), 'вкладка ' + t + ' не показалась'); }
      await hs('меню ресторана');
      await p.click('#fmX'); await p.waitForTimeout(400);
      log(await p.evaluate(() => !document.getElementById('fm').classList.contains('on')), 'меню ресторана не закрылось');
    }
    // вопросы
    const det = await p.evaluate(() => document.querySelectorAll('#faq details').length);
    if (det) { await p.evaluate(() => document.querySelector('#faq details summary').click()); await p.waitForTimeout(200);
      log(await p.evaluate(() => document.querySelector('#faq details').open), 'вопрос не раскрывается'); }
    // текст-заглушки в квадратных скобках не должны попасть на сайт
    const br = await p.evaluate(() => (document.body.innerText.match(/\[[^\]\n]{1,40}\]/g) || []));
    log(!br.length, 'заглушки в скобках на странице: ' + br.join(' '));
    // панель погод (для проверки): переключение каждой погоды
    if (await p.evaluate(() => !document.getElementById('wxPanel').hidden)) {
      await p.evaluate(() => document.getElementById('wxPanel').open = true); await p.waitForTimeout(200);
      const kinds = await p.evaluate(() => [...document.querySelectorAll('#wxKinds [data-k]')].map(b => b.dataset.k));
      for (const k of kinds) { await p.evaluate(k => document.querySelector('#wxKinds [data-k="' + k + '"]').click(), k); await p.waitForTimeout(350);
        log(await p.evaluate(k => document.getElementById('hero').dataset.wx === k, k), 'погода ' + k + ' не включилась'); }
      const auto = await p.$('#wxAuto'); if (auto) { await auto.click(); await p.waitForTimeout(300); }
      // «Сайт на телефоне» — только на компьютере
      if (w >= 1000) { const pb = await p.$('#wxPh [data-w="402"]');
        if (pb) { await pb.click(); await p.waitForTimeout(2500);
          log(await p.evaluate(() => !document.getElementById('phv').hidden), '«Сайт на телефоне» не открылся');
          const fr = p.frames().find(f => f !== p.mainFrame()); log(!!fr, 'нет страницы в рамке телефона');
          await p.click('#phvX'); await p.waitForTimeout(400); log(await p.evaluate(() => document.getElementById('phv').hidden), '«Сайт на телефоне» не закрылся'); } }
      await p.evaluate(() => document.getElementById('wxPanel').open = false);
    }
    await hs('в конце');
    errs.forEach(e => bad.push(tag + ': ' + e));
    console.log(tag, 'модуль бронирования открылся:', bookOk, '; проверено: номеров', ids.length, 'плиток альбома', alb, 'ошибок', errs.length);
    await p.close();
  }
  await b.close(); if (srv) srv.kill();
  console.log(bad.length ? 'ПРОБЛЕМЫ:\n' + [...new Set(bad)].join('\n') : 'ВСЁ ХОРОШО');
})();
