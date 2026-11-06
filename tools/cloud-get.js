// Скачать публичную папку Облака Mail.ru: node tools/cloud-get.js <weblink, напр. hZqz/XbqaKnAAn> <папка>
// Уже скачанные файлы с тем же размером пропускаются.
const fs = require('fs'), path = require('path');
const [weblink, out] = process.argv.slice(2);
const UA = {'User-Agent': 'Mozilla/5.0'};
(async () => {
  fs.mkdirSync(out, {recursive: true});
  const list = await (await fetch(`https://cloud.mail.ru/api/v4/public/list?weblink=${weblink}&limit=500`, {headers: UA})).json();
  let n = 0, mb = 0;
  for (const f of list.list.filter(x => x.kind === 'file')) {
    const dst = path.join(out, f.name);
    if (fs.existsSync(dst) && fs.statSync(dst).size === f.size) { n++; continue; }
    const disp = await (await fetch('https://cloud.mail.ru/api/v2/dispatcher', {headers: UA})).json();
    const base = disp.body.weblink_get[0].url;
    const url = `${base}/${weblink}/${encodeURIComponent(f.name)}`;
    for (let attempt = 1; attempt <= 3; attempt++) {
      try {
        const r = await fetch(url, {headers: UA});
        if (!r.ok) throw new Error('HTTP ' + r.status);
        const buf = Buffer.from(await r.arrayBuffer());
        if (buf.length !== f.size) throw new Error(`размер ${buf.length} ≠ ${f.size}`);
        fs.writeFileSync(dst, buf); n++; mb += buf.length / 1e6;
        console.log(`${n}/${list.list.length} ${f.name} ${(buf.length / 1e6).toFixed(1)} МБ`);
        break;
      } catch (e) { console.log('повтор', f.name, e.message); if (attempt === 3) throw e; }
    }
  }
  console.log(`готово: ${n} файлов, скачано ${mb.toFixed(0)} МБ`);
})();
