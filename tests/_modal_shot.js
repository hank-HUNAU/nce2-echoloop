const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  const ctx = await browser.newContext({ viewport: { width: 768, height: 1024 }, hasTouch: true });
  const page = await ctx.newPage();
  await page.goto('http://127.0.0.1:8083/index.html#/home', { waitUntil: 'load' });
  await page.waitForFunction(() => document.body.innerText.includes('NCE2 Loop'), null, { timeout: 20000 });
  await page.click('#tabLogin');
  await page.waitForTimeout(400);
  const tabs = await page.evaluate(() => document.getElementById('tabs').innerText.replace(/\n/g,' '));
  console.log('[tabs]', tabs);
  const m = await page.evaluate(() => {
    const card = document.querySelector('.lmCard');
    const cs = getComputedStyle(card);
    const inCard = card.getBoundingClientRect();
    const go = document.getElementById('lmGo').getBoundingClientRect();
    return { cardH: cs.height, cardBg: cs.backgroundColor, goInside: go.bottom <= inCard.bottom + 1, cardBottom: inCard.bottom, goBottom: go.bottom };
  });
  await page.screenshot({ path: 'E:/04 少儿原版课程/06 新概念英语/_modal_check.png' });
  console.log(JSON.stringify(m));
  await browser.close();
})().catch(e => { console.error('CRASH:', e.message); process.exit(2); });
