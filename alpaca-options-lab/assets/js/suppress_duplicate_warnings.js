/**
 * Suppress Dash's "Duplicate callback outputs" console warnings
 * These warnings are informational only when allow_duplicate=True is used intentionally
 */

(function() {
    'use strict';
    
    // Store original console.warn and console.error
    const originalWarn = console.warn;
    const originalError = console.error;
    
    // Filter function for warnings/errors that should be suppressed
    function shouldSuppress(args) {
        try {
            const message = args[0];
            if (typeof message === 'string') {
                // Suppress "Duplicate callback outputs" warnings
                if (message.includes('Duplicate callback outputs')) {
                    return true;
                }
                // Suppress related duplicate warnings
                if (message.includes('duplicate output')) {
                    return true;
                }
                // Suppress known Dash persistence error (harmless - occurs during lazy loading)
                if (message.includes("Cannot use 'in' operator to search for 'persistence'")) {
                    return true;
                }
                // Suppress JSON parsing errors from empty responses (harmless)
                if (message.includes('Unexpected end of JSON input')) {
                    return true;
                }
                // Suppress "Value is null" errors (Dash DOM access before elements exist)
                if (message.includes('Value is null')) {
                    return true;
                }
            }
            
            // Check for object messages (Dash sometimes logs as objects)
            if (message && typeof message === 'object') {
                try {
                    const msgStr = JSON.stringify(message);
                    if (msgStr && (msgStr.includes('Duplicate callback') || msgStr.includes('duplicate output'))) {
                        return true;
                    }
                    // Also suppress persistence errors in object form
                    if (msgStr && msgStr.includes('persistence')) {
                        return true;
                    }
                } catch (e) {
                    // JSON.stringify failed (circular ref, etc.) - don't suppress
                }
            }
        } catch (e) {
            // Safety catch - don't suppress if we can't check
        }
        
        return false;
    }
    
    // Override console.warn
    console.warn = function(...args) {
        if (!shouldSuppress(args)) {
            originalWarn.apply(console, args);
        }
    };
    
    // Override console.error
    console.error = function(...args) {
        if (!shouldSuppress(args)) {
            originalError.apply(console, args);
        }
    };
    
    console.log('✅ Duplicate callback warnings suppressed');
})();
