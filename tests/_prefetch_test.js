const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  const ctx = await browser.newContext({ viewport: { width: 834, height: 1194 }, hasTouch: true });
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(String(e).slice(0,120)));
  await page.goto('http://127.0.0.1:8090/index.html#/lesson/1', { waitUntil: 'load' });
  await page.waitForFunction(() => document.querySelectorAll('.sent').length > 0, null, { timeout: 20000 });
  // 等 2.5s 预取触发 + 完成（本地文件即刻完成）
  await page.waitForTimeout(4500);
  const r = await page.evaluate(async () => {
    const c = await caches.open('el2-pwa-v1');
    const m = await c.match('audio/L01.mp3');
    const sz = m ? (await m.blob()).size : 0;
    const tab = getComputedStyle(document.querySelector('nav.tabs a')).fontSize;
    const cell = document.querySelector('.cell span') ? getComputedStyle(document.querySelector('.cell span')).fontSize : 'n/a';
    return { audioCached: sz > 500000, audioSize: sz, tabFont: tab, cellFont: cell };
  });
  console.log(JSON.stringify({ ...r, errs }, null, 1));
  await browser.close();
  process.exit(r.audioCached && errs.length===0 ? 0 : 1);
})().catch(e => { console.error('CRASH:', e.message); process.exit(2); });
