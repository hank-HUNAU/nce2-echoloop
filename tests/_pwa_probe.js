const { chromium } = require('playwright');
const PW='Echo2026!nce2';
(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge', proxy: { server: 'http://127.0.0.1:' + process.env.P_PORT } });
  const ctx = await browser.newContext({ viewport: { width: 768, height: 1024 }, hasTouch: true, userAgent: 'Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1' });
  const page = await ctx.newPage();
  page.on('response', r => console.log('[net]', r.status(), r.request().method(), r.url().slice(0,95)));
  page.on('requestfailed', r => console.log('[reqfail]', r.url().slice(0,95), (r.failure()||{}).errorText));
  page.on('pageerror', e => console.log('[ERR]', String(e).slice(0,150)));
  const errs = [];
  page.on('pageerror', e => errs.push(String(e).slice(0,120)));
  await page.goto('https://hank-hunau.github.io/nce2-echoloop/login.html', { waitUntil: 'load', timeout: 60000 });
  await page.fill('#em','kid@echo.hank-hunau.dev'); await page.fill('#pw',PW); await page.click('#go');
  await page.evaluate(() => { location.hash = '#/lesson/1'; });
  await page.waitForFunction(() => document.querySelectorAll('.sent').length > 0, null, { timeout: 60000 });
  await page.waitForTimeout(4000); // 等 iOS 提示条（1.5s 延迟）与 SW 注册
  const r = await page.evaluate(async () => {
    const reg = await navigator.serviceWorker.getRegistration();
    const banner = document.querySelector('#pwaOk') ? 'iOS 添加到主屏提示条已弹出' : '无横幅';
    return {
      swRegistered: reg ? (reg.active ? 'active' : 'installing') : 'none',
      banner,
      manifestLink: !!document.querySelector('link[rel="manifest"]'),
      themeColor: document.querySelector('meta[name="theme-color"]') ? document.querySelector('meta[name="theme-color"]').content : 'none'
    };
  });
  // 点「知道了」应记忆 7 天不弹
  await page.evaluate(() => { const b = document.querySelector('#pwaNo'); if (b) b.click(); });
  const hidden = await page.evaluate(() => !!localStorage.getItem('el2_install_hide'));
  console.log(JSON.stringify({ ...r, dismissRemembered: hidden, pageErrors: errs }, null, 1));
  await browser.close();
  process.exit(errs.length ? 1 : 0);
})().catch(e => { console.error('CRASH:', e.message); process.exit(2); });
