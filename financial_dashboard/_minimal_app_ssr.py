import dash
from dash import html
import dash_bootstrap_components as dbc

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = html.Div([
    html.H1("Minimal SSR Test"),
    html.P("If you can see this text in the initial HTML source, SSR is working.")
])

if __name__ == '__main__':
    app.run(debug=True, port=8051, use_reloader=False)
