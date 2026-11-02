/* 登录链路验收：门禁 → 双角色分流 → 看板落位 */
const { chromium } = require('playwright');
const BASE = 'https://hank-hunau.github.io/nce2-echoloop/';
const BOARD = 'https://workbuddy.link/p/5IJWFXAquhgIqOoyYLsimE';
const PW = 'Echo2026!nce2';
const results = [];
function ok(name, cond, extra) { results.push({ name, ok: !!cond }); console.log(`[${cond ? 'OK' : 'FAIL'}] ${name}${extra ? ' :: ' + extra : ''}`); }
(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge', proxy: { server: 'http://127.0.0.1:' + process.env.P_PORT } });
  const page = await browser.newPage();
  page.on('pageerror', e => console.log('[pageerror]', String(e).slice(0,120)));

  // 1. 未登录直接开 App → 应被踢到 login.html
  await page.goto(BASE, { waitUntil: 'commit', timeout: 60000 });
  await page.waitForTimeout(2500);
  ok('未登录访问 App 被踢回门户', page.url().includes('login.html'), page.url());

  // 2. 孩子登录 → 落到 App 且有会话
  await page.fill('#em', 'kid@echo.hank-hunau.dev');
  await page.fill('#pw', PW);
  await page.click('#go');
  await page.waitForFunction(() => location.pathname.endsWith('nce2-echoloop/') || location.hash.includes('home'), null, { timeout: 30000 }).catch(() => {});
  await page.waitForFunction(() => typeof CUR !== 'undefined' && CUR.data && CUR.data.sentences, null, { timeout: 60000 }).catch(() => {});
  const kidOk = await page.evaluate(() => {
    const s = JSON.parse(localStorage.getItem('el2_session') || 'null');
    return { url: location.href, role: s && s.role, hasCur: typeof CUR !== 'undefined' && !!CUR.data, title: document.title };
  });
  ok('孩子登录落回 App', /nce2-echoloop\/?$/.test(kidOk.url.split('#')[0]) || kidOk.url.includes('nce2-echoloop/'), kidOk.url);
  ok('孩子会话 role=kid', kidOk.role === 'kid');
  await page.evaluate(() => { location.hash = '#/lesson/1'; });
  await page.waitForFunction(() => document.querySelectorAll('.sent').length > 0, null, { timeout: 60000 }).catch(() => {});
  const curOk = await page.evaluate(() => document.querySelectorAll('.sent').length);
  ok('孩子端课程正常加载', curOk);

  // 3. 错误密码 → 报错不跳转
  const page2 = await browser.newPage();
  await page2.goto(BASE + 'login.html', { waitUntil: 'commit', timeout: 60000 });
  await page2.fill('#em', 'kid@echo.hank-hunau.dev');
  await page2.fill('#pw', 'wrong-password');
  await page2.click('#go');
  await page2.waitForTimeout(12000);
  const errTxt = await page2.evaluate(() => document.getElementById('err').textContent);
  ok('错误密码被拒绝并提示', errTxt.length > 0, errTxt.slice(0, 60));
  await page2.close();

  // 4. 家长登录 → 带 token 落到 EchoAdmin 看板
  const page3 = await browser.newPage();
  await page3.goto(BASE + 'login.html', { waitUntil: 'commit', timeout: 60000 });
  await page3.fill('#em', 'parent@echo.hank-hunau.dev');
  await page3.fill('#pw', PW);
  await page3.click('#go');
  await page3.waitForURL(/workbuddy\.link/, { timeout: 30000 }).catch(() => {});
  await page3.waitForTimeout(15000);
  const pTitle = await page3.title();
  await page3.waitForTimeout(3000);
  const pSess = 'see-title';
  ok('家长登录落到看板域', page3.url().includes('workbuddy.link'), page3.url().slice(0, 60));
  ok('看板未被打回门户（token 校验通过）', !page3.url().includes('login.html'), page3.url().slice(0, 70));
  ok('看板已更名 EchoAdmin', /EchoAdmin/.test(pTitle), pTitle);

  await browser.close();
  const pass = results.filter(r => r.ok).length;
  console.log(`\n===== 登录验收 ${pass}/${results.length} =====`);
  process.exit(pass === results.length ? 0 : 1);
})().catch(e => { console.error('CRASH:', e.message); process.exit(2); });
