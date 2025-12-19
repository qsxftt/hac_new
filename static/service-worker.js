// Service Worker для PWA
const CACHE_NAME = 'neurospeech-v1.0.0';
const OFFLINE_URL = '/offline';

// Файлы для кэширования при установке
const CACHE_ASSETS = [
  '/',
  '/static/manifest.json',
  '/offline',
  // Добавьте критичные CSS/JS файлы
];

// Установка Service Worker
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[SW] Caching app shell');
        return cache.addAll(CACHE_ASSETS);
      })
      .then(() => self.skipWaiting())
  );
});

// Активация Service Worker
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...');
  
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('[SW] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Стратегия кэширования: Network First (для динамического контента)
self.addEventListener('fetch', (event) => {
  // Пропускаем non-GET запросы
  if (event.request.method !== 'GET') {
    return;
  }

  // Пропускаем API запросы и WebSocket
  if (event.request.url.includes('/api/') || 
      event.request.url.includes('/status/') ||
      event.request.url.includes('ws://')) {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // Клонируем ответ, так как он может быть использован только один раз
        const responseToCache = response.clone();
        
        // Кэшируем успешные ответы
        if (response.status === 200) {
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });
        }
        
        return response;
      })
      .catch(() => {
        // Если сеть недоступна, пытаемся взять из кэша
        return caches.match(event.request)
          .then((cachedResponse) => {
            if (cachedResponse) {
              return cachedResponse;
            }
            
            // Если HTML страница и нет в кэше - показываем офлайн-страницу
            if (event.request.headers.get('accept').includes('text/html')) {
              return caches.match(OFFLINE_URL);
            }
          });
      })
  );
});

// Обработка фоновой синхронизации (для будущих фич)
self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync:', event.tag);
  
  if (event.tag === 'sync-analyses') {
    event.waitUntil(syncAnalyses());
  }
});

// Обработка push-уведомлений (для будущих фич)
self.addEventListener('push', (event) => {
  console.log('[SW] Push notification received');
  
  const data = event.data ? event.data.json() : {};
  const title = data.title || 'NeuroSpeech';
  const options = {
    body: data.body || 'У вас новое уведомление',
    icon: '/static/icons/icon-192x192.png',
    badge: '/static/icons/icon-72x72.png',
    vibrate: [200, 100, 200],
    data: data.url || '/',
    actions: [
      { action: 'open', title: 'Открыть' },
      { action: 'close', title: 'Закрыть' }
    ]
  };
  
  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

// Обработка кликов по уведомлениям
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  
  if (event.action === 'open' || !event.action) {
    const url = event.notification.data || '/';
    event.waitUntil(
      clients.openWindow(url)
    );
  }
});

// Функция синхронизации данных (заглушка)
async function syncAnalyses() {
  console.log('[SW] Syncing analyses...');
  // Здесь будет логика синхронизации отложенных анализов
  return Promise.resolve();
}
