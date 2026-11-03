/* NCE2 Loop Service Worker
   缓存分两层：
     el2-shell-vN —— 外壳（HTML/图标/清单），随版本号更换，旧版自动清理
     el2-content  —— 全部课程数据与音频，跨版本永久保留（课程下载/移除都作用在这一层）
   策略：页面/catalog 网络优先（保更新）；data/*.json 缓存优先+后台更新；音频图片缓存优先 */
const VER = 'el2-shell-v3';
const CONTENT = 'el2-content';
const CORE = ['./', './index.html', './login.html', './manifest.json', './catalog.json',
  './apple-touch-icon.png', './icon-192.png', './icon-512.png',
  './covers/nce1_s.jpg', './covers/nce2_s.jpg'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(VER).then(c => c.addAll(CORE)).then(() => self.skipWaiting()));
});
/* 旧版把离线包写在 el2-pwa-vN 里；升级时先搬进 el2-content，避免老用户白下 78MB */
async function migrateLegacy() {
  const ks = await caches.keys();
  const olds = ks.filter(k => /^el2-pwa-v/.test(k));
  if (!olds.length) return;
  const dst = await caches.open(CONTENT);
  for (const k of olds) {
    const src = await caches.open(k);
    const reqs = await src.keys();
    for (const r of reqs) {
      const p = new URL(r.url).pathname;
      if (!/\/(audio|data)\//.test(p)) continue;
      if (await dst.match(r)) continue;
      const m = await src.match(r);
      if (m) await dst.put(r, m);
    }
    await caches.delete(k);
  }
}
self.addEventListener('activate', e => {
  e.waitUntil(
    migrateLegacy()
      .then(() => caches.keys())
      .then(ks => Promise.all(
        /* 只清理旧外壳，绝不碰 el2-content（课程离线包） */
        ks.filter(k => /^el2-(pwa|shell)-/.test(k) && k !== VER).map(k => caches.delete(k))
      ))
    /* 不调用 clients.claim()：避免接管竞态中断在途 fetch（触发 router 数据加载失败） */
  );
});
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const u = new URL(e.request.url);
  if (u.hostname.includes('supabase')) return;                 // API/鉴权永远直连

  const isAudioOrImg = /\.(mp3|png|jpg|jpeg|svg|webp)$/i.test(u.pathname);
  const isData = /\/data\/.*\.json$/i.test(u.pathname);

  if (isAudioOrImg) {                                          // 音频/图片：缓存优先
    e.respondWith(caches.match(e.request).then(m => m || fetch(e.request).then(r => {
      if (r.ok) { const cp = r.clone(); caches.open(CONTENT).then(c => c.put(e.request, cp)); }
      return r;
    })));
    return;
  }
  if (isData) {                                                // 课文数据：先用缓存，后台静默更新
    e.respondWith(caches.match(e.request).then(m => {
      const net = fetch(e.request).then(r => {
        if (r.ok) { const cp = r.clone(); caches.open(CONTENT).then(c => c.put(e.request, cp)); }
        return r;
      }).catch(() => m);
      return m || net;
    }));
    return;
  }
  e.respondWith(                                               // 页面/清单：网络优先
    fetch(e.request).then(r => {
      if (r.ok) { const cp = r.clone(); caches.open(VER).then(c => c.put(e.request, cp)); }
      return r;
    }).catch(() => caches.match(e.request).then(m => m || caches.match('./')))
  );
});
