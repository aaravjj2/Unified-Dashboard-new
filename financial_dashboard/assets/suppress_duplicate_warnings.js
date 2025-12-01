/**
 * Suppress Dash's "Duplicate callback outputs" console warnings
 * These warnings are informational only when allow_duplicate=True is used intentionally
 */

(function() {
    'use strict';
    
    // Store original console.warn and console.error
    const originalWarn = console.warn;
    const originalError = console.error;
    
    // Filter function for duplicate callback warnings
    function shouldSuppress(args) {
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
        }
        
        // Check for object messages (Dash sometimes logs as objects)
        if (typeof message === 'object' && message !== null) {
            const msgStr = JSON.stringify(message);
            if (msgStr.includes('Duplicate callback') || msgStr.includes('duplicate output')) {
                return true;
            }
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
