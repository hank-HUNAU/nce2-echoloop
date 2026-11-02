const { chromium } = require('playwright');
const BASE='http://127.0.0.1:8126/index.html';
async function gotoStage(page, stage){
  await page.goto(BASE+'#/home', { waitUntil: 'load' });
  await page.evaluate(st => {
    const prog = JSON.parse(localStorage.getItem('el2_progress')||'{}');
    prog['1'] = Object.assign({stage:0,si:0,listened:{},shadow:{},hard:[],firstLearnAt:Date.now(),reviews:0,lastReviewAt:0,blindDone:false,retellDone:false}, prog['1'], {stage:st});
    localStorage.setItem('el2_progress', JSON.stringify(prog));
  }, stage);
  await page.reload({ waitUntil: 'load' });
  await page.goto(BASE+'#/lesson/1', { waitUntil: 'load' });
  await page.waitForFunction(st => {
    const st0 = document.querySelector('.stepper .st.on');
    return document.querySelectorAll('.sent').length > 0 || document.getElementById('shTxt') || document.body.innerText.includes('段落复述');
  }, stage, { timeout: 20000 });
  await page.waitForTimeout(400);
}
(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  const ctx = await browser.newContext({ viewport: { width: 834, height: 1194 }, hasTouch: true });
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(String(e).slice(0,150)));
  // ① 盲听：无逐句钮
  await gotoStage(page, 0);
  const r3 = await page.evaluate(() => ({ blindPlayBtns: document.querySelectorAll('#blindBox .play').length }));
  console.log('[盲听]', JSON.stringify(r3));
  // ② 跟读：默认模糊 + 揭示切换
  await gotoStage(page, 1);
  const r4a = await page.evaluate(() => document.getElementById('shTxt').className.includes('blurred'));
  await page.evaluate(() => { document.querySelector('[data-act="revsh"]').click(); });
  await page.waitForTimeout(300);
  const r4b = await page.evaluate(() => !document.getElementById('shTxt').className.includes('blurred'));
  console.log('[跟读盲跟]', JSON.stringify({ defaultBlur: r4a, revealWorks: r4b }));
  // ③ 精听：无播放键/无标注/行点击→播放+译文
  await gotoStage(page, 2);
  const r1 = await page.evaluate(() => ({
    playBtns: document.querySelectorAll('.sent .play').length,
    noChunks: !document.getElementById('app').innerHTML.includes('class="ch"'),
    noPat: !document.getElementById('app').innerHTML.includes('class="tag"'),
    rowsClickable: !!document.querySelector('.sent[data-act="plays"]'),
    zhHidden: document.getElementById('zh0')?.style.display === 'none'
  }));
  await page.click('.sent[data-act="plays"]');
  await page.waitForTimeout(1200);
  const r2 = await page.evaluate(() => ({
    zhShown: document.getElementById('zh0').style.display === 'block',
    playing: !document.getElementById('au').paused
  }));
  console.log('[精听]', JSON.stringify(r1), '[行点击]', JSON.stringify(r2));
  // ④ 复述：提示档
  await gotoStage(page, 3);
  await page.evaluate(() => { document.querySelector('[data-act="retellhint"]').click(); });
  await page.waitForTimeout(300);
  const r5 = await page.evaluate(() => document.body.innerText.includes('…'));
  console.log('[复述提示]', JSON.stringify({ cueShown: r5 }));
  // ⑤ 闪卡 SRS
  await page.evaluate(() => localStorage.setItem('el2_hard', JSON.stringify([
    {en:'Short test one.',zh:'短句一',no:1,i:0},
    {en:'Long test sentence two.',zh:'长句二',no:1,i:1}
  ])));
  await page.goto(BASE+'#/cards', { waitUntil: 'load' });
  await page.waitForFunction(() => document.querySelectorAll('.card').length >= 2, null, { timeout: 15000 });
  const c1 = await page.evaluate(() => ({ n: document.querySelectorAll('.card').length, dueN: document.body.innerText.match(/今日待复习 (\d+) 张/)?.[1] }));
  await page.evaluate(() => { document.querySelectorAll('.card')[0].click(); });
  await page.evaluate(() => { document.querySelectorAll('.card')[0].querySelector('[data-act="cardno"]').click(); });
  const c2 = await page.evaluate(() => {
    const hard = JSON.parse(localStorage.getItem('el2_hard'));
    return { due0h: Math.round((hard[0].due - Date.now()) / 36e5), faded: document.querySelectorAll('.card')[0].style.opacity === '0.4' };
  });
  console.log('[闪卡SRS]', JSON.stringify({ ...c1, ratedDueH: c2.due0h, faded: c2.faded }));
  await browser.close();
  const pass = r3.blindPlayBtns===0 && r4a && r4b && r1.playBtns===0 && r1.noChunks && r1.noPat && r1.rowsClickable && r2.zhShown && r2.playing && r5 && c1.n>=2 && c2.due0h===12 && c2.faded && errs.length===0;
  console.log('[errs]', errs.length, '| 总判定:', pass?'PASS':'FAIL');
  process.exit(pass?0:1);
})().catch(e => { console.error('CRASH:', e.message); process.exit(2); });
