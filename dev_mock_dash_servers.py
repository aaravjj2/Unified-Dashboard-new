#!/usr/bin/env python3
"""
Lightweight mock servers for local UI tests.

Serves minimal HTML for Analysis Hub (port 8054) and Research Lab (port 8058)
so Playwright clicker presence checks can run in CI or headless environments.
"""
from flask import Flask, Response
import threading


app_8054 = Flask("analysis_hub")
app_8058 = Flask("research_lab")


@app_8054.route("/")
def analysis_index():
    html = '''
    <html><head><title>Analysis Hub</title></head><body>
    <nav>
      <a class="nav-link">Attribution Analysis</a>
      <a class="nav-link">Portfolio Analytics</a>
      <a class="nav-link">Other Tab</a>
    </nav>
    <div id="content">Analysis Hub Mock</div>
    </body></html>
    '''
    return Response(html, mimetype='text/html')


@app_8058.route("/")
def research_index():
    html = '''
    <html><head><title>Research Lab</title></head><body>
    <nav>
      <a class="nav-link">Scenario Lab</a>
      <a class="nav-link">Research Notes</a>
    </nav>

    <!-- Scenario controls -->
    <div id="scenario-controls">
      <select id="scenario-type"><option value="macro">Macro</option><option value="factor">Factor</option></select>
      <select id="scenario-preset">
        <option value="">-- select --</option>
        <option value="momentum_crash">Momentum Crash</option>
        <option value="covid_crash">COVID-19 Crash</option>
      </select>
      <select id="scenario-universe">
        <option value="sp500">S&P 500</option>
        <option value="my_portfolio">My Portfolio</option>
      </select>
      <button id="scenario-run-btn">Run Scenario</button>
    </div>

    <div id="scenario-results" style="display:none">Results placeholder</div>

    <!-- Sliders -->
    <input type="range" id="scenario-spy-change" value="-25" />
    <input type="range" id="scenario-vix-change" value="15" />

    </body></html>
    '''
    return Response(html, mimetype='text/html')


def run_app(app, port):
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)


def main():
    t1 = threading.Thread(target=run_app, args=(app_8054, 8054), daemon=True)
    t2 = threading.Thread(target=run_app, args=(app_8058, 8058), daemon=True)
    t1.start()
    t2.start()
    print("Mock servers started: http://localhost:8054 and http://localhost:8058")
    try:
        # Keep main thread alive
        t1.join()
        t2.join()
    except KeyboardInterrupt:
        print("Shutting down mock servers")


if __name__ == '__main__':
    main()
