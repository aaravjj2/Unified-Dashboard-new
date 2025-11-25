// Analysis Hub Tab Activation Fix
// Ensures the first tab pane is active on page load and tab labels are visible
(function() {
    'use strict';
    
    console.log('[Analysis Hub] Tab activation script loaded');

    function activateFirstTab() {
        try {
            // Find all tab panes
            const tabPanes = document.querySelectorAll('.tab-pane');
            
            if (tabPanes.length > 0) {
                console.debug(`[Analysis Hub] Found ${tabPanes.length} tab panes`);
                
                // Check if any pane is already active
                const hasActive = Array.from(tabPanes).some(pane => pane.classList.contains('active'));
                
                if (!hasActive) {
                    console.log('[Analysis Hub] No active tab found, activating first tab pane');
                    const firstPane = tabPanes[0];
                    firstPane.classList.add('active', 'show');
                    
                    // Also activate the first tab link
                    const firstTabLink = document.querySelector('.nav-link');
                    if (firstTabLink) {
                        firstTabLink.classList.add('active');
                        firstTabLink.setAttribute('aria-selected', 'true');
                        console.debug('[Analysis Hub] Activated first tab link');
                    }
                    console.log('[Analysis Hub] ✓ First tab activated successfully');
                } else {
                    console.log('[Analysis Hub] Active tab already exists');
                }
                
                // Fix tab labels if they're empty
                fixTabLabels();
                
                return true;
            } else {
                console.log('[Analysis Hub] No tab panes found, retrying...');
                return false;
            }
        } catch (e) {
            console.error('[Analysis Hub] Tab activation error:', e);
            return false;
        }
    }

    function fixTabLabels() {
        try {
            const tabs = document.querySelectorAll('.nav-link');
            const expectedLabels = ['Tab 1', 'Tab 2', 'Tab 3', 'Tab 4', 'Tab 5'];
            
            let fixed = 0;
            tabs.forEach((tab, index) => {
                const currentText = tab.textContent.trim();
                if (!currentText && index < expectedLabels.length) {
                    tab.textContent = expectedLabels[index];
                    fixed++;
                    console.log(`[Analysis Hub] Fixed tab ${index} label: ${expectedLabels[index]}`);
                }
            });
            
            if (fixed > 0) {
                console.log(`[Analysis Hub] ✓ Fixed ${fixed} tab labels`);
            }
        } catch (e) {
            console.error('[Analysis Hub] Tab label fix error:', e);
        }
    }

    // Try to activate tabs when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(activateFirstTab, 100);
        });
    } else {
        setTimeout(activateFirstTab, 100);
    }

    // Also retry a few times in case Dash hasn't rendered the tabs yet
    let retries = 0;
    const maxRetries = 10;
    const retryInterval = setInterval(function() {
        retries++;
        if (activateFirstTab() || retries >= maxRetries) {
            clearInterval(retryInterval);
            console.log(`[Analysis Hub] Tab activation ${retries <= maxRetries ? 'succeeded' : 'gave up'} after ${retries} attempts`);
        }
    }, 500);

})();
