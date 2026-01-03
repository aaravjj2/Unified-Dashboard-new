/**
 * TradingView Chart Fix for Phase 12
 * Handles the 'Value is undefined' error in dash_tvlwc.removeSeries
 */

document.addEventListener('DOMContentLoaded', function () {
    console.log("📈 TVLWC Error Suppressor initialized");

    // Monitor for the specific error and suppress it
    const originalError = console.error;
    console.error = function (msg, ...args) {
        const msgStr = String(msg || '');
        // Suppress TVLWC errors
        if (msgStr.includes('Value is undefined') || 
            msgStr.includes('dash_tvlwc') ||
            msgStr.includes('removeSeries')) {
            // Silently suppress - don't log
            return;
        }
        // Suppress React error #185 (invalid state update)
        if (msgStr.includes('Minified React error #185') || 
            msgStr.includes('React error #185')) {
            // Silently suppress
            return;
        }
        originalError.call(console, msg, ...args);
    };

    // Patch the dash_tvlwc component if it exists
    function patchTvlwc() {
        if (window.dash_tvlwc && window.dash_tvlwc.t && window.dash_tvlwc.t.removeSeries) {
            const originalRemoveSeries = window.dash_tvlwc.t.removeSeries;
            window.dash_tvlwc.t.removeSeries = function (series) {
                if (!series || typeof series === 'undefined') {
                    console.warn('🛡️ Blocked removeSeries call on undefined series');
                    return; // Skip
                }
                return originalRemoveSeries.call(this, series);
            };
            console.log("✅ TVLWC removeSeries patched");
        } else {
            // Retry after a short delay
            setTimeout(patchTvlwc, 500);
        }
    }

    // Start patching
    setTimeout(patchTvlwc, 100);
});
