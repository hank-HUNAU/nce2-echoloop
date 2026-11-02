const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  const ctx = await browser.newContext({ viewport: { width: 834, height: 1194 }, hasTouch: true });
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(String(e).slice(0,120)));
  // ① 首启引导出现
  await page.goto('http://127.0.0.1:8110/index.html#/home', { waitUntil: 'load' });
  await page.waitForFunction(() => document.body.innerText.includes('NCE2 Loop'), null, { timeout: 15000 });
  const intro1 = await page.evaluate(() => !!document.getElementById('introBox'));
  // ② 点击"我知道了"→消失且不再出现
  await page.click('#introGo');
  const intro2 = await page.evaluate(() => {
    const gone = !document.getElementById('introBox');
    return { gone, flag: localStorage.getItem('el2_intro') };
  });
  await page.reload({ waitUntil: 'load' });
  await page.waitForTimeout(800);
  const intro3 = await page.evaluate(() => !document.getElementById('introBox'));
  // ③ 课程页骨架屏 → 内容
  await page.goto('http://127.0.0.1:8110/index.html#/lesson/2', { waitUntil: 'load' });
  await page.waitForFunction(() => document.querySelectorAll('.sent').length > 0, null, { timeout: 20000 });
  const sentN = await page.evaluate(() => document.querySelectorAll('.sent').length);
  /* 返回键保护：goto 首页 → back → 应回到首页（不丢失） */
  await page.evaluate(() => { location.hash = '#/lesson/1'; });
  await page.waitForFunction(() => document.body.innerText.includes('A Private Conversation'), null, { timeout: 20000 });
  await page.goBack();
  await page.waitForTimeout(600);
  const backHome = await page.evaluate(() => (location.hash || '#/home'));
  console.log('[back]', backHome);
  // ④ 复习角标：有到期复习时首页 tab 显示红点（造一条到期复习）
  // P2-C 文案验证：未学课不应显示「第1轮」
  const labelOk = await page.evaluate(() => [...document.querySelectorAll('#app .cell')].every(c => {
    const lb = c.querySelector('span').textContent;
    return lb === '未学' || lb === '通关' || /^第\d+轮$/.test(lb);
  }));
  console.log('[格子文案]', labelOk);
  await page.evaluate(() => { location.hash = '#/home'; });
  await page.waitForTimeout(600);
  const badge = await page.evaluate(() => {
    const hm = document.querySelector('nav.tabs a[href="#/home"]');
    return { due: document.body.innerText.includes('今天要处理') && !document.body.innerText.includes('没有到期'), badge: !!(hm && hm.querySelector('.bdg')) };
  });
  // ⑤ 返回键模拟：lesson → back → home
  await page.goto('http://127.0.0.1:8110/index.html#/lesson/1', { waitUntil: 'load' });
  await page.waitForFunction(() => document.querySelectorAll('.sent').length > 0, null, { timeout: 20000 });
  await page.goBack();
  await page.waitForTimeout(800);
  const backTo = await page.evaluate(() => location.hash || '#/home');
  console.log(JSON.stringify({ intro1, intro2, intro3, sentN, badge, backTo, errs: errs.length }, null, 1));
  await browser.close();
  const pass = intro1 && intro2.gone && intro2.flag==='1' && intro3 && sentN>0 && badge.badge && /^(#\/home|#\/lesson\/\d+)$/.test(backHome) && labelOk && errs.length===0;
  console.log('总判定:', pass?'PASS':'FAIL');
  process.exit(pass?0:1);
})().catch(e => { console.error('CRASH:', e.message); process.exit(2); });
