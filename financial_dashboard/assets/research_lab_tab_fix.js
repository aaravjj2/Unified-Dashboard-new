// Research Lab Tab Label Injector
// Fixes empty tab labels in Research Lab

(function() {
    'use strict';
    
    // Only run on Research Lab (port 8058)
    if (window.location.port !== '8058') {
        console.log('[Research Lab Fix] Skipping - not on Research Lab');
        return;
    }
    
    console.log('[Research Lab Fix] Injecting tab labels...');
    
    const expectedLabels = [
        'New Experiment',
        'Experiments',
        'Results',
        'Scenario Lab'
    ];
    
    function injectLabels() {
        const tabs = document.querySelectorAll('.nav-link');
        
        if (tabs.length < 4) {
            return false;  // Not ready yet
        }
        
        let injected = 0;
        tabs.forEach((tab, index) => {
            if (index < expectedLabels.length && !tab.textContent.trim()) {
                tab.textContent = expectedLabels[index];
                injected++;
            }
        });
        
        if (injected > 0) {
            console.log(`[Research Lab Fix] ✓ Injected ${injected} tab labels`);
            
            // Activate the Scenario Lab tab (4th tab, index 3)
            if (tabs.length >= 4) {
                const scenarioTab = tabs[3];
                scenarioTab.classList.add('active');
                scenarioTab.setAttribute('aria-selected', 'true');
                
                // Find and activate the corresponding pane
                const panes = document.querySelectorAll('[role="tabpanel"]');
                if (panes.length >= 4) {
                    // Hide all panes first
                    panes.forEach(p => {
                        p.style.display = 'none';
                        p.classList.remove('active', 'show');
                    });
                    
                    // Show the 4th pane (Scenario Lab)
                    const scenarioPane = panes[3];
                    scenarioPane.style.display = 'block';
                    scenarioPane.classList.add('active', 'show');
                    
                    console.log('[Research Lab Fix] ✓ Activated Scenario Lab tab by default');
                }
            }
            
            return true;
        }
        
        return false;
    }
    
    // Try immediately
    setTimeout(injectLabels, 100);
    
    // Also retry a few times
    let retries = 0;
    const maxRetries = 15;
    const interval = setInterval(() => {
        retries++;
        if (injectLabels() || retries >= maxRetries) {
            clearInterval(interval);
        }
    }, 300);
    
})();
