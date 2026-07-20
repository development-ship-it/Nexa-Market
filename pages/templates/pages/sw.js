// Service Worker de NexaMarket — caché local en el navegador (estilo AppSheet).
//
// Tres almacenes separados:
//   estatico : CSS/JS/iconos      → cache-first (se purga al cambiar de versión)
//   imagenes : fotos de productos → cache-first con tope (LRU)
//   paginas  : HTML de la app     → se sirve al instante desde caché y se
//              revalida en segundo plano; el botón Sync fuerza datos frescos.
//
// Nunca se cachea: login/logout/auth/admin/api ni respuestas de escritura.

const VERSION    = '{{ version }}';
const C_ESTATICO = 'nm-estatico-' + VERSION;
const C_IMAGENES = 'nm-imagenes-' + VERSION;
const C_PAGINAS  = 'nm-paginas-' + VERSION;
const MAX_IMAGENES = 200;

const NO_CACHEAR = ['/login/', '/logout/', '/auth/', '/admin/', '/api/', '/sw.js'];

self.addEventListener('install', () => self.skipWaiting());

self.addEventListener('activate', (e) => {
  e.waitUntil((async () => {
    // Borrar cachés de versiones anteriores (deploy nuevo)
    const nombres = await caches.keys();
    await Promise.all(
      nombres.filter(n => n.startsWith('nm-') && !n.endsWith(VERSION))
             .map(n => caches.delete(n))
    );
    await self.clients.claim();
  })());
});

// Mensajes desde sync.js: purgar cachés
self.addEventListener('message', (e) => {
  const tipo = e.data && e.data.tipo;
  if (!tipo) return;
  e.waitUntil((async () => {
    if (tipo === 'PURGAR' || tipo === 'PURGAR_TODO') {
      await caches.delete(C_PAGINAS);
    }
    if (tipo === 'PURGAR_TODO') {
      await caches.delete(C_IMAGENES);
      await caches.delete(C_ESTATICO);
    }
    if (e.ports && e.ports[0]) e.ports[0].postMessage({ ok: true });
  })());
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  let url;
  try { url = new URL(req.url); } catch (err) { return; }

  // Escrituras: siempre a la red, y el caché de páginas queda obsoleto
  // (si acabo de vender, la próxima página debe traer datos frescos).
  if (req.method !== 'GET') {
    e.respondWith((async () => {
      const resp = await fetch(req);
      await caches.delete(C_PAGINAS);
      return resp;
    })());
    return;
  }

  // Imágenes (incluye las fotos de Supabase Storage, que son cross-origin)
  if (req.destination === 'image') {
    e.respondWith(cacheFirst(req, C_IMAGENES, MAX_IMAGENES));
    return;
  }

  if (url.origin !== self.location.origin) return;

  if (url.pathname.startsWith('/static/')) {
    e.respondWith(cacheFirst(req, C_ESTATICO, 0));
    return;
  }

  const esHTML = req.mode === 'navigate' ||
                 (req.headers.get('accept') || '').includes('text/html');
  if (esHTML && !NO_CACHEAR.some(p => url.pathname.startsWith(p))) {
    e.respondWith(revalidarEnSegundoPlano(e, req));
  }
});

async function cacheFirst(req, nombre, max) {
  const cache = await caches.open(nombre);
  const guardado = await cache.match(req);
  if (guardado) return guardado;
  try {
    const resp = await fetch(req);
    // Las imágenes cross-origin sin CORS llegan como 'opaque': igual se cachean
    if (resp && (resp.ok || resp.type === 'opaque')) {
      await cache.put(req, resp.clone());
      if (max) recortar(nombre, max);
    }
    return resp;
  } catch (err) {
    return guardado || Response.error();
  }
}

// Devuelve la copia guardada al instante y actualiza el caché por detrás.
async function revalidarEnSegundoPlano(evento, req) {
  const cache = await caches.open(C_PAGINAS);
  // ignoreVary: la precarga pide con Accept:text/html y la navegación con otro
  // Accept; sin esto no calzarían y la precarga no serviría de nada.
  const guardado = await cache.match(req, { ignoreVary: true });

  const red = fetch(req).then(async (resp) => {
    const cacheable = resp && resp.ok && resp.status === 200 &&
                      resp.type === 'basic' && !resp.redirected;
    if (cacheable) {
      await cache.put(req, await sinAvisos(resp.clone()));
    }
    return resp;
  }).catch(() => null);

  evento.waitUntil(red);

  if (guardado) return guardado;
  const resp = await red;
  return resp || new Response(
    '<h1>Sin conexión</h1><p>Abre una página que ya hayas visitado.</p>',
    { status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8' } }
  );
}

// Quita los mensajes de una sola vez ("Venta registrada…") antes de guardar,
// para que no reaparezcan cada vez que se sirve la página desde el caché.
async function sinAvisos(resp) {
  try {
    const html = await resp.text();
    const limpio = html.replace(/<div class="alert alert-[^"]*">[\s\S]*?<\/div>/g, '');
    return new Response(limpio, {
      status: resp.status,
      statusText: resp.statusText,
      headers: resp.headers,
    });
  } catch (err) {
    return resp;
  }
}

// Tope de imágenes guardadas: borra las más antiguas (keys() va en orden de inserción)
async function recortar(nombre, max) {
  const cache = await caches.open(nombre);
  const keys = await cache.keys();
  for (let i = 0; i < keys.length - max; i++) {
    await cache.delete(keys[i]);
  }
}
