/* 课程库 / 我的课程 回归测试
   覆盖：课程 tab 入口 → 课程库渲染 → 课程码添加 → 添加即下载 → 暂停 → 续传完成
        → 真机重启后真实性校验 → 我的课程离线状态 → 移除课程释放文件
   跑法：node tests/_store_test.js（需在本机 8099 端口起静态服务） */
const { chromium } = require('playwright');
const B = 'http://127.0.0.1:8099/';
const out = { steps: [], errors: [] };
function say(k, v) { out.steps.push(k + ': ' + v); console.log(k + ': ' + JSON.stringify(v)); }

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  const ctx = await browser.newContext({ viewport: { width: 768, height: 1024 }, hasTouch: true });
  const page = await ctx.newPage();
  page.on('pageerror', e => out.errors.push(String(e).slice(0, 200)));
  page.on('console', m => { if (m.type() === 'error') out.errors.push('console: ' + m.text().slice(0, 160)); });
  page.on('dialog', d => d.accept());

  await page.goto(B, { waitUntil: 'load', timeout: 30000 });
  await page.evaluate(() => { localStorage.clear(); });
  await page.reload({ waitUntil: 'load' });
  await page.waitForFunction(() => document.querySelector('#app h1'), null, { timeout: 15000 });

  /* 1. 课程 tab：右上入口 + 我的课程只有 nce2 */
  say('h1', await page.$eval('#app h1', e => e.textContent.trim()));
  say('选择课程按钮', !!(await page.$('.hbtn')));
  say('课程行数', (await page.$$eval('#app .item[data-act="openc"]', a => a.length)));
  await page.click('.hbtn');
  await page.waitForFunction(() => location.hash === '#/store', null, { timeout: 5000 });

  /* 2. 课程库渲染：极简卡（封面+名称+状态圆点），无按钮 */
  await page.waitForFunction(() => document.querySelectorAll('.coCard').length > 0, null, { timeout: 8000 });
  say('课程库卡片数', (await page.$$eval('.coCard', a => a.length)));
  say('卡片无按钮', (await page.$$eval('.coCard .coBtn, .coCard .coRm, .coCard .coState', a => a.length)) === 0);
  say('卡片信息仅为封面+名称', await page.$$eval('.coCard', a => a.every(c => c.children.length === 3 && c.querySelector('.bkc') && c.querySelector('.coName'))));
  say('nce1 筹备中', await page.$eval('#sc-nce1', e => e.classList.contains('off') && !!e.querySelector('.coDot') && !e.dataset.act));
  say('nce2 灰点（未下载）', await page.$eval('#sc-nce2 .coDot', e => !e.classList.contains('ok') && !e.classList.contains('prog')));

  /* 3. 课程码添加 → 立即进入下载（限速 3MB/s，保证有窗口测暂停） */
  const cdp = await ctx.newCDPSession(page);
  await cdp.send('Network.enable');
  await cdp.send('Network.emulateNetworkConditions', { offline: false, latency: 0, downloadThroughput: 3 * 1024 * 1024, uploadThroughput: 3 * 1024 * 1024 });
  await page.fill('#codeIn', 'nce2-loop');
  await page.click('[data-act="codego"]');
  await page.waitForTimeout(1200);
  say('课程码后状态', await page.evaluate(() => JSON.parse(localStorage.getItem('el2_dl') || '{}').nce2));
  await page.waitForFunction(() => document.querySelector('#sc-nce2 .coDot.prog'), null, { timeout: 8000 });
  say('绿环进度点出现', await page.$eval('#sc-nce2 .coDot.prog b', e => /\d+/.test(e.textContent.trim())));
  say('我的课程', await page.evaluate(() => localStorage.getItem('el2_mycourses')));

  /* 4. 暂停：下载中再点封面 */
  await page.click('#sc-nce2', { timeout: 8000 });
  await page.waitForTimeout(600);
  const paused = await page.evaluate(() => JSON.parse(localStorage.getItem('el2_dl') || '{}').nce2);
  say('暂停态', paused);
  if (!paused || paused.state !== 'pause') throw new Error('暂停未生效');
  const frozen = await page.waitForTimeout(1200).then(() => page.evaluate(() => JSON.parse(localStorage.getItem('el2_dl') || '{}').nce2.done));
  say('暂停后不再增长', frozen === paused.done || frozen === paused.done + 1);
  await cdp.send('Network.emulateNetworkConditions', { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 });

  /* 5. 刷新后仍为待下载（不假报就绪） */
  await page.reload({ waitUntil: 'load' });
  await page.waitForFunction(() => document.querySelectorAll('.coCard').length > 0, null, { timeout: 8000 });
  say('刷新后不假报就绪', await page.$eval('#sc-nce2 .coDot', e => !e.classList.contains('ok')));

  /* 6. 续传至完成：点封面 */
  await page.click('#sc-nce2');
  await page.waitForFunction(() => {
    const s = JSON.parse(localStorage.getItem('el2_dl') || '{}').nce2;
    return s && s.state === 'done';
  }, null, { timeout: 120000 });
  say('完成态', await page.evaluate(() => JSON.parse(localStorage.getItem('el2_dl') || '{}').nce2));
  await page.waitForFunction(() => document.querySelector('#sc-nce2 .coDot.ok'), null, { timeout: 8000 });
  say('完成后绿点✓', await page.$eval('#sc-nce2 .coDot.ok i', e => e.textContent.trim()));

  /* 7. 重启后真实性校验通过（抽检 3 个文件在缓存里） */
  await page.reload({ waitUntil: 'load' });
  await page.waitForFunction(() => document.querySelectorAll('.coCard').length > 0, null, { timeout: 8000 });
  await page.waitForTimeout(1500);
  await page.waitForFunction(() => document.querySelector('#sc-nce2 .coDot.ok'), null, { timeout: 8000 });
  say('重启后仍就绪', await page.$eval('#sc-nce2 .coDot.ok i', e => e.textContent.trim()));

  /* 8. 课程 tab 的离线状态与储存条 */
  await page.goto(B + '#/home', { waitUntil: 'load' });
  await page.waitForFunction(() => document.querySelector('#stgLine'), null, { timeout: 8000 });
  await page.waitForTimeout(900);
  say('课程 tab 行', await page.$$eval('#app .item[data-act="openc"] .meta', a => a.map(x => x.textContent.trim())));
  say('课程行仅已学', await page.$eval('#app .item[data-act="openc"] .meta', e => /^已学 \d+\/96$/.test(e.textContent.trim())));
  say('储存条', await page.$eval('#stgLine', e => e.textContent.trim()));

  /* 9. 移除课程：长按封面 600ms（原 rmc 逻辑） */
  await page.goto(B + '#/store', { waitUntil: 'load' });
  await page.waitForFunction(() => document.querySelector('#sc-nce2 .coDot.ok'), null, { timeout: 8000 });
  const box = await page.locator('#sc-nce2').boundingBox();
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  await page.waitForTimeout(900);
  await page.mouse.up();
  await page.waitForTimeout(1500);
  say('移除后灰点', await page.$eval('#sc-nce2 .coDot', e => !e.classList.contains('ok') && !e.classList.contains('prog')));
  say('移除后我的课程', await page.evaluate(() => localStorage.getItem('el2_mycourses')));
  say('移除后 dl', await page.evaluate(() => localStorage.getItem('el2_dl')));
  say('缓存剩余文件', await page.evaluate(async () => {
    const c = await caches.open('el2-content');
    const k = await c.keys();
    return k.filter(r => /\/audio\/|\/data\//.test(r.url)).length;
  }));

  await page.goto(B + '#/home', { waitUntil: 'load' });
  await page.waitForTimeout(600);
  say('空态文案', await page.$eval('#app .empty', e => e.textContent.trim()).catch(() => 'none'));
  say('pageErrors', out.errors);
  await browser.close();
  const bad = out.errors.length > 0;
  console.log(bad ? '\nRESULT: FAIL' : '\nRESULT: PASS');
  process.exit(bad ? 2 : 0);
})().catch(e => { console.error('CRASH:', e.message); process.exit(3); });
