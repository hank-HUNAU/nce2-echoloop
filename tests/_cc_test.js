const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  const ctx = await browser.newContext({ viewport: { width: 834, height: 1194 }, hasTouch: true });
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(String(e).slice(0,150)));
  // ① 课程中心
  await page.goto('http://127.0.0.1:8136/index.html#/home', { waitUntil: 'load' });
  await page.waitForFunction(() => document.body.innerText.includes('课程中心'), null, { timeout: 15000 });
  const r1 = await page.evaluate(() => ({
    today: document.body.innerText.includes('今日任务'),
    nce2: document.body.innerText.includes('新概念英语 2'),
    nce1: document.body.innerText.includes('新概念英语 1') && document.body.innerText.includes('敬请期待'),
    tabOn: document.querySelector('nav.tabs a[href="#/home"]')?.textContent
  }));
  console.log('[课程中心]', JSON.stringify(r1));
  // ② 点 NCE2 → 课程内页（96 格 + 离线包 + 返回链接）
  await page.evaluate(() => { document.querySelector('[data-go="#/c/nce2"]').click(); });
  await page.waitForFunction(() => document.body.innerText.includes('全部课程'), null, { timeout: 15000 });
  const r2 = await page.evaluate(() => ({
    hash: location.hash,
    back: document.body.innerText.includes('← 课程中心'),
    grid: document.querySelectorAll('.cell').length,
    offline: !!document.getElementById('homeOlBtn'),
    h1: document.querySelector('h1')?.textContent?.trim().slice(0,20)
  }));
  console.log('[NCE2 内页]', JSON.stringify(r2));
  // ③ NCE1 占位页
  await page.goto('http://127.0.0.1:8136/index.html#/c/nce1', { waitUntil: 'load' });
  await page.waitForTimeout(500);
  const r3 = await page.evaluate(() => ({ soon: document.body.innerText.includes('教材数据准备中'), hash: location.hash }));
  console.log('[NCE1 占位]', JSON.stringify(r3));
  // ④ 返回键保护：#c/nce2 → back → 课程中心
  await page.goto('http://127.0.0.1:8136/index.html#/c/nce2', { waitUntil: 'load' });
  await page.waitForFunction(() => document.body.innerText.includes('全部课程'), null, { timeout: 15000 });
  await page.evaluate(() => { location.hash = '#/lesson/1'; });
  await page.waitForFunction(() => document.querySelectorAll('.sent').length > 0, null, { timeout: 20000 });
  await page.goBack();
  await page.waitForTimeout(700);
  const back1 = await page.evaluate(() => location.hash);
  console.log('[back 到]', back1);
  await browser.close();
  const pass = r1.today && r1.nce2 && r1.nce1 && r2.hash==='#/c/nce2' && r2.back && r2.grid===96 && r2.offline && r3.soon && /^(#\/c\/nce2|#\/home)$/.test(back1) && errs.length===0;
  console.log('[errs]', errs.length, '| 总判定:', pass?'PASS':'FAIL');
  process.exit(pass?0:1);
})().catch(e => { console.error('CRASH:', e.message); process.exit(2); });
