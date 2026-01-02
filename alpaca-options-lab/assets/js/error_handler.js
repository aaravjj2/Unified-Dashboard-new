/**
 * Global Error Handler for Phase 12 Resilience.
 * Catches unhandled exceptions (Poison Pills) and prevents White Screen of Death.
 * 
 * FIXED: Removed aggressive fetch/XHR monkey-patching that was blocking
 * valid Dash callback responses. The patch was causing Plotly charts to
 * not update even when the server returned valid data.
 */

// Known harmless errors to suppress
function isHarmlessError(message) {
    if (!message) return false;
    const msgStr = String(message);
    
    // Dash persistence error - occurs during lazy loading, harmless
    if (msgStr.includes("Cannot use 'in' operator to search for 'persistence'")) {
        return true;
    }
    // JSON parsing errors from empty responses
    if (msgStr.includes('Unexpected end of JSON input')) {
        return true;
    }
    // Duplicate callback warnings
    if (msgStr.includes('Duplicate callback')) {
        return true;
    }
    // "Value is null" errors from Dash DOM access before elements exist
    if (msgStr.includes('Value is null')) {
        return true;
    }
    return false;
}

// 1. Global Exception Handlers - KEPT (these are safe)
window.onerror = function (message, source, lineno, colno, error) {
    // Suppress known harmless errors
    if (isHarmlessError(message)) {
        return true; // Suppress silently
    }
    console.error("🛑 ResilientGuard Caught Error:", message);
    showErrorToast("Data Error: Protocol mismatch detected. Recovering...");
    return true; // Suppress error propagation
};

window.onunhandledrejection = function (event) {
    // Suppress known harmless errors
    if (isHarmlessError(event.reason)) {
        return; // Suppress silently
    }
    console.error("🛑 ResilientGuard Caught Async Error:", event.reason);
    showErrorToast("Data Error: Async operation failed.");
};

// 2. Toast Notification UI - KEPT (this is safe)
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

// 3. REMOVED: Fetch monkey-patching
// The previous implementation was cloning responses and trying to parse JSON,
// which interfered with Dash's response handling and caused Plotly charts
// to not update even when valid data was returned.
// 
// The original intent was to detect "Poison Pills" (malformed responses),
// but it ended up blocking legitimate responses.

// 4. REMOVED: XHR monkey-patching
// Same issue as fetch - the response interception was breaking Dash callbacks.

console.log("✅ Error handler loaded (v2 - no response interception)");
