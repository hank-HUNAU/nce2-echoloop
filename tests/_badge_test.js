const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  const ctx = await browser.newContext({ viewport: { width: 834, height: 1194 }, hasTouch: true });
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(String(e).slice(0,120)));
  await page.goto('http://127.0.0.1:8115/index.html#/home', { waitUntil: 'load' });
  // 种一条已学且到期的复习（9 天前学完第 1 轮 → 第 2 轮已到期）
  await page.evaluate(() => {
    const prog = JSON.parse(localStorage.getItem('el2_progress') || '{}');
    prog['2'] = { stage:0, si:0, listened:{}, shadow:{}, hard:[], firstLearnAt: Date.now()-9*864e5, reviews:1, lastReviewAt: Date.now()-9*864e5, blindDone:true, retellDone:false };
    localStorage.setItem('el2_progress', JSON.stringify(prog));
  });
  // 到统计页（非首页），首页 tab 应有红点
  await page.reload({ waitUntil: 'load' });
  await page.goto('http://127.0.0.1:8115/index.html#/stats', { waitUntil: 'load' });
  await page.waitForTimeout(800);
  const r = await page.evaluate(() => {
    const hm = document.querySelector('nav.tabs a[href="#/home"]');
    const b = hm ? hm.querySelector('.bdg') : null;
    return { badge: !!b, dueText: document.body.innerText.includes('到期') };
  });
  // 回首页：红点应消失（首页本身展示到期卡）
  await page.goto('http://127.0.0.1:8115/index.html#/home', { waitUntil: 'load' });
  await page.waitForTimeout(600);
  const r2 = await page.evaluate(() => {
    const hm = document.querySelector('nav.tabs a[href="#/home"]');
    return { badgeGone: !(hm && hm.querySelector('.bdg')), dueCard: document.body.innerText.includes('第 2 轮复习') };
  });
  console.log(JSON.stringify({ ...r, ...r2, errs: errs.length }, null, 1));
  await browser.close();
  process.exit(r.badge && r2.badgeGone && r2.dueCard && errs.length===0 ? 0 : 1);
})().catch(e => { console.error('CRASH:', e.message); process.exit(2); });
