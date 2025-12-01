"""
Unified Financial Dashboard
Combines all 4 tabs into a single interface with iframes for each service
Run: python3 unified_dashboard.py
"""
from flask import Flask, render_template_string
import os

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Unified Financial Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
            color: #e6eef8;
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
            padding: 15px 30px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #60a5fa;
        }
        
        .header h1 {
            font-size: 28px;
            font-weight: 600;
            background: linear-gradient(135deg, #fff 0%, #93c5fd 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .header .time {
            font-size: 14px;
            color: #93c5fd;
        }
        
        /* Top-level navigation only - scope to #dashboard-top-nav to avoid styling nested navs */
        #dashboard-top-nav.nav-tabs {
            display: flex;
            background: #0f1729;
            border-bottom: 2px solid #1e3a8a;
            overflow-x: auto;
            white-space: nowrap;
        }

        #dashboard-top-nav.nav-tabs button {
            flex: 1;
            min-width: 150px;
            padding: 15px 25px;
            background: transparent;
            border: none;
            color: #94a3b8;
            font-size: 16px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
            position: relative;
            border-right: 1px solid #1e293b;
        }

        #dashboard-top-nav.nav-tabs button:last-child {
            border-right: none;
        }

        #dashboard-top-nav.nav-tabs button:hover {
            background: rgba(59, 130, 246, 0.1);
            color: #3b82f6;
        }

        #dashboard-top-nav.nav-tabs button.active {
            background: linear-gradient(180deg, rgba(59, 130, 246, 0.15) 0%, rgba(59, 130, 246, 0.05) 100%);
            color: #60a5fa;
            border-bottom: 3px solid #3b82f6;
        }

        #dashboard-top-nav.nav-tabs button::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 50%;
            transform: translateX(-50%) scaleX(0);
            width: 80%;
            height: 3px;
            background: linear-gradient(90deg, transparent, #3b82f6, transparent);
            transition: transform 0.3s ease;
        }

        #dashboard-top-nav.nav-tabs button.active::after {
            transform: translateX(-50%) scaleX(1);
        }
        
        .tab-content {
            height: calc(100vh - 130px);
            position: relative;
        }
        
        .tab-pane {
            display: none;
            width: 100%;
            height: 100%;
            position: absolute;
            top: 0;
            left: 0;
        }
        
        .tab-pane.active {
            display: block;
        }
        
        .tab-pane iframe {
            width: 100%;
            height: 100%;
            border: none;
            background: #0a0e27;
        }
        
        .loading {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            text-align: center;
            color: #64748b;
        }
        
        .loading::after {
            content: '...';
            display: inline-block;
            animation: dots 1.5s steps(4, end) infinite;
        }
        
        @keyframes dots {
            0%, 20% { content: '.'; }
            40% { content: '..'; }
            60%, 100% { content: '...'; }
        }
        
        .status-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 8px;
            background: #10b981;
            box-shadow: 0 0 8px rgba(16, 185, 129, 0.6);
            animation: pulse 2s ease-in-out infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .status-bar {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: #0f1729;
            padding: 8px 20px;
            font-size: 12px;
            color: #64748b;
            border-top: 1px solid #1e293b;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .refresh-btn {
            padding: 6px 15px;
            background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
            border: 1px solid #3b82f6;
            border-radius: 4px;
            color: white;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .refresh-btn:hover {
            background: linear-gradient(135deg, #3b82f6 0%, #60a5fa 100%);
            box-shadow: 0 2px 8px rgba(59, 130, 246, 0.4);
        }
        
        @media (max-width: 768px) {
            .header h1 {
                font-size: 20px;
            }
            .nav-tabs button {
                min-width: 120px;
                padding: 12px 15px;
                font-size: 14px;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Financial Dashboard</h1>
        <div class="time" id="current-time"></div>
    </div>
    
    <div id="dashboard-top-nav" class="nav-tabs">
        <button class="tab-btn active" data-tab="trends">
            <span class="status-indicator"></span>Market Trends
        </button>
        <button class="tab-btn" data-tab="forecast">
            <span class="status-indicator"></span>Market Forecast
        </button>
        <button class="tab-btn" data-tab="monthly">
            <span class="status-indicator"></span>Monthly Picks
        </button>
        <button class="tab-btn" data-tab="weekly">
            <span class="status-indicator"></span>Weekly Picks
        </button>
        <button class="tab-btn" data-tab="analysis">
            <span class="status-indicator"></span>Analysis Hub
        </button>
        <button class="tab-btn" data-tab="portfolio">
            <span class="status-indicator"></span>Portfolio
        </button>
        <button class="tab-btn" data-tab="research">
            <span class="status-indicator"></span>Research Lab
        </button>
    </div>
    
    <div class="tab-content">
        <div class="tab-pane active" id="trends-pane">
            <div class="loading">Loading Market Trends</div>
            <iframe src="http://localhost:8050" onload="this.previousElementSibling.style.display='none'"></iframe>
        </div>
        <div class="tab-pane" id="forecast-pane">
            <div class="loading">Loading Market Forecast</div>
            <iframe src="http://localhost:8051" onload="this.previousElementSibling.style.display='none'"></iframe>
        </div>
            <div class="tab-pane" id="monthly-pane">
                <div class="loading">Loading Monthly Picks</div>
                <iframe src="http://localhost:{monthly_port}" onload="this.previousElementSibling.style.display='none'"></iframe>
            </div>
            <div class="tab-pane" id="weekly-pane">
                <div class="loading">Loading Weekly Picks</div>
                <iframe src="http://localhost:{weekly_port}" onload="this.previousElementSibling.style.display='none'"></iframe>
            </div>
        <div class="tab-pane" id="analysis-pane">
            <div class="loading">Loading Analysis Hub</div>
            <iframe src="http://localhost:8054" onload="this.previousElementSibling.style.display='none'"></iframe>
        </div>
        <div class="tab-pane" id="portfolio-pane">
            <div class="loading">Loading Portfolio Dashboard</div>
            <iframe src="http://localhost:8056" onload="this.previousElementSibling.style.display='none'"></iframe>
        </div>
        <div class="tab-pane" id="research-pane">
            <div class="loading">Loading Research Lab</div>
            <iframe src="http://localhost:8058" onload="this.previousElementSibling.style.display='none'"></iframe>
        </div>
    </div>
    
    <div class="status-bar">
        <div>
            <span style="color: #10b981;">●</span> All services running
            <span style="margin-left: 20px; color: #64748b;">Ports: 8050-8054 (Phase 1-3) | 8056-8058 (Phase 4)</span>
        </div>
        <button class="refresh-btn" onclick="refreshCurrentTab()">⟳ Refresh</button>
    </div>
    
    <script>
        // Update time
        function updateTime() {
            const now = new Date();
            document.getElementById('current-time').textContent = now.toLocaleString('en-US', {
                weekday: 'short',
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        }
        setInterval(updateTime, 1000);
        updateTime();
        
        // Tab switching
        // Scope tab button listeners to the top-level nav only
        document.querySelectorAll('#dashboard-top-nav .tab-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const tabId = this.dataset.tab;

                // Update buttons (top nav only)
                document.querySelectorAll('#dashboard-top-nav .tab-btn').forEach(b => b.classList.remove('active'));
                this.classList.add('active');

                // Update panes
                document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
                document.getElementById(tabId + '-pane').classList.add('active');

                // Store active tab
                localStorage.setItem('activeTab', tabId);
            });
        });
        
        // Restore last active tab
        const lastTab = localStorage.getItem('activeTab');
        if (lastTab) {
            const btn = document.querySelector(`[data-tab="${lastTab}"]`);
            if (btn) btn.click();
        }
        
        // Refresh current tab
        function refreshCurrentTab() {
            const activePane = document.querySelector('.tab-pane.active');
            const iframe = activePane.querySelector('iframe');
            if (iframe) {
                iframe.src = iframe.src;
            }
        }
        
        // Keyboard shortcuts
        document.addEventListener('keydown', function(e) {
            // Ctrl/Cmd + 1-7 for tab switching
            if ((e.ctrlKey || e.metaKey) && e.key >= '1' && e.key <= '7') {
                e.preventDefault();
                const tabs = ['trends', 'forecast', 'monthly', 'weekly', 'analysis', 'portfolio', 'research'];
                const btn = document.querySelector(`[data-tab="${tabs[parseInt(e.key) - 1]}"]`);
                if (btn) btn.click();
            }
            // Ctrl/Cmd + R for refresh
            if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
                e.preventDefault();
                refreshCurrentTab();
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    # Render template with runtime ports for iframes so HTML matches actual bindings
    monthly_port = int(os.environ.get('MONTHLY_PICKS_PORT', 8052))
    weekly_port = int(os.environ.get('WEEKLY_PICKS_PORT', 8053))
    # Use simple replace to avoid interpreting CSS braces in the template via str.format
    rendered = HTML_TEMPLATE.replace('{monthly_port}', str(monthly_port)).replace('{weekly_port}', str(weekly_port))
    return render_template_string(rendered)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    print(f"\n{'='*60}")
    print(f"🚀 Unified Financial Dashboard")
    print(f"{'='*60}")
    print(f"Starting on http://0.0.0.0:{port}")
    print(f"\nRequired services:")
    print(f"  Phase 1-3:")
    print(f"    • Market Trends:   http://localhost:8050")
    print(f"    • Market Forecast: http://localhost:8051")
    monthly_port = int(os.environ.get('MONTHLY_PICKS_PORT', 8052))
    weekly_port = int(os.environ.get('WEEKLY_PICKS_PORT', 8053))
    print(f"    • Monthly Picks:   http://localhost:{monthly_port}")
    print(f"    • Weekly Picks:    http://localhost:{weekly_port}")
    print(f"    • Analysis Hub:    http://localhost:8054")
    print(f"  Phase 4:")
    print(f"    • Portfolio:       http://localhost:8056")
    print(f"    • Research Lab:    http://localhost:8058")
    print(f"\nKeyboard shortcuts:")
    print(f"  Ctrl+1-8: Switch between tabs")
    print(f"  Ctrl+R:   Refresh current tab")
    print(f"{'='*60}\n")
    
    # Also expose same rendered dashboard at /dashboard
    rendered = HTML_TEMPLATE.replace('{monthly_port}', str(monthly_port)).replace('{weekly_port}', str(weekly_port))
    @app.route('/dashboard')
    def dashboard_root():
        return render_template_string(rendered)

    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
