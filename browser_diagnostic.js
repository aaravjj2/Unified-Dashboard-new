// Browser Diagnostic Script
// Copy and paste this into your browser console after loading http://localhost:8050

console.log('=== DASHBOARD TAB DIAGNOSTIC ===\n');

// Find main tabs container
const tabsContainer = document.querySelector('#dashboard-tabs');
if (!tabsContainer) {
    console.error('❌ #dashboard-tabs container not found!');
} else {
    console.log('✅ Found #dashboard-tabs container\n');
    
    // Find all top-level nav tabs (main dashboard tabs)
    const mainNavTabs = document.querySelectorAll('#dashboard-tabs > .tabs-container > .nav > .nav-item > .nav-link');
    
    console.log(`Total main tabs found: ${mainNavTabs.length}\n`);
    
    mainNavTabs.forEach((tab, index) => {
        const tabId = tab.getAttribute('data-rb-event-key');
        const tabText = tab.textContent.trim();
        const isActive = tab.classList.contains('active');
        const isVisible = window.getComputedStyle(tab).display !== 'none';
        
        const marker = tabId === 'research_lab' ? '🔬' :
                      tabId === 'attribution_lab' ? '📊' : '  ';
        
        console.log(`${marker} ${index + 1}. ${tabId || 'NO_ID'}`);
        console.log(`   Label: "${tabText}"`);
        console.log(`   Active: ${isActive}, Visible: ${isVisible}`);
        console.log(`   Display: ${window.getComputedStyle(tab).display}`);
        console.log(`   Position: ${window.getComputedStyle(tab).position}`);
        console.log('');
    });
    
    // Check if Research Lab exists anywhere in DOM
    console.log('\n=== SEARCHING FOR MISSING TABS ===\n');
    
    const researchTab = document.querySelector('[data-rb-event-key="research_lab"]');
    const attributionTab = document.querySelector('[data-rb-event-key="attribution_lab"]');
    
    console.log(`Research Lab tab: ${researchTab ? '✅ FOUND' : '❌ NOT FOUND'}`);
    if (researchTab) {
        console.log(`  Parent: ${researchTab.parentElement?.className}`);
        console.log(`  Visible: ${window.getComputedStyle(researchTab).display !== 'none'}`);
    }
    
    console.log(`Attribution Lab tab: ${attributionTab ? '✅ FOUND' : '❌ NOT FOUND'}`);
    if (attributionTab) {
        console.log(`  Parent: ${attributionTab.parentElement?.className}`);
        console.log(`  Visible: ${window.getComputedStyle(attributionTab).display !== 'none'}`);
    }
    
    // Check React DevTools data
    console.log('\n=== REACT FIBER INSPECTION ===\n');
    const reactRoot = tabsContainer._reactRootContainer || 
                     Object.keys(tabsContainer).find(key => key.startsWith('__react'));
    console.log(`React root available: ${!!reactRoot}`);
    
    // Check for any JavaScript errors
    console.log('\n=== CHECKING FOR ERRORS ===\n');
    console.log('Check the Console tab for any red error messages');
    console.log('Check the Network tab for failed requests');
}

console.log('\n=== END DIAGNOSTIC ===');
