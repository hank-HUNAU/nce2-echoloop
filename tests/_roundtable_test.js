const { chromium } = require('playwright');
const LONG='The moment I shouted, a young man and a young woman sitting behind me started talking loudly in Chinese, which made me unable to hear the actors at all.';
(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  const ctx = await browser.newContext({ viewport: { width: 834, height: 1194 }, hasTouch: true });
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(String(e).slice(0,120)));
  // 种一条超长难句（验证卡片/难句本自适应）
  await page.goto('http://127.0.0.1:8093/index.html#/home', { waitUntil: 'load' });
  await page.evaluate(seed => localStorage.setItem('el2_hard', JSON.stringify([
    {en:'Short sentence test.',zh:'短句测试',no:1,i:0},
    {en:seed,zh:'超长句测试：当我大声喊叫时，坐在我背后的一对年轻男女开始用中文大声聊天，导致我完全听不到演员在说什么。',no:1,i:1}
  ])), LONG);
  // 难句本
  await page.goto('http://127.0.0.1:8093/index.html#/hard', { waitUntil: 'load' });
  await page.waitForFunction(() => document.body.innerText.includes('Short sentence test.'), null, { timeout: 15000 });
  const hard = await page.evaluate(() => {
    const en = document.querySelector('.item .tt .en');
    const cs = getComputedStyle(en);
    return { font: cs.fontSize, family: cs.fontFamily.slice(0,20) };
  });
  console.log('[难句本]', JSON.stringify(hard));
  // 卡片页：翻转卡自适应高度
  await page.goto('http://127.0.0.1:8093/index.html#/cards', { waitUntil: 'load' });
  await page.waitForFunction(() => document.querySelectorAll('.card').length >= 1, null, { timeout: 15000 });
  const card = await page.evaluate(() => {
    const cards = [...document.querySelectorAll('.card')];
    const long = cards[1] || cards[0];
    const cs = getComputedStyle(long);
    const inner = long.querySelector('.f').getBoundingClientRect();
    return { heightAuto: cs.height !== '190px', h: Math.round(parseFloat(cs.height)), overflowHidden: getComputedStyle(long).overflow, inH: Math.round(long.querySelector('.in').getBoundingClientRect().height) };
  });
  console.log('[卡片]', JSON.stringify(card));
  // 登录弹窗尺寸 + 键盘态
  await page.click('#tabLogin');
  const modal = await page.evaluate(() => {
    const card = document.querySelector('.lmCard');
    const cs = getComputedStyle(card);
    return { w: cs.maxWidth, h3: getComputedStyle(card.querySelector('h3')).fontSize, inp: getComputedStyle(document.getElementById('lmEm')).height + '/' + getComputedStyle(document.getElementById('lmEm')).fontSize, go: getComputedStyle(document.getElementById('lmGo')).height };
  });
  await page.focus('#lmEm');
  const kb = await page.evaluate(() => {
    const m = document.getElementById('loginMask');
    return { kb: m.classList.contains('kb'), maxH: getComputedStyle(document.querySelector('.lmCard')).maxHeight };
  });
  console.log('[弹窗]', JSON.stringify(modal));
  console.log('[键盘态]', JSON.stringify(kb));
  await page.screenshot({ path: 'E:/04 少儿原版课程/06 新概念英语/_roundtable_check.png' });
  await browser.close();
  const pass = hard.font==='18px' && /Georgia/.test(hard.family) && card.heightAuto && modal.w.includes('400') && kb.kb && errs.length===0;
  console.log('[errs]', errs.length, '| 总判定:', pass?'PASS':'FAIL');
  process.exit(pass?0:1);
})().catch(e => { console.error('CRASH:', e.message); process.exit(2); });
