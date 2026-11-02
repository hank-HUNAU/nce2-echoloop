const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge', proxy: { server: 'http://127.0.0.1:' + process.env.P_PORT, bypass: '127.0.0.1' } });
  const ctx = await browser.newContext({ viewport: { width: 834, height: 1194 }, hasTouch: true });
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(String(e).slice(0,120)));
  await page.goto('http://127.0.0.1:8103/index.html#/home', { waitUntil: 'load' });
  await page.evaluate(() => {
    const of_ = window.fetch;
    window.fetch = function(u){ console.log('[pf]', String(u).slice(0,60)); return of_.apply(this, arguments); };
    window.el2OpenLogin();
    document.getElementById('lmEm').value='kid@echo.hank-hunau.dev';
    document.getElementById('lmPw').value='Echo2026!nce2';
    document.getElementById('lmGo').click();
  });
  await page.waitForFunction(() => !!window.EL2SESS, null, { timeout: 60000 });
  console.log('[登录] EL2SESS 已就位');
  await page.evaluate(() => { location.hash = '#/me'; });
  await page.waitForFunction(() => document.querySelector('h1') && document.querySelector('h1').textContent === '我的', null, { timeout: 15000 });
  const me = await page.evaluate(() => ({
    hasEmail: document.body.innerText.includes('kid@echo.hank-hunau.dev'),
    hasOverview: document.body.innerText.includes('已学') && document.body.innerText.includes('通关'),
    hasOut: !!document.getElementById('meOut2'),
    tabOn: document.querySelector('nav.tabs a[href="#/me"]')?.className,
    tabLabel: document.querySelector('nav.tabs a[href="#/me"]')?.textContent
  }));
  console.log('[我的页]', JSON.stringify(me));
  await page.screenshot({ path: 'E:/04 少儿原版课程/06 新概念英语/_me_page.png' });
  await browser.close();
  const pass = me.hasEmail && me.hasOverview && me.hasOut && me.tabOn==='on' && errs.length===0;
  console.log('[errs]', errs.length, '| 结果:', pass?'PASS':'FAIL');
  process.exit(pass?0:1);
})().catch(e => { console.error('CRASH:', e.message); process.exit(2); });
