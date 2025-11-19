from dash import Dash, html
import dash_bootstrap_components as dbc

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

app.layout = dbc.Container([
    html.H2('Market Analysis Dashboard'),
], fluid=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8050, use_reloader=False)
