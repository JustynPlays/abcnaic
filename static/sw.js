const CACHE_NAME = 'drcare-v1.1';
const STATIC_CACHE_URLS = [
  '/',
  '/offline.html',
  '/static/styles.css',
  '/static/manifest.json',
  'https://cdn.tailwindcss.com',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css',
  'https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap'
];

const API_CACHE_NAME = 'drcare-api-v1';
const IMAGES_CACHE_NAME = 'drcare-images-v1';

// Install event - cache static resources
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Opened cache');
        return cache.addAll(STATIC_CACHE_URLS);
      })
  );
});

// Activate event - cleanup old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cache => {
          if (cache !== CACHE_NAME && cache !== API_CACHE_NAME) {
            console.log('Deleting old cache:', cache);
            return caches.delete(cache);
          }
        })
      );
    })
  );
});

// Fetch event - serve cached content when offline
self.addEventListener('fetch', event => {
  // Skip cross-origin requests except for CDN resources
  if (!event.request.url.startsWith(self.location.origin) && 
      !event.request.url.startsWith('https://cdn.tailwindcss.com') &&
      !event.request.url.startsWith('https://cdnjs.cloudflare.com') &&
      !event.request.url.startsWith('https://cdn.jsdelivr.net') &&
      !event.request.url.startsWith('https://fonts.googleapis.com') &&
      !event.request.url.startsWith('https://fonts.gstatic.com')) {
    return;
  }

  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Cache hit - return response
        if (response) {
          return response;
        }

        // Clone the request
        const fetchRequest = event.request.clone();

        return fetch(fetchRequest).then(response => {
          // Check if we received a valid response
          if (!response || response.status !== 200 || response.type !== 'basic') {
            return response;
          }

          // Clone the response
          const responseToCache = response.clone();

          // Cache different types of resources in appropriate caches
          let cacheName = CACHE_NAME;
          if (event.request.url.includes('/api/') || event.request.url.includes('/appointments')) {
            cacheName = API_CACHE_NAME;
          } else if (event.request.url.match(/\/.(png|jpg|jpeg|gif|svg|webp)$/i)) {
            cacheName = IMAGES_CACHE_NAME;
          }

          caches.open(cacheName)
            .then(cache => {
              cache.put(event.request, responseToCache);
            });

          return response;
        }).catch(error => {
          // Network failed, try to return appropriate offline fallback
          console.log('Network failed:', event.request.url, error);
          
          if (event.request.destination === 'document') {
            return caches.match('/offline.html');
          } else if (event.request.destination === 'image') {
            return caches.match('/static/icons/placeholder.png');
          } else if (event.request.url.includes('/api/')) {
            // Return cached API responses if available
            return caches.match(event.request).then(cachedResponse => {
              if (cachedResponse) {
                return cachedResponse;
              }
              // Return a generic offline message for API calls
              return new Response(JSON.stringify({
                error: 'Offline',
                message: 'This content is not available offline'
              }), {
                status: 503,
                headers: { 'Content-Type': 'application/json' }
              });
            });
          }
          
          throw error;
        });
      })
  );
});

// Background sync for appointment booking when offline
self.addEventListener('sync', event => {
  if (event.tag === 'background-sync-appointments') {
    event.waitUntil(syncAppointments());
  }
});

function syncAppointments() {
  return caches.open(API_CACHE_NAME)
    .then(cache => {
      return cache.keys();
    })
    .then(keys => {
      return Promise.all(
        keys.map(key => {
          return fetch(key.url, key)
            .then(response => {
              if (response.ok) {
                return caches.open(API_CACHE_NAME).then(cache => cache.delete(key));
              }
            })
            .catch(error => {
              console.log('Failed to sync appointment:', error);
            });
        })
      );
    });
}
