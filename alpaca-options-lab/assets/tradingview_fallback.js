// TradingView fallback shim
// Prevents attempts to load remote tradingview-widget.com resources
// Provides a minimal `TradingView` stub to avoid 403 errors and redirects chart rendering
(function(){
    try {
        if (!window.TradingView) {
            window.TradingView = {
                widget: function(config) {
                    console.warn('TradingView.widget() called — using local lightweight-charts fallback', config);
                    // Create a minimal stub element or call a provided render function
                    var container = null;
                    if (config && config.container_id) {
                        container = document.getElementById(config.container_id) || document.querySelector('#' + config.container_id);
                    }
                    if (container) {
                        container.innerHTML = '<div style="color:#94a3b8;padding:12px">TradingView widget blocked; using local LightweightCharts fallback.</div>';
                    }
                    return { onChartReady: function(cb){ if(cb) cb(); }, remove: function(){}};
                }
            };
        }

        // Intercept dynamic script insertions that try to load tradingview domains
        var origCreateElement = document.createElement.bind(document);
        document.createElement = function(tagName) {
            var el = origCreateElement(tagName);
            if (tagName && tagName.toLowerCase() === 'script') {
                Object.defineProperty(el, 'src', {
                    set: function(val) {
                        if (typeof val === 'string' && val.indexOf('tradingview') !== -1) {
                            console.warn('Blocked external TradingView script:', val);
                            // create a no-op src to avoid network call
                            this.setAttribute('data-blocked-tradingview-src', val);
                            return;
                        }
                        this.setAttribute('src', val);
                    },
                    get: function(){ return this.getAttribute('src'); }
                });
            }
            return el;
        };

        console.info('TradingView fallback shim initialized');
    } catch(e){
        console.error('TradingView fallback shim failed', e);
    }
})();
