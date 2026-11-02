const { chromium } = require('playwright');
const PW='Echo2026!nce2';
(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge', proxy: { server: 'http://127.0.0.1:' + process.env.P_PORT } });
  const ctx = await browser.newContext({ viewport: { width: 768, height: 1024 }, hasTouch: true, userAgent: 'Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1' });
  const page = await ctx.newPage();
  page.on('console', m => console.log('[c]', m.type(), m.text().slice(0,120)));
  page.on('requestfailed', r => console.log('[reqfail]', r.url().slice(0,80), (r.failure()||{}).errorText));
  page.on('response', r => console.log('[net]', r.status(), r.request().method(), r.url().slice(0,90)));
  const errs = [];
  page.on('pageerror', e => errs.push(String(e).slice(0,100)));
  await page.goto('https://hank-hunau.github.io/nce2-echoloop/login.html', { waitUntil: 'load', timeout: 60000 });
  await page.waitForFunction(() => document.getElementById('cPar').onclick !== null, null, { timeout: 30000 });
  await page.fill('#em','kid@echo.hank-hunau.dev'); await page.fill('#pw',PW); await page.click('#go');
  await page.waitForTimeout(12000);
  console.log('[after-login]', page.url().slice(0,70), '| err:', await page.evaluate(() => { var e=document.getElementById('err'); return e?e.textContent:'(navigated)'; }).catch(()=>'(navigated)'));
  await page.waitForFunction(() => location.pathname.includes('nce2-echoloop') && (location.hash === '' || location.hash.includes('home') || location.hash.includes('lesson')), null, { timeout: 60000 });
  await page.evaluate(() => { location.hash = '#/lesson/1'; });
  await page.waitForFunction(() => document.querySelectorAll('.sent').length > 0, null, { timeout: 60000 });
  const r = await page.evaluate(() => {
    const play = document.querySelector('.sent .play');
    const btn = document.querySelector('.btn');
    const star = document.querySelector('.star');
    const en = document.querySelector('.sent .en');
    const cs = el => el ? getComputedStyle(el) : null;
    return {
      sentN: document.querySelectorAll('.sent').length,
      playSize: cs(play).width,
      btnMinH: cs(btn).minHeight,
      starSize: star ? cs(star).width + 'x' + cs(star).height : 'n/a',
      enFont: cs(en).fontSize + '/' + cs(en).lineHeight,
      btnBg: cs(btn).backgroundColor,
      subColor: cs(document.querySelector('.tip')).color,
      touchAction: cs(document.body).touchAction,
      appleMeta: !!document.querySelector('meta[name="apple-mobile-web-app-capable"]'),
      iconLink: !!document.querySelector('link[rel="apple-touch-icon"]'),
      tabMinH: cs(document.querySelector('nav.tabs a')).minHeight
    };
  });
  const icon = await page.evaluate(async () => { const r = await fetch('apple-touch-icon.png'); return r.status; });
  console.log(JSON.stringify({ ...r, iconHttp: icon, pageErrors: errs }, null, 1));
  await browser.close();
  process.exit(errs.length ? 1 : 0);
})().catch(e => { console.error('CRASH:', e.message); process.exit(2); });
