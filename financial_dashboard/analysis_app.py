"""
Analysis Hub - Standalone Dash App
Combines Attribution Analysis and Scenario Testing
Run: python3 analysis_app.py
Port: 8054
"""
import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Import the analysis tab (prefer the richer attribution_analysis when available)
sys.path.insert(0, str(Path(__file__).parent))
try:
    from tabs import attribution_analysis as analysis_tab
except Exception:
    try:
        from tabs import analysis as analysis_tab
    except Exception:
        # Fallback: attempt dynamic load if package __init__ doesn't expose the module
        an_path = str(Path(__file__).parent.joinpath('tabs', 'analysis.py'))
        if Path(an_path).exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location('tabs.analysis', an_path)
            if spec is None:
                raise ImportError(f"Could not create ModuleSpec for analysis tab: {an_path}")
            mod = importlib.util.module_from_spec(spec)
            loader = getattr(spec, 'loader', None)
            if loader is None:
                raise ImportError(f"ModuleSpec.loader is missing for analysis tab: {an_path}")
            # Execute module via loader to avoid type-checker/None warnings
            loader.exec_module(mod)
            analysis_tab = mod
        else:
            raise

# Phase 6: Import Azure ML SHAP and Options Forecast callbacks
# These callbacks auto-register via @callback decorator
try:
    from tabs.azure_ml_lab.phase6_azure_integration import phase6_ui_callbacks
    print("✅ Phase 6 Azure ML callbacks loaded successfully")
except ImportError as e:
    print(f"⚠️ Phase 6 callbacks not available: {e}")
except Exception as e:
    print(f"❌ Error loading Phase 6 callbacks: {e}")

# Initialize Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.CYBORG,
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css"
    ],
    suppress_callback_exceptions=True,
    title="Analysis Hub"
)

# Custom CSS to ensure tabs are visible
import os

# Allow enabling client-side diagnostics via environment variable.
_ANALYSIS_HUB_DEBUG = os.getenv('ANALYSIS_HUB_DEBUG', '0') == '1'

debug_script = '<script>window.__ANALYSIS_HUB_DEBUG = %s;</script>\n' % ('true' if _ANALYSIS_HUB_DEBUG else 'false')

# Ensure the DOCTYPE is the very first line in the served document so browsers do not render
# the page in Quirks Mode. Place the debug script after the DOCTYPE inside the <head>.
app.index_string = '<!DOCTYPE html>\n' + debug_script + '''
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            /* Ensure body is visible with proper background */
            body {
                background-color: #222629 !important;
                color: #ffffff !important;
                min-height: 100vh !important;
                margin: 0 !important;
                padding: 0 !important;
            }
            
            /* Make sure all containers are visible */
            .container, .container-fluid {
                min-height: 100vh !important;
                padding: 20px !important;
            }
            
            /* Ensure tabs are visible and styled properly */
            .nav-tabs {
                border-bottom: 2px solid #2c3e50 !important;
                margin-bottom: 20px !important;
                background-color: transparent !important;
            }
            .nav-tabs .nav-link {
                color: #adb5bd !important;
                font-size: 16px !important;
                padding: 12px 20px !important;
                border: none !important;
                cursor: pointer !important;
                background-color: transparent !important;
            }
            .nav-tabs .nav-link.active {
                color: #00bc8c !important;
                background-color: rgba(0, 188, 140, 0.1) !important;
                border-bottom: 3px solid #00bc8c !important;
            }
            .nav-tabs .nav-link:hover {
                color: #ffffff !important;
                border-color: transparent !important;
                background-color: rgba(255, 255, 255, 0.05) !important;
            }
            .tab-content {
                margin-top: 20px !important;
                min-height: 600px !important;
                display: block !important;
                visibility: visible !important;
                opacity: 1 !important;
            }
            
            /* Standard behavior for tab panes: hidden unless active. We will
               programmatically mark the first tab active so the UI shows the
               expected initial content for tests and the browser. */
            .tab-pane {
                display: none !important;
            }
            .tab-pane.active {
                display: block !important;
                visibility: visible !important;
                opacity: 1 !important;
            }
            
            /* Fix for form inputs */
            .form-control, .Select-control {
                background-color: #222 !important;
                border: 1px solid #444 !important;
                color: #fff !important;
            }
            
            /* Ensure cards are visible */
            .card {
                background-color: #2b3035 !important;
                border: 1px solid #3a3f44 !important;
                color: #ffffff !important;
            }
            
            /* Ensure all text is visible */
            h1, h2, h3, h4, h5, h6, p, label, div {
                color: #ffffff !important;
            }
            
            .text-muted {
                color: #adb5bd !important;
            }
    </style>
    <!-- server-injected debug flag inserted above -->
        <script>
            // Inline diagnostic helpers (temporary) - logs early client errors and network failures
            (function(){
                if(!window.__ANALYSIS_HUB_DEBUG) return;
                try{
                    console.log('[diag] Analysis Hub client diagnostics enabled');

                    window.addEventListener('error', function(ev){
                        try{ console.error('[diag] window.onerror', ev && ev.message, ev && ev.filename, ev && ev.lineno, ev && ev.colno, ev && ev.error); }catch(e){}
                    });

                    window.addEventListener('unhandledrejection', function(ev){
                        try{ console.error('[diag] unhandledrejection', ev && ev.reason); }catch(e){}
                    });

                    // Wrap fetch to log rejections early
                    if(window.fetch){
                        const _fetch = window.fetch.bind(window);
                        // Retry wrapper for fetch POSTs to Dash update endpoint to handle transient aborts
                        window.fetch = function(input, init){
                            try{
                                const url = (typeof input === 'string') ? input : (input && input.url);
                                const method = (init && init.method) || (typeof input !== 'string' && input && input.method) || 'GET';

                                // Only wrap retries for POSTs to the Dash update endpoint
                                if(method && method.toUpperCase() === 'POST' && url && url.indexOf('/_dash-update-component') !== -1){
                                    const maxRetries = 3;
                                    const baseDelay = 150; // ms
                                    let attempt = 0;

                                    // maintain a short-term counter of aborted/failed dash POSTs
                                    if(!window.__dash_aborted_counter) window.__dash_aborted_counter = {count:0, ts:Date.now()};

                                    const doFetch = function(){
                                        attempt++;
                                        return _fetch(input, init).catch(function(err){
                                                try{ console.error('[diag] fetch failed', url, 'attempt', attempt, err); }catch(e){}
                                                try{
                                                    // increment recent abort counter
                                                    const now = Date.now();
                                                    if(now - window.__dash_aborted_counter.ts > 5000){
                                                        // reset window for new window
                                                        window.__dash_aborted_counter.count = 0;
                                                        window.__dash_aborted_counter.ts = now;
                                                    }
                                                    window.__dash_aborted_counter.count += 1;
                                                    // if many aborts in short time, trigger a soft reload to recover
                                                    if(window.__dash_aborted_counter.count >= 3){
                                                        console.warn('[diag] multiple dash POST failures detected, reloading page to recover');
                                                        setTimeout(function(){ try{ window.location.reload(); }catch(_){ } }, 250);
                                                    }
                                                }catch(e){}
                                            if(attempt < maxRetries){
                                                const backoff = baseDelay * Math.pow(2, attempt-1);
                                                return new Promise(function(resolve){
                                                    setTimeout(function(){ resolve(doFetch()); }, backoff);
                                                });
                                            }
                                            throw err;
                                        });
                                    };

                                    return doFetch();
                                }
                            }catch(e){
                                try{ console.error('[diag] fetch wrapper error', e); }catch(_){ }
                            }
                            return _fetch.apply(this, arguments).catch(function(err){
                                try{ console.error('[diag] fetch failed', arguments && arguments[0], err); }catch(e){}
                                throw err;
                            });
                        };
                    }

                    // Monitor XHR aborts/errors
                    try{
                        const _open = XMLHttpRequest.prototype.open;
                        XMLHttpRequest.prototype.open = function(){
                            try{
                                this.addEventListener('error', function(){ try{ console.error('[diag] XHR error', this && this.responseURL); }catch(e){} });
                                this.addEventListener('abort', function(){ try{ console.error('[diag] XHR abort', this && this.responseURL); }catch(e){} });

                                // If this XHR is a POST to /_dash-update-component, add a simple retry-on-abort behavior
                                const _onreadystatechange = this.onreadystatechange;
                                this.onreadystatechange = function(){
                                    try{
                                        if(this.readyState === 4 && this.status === 0 && this.responseURL && this.responseURL.indexOf('/_dash-update-component')!==-1){
                                            // status 0 often indicates an abort; attempt a single retry after a short delay
                                            setTimeout(function(){
                                                try{
                                                    const retryXhr = new XMLHttpRequest();
                                                    retryXhr.open('POST', this.responseURL);
                                                    // copy headers if possible (best-effort)
                                                    // Note: we don't re-send the original body reliably here, so rely on fetch wrapper for major retries
                                                    retryXhr.send();
                                                    console.warn('[diag] XHR retry attempted for', this.responseURL);
                                                }catch(e){ console.error('[diag] XHR retry failed', e); }
                                            }.bind(this), 200);
                                        }
                                    }catch(e){}
                                    if(typeof _onreadystatechange === 'function'){
                                        try{ _onreadystatechange.apply(this, arguments); }catch(e){}
                                    }
                                };
                            }catch(e){}
                            return _open.apply(this, arguments);
                        };
                    }catch(e){}

                    // Small hook to detect when Dash renderer script runs (it sets window.dash_clientside)
                    (function pollRenderer(attempts){
                        try{
                            if(window.dash_clientside || window.dash_renderer){
                                console.log('[diag] Dash renderer detected', {dash_clientside: !!window.dash_clientside, dash_renderer: !!window.dash_renderer});
                                return;
                            }
                        }catch(e){}
                        if(attempts>60) return; // stop after ~60 attempts (~6s)
                        setTimeout(function(){ pollRenderer(attempts+1); }, 100);
                    })(0);

                }catch(e){
                    try{ console.error('[diag] failed to install diagnostics', e); }catch(_){ }
                }
            })();
        </script>
        <script>
            // Passive MutationObserver logger: record class/style mutations on
            // tab-related nodes so we can trace what code is toggling visibility
            // without mutating the DOM ourselves. This avoids interfering with
            // Dash/Bootstrap tab behavior while still providing diagnostics.
            (function(){
                if(!window.__ANALYSIS_HUB_DEBUG) return;
                try{
                    function startLogging(){
                        try{
                            console.log('[diag-mutation] installing passive MutationObserver for tab nodes');
                            var selector = '.nav-tabs, .nav-tabs .nav-link, .tab-content, .tab-content .tab-pane';
                            var roots = document.querySelectorAll('.nav-tabs, .tab-content');
                            if(!roots || roots.length===0){
                                // nothing to observe yet; schedule a retry
                                setTimeout(startLogging, 250);
                                return;
                            }

                            var obs = new MutationObserver(function(mutations){
                                try{
                                    mutations.forEach(function(m){
                                        // Log class and attribute changes concisely
                                        if(m.type === 'attributes'){
                                            try{
                                                var t = m.target;
                                                if(t && (t.classList || t.getAttribute)){
                                                    console.log('[diag-mutation] ATTR:', t.tagName, 'id='+(t.id||''), 'class='+ (t.className||''), 'aria-selected='+t.getAttribute && t.getAttribute('aria-selected'));
                                                }
                                            }catch(_e){}
                                        } else if(m.type === 'childList'){
                                            try{
                                                console.log('[diag-mutation] CHILDLIST:', m.addedNodes && m.addedNodes.length, 'added,', m.removedNodes && m.removedNodes.length, 'removed');
                                            }catch(_e){}
                                        }
                                    });
                                }catch(e){ console.warn('[diag-mutation] observer callback error', e); }
                            });

                            roots.forEach(function(r){ obs.observe(r, { attributes: true, childList: true, subtree: true, attributeFilter: ['class', 'style', 'aria-selected'] }); });
                        }catch(e){ console.warn('[diag-mutation] startLogging failed', e); }
                    }

                    document.addEventListener('DOMContentLoaded', function(){ startLogging(); });
                    // Also attempt to start immediately in case DOMContentLoaded already fired
                    try{ startLogging(); }catch(e){}
                }catch(e){ console.warn('[diag-mutation] install failed', e); }
            })();
        </script>
        <script>
            // Diagnostics: log computed styles for key elements and optionally
            // force them visible if the pane remains hidden in some browsers.
            (function(){
                if(!window.__ANALYSIS_HUB_DEBUG) return;
                try{
                    function diagLog(){
                        try{
                            console.log('[diag-style] starting computed-style checks');
                            var pane = document.querySelector('.tab-content .tab-pane');
                            var runBtn = document.getElementById('attr-run-button');
                            var results = document.getElementById('attr-results-container');

                            function dump(el, name){
                                if(!el){ console.log('[diag-style] %s: MISSING', name); return; }
                                var cs = window.getComputedStyle(el);
                                console.log('[diag-style] %s: classList=%o, display=%s, visibility=%s, opacity=%s, height=%s, aria-hidden=%s',
                                          name, el.className, cs.display, cs.visibility, cs.opacity, cs.height, el.getAttribute('aria-hidden'));
                            }

                            dump(pane, 'first-pane');
                            dump(runBtn, 'attr-run-button');
                            dump(results, 'attr-results-container');
                        }catch(e){ console.warn('[diag-style] dump failed', e); }
                    }

                    document.addEventListener('DOMContentLoaded', function(){
                        try{
                            // Run immediately and again after a short delay to catch async changes
                            diagLog();
                            setTimeout(function(){
                                try{
                                    diagLog();
                                    // If the pane or results container appears hidden, log a warning
                                    // but do NOT mutate styles. The passive mutation logger will
                                    // record subsequent changes so we can trace the source.
                                    try{
                                        var pane = document.querySelector('.tab-content .tab-pane');
                                        if(pane){
                                            var cs = window.getComputedStyle(pane);
                                            if(cs.display === 'none' || cs.visibility === 'hidden' || cs.opacity === '0'){
                                                console.warn('[diag-style] pane still hidden (no auto-fix applied); computed style=', cs.display, cs.visibility, cs.opacity);
                                            }
                                        }
                                        var results = document.getElementById('attr-results-container');
                                        if(results){
                                            var cr = window.getComputedStyle(results);
                                            if(cr.display === 'none' || cr.visibility === 'hidden' || cr.opacity === '0'){
                                                console.warn('[diag-style] results container hidden (no auto-fix applied); computed style=', cr.display, cr.visibility, cr.opacity);
                                            }
                                        }
                                    }catch(e){ console.warn('[diag-style] detect-only failed', e); }
                                    // re-run the dump so we can observe the new computed styles in the console
                                    try{ diagLog(); }catch(_e){}
                                }catch(e){ console.warn('[diag-style] timed dump failed', e); }
                            }, 600);
                        }catch(e){ console.warn('[diag-style] DOMContentLoaded handler failed', e); }
                    });
                }catch(e){ console.warn('[diag-style] install failed', e); }
            })();
        </script>
    </head>
    <body>
        {%app_entry%}
        <footer>
            <!-- Inject test helper to expose persisted prices to client for E2E tests -->
            <script src="/assets/inject_prices.js"></script>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Set app layout from the analysis tab (no duplicate header)
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            analysis_tab.layout()
        ])
    ])
], fluid=True)

# Register callbacks from the analysis tab
analysis_tab.register_callbacks(app)

if __name__ == '__main__':
    port = 8054
    print(f"\n{'='*60}")
    print(f"📈 Analysis Hub - Standalone Service")
    print(f"{'='*60}")
    print(f"Starting on http://0.0.0.0:{port}")
    print(f"\nFeatures:")
    print(f"  • Attribution Analysis (Alpha/Beta breakdown)")
    print(f"  • Scenario Testing (Macro sensitivity analysis)")
    print(f"\nThis service is designed to be embedded in the unified dashboard")
    print(f"Access directly: http://localhost:{port}")
    print(f"Or via unified dashboard: http://localhost:8000")
    print(f"{'='*60}\n")
    
    app.run(host='0.0.0.0', port=port, debug=False)
