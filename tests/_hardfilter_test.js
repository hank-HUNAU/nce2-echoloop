/* 难句本 / 闪卡：课程标识 + 课程范围（方案 C：跟随 + 状态外显）
   ① 两门课都有难句时出现筛选条（全部 + 每门课，带计数）
   ② 每行/每卡显示课程短名，L5 不再无法区分
   ③ 筛选后列表只剩该课条目
   ④ 筛选态下自评，只改对应那条的 due，另一门课不受影响（精确定位，不靠数组下标）
   ⑤ 筛选态下取消收藏，只删对应那条，两处存储同步
   ⑥ 只有一门课的难句且未筛选时不显示筛选条（不制造无意义控件）
   ⑦ 从某门课程的课程页进来 → 默认选中这门课（范围跟随）
   ⑧ 从课程中心进来 → 默认「全部」
   ⑨ 难句 ↔ 卡片 之间切换 → 沿用当前选择，不打断筛选 */
const { chromium } = require('playwright');
const B = 'http://127.0.0.1:8099/';
const R = {};
function say(k, v) { R[k] = v; console.log(k + ': ' + JSON.stringify(v)); }

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  const ctx = await browser.newContext({ viewport: { width: 768, height: 1024 }, hasTouch: true });
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(String(e).slice(0, 160)));
  page.on('dialog', d => d.accept());

  await page.goto(B, { waitUntil: 'load' });
  await page.evaluate(() => {
    localStorage.clear();
    localStorage.setItem('el2_mycourses', JSON.stringify(['nce2', 'nce1']));
    localStorage.setItem('el2_hard', JSON.stringify([
      { cid: 'nce2', no: 5, i: 2, en: 'Just then, the telephone rang.', zh: '正在这时，电话铃响了。', pat: 'SV', ts: 2 },
      { cid: 'nce1', no: 5, i: 1, en: 'This is my umbrella.', zh: '这是我的伞。', pat: 'SVP', ts: 1 }
    ]));
    localStorage.setItem('el2_progress', JSON.stringify({ _v: 3, courses: { nce2: {}, nce1: {} } }));
  });

  /* ① 难句本筛选条 */
  await page.goto(B + '#/hard', { waitUntil: 'load' });
  await page.waitForTimeout(700);
  say('筛选条', await page.$$eval('.hchip', a => a.map(x => x.textContent.trim())));
  say('难句行数', await page.$$eval('#app .item', a => a.length));
  say('每行课程标识', await page.$$eval('#app .item .zh', a => a.map(x => x.textContent.replace(/\s+/g, ' ').trim())));

  /* ③ 筛选到 N1 */
  await page.click('.hchip[data-v="nce1"]');
  await page.waitForTimeout(400);
  say('筛选 N1 后行数', await page.$$eval('#app .item', a => a.length));
  say('筛选 N1 内容', await page.$eval('#app .item .en', e => e.textContent.trim()));
  say('筛选后范围提示', await page.$$eval('.tip', a => a.some(x => x.textContent.includes('当前只看'))));

  /* ④ 卡片：跨 tab 沿用筛选，且正面显示课程 */
  await page.goto(B + '#/cards', { waitUntil: 'load' });
  await page.waitForTimeout(600);
  say('卡片筛选条', await page.$$eval('.hchip', a => a.length));
  say('卡片数（沿用 N1）', await page.$$eval('.card', a => a.length));
  say('卡片正面', await page.$eval('.card .f', e => e.textContent.replace(/\s+/g, ' ').trim()));

  await page.click('.card');                 /* 先翻面，背面的按钮才可点 */
  await page.waitForTimeout(600);
  await page.click('[data-act="cardok"]');
  await page.waitForTimeout(400);
  const hard1 = await page.evaluate(() => JSON.parse(localStorage.getItem('el2_hard')));
  say('自评后 nce1 有 due', !!(hard1.find(x => x.cid === 'nce1').due));
  say('自评后 nce2 无 due（未被误改）', !(hard1.find(x => x.cid === 'nce2').due));

  /* ⑤ 筛选态下取消收藏 */
  await page.goto(B + '#/hard', { waitUntil: 'load' });
  await page.waitForTimeout(600);
  await page.click('[data-act="unstar"]');
  await page.waitForTimeout(400);
  const hard2 = await page.evaluate(() => JSON.parse(localStorage.getItem('el2_hard')));
  say('取消收藏后剩余', hard2.map(x => x.cid));
  say('空态文案', await page.$eval('#app .empty', e => e.textContent.trim()).catch(() => 'none'));

  /* ⑥ 只剩一门课且未筛选时不显示筛选条 */
  await page.evaluate(() => {
    localStorage.setItem('el2_hard', JSON.stringify([{ cid: 'nce2', no: 5, i: 2, en: 'A', zh: '甲', ts: 1 }]));
  });
  await page.goto(B + '#/home', { waitUntil: 'load' });
  await page.reload({ waitUntil: 'load' });
  await page.evaluate(() => { location.hash = '#/home'; });
  await page.waitForTimeout(300);
  await page.evaluate(() => { location.hash = '#/hard'; });
  await page.waitForTimeout(700);
  say('单课程时筛选条数', await page.$$eval('.hchip', a => a.length));
  say('单课程时仍显示标识', await page.$eval('#app .item .zh', e => e.textContent.replace(/\s+/g, ' ').trim()));

  /* ⑦ 从课程页进入 → 默认跟随该课 */
  await page.evaluate(() => {
    localStorage.setItem('el2_hard', JSON.stringify([
      { cid: 'nce2', no: 5, i: 2, en: 'Just then, the telephone rang.', zh: '正在这时，电话铃响了。', pat: 'SV', ts: 2 },
      { cid: 'nce1', no: 5, i: 1, en: 'This is my umbrella.', zh: '这是我的伞。', pat: 'SVP', ts: 1 }
    ]));
    location.hash = '#/c/nce2';
  });
  await page.waitForTimeout(900);
  say('课程页标题', await page.$eval('#app h1', e => e.textContent.replace(/\s+/g, ' ').trim()));
  await page.click('nav.tabs a[href="#/hard"]');
  await page.waitForTimeout(700);
  say('跟随：选中胶囊', await page.$$eval('.hchip.on', a => a.map(x => x.textContent.trim())));
  say('跟随：行数', await page.$$eval('#app .item', a => a.length));
  say('跟随：内容', await page.$eval('#app .item .en', e => e.textContent.trim()));

  /* ⑨ 切到卡片仍沿用 */
  await page.click('nav.tabs a[href="#/cards"]');
  await page.waitForTimeout(600);
  say('跟随：卡片数', await page.$$eval('.card', a => a.length));
  say('跟随：卡片选中胶囊', await page.$$eval('.hchip.on', a => a.map(x => x.textContent.trim())));

  /* ⑧ 从课程中心进入 → 全部 */
  await page.click('nav.tabs a[href="#/home"]');
  await page.waitForTimeout(700);
  await page.click('nav.tabs a[href="#/hard"]');
  await page.waitForTimeout(700);
  say('课程中心进入：选中胶囊', await page.$$eval('.hchip.on', a => a.map(x => x.textContent.trim())));
  say('课程中心进入：行数', await page.$$eval('#app .item', a => a.length));

  say('pageErrors', errs);
  await browser.close();
  const ok = R['筛选条'].length === 3
    && /N2/.test(R['筛选条'][1]) && /N1/.test(R['筛选条'][2])
    && R['难句行数'] === 2
    && /N1/.test(R['每行课程标识'][1]) && /N2/.test(R['每行课程标识'][0])
    && R['筛选 N1 后行数'] === 1
    && R['筛选后范围提示'] === true
    && R['卡片筛选条'] === 3
    && R['卡片数（沿用 N1）'] === 1
    && /N1/.test(R['卡片正面'])
    && R['自评后 nce1 有 due'] === true && R['自评后 nce2 无 due（未被误改）'] === true
    && R['取消收藏后剩余'].join() === 'nce2'
    && R['单课程时筛选条数'] === 0
    && /N2/.test(R['单课程时仍显示标识'])
    && /新概念英语 2/.test(R['课程页标题'])
    && R['跟随：选中胶囊'].length === 1 && /N2/.test(R['跟随：选中胶囊'][0])
    && R['跟随：行数'] === 1 && /telephone/.test(R['跟随：内容'])
    && R['跟随：卡片数'] === 1 && R['跟随：卡片选中胶囊'].length === 1
    && /全部/.test(R['课程中心进入：选中胶囊'][0])
    && R['课程中心进入：行数'] === 2
    && errs.length === 0;
  console.log(ok ? '\nRESULT: PASS' : '\nRESULT: FAIL');
  process.exit(ok ? 0 : 2);
})().catch(e => { console.error('CRASH:', e.message); process.exit(3); });
