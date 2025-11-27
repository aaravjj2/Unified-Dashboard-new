// Analysis Hub Tab Activation Fix
// Ensures the first tab pane is active on page load and tab labels are visible
(function() {
    'use strict';
    
    // Silent initialization - only log when actually fixing something
    let hasLogged = false;

    function activateFirstTab(isFinalAttempt) {
        try {
            // Find all tab panes
            const tabPanes = document.querySelectorAll('.tab-pane');
            
            if (tabPanes.length > 0) {
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
                    }
                    console.log('[Analysis Hub] ✓ First tab activated successfully');
                }
                
                // Fix tab labels if they're empty
                fixTabLabels();
                
                return true;
            } else {
                // Only log on final attempt to reduce console noise
                if (isFinalAttempt && !hasLogged) {
                    hasLogged = true;
                    // This is expected on pages without Analysis Hub tabs - silent fail
                }
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
            setTimeout(function() { activateFirstTab(false); }, 100);
        });
    } else {
        setTimeout(function() { activateFirstTab(false); }, 100);
    }

    // Also retry a few times in case Dash hasn't rendered the tabs yet
    let retries = 0;
    const maxRetries = 5;  // Reduced from 10
    const retryInterval = setInterval(function() {
        retries++;
        const isFinal = retries >= maxRetries;
        if (activateFirstTab(isFinal) || isFinal) {
            clearInterval(retryInterval);
            // Only log success when tabs were actually found and fixed
        }
    }, 500);

})();
