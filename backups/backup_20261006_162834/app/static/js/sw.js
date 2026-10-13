// Service Worker for Ucuz Bilet Bul Web Push Notifications

self.addEventListener('push', function(event) {
    const data = event.data ? event.data.json() : {};
    const title = data.title || "🔥 Fırsat Bileti Yakalandı!";
    const options = {
        body: data.body || "Takip ettiğiniz rotada bilet fiyatı hedefinizin altına düştü.",
        icon: data.icon || "/static/icons/ticket.png",
        badge: data.badge || "/static/icons/badge.png",
        data: {
            url: data.url || "/"
        }
    };
    event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    const targetUrl = (event.notification.data && event.notification.data.url) ? event.notification.data.url : "/";
    event.waitUntil(
        clients.matchAll({ type: 'window' }).then(windowClients => {
            for (let i = 0; i < windowClients.length; i++) {
                const client = windowClients[i];
                if (client.url === targetUrl && 'focus' in client) {
                    return client.focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow(targetUrl);
            }
        })
    );
});
