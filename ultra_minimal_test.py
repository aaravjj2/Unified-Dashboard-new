"""
Ultra Minimal Test - Find what's hanging
"""
print("1. Starting...", flush=True)

print("2. Importing dash...", flush=True)
from dash import Dash, html
print("3. Dash imported OK", flush=True)

print("4. Creating app...", flush=True)
app = Dash(__name__)
print("5. App created OK", flush=True)

print("6. Setting layout...", flush=True)
app.layout = html.Div([html.H1("Test")])
print("7. Layout set OK", flush=True)

print("8. About to run server...", flush=True)
if __name__ == '__main__':
    app.run_server(debug=False, host='0.0.0.0', port=8050)
