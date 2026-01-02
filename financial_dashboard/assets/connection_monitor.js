/**
 * Connection Monitor & Exponential Backoff
 * Handles network outages by showing a "Reconnecting..." badge.
 * Phase 12 Quality Requirement.
 */
document.addEventListener('DOMContentLoaded', function () {
    console.log("📡 Connection Monitor initialized");

    const POLL_ENDPOINT = '/api/options/ready'; // Checks Backend + Redis (Readiness)
    let interval = 2000;
    const MAX_INTERVAL = 30000;
    let timer = null;

    // Create badge element
    const badge = document.createElement('div');
    badge.id = 'connection-status-badge';
    badge.innerHTML = `
        <div style="display: flex; align-items: center; gap: 10px;">
            <div class="spinner-border text-light" role="status" style="width: 1rem; height: 1rem;"></div>
            <span>Reconnecting...</span>
        </div>
    `;
    badge.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background-color: #dc3545; /* Danger color */
        color: white;
        padding: 10px 20px;
        border-radius: 5px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        z-index: 9999;
        font-family: system-ui, -apple-system, sans-serif;
        font-weight: 500;
        display: none; /* Hidden by default */
        transition: opacity 0.3s ease;
    `;
    document.body.appendChild(badge);

    function showBadge() {
        badge.style.display = 'block';
        badge.style.opacity = '1';
    }

    function hideBadge() {
        badge.style.opacity = '0';
        setTimeout(() => {
            if (badge.style.opacity === '0') {
                badge.style.display = 'none';
            }
        }, 300);
    }

    function checkConnection() {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 3000); // 3s timeout

        fetch(POLL_ENDPOINT, {
            method: 'GET',
            cache: 'no-store',
            signal: controller.signal
        })
            .then(response => {
                clearTimeout(timeoutId);
                if (response.ok) {
                    // Success
                    if (interval > 2000) {
                        console.log("✅ Connection restored");
                    }
                    interval = 2000; // Reset backoff
                    hideBadge();
                } else {
                    throw new Error("Server error " + response.status);
                }
            })
            .catch(error => {
                clearTimeout(timeoutId);
                const isTimeout = error.name === 'AbortError';
                const msg = isTimeout ? 'Request timed out' : error.message;

                console.warn(`⚠️ Connection lost: ${msg}. Retrying in ${interval}ms`);
                showBadge();

                // Exponential Backoff
                interval = Math.min(interval * 1.5, MAX_INTERVAL);
            })
            .finally(() => {
                clearTimeout(timer);
                timer = setTimeout(checkConnection, interval);
            });
    }

    // Start polling
    timer = setTimeout(checkConnection, interval);
});
