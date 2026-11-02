const { chromium } = require('playwright');
const PW='Echo2026!nce2';
(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' }); // 本地无代理
  const ctx = await browser.newContext({ viewport: { width: 768, height: 1024 }, hasTouch: true });
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(String(e).slice(0,150)));
  await page.goto('http://127.0.0.1:8077/login.html', { waitUntil: 'load', timeout: 30000 });
  await page.fill('#em','kid@echo.hank-hunau.dev'); await page.fill('#pw',PW); await page.click('#go');
  await page.waitForFunction(() => location.pathname.endsWith('/') && !location.pathname.includes('login'), null, { timeout: 20000 });
  await page.evaluate(() => { location.hash = '#/lesson/1'; });
  await page.waitForFunction(() => document.querySelectorAll('.sent').length > 0, null, { timeout: 20000 });
  await page.waitForTimeout(3000);
  const r = await page.evaluate(async () => {
    const reg = await navigator.serviceWorker.getRegistration();
    return {
      sentN: document.querySelectorAll('.sent').length,
      playW: getComputedStyle(document.querySelector('.sent .play')).width,
      sw: reg ? (reg.active ? 'active' : 'installing') : 'none',
      swCtl: !!navigator.serviceWorker.controller,
      banner: !!document.querySelector('#pwaOk'),
      manifest: !!document.querySelector('link[rel="manifest"]')
    };
  });
  console.log(JSON.stringify({ ...r, pageErrors: errs }, null, 1));
  await browser.close();
  process.exit(0);
})().catch(e => { console.error('CRASH:', e.message); process.exit(2); });
