// Portfolio tab label injector
// Fixes dash-bootstrap-components tab label rendering issue

(function() {
    'use strict';
    
    // GUARD: Only run on Portfolio (8056) or Unified Dashboard (8055)
    if (window.location.port !== '8056' && window.location.port !== '8055' && window.location.port !== '') {
        console.log('[Portfolio Fix] Skipping - not on Portfolio/Unified Dashboard');
        return;
    }
    
    // Define tab labels in order
    const tabLabels = [
        'Positions',
        'Order History',
        'Analytics',
        'Factor Exposure',
        'Optimization'
    ];
    
    function injectTabLabels() {
        const tabs = document.querySelectorAll('#portfolio-tracker-subtabs .nav-link');
        
        if (tabs.length === 0) {
            console.log('[Tab Fix] Tabs not found yet, retrying...');
            return false;
        }
        
        console.log(`[Tab Fix] Found ${tabs.length} tabs, injecting labels...`);
        
        tabs.forEach((tab, index) => {
            if (index < tabLabels.length) {
                // Only inject if tab is empty or has very little text
                if (!tab.textContent || tab.textContent.trim().length < 3) {
                    tab.textContent = tabLabels[index];
                    console.log(`[Tab Fix] Injected label "${tabLabels[index]}" into tab ${index}`);
                }
            }
        });
        
        return true;
    }
    
    // Try to inject labels when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(injectTabLabels, 500);
        });
    } else {
        setTimeout(injectTabLabels, 500);
    }
    
    // Also retry after Dash finishes loading
    const checkInterval = setInterval(function() {
        if (injectTabLabels()) {
            clearInterval(checkInterval);
        }
    }, 1000);
    
    // Stop retrying after 30 seconds
    setTimeout(function() {
        clearInterval(checkInterval);
    }, 30000);
    
    console.log('[Tab Fix] Portfolio tab label injector loaded');
})();
