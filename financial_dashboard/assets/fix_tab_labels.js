/**
 * Fix for Dash Bootstrap Components tab labels rendering as "Tab 1", "Tab 2", etc.
 * This script updates the tab labels with their correct names after React renders.
 */

// Tab configuration - must match the order in index.py ENABLED_TABS
const TAB_LABELS = [
    '🎯 Command Center',
    '🔬 Research Lab',
    '📊 Attribution Lab',
    '⚡ Strategy Lab',
    'Weekly Picks',
    'Monthly Picks',
    'Market Trends',
    'Market Forecast',
    '⚡ Volatility Lab',
    'Portfolio',
    '💹 Options Lab'
];

function fixTabLabels() {
    console.log('[TabLabelFix] Attempting to fix tab labels...');

    // Find all tab links
    const tabLinks = document.querySelectorAll('#dashboard-tabs .nav-link[role="tab"]');

    if (tabLinks.length === 0) {
        console.log('[TabLabelFix] No tabs found yet, will retry...');
        return false;
    }

    console.log(`[TabLabelFix] Found ${tabLinks.length} tabs`);

    // Update each tab label
    tabLinks.forEach((tab, index) => {
        if (index < TAB_LABELS.length) {
            const oldLabel = tab.textContent.trim();
            const newLabel = TAB_LABELS[index];

            if (oldLabel !== newLabel) {
                tab.textContent = newLabel;
                console.log(`[TabLabelFix] Updated tab ${index + 1}: "${oldLabel}" → "${newLabel}"`);
            }
        }
    });

    console.log('[TabLabelFix] ✅ Tab labels fixed!');
    return true;
}

// Try to fix labels when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
        setTimeout(fixTabLabels, 500);
    });
} else {
    setTimeout(fixTabLabels, 500);
}

// Retry multiple times to ensure labels are fixed
let retryCount = 0;
const maxRetries = 10;

function retryFixTabLabels() {
    if (retryCount >= maxRetries) {
        console.log('[TabLabelFix] Max retries reached');
        return;
    }

    const success = fixTabLabels();
    if (!success) {
        retryCount++;
        setTimeout(retryFixTabLabels, 1000);
    }
}

setTimeout(retryFixTabLabels, 1000);

// Also fix labels when Dash finishes rendering (listen for Dash events)
if (window.dash_clientside) {
    window.dash_clientside.no_update = window.dash_clientside.no_update || {};
}

// Monitor for React updates and reapply fixes
const observer = new MutationObserver(function (mutations) {
    mutations.forEach(function (mutation) {
        if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
            // Check if tabs were added/modified
            mutation.addedNodes.forEach(function (node) {
                if (node.nodeType === 1 && (node.matches('.nav-link[role="tab"]') || node.querySelector('.nav-link[role="tab"]'))) {
                    console.log('[TabLabelFix] Tabs changed, reapplying fix...');
                    setTimeout(fixTabLabels, 100);
                }
            });
        }
    });
});

// Start observing the document
setTimeout(function () {
    const tabsContainer = document.getElementById('dashboard-tabs');
    if (tabsContainer) {
        observer.observe(tabsContainer, {
            childList: true,
            subtree: true
        });
        console.log('[TabLabelFix] Monitoring tabs for changes');
    }
}, 2000);
