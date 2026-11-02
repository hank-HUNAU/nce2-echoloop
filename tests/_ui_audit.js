const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  const ctx = await browser.newContext({ viewport: { width: 834, height: 1194 }, hasTouch: true });
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(String(e).slice(0,150)));
  page.on('console', m => { if(m.type()==='error') errs.push('[console] '+m.text().slice(0,120)); });
  const out = {};
  // ① 首页
  await page.goto('http://127.0.0.1:8095/index.html#/home', { waitUntil: 'load' });
  await page.waitForFunction(() => document.body.innerText.includes('NCE2 Loop'), null, { timeout: 15000 });
  out.home = await page.evaluate(() => ({
    h1: document.querySelector('h1')?.textContent?.trim(),
    hasGrid: !!document.querySelector('.grid'),
    cellN: document.querySelectorAll('.cell').length,
    hasDue: document.body.innerText.includes('今天要处理'),
    hasContinue: document.body.innerText.includes('继续学习') || document.body.innerText.includes('继续')
  }));
  // ② 课程页：四流程切换
  await page.goto('http://127.0.0.1:8095/index.html#/lesson/1', { waitUntil: 'load' });
  await page.waitForFunction(() => document.querySelectorAll('.sent').length > 0, null, { timeout: 15000 });
  out.lesson = await page.evaluate(() => ({
    sentN: document.querySelectorAll('.sent').length,
    stages: [...document.querySelectorAll('.stepper .st')].map(s=>s.textContent.trim()),
    hasPlay: !!document.querySelector('.sent .play'),
    hasStar: !!document.querySelector('.sent .star'),
    hasDetail: document.querySelectorAll('.detail').length,
    title: document.querySelector('h1')?.textContent?.trim()
  }));
  // 点播放（验证音频元素起播）
  await page.click('.sent .play');
  await page.waitForTimeout(1200);
  out.audio = await page.evaluate(() => { const au=document.getElementById('au'); return { playing: !au.paused, t: Math.round(au.currentTime*10)/10 }; });
  // ③ 盲听遮罩
  await page.evaluate(() => { location.hash='#/lesson/1'; });
  await page.waitForTimeout(500);
  const stages = await page.$$('.stepper .st');
  // 切到盲听（按新顺序 [盲听0,跟读1,精听2,复述3]）
  if (stages[0]) { await stages[0].click(); await page.waitForTimeout(600); }
  out.blind = await page.evaluate(() => ({ hasMask: !!document.querySelector('.shadow, [class*="blind"]'), txt: document.body.innerText.slice(0,60).replace(/\n+/g,'|') }));
  // ④ 统计页
  await page.goto('http://127.0.0.1:8095/index.html#/stats', { waitUntil: 'load' });
  await page.waitForTimeout(600);
  out.stats = await page.evaluate(() => ({
    h1: document.querySelector('h1')?.textContent?.trim(),
    hasSvg: document.querySelectorAll('svg').length > 0,
    hasBackup: document.body.innerText.includes('备份') || document.body.innerText.includes('导出')
  }));
  // ⑤ 难句/卡片空态
  await page.goto('http://127.0.0.1:8095/index.html#/hard', { waitUntil: 'load' });
  await page.waitForTimeout(500);
  out.hard = await page.evaluate(() => document.body.innerText.slice(0,80).replace(/\n+/g,'|'));
  await page.goto('http://127.0.0.1:8095/index.html#/cards', { waitUntil: 'load' });
  await page.waitForTimeout(500);
  out.cards = await page.evaluate(() => document.body.innerText.slice(0,80).replace(/\n+/g,'|'));
  // 截图存档
  await page.goto('http://127.0.0.1:8095/index.html#/home', { waitUntil: 'load' });
  await page.waitForTimeout(500);
  await page.screenshot({ path: 'E:/04 少儿原版课程/06 新概念英语/_audit_home.png', fullPage: false });
  console.log(JSON.stringify({ out, errs: errs.slice(0,8) }, null, 1));
  await browser.close();
})().catch(e => { console.error('CRASH:', e.message); process.exit(2); });
