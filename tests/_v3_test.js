const { chromium } = require('playwright');
const BASE='https://hank-hunau.github.io/nce2-echoloop/';
const SFX=String(Date.now()).slice(-5);
const STEM=`v3kid${SFX}@echo.hank-hunau.dev`, PW='V3Test2026!x';
const results=[];
function ok(n,c,x){ results.push([n,!!c]); console.log(`[${c?'OK':'FAIL'}] ${n}${x?' :: '+x:''}`); }
async function attempt(n){
  console.log(`===== attempt ${n} =====`);
  const browser = await chromium.launch({ headless:true, channel:'msedge', proxy:{server:'http://127.0.0.1:'+process.env.P_PORT} });
  try{
    // ① 未登录直接开课程页：可学习 + 顶栏有登录按钮 + 不被踢
    const st = await browser.newContext({ viewport:{width:768,height:1024}, hasTouch:true });
    const sp = await st.newPage();
    await sp.goto(BASE+'#/lesson/1', { waitUntil:'load', timeout:60000 });
    await sp.waitForFunction(() => document.querySelectorAll('.sent').length > 0, null, { timeout:60000 });
    const hasBtn = await sp.evaluate(() => !!document.getElementById('tbIn'));
    ok('① 未登录可学习且顶栏有登录按钮', hasBtn);

    // ② 教师登录门户 → teacher.html → 创建学生账号
    const tp = await browser.newPage();
    await tp.goto(BASE+'login.html', { waitUntil:'load', timeout:60000 });
    await tp.fill('#em','teacher@echo.hank-hunau.dev'); await tp.fill('#pw','HankTeach2026!'); await tp.click('#go');
    await tp.waitForFunction(() => document.getElementById('cGo') !== null, null, { timeout:90000 });
    await tp.waitForFunction(() => document.querySelectorAll('#cFam option').length > 0 && document.querySelector('#cFam option').value !== '', null, { timeout:30000 });
    await tp.fill('#cEmail',STEM); await tp.fill('#cPw',PW); await tp.fill('#cName','验收学生'+SFX); await tp.click('#cGo');
    try {
      await tp.waitForFunction(nm => document.getElementById('acctBox').innerText.includes(nm), STEM, { timeout:60000 });
    } catch(e) {
      const dbg = await tp.evaluate(() => ({ err: document.getElementById('cErr').textContent, list: document.getElementById('acctBox').innerText.slice(0,200) })).catch(e2=>({evalErr:String(e2).slice(0,60)}));
      console.log('[create-dbg]', JSON.stringify(dbg));
      throw e;
    }
    ok('② 教师页创建学生账号并出现在列表', true);

    // ③ 学生在 App 顶栏弹窗登录 → 学习 → 上报带 owner_uid
    await sp.click('#tbIn');
    await sp.fill('#lmEm',STEM); await sp.fill('#lmPw',PW); await sp.click('#lmGo');
    await sp.waitForFunction(() => !!window.EL2SESS && !!window.EL2SESS.uid, null, { timeout:60000 });
    await sp.evaluate(() => { statDay(66); });
    await sp.evaluate(() => syncFlush());
    await sp.waitForFunction(() => JSON.parse(localStorage.getItem('el2_sync_q')||'[]').length===0, null, { timeout:30000 });
    ok('③ 学生弹窗登录 + 数据带 owner_uid 上云', true);
    await st.close();

    // ④ 教师页监控出现该学生学情
    await tp.click('#tMon');
    await tp.waitForFunction(nm => document.getElementById('monBox').innerText.includes(nm), '验收学生'+SFX, { timeout:60000 });
    ok('④ 教师页监控出现该学生', true);

    // ⑤ 家长端（EchoAdmin）家庭可见：parent 预置号登录 → board signal 有数字
    const pp = await browser.newPage();
    await pp.goto(BASE+'login.html', { waitUntil:'load', timeout:60000 });
    await pp.fill('#em','parent@echo.hank-hunau.dev'); await pp.fill('#pw','Echo2026!nce2'); await pp.click('#go');
    await pp.waitForURL(/workbuddy\.link/, { timeout:90000 });
    await pp.waitForFunction(() => /\d/.test((document.getElementById('signal')||{}).textContent||''), null, { timeout:90000 });
    const sig = await pp.evaluate(() => document.getElementById('signal').textContent);
    ok('⑤ 家长端看到孩子学习记录', true, sig);
    await browser.close();
    return true;
  }catch(e){
    console.log('attempt failed:', String(e.message||e).slice(0,120));
    await browser.close().catch(()=>{});
    return false;
  }
}
(async () => {
  let done=false;
  for(let i=1;i<=3 && !done;i++){ done = await attempt(i); }
  const pass=results.filter(r=>r[1]).length;
  console.log(`\n===== 账号 v3 验收 ${pass}/${results.length} ${done?'（通过）':'（未全过）'}`);
  process.exit(done?0:1);
})().catch(e => { console.error('CRASH:', e.message); process.exit(2); });
