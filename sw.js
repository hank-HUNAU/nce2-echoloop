/* NCE2 Loop Service Worker：离线学习 + PWA 可安装
   策略：HTML/JSON 网络优先（保更新），音频/图片缓存优先（边听边存）；Supabase API 不缓存 */
const VER = 'el2-pwa-v1';
const CORE = ['./', './index.html', './login.html', './manifest.json', './apple-touch-icon.png', './icon-192.png', './icon-512.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(VER).then(c => c.addAll(CORE)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(ks => Promise.all(ks.filter(k => k !== VER).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const u = new URL(e.request.url);
  if (u.hostname.includes('supabase')) return;             // API/鉴权永远直连
  if (/\.(mp3|png|jpg|jpeg|svg|webp)$/i.test(u.pathname)) { // 媒体：缓存优先
    e.respondWith(
      caches.open(VER).then(c => c.match(e.request).then(m =>
        m || fetch(e.request).then(r => {
          if (r.ok) c.put(e.request, r.clone());
          return r;
        })
      ))
    );
  } else {                                                  // 页面/数据：网络优先
    e.respondWith(
      fetch(e.request).then(r => {
        if (r.ok) { const cp = r.clone(); caches.open(VER).then(c => c.put(e.request, cp)); }
        return r;
      }).catch(() => caches.match(e.request).then(m => m || caches.match('./')))
    );
  }
});
