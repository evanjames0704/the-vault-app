// THE VAULT keeps a local shell for offline use.
const CACHE = 'the-vault-shell-v25';
const SHELL = ['./', './index.html', './manifest.webmanifest', './icon.svg', './icon-192.png', './icon-512.png', './apple-touch-icon.png'];
const paths = new Set(SHELL.map(path => new URL(path, self.registration.scope).pathname));
const home = new URL('./', self.registration.scope).href;

self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    await cache.addAll(SHELL.map(path => new Request(new URL(path, home), {cache: 'reload'})));
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(key => key !== CACHE &&
      (key.startsWith('vault-shell-') || key.startsWith('the-vault-'))).map(key => caches.delete(key)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin) return;
  const shell = paths.has(url.pathname);
  const entry = url.pathname === new URL(home).pathname || url.pathname === new URL('./index.html', home).pathname;
  const key = entry ? home : url.origin + url.pathname;
  if (!shell && url.pathname !== new URL('./lego-catalog.json', home).pathname) return;

  event.respondWith((async () => {
    let response;
    try {
      response = await fetch(request, entry ? {cache: 'reload'} : undefined);
    } catch {
      const cache = await caches.open(CACHE);
      return await cache.match(key) || Response.error();
    }
    if (response.ok && shell) {
      const cache = await caches.open(CACHE);
      await cache.put(key, response.clone()).catch(() => {});
    }
    return response;
  })());
});

self.addEventListener('message', event => {
  if (event.data === 'CACHE_LEGO') {
    event.waitUntil(caches.open(CACHE).then(cache => cache.add('./lego-catalog.json')).catch(() => {}));
  }
});
