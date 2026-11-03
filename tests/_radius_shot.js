const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  const ctx = await browser.newContext({ viewport: { width: 834, height: 1194 }, hasTouch: true });
  const page = await ctx.newPage();
  await page.goto('http://127.0.0.1:8138/index.html#/home', { waitUntil: 'load' });
  await page.waitForFunction(() => document.body.innerText.includes('我的课程'), null, { timeout: 15000 });
  await page.waitForTimeout(600);
  await page.screenshot({ path: 'E:/04 少儿原版课程/06 新概念英语/_radius_check.png' });
  await browser.close();
  console.log('shot done');
})().catch(e => console.error('CRASH:', e.message));
