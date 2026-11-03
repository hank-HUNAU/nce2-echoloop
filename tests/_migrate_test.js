/* 进度存储 v3 迁移回归：旧扁平结构 → 按课程分组
   ① 旧格式（课号做键）读入后自动包成 courses.nce2，键与内容不丢
   ② 难句本条目补 cid
   ③ v2 顺序迁移对老数据仍然生效（stage 0↔2 互换只做一次）
   ④ 已学/到期统计口径正确，且不把已移除课程的进度算进来
   ⑤ 再次 reload 不重复迁移（幂等） */
const { chromium } = require('playwright');
const B = 'http://127.0.0.1:8099/';
const T = {};
function say(k, v) { T[k] = v; console.log(k + ': ' + JSON.stringify(v)); }

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  const ctx = await browser.newContext({ viewport: { width: 768, height: 1024 }, hasTouch: true });
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(String(e).slice(0, 180)));
  page.on('dialog', d => d.accept());

  await page.goto(B, { waitUntil: 'load' });
  /* 造一份「旧版本用户」的数据：扁平结构 + 无 cid 的难句 + 未跑过 v2 迁移 */
  await page.evaluate(() => {
    localStorage.clear();
    const rec = (stage, si, extra) => Object.assign({
      stage, si, listened: { 0: 1 }, shadow: { 0: 4 }, hard: [], firstLearnAt: Date.now() - 2 * 864e5,
      reviews: 1, lastReviewAt: 0, blindDone: true, retellDone: false
    }, extra || {});
    localStorage.setItem('el2_progress', JSON.stringify({ '1': rec(0, 3), '5': rec(2, 1), '9': rec(3, 0, { firstLearnAt: 0 }) }));
    localStorage.setItem('el2_hard', JSON.stringify([{ no: 5, i: 2, en: 'Just then, the telephone rang.', zh: '正在这时，电话铃响了。', pat: 'SV', ts: 1 }]));
    localStorage.removeItem('el2_dl'); localStorage.removeItem('el2_mycourses');
  });
  await page.reload({ waitUntil: 'load' });
  await page.waitForFunction(() => document.querySelector('#app h1'), null, { timeout: 15000 });
  await page.waitForTimeout(800);

  /* ① 结构迁移 + 键保留 */
  const st = await page.evaluate(() => JSON.parse(localStorage.getItem('el2_progress')));
  say('顶层版本', st._v);
  say('课程键', Object.keys(st.courses || {}));
  say('nce2 课号', Object.keys((st.courses || {}).nce2 || {}));
  say('句1 stage（v2 迁移后应为 2）', ((st.courses || {}).nce2 || {})['1'].stage);
  say('句5 stage（v2 迁移后应为 0）', ((st.courses || {}).nce2 || {})['5'].stage);
  say('listened/shadow 保留', JSON.stringify([((st.courses || {}).nce2 || {})['1'].listened, ((st.courses || {}).nce2 || {})['1'].shadow]));

  /* ② 难句本补 cid */
  say('难句 cid', await page.evaluate(() => (JSON.parse(localStorage.getItem('el2_hard') || '[]')[0] || {}).cid));

  /* ③ 首页统计口径：只算 firstLearnAt 的两课（句9 未学） */
  say('我的课程卡', await page.$eval('#app .item[data-act="openc"] .meta', e => e.textContent.trim()));
  const dueMeta = await page.evaluate(() => [...document.querySelectorAll('#app .sec')[0].querySelectorAll('.item')].map(x => x.textContent.replace(/\s+/g, ' ').trim()));
  say('今日任务', dueMeta);

  /* ④ 已移除课程的进度不进统计 */
  await page.evaluate(() => {
    const st = JSON.parse(localStorage.getItem('el2_progress'));
    st.courses.nce1 = { '3': { stage: 3, si: 0, listened: {}, shadow: {}, hard: [], firstLearnAt: Date.now(), reviews: 0, lastReviewAt: 0, blindDone: false, retellDone: false } };
    localStorage.setItem('el2_progress', JSON.stringify(st));
    localStorage.setItem('el2_mycourses', JSON.stringify(['nce2']));   /* 只保留 nce2 */
  });
  await page.reload({ waitUntil: 'load' });
  await page.waitForTimeout(700);
  say('nce1 已存在于存储', await page.evaluate(() => !!JSON.parse(localStorage.getItem('el2_progress')).courses.nce1));
  say('首页已学（应仍为 2，不含 nce1）', await page.$eval('#app .item[data-act="openc"] .meta', e => e.textContent.trim()));
  await page.goto(B + '#/stats', { waitUntil: 'load' });
  await page.waitForTimeout(600);
  say('统计页', await page.$eval('#app .tip', e => e.textContent.trim()));

  /* ⑤ 幂等：再 reload 一次，结构不变、内容不变 */
  const before = await page.evaluate(() => localStorage.getItem('el2_progress'));
  await page.reload({ waitUntil: 'load' });
  await page.waitForTimeout(700);
  const after = await page.evaluate(() => localStorage.getItem('el2_progress'));
  say('幂等', before === after);

  /* ⑥ 难句本仍可用（含重练链接带课程） */
  await page.goto(B + '#/hard', { waitUntil: 'load' });
  await page.waitForTimeout(500);
  say('难句本行数', await page.$$eval('#app .item', a => a.length));
  say('重练按钮 c', await page.$eval('[data-act="goSent"]', e => e.dataset.c).catch(() => 'none'));

  say('pageErrors', errs);
  await browser.close();
  const ok = st._v === 3
    && Object.keys(st.courses).join() === 'nce2'
    && Object.keys(st.courses.nce2).join() === '1,5,9'
    && st.courses.nce2['1'].stage === 2 && st.courses.nce2['5'].stage === 0
    && T['难句 cid'] === 'nce2'
    && /已学 2\/96/.test(T['首页已学（应仍为 2，不含 nce1）'])
    && T['幂等'] === true
    && T['重练按钮 c'] === 'nce2'
    && errs.length === 0;
  console.log(ok ? '\nRESULT: PASS' : '\nRESULT: FAIL');
  process.exit(ok ? 0 : 2);
})().catch(e => { console.error('CRASH:', e.message); process.exit(3); });
