/**
 * Universal Search (Cmd+K) Component
 * Implements #253 from ROADMAP_ULTIMATE.md
 */

// Search configuration
const SEARCH_CONFIG = {
    maxResults: 50,
    debounceMs: 150,
    recentItemsKey: 'dashboard_recent_searches',
    maxRecentItems: 10
};

// Search categories
const SEARCH_CATEGORIES = {
    tickers: {
        name: 'Tickers',
        icon: '📈',
        shortcut: 't:',
        color: '#4CAF50'
    },
    pages: {
        name: 'Pages',
        icon: '📄',
        shortcut: 'p:',
        color: '#2196F3'
    },
    actions: {
        name: 'Actions',
        icon: '⚡',
        shortcut: 'a:',
        color: '#FF9800'
    },
    strategies: {
        name: 'Strategies',
        icon: '🎯',
        shortcut: 's:',
        color: '#9C27B0'
    },
    settings: {
        name: 'Settings',
        icon: '⚙️',
        shortcut: 'set:',
        color: '#607D8B'
    }
};

// Pages registry
const PAGES = [
    { id: 'market-overview', name: 'Market Overview', path: '/market-overview', keywords: ['market', 'overview', 'dashboard', 'home'] },
    { id: 'options-lab', name: 'Options Lab', path: '/options-lab', keywords: ['options', 'greeks', 'volatility', 'chains'] },
    { id: 'volatility-lab', name: 'Volatility Lab', path: '/volatility-lab', keywords: ['vol', 'iv', 'surface', 'skew'] },
    { id: 'strategy-lab', name: 'Strategy Lab', path: '/strategy-lab', keywords: ['strategy', 'backtest', 'signals'] },
    { id: 'research-lab', name: 'Research Lab', path: '/research-lab', keywords: ['research', 'analysis', 'ai', 'ml'] },
    { id: 'portfolio', name: 'Portfolio', path: '/portfolio', keywords: ['portfolio', 'positions', 'holdings'] },
    { id: 'risk', name: 'Risk Analysis', path: '/risk', keywords: ['risk', 'var', 'drawdown', 'sharpe'] },
    { id: 'news', name: 'News & Sentiment', path: '/news', keywords: ['news', 'sentiment', 'headlines'] },
    { id: 'chatbot', name: 'AI Chat', path: '/chatbot', keywords: ['chat', 'ai', 'gpt', 'assistant'] },
    { id: 'market-forecast', name: 'Market Forecast', path: '/market-forecast', keywords: ['forecast', 'prediction', 'ml'] },
    { id: 'settings', name: 'Settings', path: '/settings', keywords: ['settings', 'preferences', 'config'] }
];

// Actions registry
const ACTIONS = [
    { id: 'refresh', name: 'Refresh Data', action: () => location.reload(), keywords: ['refresh', 'reload', 'update'] },
    { id: 'export', name: 'Export to Excel', action: () => triggerExport('excel'), keywords: ['export', 'excel', 'download'] },
    { id: 'export-pdf', name: 'Export to PDF', action: () => triggerExport('pdf'), keywords: ['export', 'pdf', 'report'] },
    { id: 'clear-cache', name: 'Clear Cache', action: () => clearCache(), keywords: ['clear', 'cache', 'reset'] },
    { id: 'toggle-dark', name: 'Toggle Theme', action: () => toggleTheme(), keywords: ['theme', 'dark', 'light', 'mode'] },
    { id: 'fullscreen', name: 'Toggle Fullscreen', action: () => toggleFullscreen(), keywords: ['fullscreen', 'expand'] },
    { id: 'help', name: 'Show Help', action: () => showHelp(), keywords: ['help', 'docs', 'documentation'] }
];

// Popular tickers
const POPULAR_TICKERS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AMD', 'NFLX', 'SPY',
    'QQQ', 'IWM', 'DIA', 'VIX', 'GLD', 'SLV', 'TLT', 'XLF', 'XLE', 'XLK'
];

class UniversalSearch {
    constructor() {
        this.isOpen = false;
        this.selectedIndex = 0;
        this.results = [];
        this.query = '';
        this.recentItems = this.loadRecentItems();
        
        this.init();
    }
    
    init() {
        // Create search modal
        this.createModal();
        
        // Add keyboard listeners
        document.addEventListener('keydown', (e) => this.handleKeydown(e));
    }
    
    createModal() {
        const modal = document.createElement('div');
        modal.id = 'universal-search-modal';
        modal.innerHTML = `
            <div class="us-overlay" onclick="universalSearch.close()"></div>
            <div class="us-container">
                <div class="us-header">
                    <span class="us-icon">🔍</span>
                    <input type="text" 
                           id="us-input" 
                           class="us-input" 
                           placeholder="Search anything... (type t: for tickers, p: for pages)"
                           autocomplete="off" />
                    <kbd class="us-kbd">ESC</kbd>
                </div>
                <div class="us-results" id="us-results"></div>
                <div class="us-footer">
                    <span><kbd>↑↓</kbd> Navigate</span>
                    <span><kbd>↵</kbd> Select</span>
                    <span><kbd>ESC</kbd> Close</span>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Add styles
        this.addStyles();
        
        // Input handler
        const input = document.getElementById('us-input');
        input.addEventListener('input', (e) => this.handleSearch(e.target.value));
    }
    
    addStyles() {
        const style = document.createElement('style');
        style.textContent = `
            #universal-search-modal {
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                z-index: 99999;
            }
            
            #universal-search-modal.open {
                display: flex;
                justify-content: center;
                padding-top: 15vh;
            }
            
            .us-overlay {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.7);
                backdrop-filter: blur(4px);
            }
            
            .us-container {
                position: relative;
                width: 600px;
                max-width: 90vw;
                max-height: 60vh;
                background: #1e1e2e;
                border-radius: 12px;
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
                overflow: hidden;
                display: flex;
                flex-direction: column;
            }
            
            .us-header {
                display: flex;
                align-items: center;
                padding: 16px;
                border-bottom: 1px solid #313244;
                gap: 12px;
            }
            
            .us-icon {
                font-size: 20px;
            }
            
            .us-input {
                flex: 1;
                background: transparent;
                border: none;
                outline: none;
                font-size: 18px;
                color: #cdd6f4;
            }
            
            .us-input::placeholder {
                color: #6c7086;
            }
            
            .us-kbd {
                background: #313244;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
                color: #a6adc8;
            }
            
            .us-results {
                flex: 1;
                overflow-y: auto;
                padding: 8px;
            }
            
            .us-category {
                padding: 8px 12px;
                font-size: 12px;
                font-weight: 600;
                color: #6c7086;
                text-transform: uppercase;
            }
            
            .us-result {
                display: flex;
                align-items: center;
                padding: 12px;
                margin: 2px 0;
                border-radius: 8px;
                cursor: pointer;
                transition: background 0.15s;
            }
            
            .us-result:hover,
            .us-result.selected {
                background: #313244;
            }
            
            .us-result-icon {
                width: 32px;
                height: 32px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 8px;
                margin-right: 12px;
                font-size: 16px;
            }
            
            .us-result-content {
                flex: 1;
            }
            
            .us-result-title {
                font-weight: 500;
                color: #cdd6f4;
            }
            
            .us-result-subtitle {
                font-size: 12px;
                color: #6c7086;
                margin-top: 2px;
            }
            
            .us-result-badge {
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 500;
            }
            
            .us-footer {
                display: flex;
                gap: 16px;
                padding: 12px 16px;
                border-top: 1px solid #313244;
                font-size: 12px;
                color: #6c7086;
            }
            
            .us-footer kbd {
                background: #313244;
                padding: 2px 6px;
                border-radius: 3px;
                margin-right: 4px;
            }
            
            .us-empty {
                padding: 40px;
                text-align: center;
                color: #6c7086;
            }
            
            .us-recent-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 8px 12px;
            }
            
            .us-clear-btn {
                font-size: 12px;
                color: #89b4fa;
                cursor: pointer;
            }
            
            .us-clear-btn:hover {
                text-decoration: underline;
            }
        `;
        document.head.appendChild(style);
    }
    
    handleKeydown(e) {
        // Cmd/Ctrl + K to open
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
            e.preventDefault();
            this.open();
            return;
        }
        
        if (!this.isOpen) return;
        
        switch (e.key) {
            case 'Escape':
                this.close();
                break;
            case 'ArrowDown':
                e.preventDefault();
                this.selectNext();
                break;
            case 'ArrowUp':
                e.preventDefault();
                this.selectPrev();
                break;
            case 'Enter':
                e.preventDefault();
                this.executeSelected();
                break;
        }
    }
    
    open() {
        const modal = document.getElementById('universal-search-modal');
        modal.classList.add('open');
        this.isOpen = true;
        
        const input = document.getElementById('us-input');
        input.value = '';
        input.focus();
        
        this.showRecentItems();
    }
    
    close() {
        const modal = document.getElementById('universal-search-modal');
        modal.classList.remove('open');
        this.isOpen = false;
        this.query = '';
        this.results = [];
        this.selectedIndex = 0;
    }
    
    handleSearch(query) {
        this.query = query.trim();
        
        if (!this.query) {
            this.showRecentItems();
            return;
        }
        
        this.results = [];
        
        // Check for category shortcuts
        const categoryMatch = this.query.match(/^([a-z]+):\s*(.*)$/i);
        if (categoryMatch) {
            const [, prefix, term] = categoryMatch;
            this.searchCategory(prefix.toLowerCase(), term);
        } else {
            // Search all categories
            this.searchAll(this.query);
        }
        
        this.renderResults();
    }
    
    searchAll(query) {
        const q = query.toLowerCase();
        
        // Search tickers
        POPULAR_TICKERS.forEach(ticker => {
            if (ticker.toLowerCase().includes(q)) {
                this.results.push({
                    type: 'ticker',
                    title: ticker,
                    subtitle: 'View ticker details',
                    icon: '📈',
                    color: SEARCH_CATEGORIES.tickers.color,
                    action: () => this.navigateToTicker(ticker)
                });
            }
        });
        
        // Search pages
        PAGES.forEach(page => {
            if (page.name.toLowerCase().includes(q) || 
                page.keywords.some(k => k.includes(q))) {
                this.results.push({
                    type: 'page',
                    title: page.name,
                    subtitle: page.path,
                    icon: '📄',
                    color: SEARCH_CATEGORIES.pages.color,
                    action: () => this.navigateToPage(page.path)
                });
            }
        });
        
        // Search actions
        ACTIONS.forEach(action => {
            if (action.name.toLowerCase().includes(q) ||
                action.keywords.some(k => k.includes(q))) {
                this.results.push({
                    type: 'action',
                    title: action.name,
                    subtitle: 'Action',
                    icon: '⚡',
                    color: SEARCH_CATEGORIES.actions.color,
                    action: action.action
                });
            }
        });
        
        // Limit results
        this.results = this.results.slice(0, SEARCH_CONFIG.maxResults);
    }
    
    searchCategory(prefix, term) {
        const q = term.toLowerCase();
        
        switch (prefix) {
            case 't':
            case 'ticker':
                POPULAR_TICKERS.forEach(ticker => {
                    if (!q || ticker.toLowerCase().includes(q)) {
                        this.results.push({
                            type: 'ticker',
                            title: ticker,
                            subtitle: 'View ticker details',
                            icon: '📈',
                            color: SEARCH_CATEGORIES.tickers.color,
                            action: () => this.navigateToTicker(ticker)
                        });
                    }
                });
                break;
                
            case 'p':
            case 'page':
                PAGES.forEach(page => {
                    if (!q || page.name.toLowerCase().includes(q)) {
                        this.results.push({
                            type: 'page',
                            title: page.name,
                            subtitle: page.path,
                            icon: '📄',
                            color: SEARCH_CATEGORIES.pages.color,
                            action: () => this.navigateToPage(page.path)
                        });
                    }
                });
                break;
                
            case 'a':
            case 'action':
                ACTIONS.forEach(action => {
                    if (!q || action.name.toLowerCase().includes(q)) {
                        this.results.push({
                            type: 'action',
                            title: action.name,
                            subtitle: 'Action',
                            icon: '⚡',
                            color: SEARCH_CATEGORIES.actions.color,
                            action: action.action
                        });
                    }
                });
                break;
        }
    }
    
    renderResults() {
        const container = document.getElementById('us-results');
        
        if (this.results.length === 0) {
            container.innerHTML = `
                <div class="us-empty">
                    No results found for "${this.query}"
                </div>
            `;
            return;
        }
        
        // Group by type
        const grouped = {};
        this.results.forEach((result, idx) => {
            if (!grouped[result.type]) grouped[result.type] = [];
            grouped[result.type].push({ ...result, idx });
        });
        
        let html = '';
        for (const [type, items] of Object.entries(grouped)) {
            const category = SEARCH_CATEGORIES[type + 's'] || { name: type, icon: '📌' };
            html += `<div class="us-category">${category.icon} ${category.name}</div>`;
            
            items.forEach(item => {
                const selected = item.idx === this.selectedIndex ? 'selected' : '';
                html += `
                    <div class="us-result ${selected}" 
                         data-idx="${item.idx}"
                         onclick="universalSearch.executeAt(${item.idx})">
                        <div class="us-result-icon" style="background: ${item.color}20; color: ${item.color}">
                            ${item.icon}
                        </div>
                        <div class="us-result-content">
                            <div class="us-result-title">${item.title}</div>
                            <div class="us-result-subtitle">${item.subtitle}</div>
                        </div>
                    </div>
                `;
            });
        }
        
        container.innerHTML = html;
    }
    
    showRecentItems() {
        const container = document.getElementById('us-results');
        
        if (this.recentItems.length === 0) {
            container.innerHTML = `
                <div class="us-empty">
                    Start typing to search...<br>
                    <small>Tip: Use t: for tickers, p: for pages</small>
                </div>
            `;
            return;
        }
        
        let html = `
            <div class="us-recent-header">
                <span class="us-category">Recent</span>
                <span class="us-clear-btn" onclick="universalSearch.clearRecent()">Clear</span>
            </div>
        `;
        
        this.results = this.recentItems.map((item, idx) => ({
            ...item,
            idx
        }));
        
        this.recentItems.forEach((item, idx) => {
            const selected = idx === this.selectedIndex ? 'selected' : '';
            html += `
                <div class="us-result ${selected}" 
                     data-idx="${idx}"
                     onclick="universalSearch.executeAt(${idx})">
                    <div class="us-result-icon" style="background: ${item.color}20; color: ${item.color}">
                        ${item.icon}
                    </div>
                    <div class="us-result-content">
                        <div class="us-result-title">${item.title}</div>
                        <div class="us-result-subtitle">${item.subtitle}</div>
                    </div>
                </div>
            `;
        });
        
        container.innerHTML = html;
    }
    
    selectNext() {
        if (this.results.length === 0) return;
        this.selectedIndex = (this.selectedIndex + 1) % this.results.length;
        this.updateSelection();
    }
    
    selectPrev() {
        if (this.results.length === 0) return;
        this.selectedIndex = (this.selectedIndex - 1 + this.results.length) % this.results.length;
        this.updateSelection();
    }
    
    updateSelection() {
        const results = document.querySelectorAll('.us-result');
        results.forEach((el, idx) => {
            el.classList.toggle('selected', idx === this.selectedIndex);
        });
        
        // Scroll into view
        const selected = document.querySelector('.us-result.selected');
        if (selected) {
            selected.scrollIntoView({ block: 'nearest' });
        }
    }
    
    executeSelected() {
        if (this.results.length === 0) return;
        this.executeAt(this.selectedIndex);
    }
    
    executeAt(idx) {
        const result = this.results[idx];
        if (!result) return;
        
        // Save to recent
        this.addToRecent(result);
        
        // Execute action
        if (result.action) {
            result.action();
        }
        
        this.close();
    }
    
    navigateToTicker(ticker) {
        // Navigate to ticker page or update ticker input
        const tickerInput = document.querySelector('input[id*="ticker"]');
        if (tickerInput) {
            tickerInput.value = ticker;
            tickerInput.dispatchEvent(new Event('input', { bubbles: true }));
        }
        // Also try to trigger any submit buttons
        const submitBtn = document.querySelector('button[id*="submit"], button[id*="analyze"]');
        if (submitBtn) submitBtn.click();
    }
    
    navigateToPage(path) {
        // For Dash apps, update URL
        window.history.pushState({}, '', path);
        window.dispatchEvent(new PopStateEvent('popstate'));
        
        // Also try clicking nav links
        const navLink = document.querySelector(`a[href="${path}"], [data-path="${path}"]`);
        if (navLink) navLink.click();
    }
    
    addToRecent(item) {
        const recentItem = {
            type: item.type,
            title: item.title,
            subtitle: item.subtitle,
            icon: item.icon,
            color: item.color,
            action: item.action
        };
        
        // Remove if exists
        this.recentItems = this.recentItems.filter(r => r.title !== item.title);
        
        // Add to front
        this.recentItems.unshift(recentItem);
        
        // Limit
        this.recentItems = this.recentItems.slice(0, SEARCH_CONFIG.maxRecentItems);
        
        this.saveRecentItems();
    }
    
    clearRecent() {
        this.recentItems = [];
        this.saveRecentItems();
        this.showRecentItems();
    }
    
    loadRecentItems() {
        try {
            const stored = localStorage.getItem(SEARCH_CONFIG.recentItemsKey);
            return stored ? JSON.parse(stored) : [];
        } catch {
            return [];
        }
    }
    
    saveRecentItems() {
        try {
            // Can't serialize functions, so store without action
            const toStore = this.recentItems.map(({ action, ...rest }) => rest);
            localStorage.setItem(SEARCH_CONFIG.recentItemsKey, JSON.stringify(toStore));
        } catch (e) {
            console.warn('Could not save recent items:', e);
        }
    }
}

// Helper functions
function triggerExport(format) {
    console.log('Exporting to', format);
    // Will be implemented by export service
    window.dispatchEvent(new CustomEvent('export-request', { detail: { format } }));
}

function clearCache() {
    localStorage.clear();
    sessionStorage.clear();
    console.log('Cache cleared');
    alert('Cache cleared successfully');
}

function toggleTheme() {
    document.body.classList.toggle('dark-theme');
}

function toggleFullscreen() {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen();
    } else {
        document.exitFullscreen();
    }
}

function showHelp() {
    window.open('/docs', '_blank');
}

// Initialize
let universalSearch;
document.addEventListener('DOMContentLoaded', () => {
    universalSearch = new UniversalSearch();
});

// Export for use in other modules
if (typeof module !== 'undefined') {
    module.exports = { UniversalSearch, SEARCH_CATEGORIES, PAGES, ACTIONS };
}
