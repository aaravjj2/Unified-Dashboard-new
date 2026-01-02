/**
 * Hotkey System for Terminal UX
 * Phase 6 - Agent-Viz
 * 
 * Hotkeys:
 * - Shift+B: Focus Buy Ticket input
 * - Shift+C: Cancel All orders
 * - Shift+R: Refresh data
 * 
 * Theme: Alpaca Dark (#1E1E1E bg, #F5C211 accent)
 */

(function() {
    'use strict';

    // Alpaca Dark Theme Colors
    const ALPACA_DARK = {
        bg: '#1E1E1E',
        paper: '#252525',
        accent: '#F5C211',
        positive: '#00C853',
        negative: '#FF5252',
        text: '#E0E0E0',
        grid: '#333333'
    };

    // Hotkey configuration
    const HOTKEYS = {
        'Shift+B': {
            action: 'focusBuyTicket',
            description: 'Focus Buy Ticket'
        },
        'Shift+C': {
            action: 'cancelAll',
            description: 'Cancel All Orders'
        },
        'Shift+R': {
            action: 'refreshData',
            description: 'Refresh Data'
        },
        // Workspace navigation hotkeys
        'Ctrl+1': {
            action: 'switchWorkspace',
            description: 'Scanner Workspace',
            workspace: 'scanner-workspace-tab'
        },
        'Ctrl+2': {
            action: 'switchWorkspace',
            description: 'Strategy Workspace',
            workspace: 'strategy-workspace-tab'
        },
        'Ctrl+3': {
            action: 'switchWorkspace',
            description: 'Command Workspace',
            workspace: 'command-workspace-tab'
        },
        'Ctrl+4': {
            action: 'switchWorkspace',
            description: 'Admin Workspace',
            workspace: 'admin-workspace-tab'
        },
        'Ctrl+K': {
            action: 'openCommandPalette',
            description: 'Open Command Palette'
        }
    };

    // Track if hotkeys are enabled
    let hotkeysEnabled = true;

    /**
     * Focus the buy ticket input
     */
    function focusBuyTicket() {
        // Try multiple possible selectors for order ticket
        const selectors = [
            '#order-ticket-input',
            '#buy-ticket-input',
            '#ticker-input',
            '#market-viz-ticker-input',
            'input[placeholder*="ticker"]',
            'input[placeholder*="symbol"]',
            'input[placeholder*="Symbol"]',
            '.order-entry input[type="text"]',
            '.trade-ticket input'
        ];

        for (const selector of selectors) {
            const input = document.querySelector(selector);
            if (input) {
                input.focus();
                input.select();
                showNotification('Buy Ticket Focused', 'success');
                console.log('[Hotkeys] Shift+B: Focused', selector);
                return true;
            }
        }

        // If no specific input found, try the first visible text input
        const allInputs = document.querySelectorAll('input[type="text"]:not([style*="display: none"])');
        for (const input of allInputs) {
            if (input.offsetParent !== null) {
                input.focus();
                input.select();
                showNotification('Input Focused', 'success');
                console.log('[Hotkeys] Shift+B: Focused first visible input');
                return true;
            }
        }

        showNotification('No ticket input found', 'warning');
        console.warn('[Hotkeys] Shift+B: No ticket input found');
        return false;
    }

    /**
     * Trigger cancel all orders
     */
    function cancelAll() {
        // Try to find and click cancel all button
        const cancelSelectors = [
            '#cancel-all-btn',
            '#cancel-all-orders',
            'button[data-action="cancel-all"]',
            '.cancel-all-button',
            'button:contains("Cancel All")'
        ];

        for (const selector of cancelSelectors) {
            const btn = document.querySelector(selector);
            if (btn) {
                btn.click();
                showNotification('Cancel All Triggered', 'negative');
                console.log('[Hotkeys] Shift+C: Clicked', selector);
                return true;
            }
        }

        // Fallback: dispatch custom event
        const event = new CustomEvent('cancelAllOrders', {
            bubbles: true,
            detail: { source: 'hotkey' }
        });
        document.dispatchEvent(event);
        showNotification('Cancel All Signal Sent', 'warning');
        console.log('[Hotkeys] Shift+C: Dispatched cancelAllOrders event');
        return true;
    }

    /**
     * Switch to a specific workspace tab
     */
    function switchWorkspace(workspaceId, description) {
        // Find the Dash tabs component
        const tabsContainer = document.querySelector('#main-workspace-tabs');
        if (!tabsContainer) {
            console.warn('[Hotkeys] Tabs container not found');
            showNotification('Tabs not found', 'warning');
            return false;
        }

        // Find and click the correct tab
        const tabs = tabsContainer.querySelectorAll('.tab');
        const tabMapping = {
            'scanner-workspace-tab': 0,
            'strategy-workspace-tab': 1,
            'command-workspace-tab': 2,
            'admin-workspace-tab': 3
        };

        const tabIndex = tabMapping[workspaceId];
        if (tabIndex !== undefined && tabs[tabIndex]) {
            tabs[tabIndex].click();
            showNotification(`Switched to ${description}`, 'success');
            console.log(`[Hotkeys] Switched to ${workspaceId}`);
            return true;
        }

        // Fallback: Try using Dash's setProps pattern
        try {
            // Dispatch a custom event that can be caught by clientside callbacks
            const event = new CustomEvent('workspaceSwitch', {
                bubbles: true,
                detail: { workspace: workspaceId, description: description }
            });
            document.dispatchEvent(event);

            // Also try to find React fiber and trigger change
            const reactKey = Object.keys(tabsContainer).find(key => key.startsWith('__reactFiber'));
            if (reactKey) {
                // This is a React component - dispatch via Dash callback system
                if (window.dash_clientside && window.dash_clientside.set_props) {
                    window.dash_clientside.set_props('main-workspace-tabs', { value: workspaceId });
                }
            }

            showNotification(`Switching to ${description}...`, 'info');
            return true;
        } catch (e) {
            console.error('[Hotkeys] Error switching workspace:', e);
            showNotification('Failed to switch workspace', 'negative');
            return false;
        }
    }

    /**
     * Open command palette modal
     */
    function openCommandPalette() {
        // Try to find and click the command palette trigger
        const triggerBtn = document.querySelector('#command-palette-trigger');
        if (triggerBtn) {
            triggerBtn.click();
            showNotification('Command Palette', 'info');
            console.log('[Hotkeys] Ctrl+K: Opened Command Palette');
            return true;
        }

        // Fallback: dispatch custom event
        const event = new CustomEvent('openCommandPalette', {
            bubbles: true,
            detail: { source: 'hotkey' }
        });
        document.dispatchEvent(event);
        showNotification('Opening Command Palette...', 'info');
        return true;
    }

    /**
     * Trigger data refresh
     */
    function refreshData() {
        // Try to find and click refresh button
        const refreshSelectors = [
            '#market-viz-refresh-btn',
            '#refresh-data-btn',
            '#refresh-btn',
            'button[data-action="refresh"]',
            '.refresh-button',
            'button:contains("Refresh")'
        ];

        for (const selector of refreshSelectors) {
            const btn = document.querySelector(selector);
            if (btn) {
                btn.click();
                showNotification('Data Refreshed', 'success');
                console.log('[Hotkeys] Shift+R: Clicked', selector);
                return true;
            }
        }

        // Fallback: dispatch custom event
        const event = new CustomEvent('refreshData', {
            bubbles: true,
            detail: { source: 'hotkey' }
        });
        document.dispatchEvent(event);
        showNotification('Refresh Signal Sent', 'info');
        console.log('[Hotkeys] Shift+R: Dispatched refreshData event');
        return true;
    }

    /**
     * Show a notification toast
     */
    function showNotification(message, type = 'info') {
        // Remove existing notifications
        const existing = document.querySelectorAll('.hotkey-notification');
        existing.forEach(el => el.remove());

        // Create notification
        const notification = document.createElement('div');
        notification.className = 'hotkey-notification';
        notification.textContent = message;

        // Style based on type
        const colors = {
            success: ALPACA_DARK.positive,
            negative: ALPACA_DARK.negative,
            warning: ALPACA_DARK.accent,
            info: ALPACA_DARK.text
        };

        Object.assign(notification.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            padding: '12px 24px',
            backgroundColor: ALPACA_DARK.paper,
            color: colors[type] || ALPACA_DARK.text,
            border: `2px solid ${colors[type] || ALPACA_DARK.grid}`,
            borderRadius: '8px',
            fontFamily: 'system-ui, sans-serif',
            fontSize: '14px',
            fontWeight: 'bold',
            zIndex: '10000',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
            animation: 'slideIn 0.3s ease-out'
        });

        document.body.appendChild(notification);

        // Auto-remove after 2 seconds
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(100px)';
            notification.style.transition = 'all 0.3s ease-in';
            setTimeout(() => notification.remove(), 300);
        }, 2000);
    }

    /**
     * Handle keydown events
     */
    function handleKeydown(event) {
        if (!hotkeysEnabled) return;

        // Build key combo string
        let combo = '';
        if (event.shiftKey) combo += 'Shift+';
        if (event.ctrlKey) combo += 'Ctrl+';
        if (event.altKey) combo += 'Alt+';
        if (event.metaKey) combo += 'Meta+';
        combo += event.key.toUpperCase();

        // Check for matching hotkey
        const hotkey = HOTKEYS[combo];
        if (hotkey) {
            event.preventDefault();
            event.stopPropagation();

            console.log(`[Hotkeys] Triggered: ${combo} -> ${hotkey.description}`);

                switch (hotkey.action) {
                case 'focusBuyTicket':
                    focusBuyTicket();
                    break;
                case 'cancelAll':
                    cancelAll();
                    break;
                case 'refreshData':
                    refreshData();
                    break;
                case 'switchWorkspace':
                    switchWorkspace(hotkey.workspace, hotkey.description);
                    break;
                case 'openCommandPalette':
                    openCommandPalette();
                    break;
            }
        }
    }

    /**
     * Apply Alpaca Dark theme to charts
     */
    function enforceAlpacaDarkTheme() {
        // Target Plotly charts
        const plotlyCharts = document.querySelectorAll('.js-plotly-plot');
        
        plotlyCharts.forEach(chart => {
            if (chart._fullLayout) {
                // Check if already themed
                if (chart._fullLayout.paper_bgcolor === ALPACA_DARK.paper) return;

                // Update layout
                try {
                    Plotly.relayout(chart, {
                        'paper_bgcolor': ALPACA_DARK.paper,
                        'plot_bgcolor': ALPACA_DARK.bg,
                        'font.color': ALPACA_DARK.text,
                        'xaxis.gridcolor': ALPACA_DARK.grid,
                        'yaxis.gridcolor': ALPACA_DARK.grid,
                        'xaxis.tickfont.color': ALPACA_DARK.text,
                        'yaxis.tickfont.color': ALPACA_DARK.text
                    });
                    console.log('[Theme] Applied Alpaca Dark to chart');
                } catch (e) {
                    console.debug('[Theme] Could not restyle chart:', e);
                }
            }
        });

        // Target dash tables
        const tables = document.querySelectorAll('.dash-table-container');
        tables.forEach(table => {
            table.style.backgroundColor = ALPACA_DARK.bg;
        });
    }

    /**
     * Create hotkey hint panel
     */
    function createHotkeyHintPanel() {
        const panel = document.createElement('div');
        panel.id = 'hotkey-hint-panel';
        panel.innerHTML = `
            <div style="font-weight:bold;margin-bottom:8px;color:${ALPACA_DARK.accent}">⌨️ Hotkeys</div>
            <div style="font-size:11px">
                <div style="margin-bottom:4px;color:#9ca3af">Navigation:</div>
                <div><kbd>Ctrl+1</kbd> Scanner</div>
                <div><kbd>Ctrl+2</kbd> Strategy</div>
                <div><kbd>Ctrl+3</kbd> Command</div>
                <div><kbd>Ctrl+4</kbd> Admin</div>
                <div><kbd>Ctrl+K</kbd> Cmd Palette</div>
                <div style="margin-top:8px;margin-bottom:4px;color:#9ca3af">Trading:</div>
                <div><kbd>Shift+B</kbd> Buy Ticket</div>
                <div><kbd>Shift+C</kbd> Cancel All</div>
                <div><kbd>Shift+R</kbd> Refresh</div>
            </div>
        `;
        
        Object.assign(panel.style, {
            position: 'fixed',
            bottom: '20px',
            right: '20px',
            padding: '12px 16px',
            backgroundColor: ALPACA_DARK.paper,
            color: ALPACA_DARK.text,
            borderRadius: '8px',
            border: `1px solid ${ALPACA_DARK.grid}`,
            fontFamily: 'system-ui, sans-serif',
            fontSize: '12px',
            zIndex: '9999',
            boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
            opacity: '0.7',
            transition: 'opacity 0.2s'
        });

        panel.addEventListener('mouseenter', () => panel.style.opacity = '1');
        panel.addEventListener('mouseleave', () => panel.style.opacity = '0.7');

        // Style kbd elements
        const style = document.createElement('style');
        style.textContent = `
            #hotkey-hint-panel kbd {
                background: ${ALPACA_DARK.bg};
                padding: 2px 6px;
                border-radius: 4px;
                border: 1px solid ${ALPACA_DARK.grid};
                font-family: monospace;
                margin-right: 4px;
            }
            @keyframes slideIn {
                from { transform: translateX(100px); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
        `;
        document.head.appendChild(style);

        return panel;
    }

    /**
     * Initialize hotkey system
     */
    function init() {
        console.log('[Hotkeys] Initializing Terminal UX hotkey system...');

        // Add keydown listener
        document.addEventListener('keydown', handleKeydown, true);

        // Add hotkey hint panel
        if (!document.getElementById('hotkey-hint-panel')) {
            const panel = createHotkeyHintPanel();
            document.body.appendChild(panel);
        }

        // Apply theme enforcement on mutation
        const observer = new MutationObserver((mutations) => {
            let shouldEnforce = false;
            mutations.forEach(mutation => {
                if (mutation.addedNodes.length > 0) {
                    mutation.addedNodes.forEach(node => {
                        if (node.nodeType === 1 && 
                            (node.classList?.contains('js-plotly-plot') ||
                             node.querySelector?.('.js-plotly-plot'))) {
                            shouldEnforce = true;
                        }
                    });
                }
            });
            if (shouldEnforce) {
                setTimeout(enforceAlpacaDarkTheme, 100);
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        // Initial theme enforcement
        setTimeout(enforceAlpacaDarkTheme, 500);

        console.log('[Hotkeys] Terminal UX initialized');
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Expose API for Dash callbacks
    window.TerminalUX = {
        hotkeysEnabled: () => hotkeysEnabled,
        enableHotkeys: () => { hotkeysEnabled = true; },
        disableHotkeys: () => { hotkeysEnabled = false; },
        showNotification: showNotification,
        enforceTheme: enforceAlpacaDarkTheme
    };

})();
