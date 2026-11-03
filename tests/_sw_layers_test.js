/* SW 缓存分层探针
   ① 旧 el2-pwa-v2 里的离线包被迁移进 el2-content（老用户不白下一遍）
   ② 外壳 el2-shell-v3 与内容 el2-content 分仓
   ③ 课文数据由 SW 落内容仓
   ④ 断网仍能进课程 */
const { chromium } = require('playwright');
const B = 'http://127.0.0.1:8099/';
(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(String(e).slice(0, 160)));

  await page.goto(B, { waitUntil: 'load' });
  await page.waitForTimeout(1200);

  /* 造一个「老版本用户」：旧缓存里有离线包，localStorage 有 el2_offline 标记 */
  await page.evaluate(async () => {
    const regs = await navigator.serviceWorker.getRegistrations();
    for (const r of regs) await r.unregister();
    const ks = await caches.keys();
    for (const k of ks) await caches.delete(k);
    const old = await caches.open('el2-pwa-v2');
    await old.put('audio/L99.mp3', new Response('FAKE-AUDIO'));
    await old.put('data/L99.json', new Response('FAKE-DATA'));
    localStorage.setItem('el2_offline', JSON.stringify({ at: Date.now() }));
    localStorage.removeItem('el2_dl');
  });

  await page.reload({ waitUntil: 'load' });
  await page.waitForTimeout(3000);
  const r1 = await page.evaluate(async () => {
    const ks = await caches.keys();
    const c = await caches.open('el2-content');
    const moved = (await c.keys()).filter(x => /L99/.test(x.url)).length;
    return { keys: ks, moved, oldGone: !ks.includes('el2-pwa-v2') };
  });
  console.log('迁移:', JSON.stringify(r1));

  const r2 = await page.evaluate(() => {
    const m = JSON.parse(localStorage.getItem('el2_dl') || '{}');
    return { nce2: m.nce2, my: localStorage.getItem('el2_mycourses') };
  });
  console.log('标记迁移:', JSON.stringify(r2));

  await page.reload({ waitUntil: 'load' });                 /* 这次由 SW 接管 */
  await page.goto(B + '#/lesson/1', { waitUntil: 'load' });
  await page.waitForFunction(() => document.querySelectorAll('.sent').length > 0, null, { timeout: 20000 });
  await page.waitForTimeout(4000);
  const r3 = await page.evaluate(async () => {
    const c = await caches.open('el2-content');
    const k = await c.keys();
    return { audio: k.filter(x => /\/audio\//.test(x.url)).length, data: k.filter(x => /\/data\//.test(x.url)).length, ctl: !!navigator.serviceWorker.controller };
  });
  console.log('内容仓:', JSON.stringify(r3));

  await ctx.setOffline(true);
  await page.reload({ waitUntil: 'load' });
  const r4 = await page.evaluate(() => ({ h1: (document.querySelector('#app h1') || {}).textContent || '', sent: document.querySelectorAll('.sent').length })).catch(() => ({ err: 1 }));
  console.log('离线:', JSON.stringify(r4));
  await ctx.setOffline(false);
  console.log('pageErrors:', JSON.stringify(errs));

  await browser.close();
  const ok = r1.oldGone && r1.moved === 2 && r1.keys.includes('el2-shell-v3') && r1.keys.includes('el2-content')
    && r2.nce2 && r2.nce2.state !== 'done'   /* 只有 2 个抽样文件命中 → 必须降级为未就绪，绝不假报 */
    && r3.data > 0 && r4.sent > 0 && errs.length === 0;
  console.log(ok ? 'RESULT: PASS' : 'RESULT: FAIL');
  process.exit(ok ? 0 : 2);
})().catch(e => { console.error('CRASH:', e.message); process.exit(3); });
