/**
 * Global Error Handler for Phase 12 Resilience.
 * Catches unhandled exceptions (Poison Pills) and prevents White Screen of Death.
 */

// 1. Global Exception Handlers
window.onerror = function (message, source, lineno, colno, error) {
    console.error("🛑 ResilientGuard Caught Error:", message);
    showErrorToast("Data Error: Protocol mismatch detected. Recovering...");
    return true; // Suppress error propagation
};

window.onunhandledrejection = function (event) {
    console.error("🛑 ResilientGuard Caught Async Error:", event.reason);
    showErrorToast("Data Error: Async operation failed.");
};

// 2. Toast Notification UI
function showErrorToast(msg) {
    let toast = document.getElementById('resilience-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'resilience-toast';
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background-color: #ff9800; /* Warning/Error Orange */
            color: white;
            padding: 15px 25px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            z-index: 10000;
            font-family: system-ui, -apple-system, sans-serif;
            font-weight: bold;
            display: none;
            animation: slideIn 0.3s ease-out;
        `;

        // Add animation style
        const style = document.createElement('style');
        style.textContent = `
            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
        `;
        document.head.appendChild(style);
        document.body.appendChild(toast);
    }

    toast.textContent = msg;
    toast.style.display = 'block';

    // Auto-dismiss
    setTimeout(() => {
        toast.style.display = 'none';
    }, 6000);
}

// 3. 🛡️ Monkey Patch Fetch to intercept Poison Pills (Phase 12)
const originalFetch = window.fetch;
window.fetch = async function (resource, config) {
    try {
        const response = await originalFetch(resource, config);

        // Only inspect Dash update requests
        const url = (typeof resource === 'string') ? resource : (resource.url || '');
        if (url && url.includes('_dash-update-component') && response.ok) {
            const clone = response.clone();
            try {
                // Try to parse JSON and validate structure
                const data = await clone.json();

                // Poison Pill Detection: response must be object, not string/garbage
                // Default Dash response is {response: {...}, multi: bool}
                if (data && data.response && typeof data.response !== 'object') {
                    throw new Error("Invalid Dash Response Structure detected (Poison Pill)");
                }
                // Additional checks can be added here

            } catch (e) {
                console.warn("🛡️ Security Guard blocked toxic data:", e);
                showErrorToast("Data Error: Toxic payload blocked.");

                // Return safe empty response to prevent Renderer crash
                // This keeps the UI alive ("Not blanked out")
                return new Response(JSON.stringify({ response: {} }), {
                    status: 200,
                    headers: response.headers
                });
            }
        }
        return response;
    } catch (err) {
        // Network errors handled elsewhere
        throw err;
    }
};

// 4. 🛡️ Monkey Patch XHR (Legacy Dash Support)
const originalOpen = XMLHttpRequest.prototype.open;
XMLHttpRequest.prototype.open = function (method, url) {
    this._url = url;
    return originalOpen.apply(this, arguments);
};

const originalSend = XMLHttpRequest.prototype.send;
XMLHttpRequest.prototype.send = function () {
    this.addEventListener('load', function () {
        if (this._url && (typeof this._url === 'string') && this._url.includes('_dash-update-component')) {
            try {
                // Try parse
                const data = JSON.parse(this.responseText);
                if (data && data.response && typeof data.response !== 'object') {
                    throw new Error("Invalid Dash Response Structure detected (XHR Poison Pill)");
                }
            } catch (e) {
                console.warn("🛡️ Security Guard blocked XHR toxic data:", e);
                showErrorToast("Data Error: Toxic XHR payload blocked.");

                // Overwrite response to safe value
                try {
                    Object.defineProperty(this, 'responseText', { value: '{"response": {}}', writable: true, configurable: true });
                    Object.defineProperty(this, 'response', { value: '{"response": {}}', writable: true, configurable: true });
                } catch (err) {
                    console.error("Failed to overwrite XHR response", err);
                }
            }
        }
    });
    return originalSend.apply(this, arguments);
};
