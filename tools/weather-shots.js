// Снимки всех погод на обложке собранного сайта (site/): node tools/weather-shots.js d|m [погоды через запятую]
const pw=require('playwright'),serve=require('./serve');(async()=>{const srv=await serve();const b=await pw.chromium.launch({args:['--use-gl=swiftshader','--enable-unsafe-swiftshader']});
require('fs').mkdirSync('shots',{recursive:true});
const [w,h,tag]=process.argv[2]==='m'?[402,874,'m']:[1440,900,'d'];
const kinds=(process.argv[3]||'clear,partly,overcast,fog,drizzle,rain,sleet,snow,heavysnow,blizzard,thunder').split(',');
const p=await b.newPage({viewport:{width:w,height:h},deviceScaleFactor:1}); p.on('pageerror',e=>console.log('ERR',e.message)); p.on('console',c=>{if(c.type()==='error')console.log('CERR',c.text())});
await p.route('https://api.open-meteo.com/**',r=>r.abort());
await p.goto(srv.url+'/');await p.waitForTimeout(800);
await p.evaluate(()=>{const d=document.querySelector('details.wxpanel');if(d)d.style.display='none';});
for(const k of kinds){
  await p.evaluate(k=>document.querySelector('[data-k="'+k+'"]').click(),k);
  await p.waitForTimeout(+(process.env.WAIT||2500));
  if(k==='thunder'){ // grab several frames, keep brightest
    let best=null,bv=-1;
    for(let i=0;i<60;i++){const buf=await p.screenshot({clip:{x:0,y:0,width:w,height:h}});const v=buf.length; if(v>bv){bv=v;best=buf;} await p.waitForTimeout(180);}
    require('fs').writeFileSync(`shots/${tag}_${k}.png`,best);
  } else await p.screenshot({path:`shots/${tag}_${k}.png`});
}
await b.close();srv.close();})();
