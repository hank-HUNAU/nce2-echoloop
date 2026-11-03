/* IA 修正回归（评估清单 #1/#3/#6/#9）
   ① 一级页改名：课程中心 → 我的课程
   ② 继续目标按「最近在学」排序（非添加顺序）
   ③ 下载失败态可见：课程库封面红环 + 我的页「下载失败·重试」
   ④ 添加引导 toast（点封面/课程码 后出现） */
const { chromium } = require('playwright');
const B = 'http://127.0.0.1:8099/index.html';
const R = {};
function say(k, v) { R[k] = v; console.log(k + ': ' + JSON.stringify(v)); }

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  const ctx = await browser.newContext({ viewport: { width: 768, height: 1024 }, hasTouch: true });
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(String(e).slice(0, 160)));
  page.on('dialog', d => d.accept());

  await page.goto(B + '#/home', { waitUntil: 'load' });
  await page.evaluate(() => {
    localStorage.clear();
    localStorage.setItem('el2_mycourses', JSON.stringify(['nce2', 'nce1']));
    localStorage.setItem('el2_progress', JSON.stringify({ _v: 3, courses: {
      nce2: { 1: { firstLearnAt: Date.now() - 2 * 36e5, reviews: 1, stage: 1, si: 0 } },
      nce1: { 1: { firstLearnAt: Date.now() - 36e5, reviews: 0, stage: 0, si: 0 } }
    } }));
  });
  await page.reload({ waitUntil: 'load' });
  await page.waitForTimeout(1000);

  /* ① h1 改名 */
  say('h1', await page.$eval('#app h1', e => e.textContent.trim()));

  /* ② 继续目标 = 最近在学（nce1 更新） */
  say('继续目标课', await page.$eval('#app .sec .item .en', e => e.textContent.trim()));

  /* ③ 失败态：课程库红环 + 我的页重试 */
  await page.evaluate(() => {
    localStorage.setItem('el2_dl', JSON.stringify({ nce2: { done: 5, total: 192, state: 'fail' } }));
    location.hash = '#/store';
  });
  await page.waitForTimeout(1000);
  say('封面红环', await page.$eval('#sc-nce2 .cover.fail .pring', e => !!e));
  say('失败标记', await page.$eval('#sc-nce2 .ppct.rd', e => e.textContent.trim()));
  await page.evaluate(() => { location.hash = '#/me'; });
  await page.waitForTimeout(800);
  say('我的页失败文案', await page.$eval('#ol-nce2 .meta', e => e.textContent.trim()));
  say('重试按钮', await page.$eval('#ol-nce2 [data-act="dlc"]', e => e.textContent.trim()));

  /* ④ toast：未添加 → 点封面添加即出提示 */
  await page.evaluate(() => {
    localStorage.setItem('el2_mycourses', JSON.stringify(['nce1']));
    localStorage.setItem('el2_dl', JSON.stringify({ nce1: { done: 288, total: 288, state: 'pause' } }));
    location.hash = '#/store';
  });
  await page.waitForTimeout(900);
  await page.click('#sc-nce2');
  await page.waitForTimeout(400);
  say('添加 toast', await page.evaluate(() => {
    const t = document.getElementById('el2toast');
    return t ? { on: t.classList.contains('on'), text: t.textContent } : null;
  }));

  say('pageErrors', errs);
  await browser.close();
  const ok = R['h1'] === '我的课程'
    && /新概念英语 1/.test(R['继续目标课'])
    && R['封面红环'] === true && R['失败标记'] === '!'
    && /下载失败/.test(R['我的页失败文案']) && R['重试按钮'] === '重试'
    && R['添加 toast'] && R['添加 toast'].on === true && /已加入/.test(R['添加 toast'].text)
    && errs.length === 0;
  console.log(ok ? '\nRESULT: PASS' : '\nRESULT: FAIL');
  process.exit(ok ? 0 : 2);
})().catch(e => { console.error('CRASH:', e.message); process.exit(3); });
