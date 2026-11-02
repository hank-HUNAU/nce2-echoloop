const { chromium } = require('playwright');
const UA='Mozilla/5.0 (Linux; Android 12; MatePad 11) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/110.0.0.0 HuaweiBrowser/14.0.5 Mobile Safari/537.36';
(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  // 竖屏 800×1280（MatePad CSS 尺寸）
  let ctx = await browser.newContext({ viewport: { width: 800, height: 1280 }, hasTouch: true, userAgent: UA });
  let page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(String(e).slice(0,120)));
  await page.goto('http://127.0.0.1:8084/index.html#/lesson/1', { waitUntil: 'load' });
  await page.waitForFunction(() => document.querySelectorAll('.sent').length > 0, null, { timeout: 20000 });
  await page.waitForTimeout(2200); // 等华为引导横幅
  const r1 = await page.evaluate(() => ({
    sentN: document.querySelectorAll('.sent').length,
    tabs: document.getElementById('tabs').innerText.replace(/\n/g,' '),
    banner: !!document.querySelector('#pwaOk'),
    bannerTitle: document.querySelector('.lmCard div') ? document.querySelector('.lmCard').innerText.slice(0,40) : 'none',
    wrapW: getComputedStyle(document.querySelector('.wrap')).maxWidth
  }));
  console.log('[portrait]', JSON.stringify(r1));
  await ctx.close();
  // 横屏 1280×800
  ctx = await browser.newContext({ viewport: { width: 1280, height: 800 }, hasTouch: true, userAgent: UA });
  page = await ctx.newPage();
  await page.goto('http://127.0.0.1:8084/index.html#/home', { waitUntil: 'load' });
  await page.waitForFunction(() => document.body.innerText.includes('NCE2 Loop'), null, { timeout: 20000 });
  const r2 = await page.evaluate(() => ({ wrapW: getComputedStyle(document.querySelector('.wrap')).maxWidth }));
  console.log('[landscape]', JSON.stringify(r2));
  ok = r1.sentN>0 && r1.banner && r2.wrapW==='1100px' && errs.length===0;
  console.log('[errs]', errs.length);
  await browser.close();
  process.exit(ok?0:1);
})().catch(e => { console.error('CRASH:', e.message); process.exit(2); });
