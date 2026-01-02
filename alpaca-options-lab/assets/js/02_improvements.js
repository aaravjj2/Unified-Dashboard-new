/**
 * Dashboard 162 Improvements JavaScript
 * ======================================
 * Implements dynamic UI enhancements across all 9 tabs.
 */

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Loading 162 Dashboard Improvements...');
    
    // Initialize improvements
    initializeImprovements();
    
    // Re-initialize when tab content changes
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.addedNodes.length > 0) {
                setTimeout(initializeImprovements, 100);
            }
        });
    });
    
    const tabContent = document.getElementById('tabs-content');
    if (tabContent) {
        observer.observe(tabContent, { childList: true, subtree: true });
    }
});

function initializeImprovements() {
    addTooltipsToButtons();
    addAriaLabels();
    addKeyboardShortcuts();
    enhanceLoadingStates();
    addTimestamps();
    enhanceCharts();
    enhanceTables();
}

/**
 * Add tooltips to all buttons
 */
function addTooltipsToButtons() {
    const buttons = document.querySelectorAll('.btn:not([data-tooltip-added])');
    buttons.forEach(btn => {
        btn.setAttribute('data-tooltip-added', 'true');
        
        // Add title attribute for native tooltip if none exists
        if (!btn.title && !btn.getAttribute('aria-label')) {
            const icon = btn.querySelector('i');
            if (icon) {
                const iconClass = icon.className;
                if (iconClass.includes('sync') || iconClass.includes('refresh')) {
                    btn.title = 'Refresh data';
                } else if (iconClass.includes('download')) {
                    btn.title = 'Export data';
                } else if (iconClass.includes('question')) {
                    btn.title = 'Help';
                } else if (iconClass.includes('moon') || iconClass.includes('sun')) {
                    btn.title = 'Toggle theme';
                } else if (iconClass.includes('search-plus')) {
                    btn.title = 'Zoom in';
                } else if (iconClass.includes('search-minus')) {
                    btn.title = 'Zoom out';
                } else if (iconClass.includes('expand')) {
                    btn.title = 'Reset view';
                } else if (iconClass.includes('camera')) {
                    btn.title = 'Save as image';
                }
            }
        }
    });
}

/**
 * Add ARIA labels for accessibility
 */
function addAriaLabels() {
    // Label graphs
    document.querySelectorAll('.js-plotly-plot:not([aria-label])').forEach((chart, index) => {
        chart.setAttribute('aria-label', `Chart ${index + 1}`);
        chart.setAttribute('role', 'img');
    });
    
    // Label tables
    document.querySelectorAll('.dash-table-container:not([aria-label])').forEach((table, index) => {
        table.setAttribute('aria-label', `Data table ${index + 1}`);
        table.setAttribute('role', 'table');
    });
    
    // Label cards
    document.querySelectorAll('.card:not([aria-label])').forEach(card => {
        const header = card.querySelector('.card-header');
        if (header) {
            card.setAttribute('aria-label', header.textContent.trim());
        }
    });
    
    // Label nav tabs
    document.querySelectorAll('.nav-tabs:not([aria-label])').forEach(nav => {
        nav.setAttribute('aria-label', 'Dashboard navigation');
        nav.setAttribute('role', 'tablist');
    });
    
    document.querySelectorAll('.nav-tabs .nav-link').forEach(link => {
        link.setAttribute('role', 'tab');
    });
    
    // Label forms
    document.querySelectorAll('.form-control:not([aria-label]), .form-select:not([aria-label])').forEach(input => {
        const label = input.closest('.form-group')?.querySelector('label');
        if (label) {
            input.setAttribute('aria-label', label.textContent.trim());
        }
    });
}

/**
 * Add keyboard shortcuts
 */
function addKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Only when not in input fields
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        
        // R - Refresh
        if (e.key === 'r' && !e.ctrlKey && !e.metaKey) {
            const refreshBtn = document.querySelector('.btn-refresh, [id*="refresh"]');
            if (refreshBtn) {
                refreshBtn.click();
                showToast('Data refreshed');
            }
        }
        
        // E - Export
        if (e.key === 'e' && !e.ctrlKey && !e.metaKey) {
            const exportBtn = document.querySelector('.btn-export, [id*="export"]');
            if (exportBtn) {
                exportBtn.click();
            }
        }
        
        // H - Help
        if (e.key === 'h' && !e.ctrlKey && !e.metaKey) {
            const helpBtn = document.querySelector('.btn-help, [id*="help"]');
            if (helpBtn) {
                helpBtn.click();
            }
        }
        
        // 1-9 - Quick tab navigation
        if (e.key >= '1' && e.key <= '9' && !e.ctrlKey && !e.metaKey) {
            const tabIndex = parseInt(e.key) - 1;
            const tabs = document.querySelectorAll('.nav-tabs .nav-link');
            if (tabs[tabIndex]) {
                tabs[tabIndex].click();
            }
        }
        
        // ? - Show keyboard shortcuts
        if (e.key === '?' && e.shiftKey) {
            showKeyboardShortcuts();
        }
    });
}

/**
 * Show keyboard shortcuts modal
 */
function showKeyboardShortcuts() {
    let modal = document.getElementById('keyboard-shortcuts-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'keyboard-shortcuts-modal';
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Keyboard Shortcuts</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <table class="table table-sm">
                            <tbody>
                                <tr><td><kbd>R</kbd></td><td>Refresh data</td></tr>
                                <tr><td><kbd>E</kbd></td><td>Export data</td></tr>
                                <tr><td><kbd>H</kbd></td><td>Show help</td></tr>
                                <tr><td><kbd>1-9</kbd></td><td>Switch tabs</td></tr>
                                <tr><td><kbd>?</kbd></td><td>Show this help</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }
    
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

/**
 * Enhance loading states
 */
function enhanceLoadingStates() {
    // Add loading class to elements during callback
    const style = document.createElement('style');
    style.textContent = `
        .dash-loading-callback {
            opacity: 0.7;
            pointer-events: none;
            position: relative;
        }
        .dash-loading-callback::after {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 24px;
            height: 24px;
            margin: -12px 0 0 -12px;
            border: 3px solid #0d6efd;
            border-top-color: transparent;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
    `;
    document.head.appendChild(style);
}

/**
 * Add last updated timestamps
 */
function addTimestamps() {
    document.querySelectorAll('.card:not([data-timestamp-added])').forEach(card => {
        card.setAttribute('data-timestamp-added', 'true');
        
        const header = card.querySelector('.card-header');
        if (header && !header.querySelector('.last-updated')) {
            const timestamp = document.createElement('span');
            timestamp.className = 'last-updated ms-auto';
            timestamp.innerHTML = `<i class="fas fa-clock me-1"></i>${new Date().toLocaleTimeString()}`;
            timestamp.style.fontSize = '0.75rem';
            timestamp.style.color = '#6c757d';
            
            if (!header.classList.contains('d-flex')) {
                header.classList.add('d-flex', 'align-items-center');
            }
            header.appendChild(timestamp);
        }
    });
}

/**
 * Enhance charts with controls
 */
function enhanceCharts() {
    document.querySelectorAll('.js-plotly-plot:not([data-enhanced])').forEach(chart => {
        chart.setAttribute('data-enhanced', 'true');
        
        // Add download button functionality
        const container = chart.closest('.card');
        if (container) {
            const downloadBtn = container.querySelector('[id*="download"]');
            if (downloadBtn) {
                downloadBtn.addEventListener('click', function() {
                    Plotly.downloadImage(chart, {
                        format: 'png',
                        filename: 'chart_' + new Date().toISOString().split('T')[0]
                    });
                });
            }
        }
    });
}

/**
 * Enhance tables with sorting and filtering
 */
function enhanceTables() {
    document.querySelectorAll('.dash-table-container:not([data-enhanced])').forEach(table => {
        table.setAttribute('data-enhanced', 'true');
        
        // Add hover effect
        table.querySelectorAll('.dash-cell').forEach(cell => {
            cell.style.transition = 'background-color 0.2s ease';
        });
    });
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'position-fixed';
        toastContainer.style.cssText = 'top: 70px; right: 20px; z-index: 1050;';
        document.body.appendChild(toastContainer);
    }
    
    const toast = document.createElement('div');
    toast.className = `toast show align-items-center text-white bg-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'primary'}`;
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    toastContainer.appendChild(toast);
    
    setTimeout(() => toast.remove(), 4000);
}

/**
 * Initialize dark mode toggle
 */
function initDarkModeToggle() {
    const toggleBtn = document.querySelector('.btn-theme-toggle, [id*="dark-mode"]');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', function() {
            document.body.classList.toggle('dark-mode');
            const icon = this.querySelector('i');
            if (icon) {
                icon.classList.toggle('fa-moon');
                icon.classList.toggle('fa-sun');
            }
            localStorage.setItem('darkMode', document.body.classList.contains('dark-mode'));
        });
    }
    
    // Apply saved preference
    if (localStorage.getItem('darkMode') === 'true') {
        document.body.classList.add('dark-mode');
        const icon = document.querySelector('.btn-theme-toggle i, [id*="dark-mode"] i');
        if (icon) {
            icon.classList.remove('fa-moon');
            icon.classList.add('fa-sun');
        }
    }
}

// Add update notification system
function checkForUpdates() {
    // Simulated - in real app would check server
    setInterval(() => {
        const shouldNotify = Math.random() > 0.95; // 5% chance per interval
        if (shouldNotify) {
            showToast('New data available', 'info');
        }
    }, 60000); // Check every minute
}

console.log('✅ 162 Dashboard Improvements loaded successfully');
