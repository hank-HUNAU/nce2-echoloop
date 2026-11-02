/* NCE2 Loop 播放功能模拟测试：3 轮 精听逐句 + 整段播放，断言 src/网络/时间推进/错误事件 */
const { chromium } = require('playwright');

const SITE = 'https://hank-hunau.github.io/nce2-echoloop/';
const ROUNDS = 3;

(async () => {
  const browser = await chromium.launch({
    headless: true, channel: 'msedge',
    proxy: { server: 'http://127.0.0.1:49296' },
    args: ['--autoplay-policy=no-user-gesture-required', '--mute-audio'],
  });
  const page = await browser.newPage({ viewport: { width: 900, height: 800 } });

  const audioResponses = [];
  page.on('response', r => {
    if (r.url().includes('.mp3')) audioResponses.push({ url: r.url(), status: r.status() });
  });
  const pageErrors = [];
  page.on('pageerror', e => pageErrors.push(String(e)));
  const consoleErrors = [];
  const failedReq = [];
  page.on('requestfailed', r => failedReq.push(r.url().slice(0, 90) + ' :: ' + (r.failure() || {}).errorText));
  page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text()); });

  console.log('== 打开站点 ==');
  console.log('导航前: 打印调试模式');
  await page.goto(SITE + '#/lesson/1', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForFunction(() => typeof CUR !== 'undefined' && CUR.data && CUR.data.sentences && CUR.data.sentences.length > 0, null, { timeout: 60000 });
  const info = await page.evaluate(() => ({ title: CUR.data.title, audio: CUR.data.audio, n: CUR.data.sentences.length, src: document.getElementById('au').src }));
  console.log('课程:', JSON.stringify(info));
  if (failedReq.length) console.log('失败请求:', failedReq.slice(0, 5));

  const results = [];
  for (let round = 1; round <= ROUNDS; round++) {
    console.log(`\n== 第 ${round} 轮 ==`);

    // --- A. 精听逐句：顺序播前 3 句 ---
    const sent = await page.evaluate(() => CUR.data.sentences.filter(s => !s.meta).slice(0, 3).map(s => ({ i: +s.i, t: +s.t, t2: +s.t2, en: s.en.slice(0, 40) })));
    for (const s of sent) {
      const r = await page.evaluate(async (s) => {
        const AU = document.getElementById('au');
        let err = null;
        const onErr = () => { err = AU.error ? (AU.error.code + '/' + AU.error.message) : 'unknown'; };
        AU.addEventListener('error', onErr);
        playSeg(s.t, s.t2);
        const t0 = Date.now();
        while (Date.now() - t0 < 45000) {
          if (err) break;
          if (AU.readyState >= 3 || AU.currentTime > 0) {
            if (AU.paused) break;                       // 播完被 segStop 暂停
            if (AU.currentTime >= s.t2 - 0.15) break;   // 接近句尾
          }
          await new Promise(r => setTimeout(r, 200));
        }
        const out = { src: AU.src.split('/').slice(-2).join('/'), started: AU.currentTime > 0 || AU.readyState >= 2, cur: +AU.currentTime.toFixed(2), paused: AU.paused, err, readyState: AU.readyState };
        AU.pause(); AU.removeEventListener('error', onErr);
        return out;
      }, s);
      const ok = !r.err && r.src === 'audio/L01.mp3' && r.cur >= s.t;
      results.push({ round, kind: `逐句S${s.i}`, ok, ...r, en: s.en });
      console.log(`  [逐句S${s.i}] ${ok ? 'OK' : 'FAIL'} src=${r.src} cur=${r.cur}s paused=${r.paused} ready=${r.readyState} err=${r.err} "${s.en}"`);
      await page.waitForTimeout(300);
    }

    // --- B. 整段播放：播 5 秒观察推进 ---
    const b = await page.evaluate(async () => {
      const AU = document.getElementById('au');
      playAll();
      await new Promise(r => setTimeout(r, 5000));
      const c1 = AU.currentTime;
      await new Promise(r => setTimeout(r, 2000));
      const c2 = AU.currentTime;
      const advancing = c2 > c1;
      AU.pause();
      return { src: AU.src.split('/').slice(-2).join('/'), c1: +c1.toFixed(2), c2: +c2.toFixed(2), advancing };
    });
    results.push({ round, kind: '整段', ok: b.advancing && !b.src.includes('L01') === false && b.src === 'audio/L01.mp3', ...b });
    console.log(`  [整段] ${b.advancing ? 'OK' : 'FAIL'} src=${b.src} ${b.c1}s -> ${b.c2}s (推进 ${(b.c2 - b.c1).toFixed(2)}s)`);

    // --- C. 跟读台录音按钮可用性（不真录，只查权限入口存在）---
    if (round === ROUNDS) {
      const ui = await page.evaluate(() => ({
        hasRecBtn: !!document.querySelector('button'),
        hardCount: (typeof HARD === 'object' && HARD) ? Object.keys(HARD).length : null,
        stats: typeof S === 'object' ? Object.keys(S).length : null,
      }));
      console.log('  [UI] buttons 可交互, state keys:', JSON.stringify(ui));
    }
  }

  // --- 汇总 ---
  const audioOk = audioResponses.length > 0 && audioResponses.every(r => r.status === 200);
  const pass = results.filter(r => r.ok).length;
  console.log('\n===== 汇总 =====');
  console.log(`断言: ${pass}/${results.length} 通过`);
  console.log(`音频网络请求: ${audioResponses.length} 次, 全部 200: ${audioOk}`, JSON.stringify(audioResponses));
  console.log(`页面 JS 错误: ${pageErrors.length}`, pageErrors.slice(0, 3));
  console.log(`控制台错误: ${consoleErrors.length}`, consoleErrors.slice(0, 3));
  console.log('失败请求明细:', failedReq.slice(0, 8));
  const ls = await page.evaluate(() => Object.fromEntries(Object.entries(localStorage).filter(([k]) => k.startsWith('el2_')).map(([k, v]) => [k, v.slice(0, 80)])));
  console.log('localStorage 进度:', JSON.stringify(ls).slice(0, 400));
  await browser.close();
  process.exit(pass === results.length && audioOk ? 0 : 1);
})().catch(e => { console.error('TEST CRASH:', e); process.exit(2); });
