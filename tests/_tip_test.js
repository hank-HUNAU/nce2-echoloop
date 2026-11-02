const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  const ctx = await browser.newContext({ viewport: { width: 834, height: 1194 }, hasTouch: true });
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(String(e).slice(0,150)));
  // ① 首页：排程说明默认隐藏，? 展开可见
  await page.goto('http://127.0.0.1:8132/index.html#/home', { waitUntil: 'load' });
  await page.waitForFunction(() => document.body.innerText.includes('NCE2 Loop'), null, { timeout: 15000 });
  const r1 = await page.evaluate(() => {
    const d = document.getElementById('tipd-sched');
    return { tipdExists: !!d, hiddenByDefault: d && d.style.display === 'none', footClean: !document.body.innerText.includes('数据存本机浏览器') };
  });
  await page.evaluate(() => document.querySelector('[data-act="tipq"][data-tk="sched"]').click());
  const r2 = await page.evaluate(() => document.getElementById('tipd-sched').style.display === 'block');
  // ② 精听：? 钮 + 无常驻说明（种 stage=2）
  await page.evaluate(() => {
    const prog = JSON.parse(localStorage.getItem('el2_progress')||'{}');
    prog['1'] = Object.assign({stage:0,si:0,listened:{},shadow:{},hard:[],firstLearnAt:Date.now(),reviews:0,lastReviewAt:0,blindDone:false,retellDone:false}, prog['1'], {stage:2});
    localStorage.setItem('el2_progress', JSON.stringify(prog));
  });
  await page.reload({ waitUntil: 'load' });
  await page.goto('http://127.0.0.1:8132/index.html#/lesson/1', { waitUntil: 'load' });
  await page.waitForFunction(() => document.querySelectorAll('.sent').length > 0, null, { timeout: 20000 });
  const r3 = await page.evaluate(() => {
    const q = document.querySelector('.tipq[data-tk="int"]');
    return { hasQ: !!q, tipHidden: document.getElementById('tipd-int')?.style.display === 'none' };
  });
  await page.evaluate(() => document.querySelector('.tipq[data-tk="int"]').click());
  const r4 = await page.evaluate(() => document.getElementById('tipd-int').style.display === 'block');
  // ③ 卡片页：今日计数保留、规则收进 ?
  await page.evaluate(() => localStorage.setItem('el2_hard', JSON.stringify([{en:'T1',zh:'一',no:1,i:0}])));
  await page.goto('http://127.0.0.1:8132/index.html#/cards', { waitUntil: 'load' });
  await page.waitForTimeout(700);
  const r5 = await page.evaluate(() => ({
    todayTip: document.body.innerText.includes('今日待复习 1 张'),
    ruleHidden: !document.body.innerText.includes('12 小时后再出现'),
    hasQ: !!document.querySelector('.tipq[data-tk="cards"]')
  }));
  // ④ 我的页：孩子语言
  await page.evaluate(() => { window.el2OpenLogin && el2OpenLogin(); });
  await page.evaluate(() => {
    document.getElementById('lmEm').value='kid@echo.hank-hunau.dev';
    document.getElementById('lmPw').value='Echo2026!nce2';
    document.getElementById('lmGo').click();
  });
  await page.waitForFunction(() => !!window.EL2SESS, null, { timeout: 60000 });
  await page.evaluate(() => { location.hash = '#/me'; });
  await page.waitForTimeout(600);
  const r6 = await page.evaluate(() => ({
    kidLang: document.body.innerText.includes('学习记录会同步给爸爸妈妈和老师'),
    noTech: !document.body.innerText.includes('补传') && !document.body.innerText.includes('上云')
  }));
  console.log(JSON.stringify({ r1, r2, r3, r4, r5, r6, errs: errs.length }, null, 1));
  await browser.close();
  const pass = r1.tipdExists && r1.hiddenByDefault && r1.footClean && r2 && r3.hasQ && r3.tipHidden && r4 && r5.todayTip && r5.ruleHidden && r5.hasQ && r6.kidLang && r6.noTech && errs.length===0;
  console.log('总判定:', pass?'PASS':'FAIL');
  process.exit(pass?0:1);
})().catch(e => { console.error('CRASH:', e.message); process.exit(2); });
