const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  const errs = [];
  // iPad Air 横屏 1180×820 + iPad Safari 桌面 UA（iPadOS 实况）
  const ctx = await browser.newContext({ viewport: { width: 1180, height: 820 }, hasTouch: true,
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15' });
  const page = await ctx.newPage();
  page.on('pageerror', e => errs.push(String(e).slice(0,120)));
  await page.goto('http://127.0.0.1:8085/index.html#/lesson/1', { waitUntil: 'load' });
  await page.waitForFunction(() => document.querySelectorAll('.sent').length > 0, null, { timeout: 20000 });
  const r1 = await page.evaluate(() => ({
    secW: getComputedStyle(document.querySelector('.sec')).maxWidth,
    sentN: document.querySelectorAll('.sent').length,
    tabs: document.getElementById('tabs').innerText.replace(/\n/g,' ')
  }));
  console.log('[ipad横屏]', JSON.stringify(r1));
  // 登录框键盘避让类
  await page.evaluate(() => { location.hash='#/me'; });
  await page.waitForTimeout(500);
  await page.click('[data-act="melogin"]');
  await page.focus('#lmEm');
  const kb = await page.evaluate(() => document.getElementById('loginMask').classList.contains('kb'));
  await page.evaluate(() => document.getElementById('lmEm').blur());
  const kbOff = await page.evaluate(() => !document.getElementById('loginMask').classList.contains('kb'));
  console.log('[kb避让]', JSON.stringify({ focusOn: kb, blurOff: kbOff }));
  // 竖屏 834×1194
  const ctx2 = await browser.newContext({ viewport: { width: 834, height: 1194 }, hasTouch: true });
  const p2 = await ctx2.newPage();
  await p2.goto('http://127.0.0.1:8085/index.html#/home', { waitUntil: 'load' });
  await p2.waitForFunction(() => document.body.innerText.includes('NCE2 Loop'), null, { timeout: 20000 });
  const r2 = await p2.evaluate(() => ({ wrapW: getComputedStyle(document.querySelector('.wrap')).maxWidth }));
  console.log('[ipad竖屏]', JSON.stringify(r2));
  await browser.close();
  const pass = r1.sentN>0 && r1.secW==='920px' && kb && kbOff && errs.length===0;
  console.log('[errs]', errs.length, '| 结果:', pass?'PASS':'FAIL');
  process.exit(pass?0:1);
})().catch(e => { console.error('CRASH:', e.message); process.exit(2); });
