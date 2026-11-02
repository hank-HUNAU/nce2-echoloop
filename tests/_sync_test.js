const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge', proxy: { server: 'http://127.0.0.1:57705' } });
  const page = await browser.newPage();
  await page.goto('https://hank-hunau.github.io/nce2-echoloop/#/lesson/1', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForFunction(() => typeof CUR !== 'undefined' && CUR.data && CUR.data.sentences, null, { timeout: 60000 });
  // 模拟两段学习：精听 65s + 跟读自评 4 星（走真实 statDay/rate 入队路径）
  await page.evaluate(() => { statDay(65); });
  await page.evaluate(() => { syncEnqueue('shadow', 30, 4); });
  const q1 = await page.evaluate(() => JSON.parse(localStorage.getItem('el2_sync_q') || '[]').length);
  // 触发 flush
  await page.evaluate(() => syncFlush());
  await page.waitForTimeout(5000);
  const q2 = await page.evaluate(() => JSON.parse(localStorage.getItem('el2_sync_q') || '[]').length);
  const did = await page.evaluate(() => localStorage.getItem('el2_did'));
  console.log(JSON.stringify({ queueBefore: q1, queueAfter: q2, deviceId: did }));
  await browser.close();
})().catch(e => { console.error('CRASH:', e.message); process.exit(2); });
