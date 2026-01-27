const CACHE_NAME = 'cv2-v3';
const ASSETS = [
  '/',
  '/index.html',
  '/auth.html',
  '/dashboard.html',
  '/talent-app.html',
  '/hm-onboarding.html',
  '/job-command-center.html',
  '/css/design.css',
  '/js/config.js',
  '/js/app.js',
  '/manifest.json',
];

// Install — cache essential assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
  );
  self.skipWaiting();
});

// Activate — clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Fetch — network first, fallback to cache
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET, non-http(s), and API calls
  if (
    request.method !== 'GET' ||
    !url.protocol.startsWith('http') ||
    url.pathname.startsWith('/api/') ||
    url.pathname.startsWith('/a2a/') ||
    url.pathname.startsWith('/master-ai/') ||
    url.pathname.startsWith('/jobs/') ||
    url.pathname.startsWith('/onboarding/') ||
    url.pathname.startsWith('/user/') ||
    url.pathname.startsWith('/chat/') ||
    url.pathname.startsWith('/calibration/') ||
    url.pathname.startsWith('/network/') ||
    url.pathname.startsWith('/health')
  ) {
    return;
  }

  event.respondWith(
    fetch(request)
      .then((response) => {
        // Cache successful responses (only http/https)
        if (response.ok && url.protocol.startsWith('http')) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            try {
              cache.put(request, clone);
            } catch (e) {
              // Ignore cache errors (e.g., for chrome-extension URLs)
            }
          });
        }
        return response;
      })
      .catch(() => caches.match(request))
  );
});

// Push notifications
self.addEventListener('push', (event) => {
  let data = { title: 'CV 2.0', body: 'You have a new notification' };

  if (event.data) {
    try {
      data = event.data.json();
    } catch (e) {
      data.body = event.data.text();
    }
  }

  const options = {
    body: data.body || data.message || '',
    icon: '/icons/icon-192.png',
    badge: '/icons/icon-192.png',
    tag: data.tag || 'cv2-notification',
    data: { url: data.url || '/dashboard.html' },
    actions: data.actions || [
      { action: 'open', title: 'View' },
      { action: 'dismiss', title: 'Dismiss' },
    ],
    vibrate: [100, 50, 100],
  };

  event.waitUntil(self.registration.showNotification(data.title || 'CV 2.0', options));
});

// Notification click
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  if (event.action === 'dismiss') return;

  const url = event.notification.data?.url || '/dashboard.html';
  event.waitUntil(
    self.clients.matchAll({ type: 'window' }).then((clients) => {
      // Focus existing window if open
      for (const client of clients) {
        if (client.url.includes(url) && 'focus' in client) {
          return client.focus();
        }
      }
      // Otherwise open new window
      return self.clients.openWindow(url);
    })
  );
});
