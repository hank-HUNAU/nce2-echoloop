/* 「我的」页（原「统计」+「登录」合并）回归
   ① 底部只剩 4 个 tab，第 4 个恒为「我的」（未登录时不再变「登录」）
   ② 未登录进入 #/me：显示页内登录卡，点「登录」弹出登录弹窗（不再跳走）
   ③ 已登录进入 #/me：账号邮箱 + 学习概览环图 + 离线包行 + 数据管理，tab 高亮
   ④ 点「退出」→ 不刷新页面，当场变回登录卡（el2AuthChanged 生效）
   ⑤ 旧地址 #/stats 仍能打开同一页（兼容书签） */
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

  /* ① 未登录：tab 结构 */
  await page.goto(B + '#/home', { waitUntil: 'load' });
  await page.evaluate(() => localStorage.clear());
  await page.goto(B + '#/me', { waitUntil: 'load' });
  await page.waitForTimeout(800);
  say('tab 文案', await page.$$eval('nav.tabs a', a => a.map(x => x.textContent.trim())));
  say('tab 链接', await page.$$eval('nav.tabs a', a => a.map(x => x.getAttribute('href'))));

  /* ② 未登录：页内登录卡 + 弹窗 */
  say('未登录 h1', await page.$eval('#app h1', e => e.textContent.trim()));
  say('有登录按钮', await page.$$eval('[data-act="melogin"]', a => a.length));
  say('未登录也有数据管理', await page.evaluate(() => document.body.innerText.includes('导出 JSON 备份')));
  await page.click('[data-act="melogin"]');
  await page.waitForTimeout(400);
  say('弹窗已开', await page.evaluate(() => {
    const m = document.getElementById('loginMask');
    return !!m && getComputedStyle(m).display !== 'none';
  }));
  await page.click('#lmx');
  await page.waitForTimeout(200);
  say('弹窗可关', await page.evaluate(() => getComputedStyle(document.getElementById('loginMask')).display === 'none'));

  /* ③ 已登录：伪造会话（不依赖网络） */
  await page.evaluate(() => {
    localStorage.setItem('el2_session', JSON.stringify({
      access_token: 'fake', refresh_token: 'fake', expires_at: Date.now() + 3600e3,
      role: 'kid', family_code: 'ECHO-HANK-01', uid: 'u-test', email: 'kid@example.com'
    }));
    localStorage.setItem('el2_mycourses', JSON.stringify(['nce2']));
    localStorage.setItem('el2_dl', JSON.stringify({ nce2: { done: 10, total: 10, state: 'done' } }));
  });
  await page.reload({ waitUntil: 'load' });
  await page.waitForTimeout(900);
  say('已登录 tab 高亮', await page.$$eval('nav.tabs a[href="#/me"]', a => a[0] && a[0].className));
  say('账号邮箱', await page.evaluate(() => document.body.innerText.includes('kid@example.com')));
  say('环图数', await page.$$eval('svg.ring', a => a.length));
  say('概览行', await page.evaluate(() => /已学 \d+\/\d+ · 通关 \d+\/\d+/.test(document.body.innerText)));
  say('离线包行', await page.$$eval('[id^="ol-"]', a => a.map(x => x.id)));
  /* 假 done 但缓存里没文件 → verifyDl 必须降级为「未下载」（界面不假报就绪） */
  say('离线未下载（不假报就绪）', await page.evaluate(() => document.body.innerText.includes('未下载')));
  say('离线不假报就绪', await page.evaluate(() => !document.body.innerText.includes('✓ 已就绪')));
  say('有退出按钮', await page.$$eval('#meOut2', a => a.length));
  say('数据管理 no-print', await page.evaluate(() => {
    const s = [...document.querySelectorAll('.sec')].find(x => x.textContent.includes('导出 JSON 备份'));
    return !!s && s.classList.contains('no-print');
  }));

  /* ④ 退出：不刷新页面，当场变回登录卡 */
  await page.click('#meOut2');
  await page.waitForTimeout(600);
  say('退出后仍有页内登录按钮', await page.$$eval('[data-act="melogin"]', a => a.length));
  say('退出后 EL2SESS', await page.evaluate(() => !!window.EL2SESS));
  say('退出后 tab 仍叫我的', await page.$$eval('nav.tabs a', a => a[a.length - 1].textContent.trim()));

  /* ⑤ 旧地址兼容 */
  await page.evaluate(() => { location.hash = '#/stats'; });
  await page.waitForTimeout(600);
  say('#/stats 打开同一页', await page.$eval('#app h1', e => e.textContent.trim()));

  say('pageErrors', errs);
  await browser.close();
  const ok = R['tab 文案'].join(',') === '课程,难句,卡片,我的'
    && R['tab 链接'][3] === '#/me'
    && R['未登录 h1'] === '我的'
    && R['有登录按钮'] === 1
    && R['未登录也有数据管理'] === true
    && R['弹窗已开'] === true && R['弹窗可关'] === true
    && R['已登录 tab 高亮'] === 'on'
    && R['账号邮箱'] === true
    && R['环图数'] === 3
    && R['概览行'] === true
    && R['离线包行'].join() === 'ol-nce2'
    && R['离线未下载（不假报就绪）'] === true
    && R['离线不假报就绪'] === true
    && R['有退出按钮'] === 1
    && R['数据管理 no-print'] === true
    && R['退出后仍有页内登录按钮'] === 1
    && R['退出后 EL2SESS'] === false
    && R['退出后 tab 仍叫我的'] === '我的'
    && R['#/stats 打开同一页'] === '我的'
    && errs.length === 0;
  console.log(ok ? '\nRESULT: PASS' : '\nRESULT: FAIL');
  process.exit(ok ? 0 : 2);
})().catch(e => { console.error('CRASH:', e.message); process.exit(3); });
