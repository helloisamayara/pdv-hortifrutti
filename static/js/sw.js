// static/js/sw.js
const CACHE_NAME = 'pdv-v1';
const ASSETS = [
  '/', 
  '/vender',
  '/produtos',
  '/caixa',
  '/produtos_vendidos',
  '/static/js/pdv.js',
  '/static/js/sw.js',
  // adicione aqui outros assets que você queira cachear:
  // '/static/css/main.css',
  // '/static/img/logo.png',
];

self.addEventListener('install', ev => {
  ev.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', ev => {
  ev.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(key => key !== CACHE_NAME)
          .map(key => caches.delete(key))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', ev => {
  const req = ev.request;
  const url = new URL(req.url);

  // Tratamento especial para POST de finalizar venda
  if (req.method === 'POST' && url.pathname === '/finalizar_venda') {
    ev.respondWith(
      fetch(req.clone())
        .then(res => {
          // Se a venda online foi bem-sucedida, solicite sincronização de pendentes
          self.clients.matchAll().then(clients =>
            clients.forEach(c => c.postMessage({ type: 'syncPending' }))
          );
          return res;
        })
        .catch(() => {
          // Offline: retorna 503 para que o front salve a venda localmente
          return new Response(null, { status: 503 });
        })
    );
    return;
  }

  // Para GETs, tente rede primeiro, senão sirva do cache
  if (req.method === 'GET') {
    ev.respondWith(
      fetch(req)
        .then(res => {
          // Atualiza cache
          const copy = res.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(req, copy));
          return res;
        })
        .catch(() => caches.match(req).then(cached => cached || caches.match('/')))
    );
  }
});
