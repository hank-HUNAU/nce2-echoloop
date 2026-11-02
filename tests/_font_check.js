const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  const ctx = await browser.newContext({ viewport: { width: 834, height: 1194 }, hasTouch: true });
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(String(e).slice(0,120)));
  await page.goto('http://127.0.0.1:8091/index.html#/lesson/1', { waitUntil: 'load' });
  await page.waitForFunction(() => document.querySelectorAll('.sent').length > 0, null, { timeout: 20000 });
  const r1 = await page.evaluate(() => ({
    st: getComputedStyle(document.querySelector('.stepper .st')).fontSize,
    en: getComputedStyle(document.querySelector('.sent .en')).fontSize,
    zh: getComputedStyle(document.querySelector('.sent .zh')).fontSize,
    tab: getComputedStyle(document.querySelector('nav.tabs a')).fontSize,
    tabIcon: getComputedStyle(document.querySelector('nav.tabs a svg')).width,
    navH: getComputedStyle(document.querySelector('nav.tabs a')).minHeight
  }));
  console.log('[lesson]', JSON.stringify(r1));
  // 底栏 5 项在 834px 是否放得下（不换行不挤压）
  const fit = await page.evaluate(() => {
    const as = [...document.querySelectorAll('nav.tabs a')];
    return as.every(a => a.getBoundingClientRect().height < 70);
  });
  console.log('[底栏单行]', fit);
  await page.goto('http://127.0.0.1:8091/index.html#/stats', { waitUntil: 'load' });
  await page.waitForTimeout(800);
  const h1 = await page.evaluate(() => getComputedStyle(document.querySelector('h1')).fontSize);
  console.log('[stats h1]', h1);
  await page.screenshot({ path: 'E:/04 少儿原版课程/06 新概念英语/_font_check.png' });
  await browser.close();
  process.exit((r1.st==='15px'&&r1.tab==='14px'&&r1.en==='18px'&&fit&&errs.length===0)?0:1);
})().catch(e => { console.error('CRASH:', e.message); process.exit(2); });
