// Проверка вёрстки собранного сайта (site/) на 15 ширинах: node tools/qa.js
const pw = require('playwright'), serve = require('./serve');
const MOCK = {current:{temperature_2m:-14.2,weather_code:75,is_day:1,wind_speed_10m:42,cloud_cover:100},daily:{sunrise:['2026-10-28T07:05'],sunset:['2026-10-28T17:25']}};
(async()=>{ const srv = await serve(); const b = await pw.chromium.launch(); const f = srv.url + '/'; const errs=[]; const issues=[];
 for (const w of [320,360,375,390,402,430,600,768,900,1024,1180,1280,1366,1440,1920]){
  const ctx = await b.newContext({viewport:{width:w,height:860}, isMobile:w<700, hasTouch:w<700, deviceScaleFactor:1});
  const m = await ctx.newPage(); m.on('pageerror',e=>errs.push(w+': '+e.message)); m.on('console',c=>{ if(c.type()==='error' && !/net::|Failed to load resource/.test(c.text())) errs.push(w+' console: '+c.text()); });
  await m.route('https://api.open-meteo.com/**', r=>r.fulfill({status:200, contentType:'application/json', headers:{'access-control-allow-origin':'*'}, body: JSON.stringify(MOCK)}));
  await m.route('https://fonts.**', r=>r.continue().catch(()=>{}));
  await m.goto(f); await m.waitForTimeout(900);
  const r = await m.evaluate(()=>{ const out=[]; const vw=innerWidth;
    if (document.documentElement.scrollWidth > vw+1) out.push('h-overflow '+document.documentElement.scrollWidth);
    const lb=document.getElementById('logoBtn').getBoundingClientRect(), hr=document.querySelector('.hdr-r').getBoundingClientRect(), nav=document.querySelector('.nav').getBoundingClientRect();
    if (hr.right > vw-8) out.push('hdr-r past edge '+hr.right);
    if (lb.right+6 > hr.left) out.push('logo overlaps right '+lb.right+'>'+hr.left);
    if (nav.width && (lb.right+6>nav.left || nav.right+6>hr.left)) out.push('nav overlap');
    const c=document.querySelector('.call'), t=document.querySelector('.call .ct b'); if (t.offsetWidth && t.getBoundingClientRect().right > c.getBoundingClientRect().right-4) out.push('number outside pill');
    document.querySelectorAll('.hp-c, .hp-wx, .btn, .room, .panel').forEach(e=>{ if (e.offsetWidth && e.scrollWidth > e.clientWidth+2) out.push('inner overflow '+e.className+' '+e.scrollWidth+'>'+e.clientWidth); });
    return out; });
  if (r.length) issues.push(w+': '+[...new Set(r)].join('; '));
  if (w===402){ // interactions
    await m.click('#logoBtn'); await m.waitForTimeout(300); const mo = await m.evaluate(()=>document.getElementById('siteMenu').classList.contains('on')); await m.keyboard.press('Escape'); await m.waitForTimeout(200);
    const mc = await m.evaluate(()=>!document.getElementById('siteMenu').classList.contains('on'));
    await m.evaluate(()=>document.querySelector('#r-lux .pl').click()); await m.waitForTimeout(400); const po = await m.evaluate(()=>document.getElementById('pm').classList.contains('on'));
    await m.keyboard.press('Escape'); await m.waitForTimeout(200); const pc = await m.evaluate(()=>!document.getElementById('pm').classList.contains('on') && document.body.style.overflow==='');
    if (!(mo&&mc&&po&&pc)) issues.push('interactions '+[mo,mc,po,pc]);
    const a11y = await m.evaluate(()=>{ const o=[]; document.querySelectorAll('button').forEach(bt=>{ if(!(bt.innerText.trim()||bt.getAttribute('aria-label'))) o.push('button no name: '+bt.outerHTML.slice(0,80)); });
      document.querySelectorAll('img').forEach(i=>{ if(!i.alt) o.push('img no alt'); }); o.push('h1 count '+document.querySelectorAll('h1').length);
      const small=[]; document.querySelectorAll('a,button').forEach(e=>{ const r=e.getBoundingClientRect(); if (r.width && r.height && r.height<36 && getComputedStyle(e).display!=='none' && !e.closest('footer') && !e.closest('.mtog')) small.push((e.innerText||e.getAttribute('aria-label')||'').trim().slice(0,25)+' '+Math.round(r.height)); }); if (small.length) o.push('small targets: '+small.join(' | '));
      o.push('links: '+[...new Set([...document.querySelectorAll('a[href]')].map(a=>a.getAttribute('href')))].join(' '));
      return o; });
    console.log(a11y.join('\n'));
    console.log('now:', await m.evaluate(()=>document.querySelector('.hp-wx').textContent));
  }
  await ctx.close(); }
 console.log('ISSUES\n'+issues.join('\n')); console.log('ERRORS', errs); await b.close(); srv.close(); })();
