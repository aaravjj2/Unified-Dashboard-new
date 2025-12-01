import dash
from dash import html
import dash_bootstrap_components as dbc
import os

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = html.Div([
    html.H1("Minimal SSR Test v2"),
    html.P("If you can see this text in the initial HTML source, SSR is working.")
])

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8051))
    app.run(debug=True, host='0.0.0.0', port=port, use_reloader=False)
