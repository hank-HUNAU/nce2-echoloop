const { chromium } = require('playwright');
const BASE='https://hank-hunau.github.io/nce2-echoloop/';
const PW='V2Test2026!x';
const SFX=String(Date.now()).slice(-5);
const results=[];
function ok(n,c,x){ results.push([n,!!c]); console.log(`[${c?'OK':'FAIL'}] ${n}${x?' :: '+x:''}`); }
(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge', proxy: { server: 'http://127.0.0.1:' + process.env.P_PORT } });

  // ① 门户注册 fresh kid → 自动登录落 App
  const kid = await browser.newContext({ viewport:{width:768,height:1024}, hasTouch:true });
  const kp = await kid.newPage();
  await kp.goto(BASE+'login.html', { waitUntil:'load', timeout:60000 });
  await kp.click('#tabReg');
  await kp.fill('#em',`v2kid${SFX}@echo.hank-hunau.dev`);
  await kp.fill('#pw',PW);
  await kp.click('#rKid');
  await kp.fill('#fam','ECHO-HANK-01');
  await kp.click('#go');
  await kp.waitForFunction(() => location.pathname.includes('nce2-echoloop') && !location.pathname.includes('login'), null, { timeout:90000 });
  await kp.evaluate(() => { location.hash = '#/lesson/1'; });
  await kp.waitForFunction(() => document.querySelectorAll('.sent').length > 0, null, { timeout:60000 });
  const kidSess = await kp.evaluate(() => JSON.parse(localStorage.getItem('el2_session')||'null'));
  ok('① 注册孩子号并自动落 App', kidSess && kidSess.role==='kid', 'family='+(kidSess&&kidSess.family_code));

  console.log('[step2] 开始');
  await kp.evaluate(() => { statDay(88); });
  await kp.evaluate(() => syncFlush());
  await kp.waitForFunction(() => (JSON.parse(localStorage.getItem('el2_sync_q')||'[]').length===0), null, { timeout:30000 });

  console.log('[step3] 开始');
  const par = await browser.newContext({ viewport:{width:900,height:900} });
  const pp = await par.newPage();
  await pp.goto(BASE+'login.html', { waitUntil:'load', timeout:60000 });
  await pp.click('#tabReg');
  await pp.fill('#em',`v2par${SFX}@echo.hank-hunau.dev`);
  await pp.fill('#pw',PW);
  await pp.click('#rPar');
  await pp.fill('#fam','ECHO-HANK-01');
  await pp.click('#go');
  await pp.waitForURL(/workbuddy\.link/, { timeout:90000 });
  for (let i = 0; i < 4; i++) {
    await pp.waitForTimeout(20000);
    const st = await pp.evaluate(() => ({ u: location.href.slice(0,70), sig: (document.getElementById('signal')||{}).textContent||'NOEL', box: (document.getElementById('box')||{}).innerText?document.getElementById('box').innerText.slice(0,80):'NOBOX' })).catch(e=>({evalErr:String(e).slice(0,60)}));
    console.log('[par t+' + ((i+1)*20) + 's]', JSON.stringify(st));
    if (/\d/.test(st.sig||'')) break;
  }
  await pp.waitForFunction(() => /\d/.test((document.getElementById('signal')||{}).textContent||''), null, { timeout:60000 });
  const sig = await pp.evaluate(() => document.getElementById('signal').textContent);
  const stat = await pp.evaluate(() => (document.getElementById('box')||{}).innerText || '');
  ok('② 注册家长号并落到 EchoAdmin', pp.url().includes('workbuddy.link'));
  ok('③ 家长端监控出现本周数据', /3|达标|\/3/.test(sig), sig);
  ok('④ 家长端 7 天图有数据柱', stat.includes('分钟'), stat.slice(0,80).replace(/\n/g,' '));

  console.log('[step4] 开始');
  const par2 = await browser.newContext({ viewport:{width:1280,height:800} });
  const p2 = await par2.newPage();
  await p2.goto(BASE+'login.html', { waitUntil:'load', timeout:60000 });
  await p2.fill('#em',`v2par${SFX}@echo.hank-hunau.dev`); await p2.fill('#pw',PW); await p2.click('#go');
  await p2.waitForURL(/workbuddy\.link/, { timeout:90000 });
  ok('⑤ 同一账号第二设备并发登录成功', p2.url().includes('workbuddy.link'));

  console.log('[step5] 开始');
  const iso = await pp.evaluate(async (tok) => {
    const r = await fetch('https://zwatrfbqkrvxpqtypdgx.supabase.co/rest/v1/el2_events?select=family_code&limit=100',
      { headers:{ apikey:'sb_publishable_mnkBBrHF70guvwfUNXuhBg_sIok8eBc', Authorization:'Bearer '+tok } });
    const rows = await r.json();
    const fams = [...new Set(rows.map(x=>x.family_code))];
    return { n: rows.length, fams };
  }, new URL(pp.url()).hash.match(/t=([^&]+)/)[1]);
  ok('⑥ 家庭隔离：只见自家 family', iso.fams.length===1 && iso.fams[0]==='ECHO-HANK-01', JSON.stringify(iso));

  await browser.close();
  const pass=results.filter(r=>r[1]).length;
  console.log(`\n===== 账号 v2 验收 ${pass}/${results.length} =====`);
  process.exit(pass===results.length?0:1);
})().catch(e => { console.error('CRASH:', e.message); process.exit(2); });
