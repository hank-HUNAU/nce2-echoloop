const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  const ctx = await browser.newContext({ viewport: { width: 834, height: 1194 }, hasTouch: true });
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(String(e).slice(0,150)));
  await page.goto('http://127.0.0.1:8137/index.html#/home', { waitUntil: 'load' });
  await page.waitForFunction(() => document.body.innerText.includes('我的课程'), null, { timeout: 15000 });
  const r1 = await page.evaluate(async () => {
    const imgs = [...document.querySelectorAll('.bk2')];
    const loaded = await Promise.all(imgs.map(i => new Promise(res => { if(i.complete) res(i.naturalWidth>0); else i.onload=()=>res(i.naturalWidth>0), i.onerror=()=>res(false); })));
    return { covers: imgs.length, allLoaded: loaded.every(Boolean), srcs: imgs.map(i=>i.getAttribute('src')) };
  });
  console.log('[课程中心封面]', JSON.stringify(r1));
  await page.evaluate(() => { document.querySelector('[data-go="#/c/nce2"]').click(); });
  await page.waitForFunction(() => document.body.innerText.includes('全部课程'), null, { timeout: 15000 });
  const r2 = await page.evaluate(() => ({ titleCover: !!document.querySelector('h1 img') }));
  console.log('[NCE2 标题封面]', JSON.stringify(r2));
  await page.goto('http://127.0.0.1:8137/index.html#/c/nce1', { waitUntil: 'load' });
  await page.waitForTimeout(500);
  const r3 = await page.evaluate(() => ({ n1Cover: !!document.querySelector('img.bk2[src="covers/nce1_s.jpg"]') }));
  console.log('[NCE1 封面]', JSON.stringify(r3));
  await page.screenshot({ path: 'E:/04 少儿原版课程/06 新概念英语/_cc_covers.png' });
  await browser.close();
  const pass = r1.covers===2 && r1.allLoaded && r2.titleCover && r3.n1Cover && errs.length===0;
  console.log('[errs]', errs.length, '| 总判定:', pass?'PASS':'FAIL');
  process.exit(pass?0:1);
})().catch(e => { console.error('CRASH:', e.message); process.exit(2); });
