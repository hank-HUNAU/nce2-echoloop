const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  const ctx = await browser.newContext({ viewport: { width: 834, height: 1194 }, hasTouch: true });
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(String(e).slice(0,150)));
  // ① 首页入口存在
  await page.goto('http://127.0.0.1:8135/index.html#/home', { waitUntil: 'load' });
  await page.waitForFunction(() => document.body.innerText.includes('NCE2 Loop'), null, { timeout: 15000 });
  const home = await page.evaluate(() => ({ btn: !!document.getElementById('homeOlBtn'), tip: document.body.innerText.includes('下载后断网也能学') }));
  console.log('[首页入口]', JSON.stringify(home));
  // ② 我的页：登录 → 离线包 sec → 点击下载 → 等完成
  await page.evaluate(() => { window.el2OpenLogin && el2OpenLogin(); });
  await page.evaluate(() => {
    document.getElementById('lmEm').value='kid@echo.hank-hunau.dev';
    document.getElementById('lmPw').value='Echo2026!nce2';
    document.getElementById('lmGo').click();
  });
  await page.waitForFunction(() => !!window.EL2SESS, null, { timeout: 60000 });
  await page.evaluate(() => { location.hash = '#/me'; });
  await page.waitForFunction(() => document.getElementById('olBtn'), null, { timeout: 15000 });
  const st0 = await page.evaluate(() => document.getElementById('olBtn').textContent);
  await page.click('#olBtn');
  await page.waitForFunction(() => localStorage.getItem('el2_offline'), null, { timeout: 120000 });
  // ③ 缓存验证：抽查首尾音频 + 数据
  const cache = await page.evaluate(async () => {
    const c = await caches.open('el2-pwa-v1');
    const checks = {};
    for (const p of ['audio/L01.mp3','audio/L48.mp3','audio/L96.mp3','data/L01.json','data/L96.json']) {
      const m = await c.match(p);
      checks[p] = m ? Math.round((await m.blob()).size/1024) + 'KB' : 'MISS';
    }
    let cnt = 0;
    const keys = await c.keys();
    keys.forEach(r => { if (r.url.includes('/audio/')) cnt++; });
    checks.audioCached = cnt;
    return checks;
  });
  const r6 = await page.evaluate(() => ({ state: document.getElementById('olState').textContent, btn: document.getElementById('olBtn').textContent }));
  console.log('[下载前按钮]', st0);
  console.log('[缓存抽查]', JSON.stringify(cache));
  console.log('[我的页状态]', JSON.stringify(r6));
  await browser.close();
  const pass = home.btn && home.tip && cache['audio/L01.mp3']!=='MISS' && cache['audio/L96.mp3']!=='MISS' && cache['data/L96.json']!=='MISS' && cache.audioCached>=90 && errs.length===0;
  console.log('[errs]', errs.length, '| 总判定:', pass?'PASS':'FAIL');
  process.exit(pass?0:1);
})().catch(e => { console.error('CRASH:', e.message); process.exit(2); });
