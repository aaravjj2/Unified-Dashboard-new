from dash_extensions.enrich import DashProxy, MultiplexerTransform, dcc, html

# Initialize DashProxy with all arguments as keywords to avoid conflicts.
app = DashProxy(name=__name__, transforms=[MultiplexerTransform()])

app.layout = html.Div([
    html.H1("Minimal Test Case"),
    dcc.Input(id="input", placeholder="input..."),
    html.Div(id="output")
])

if __name__ == '__main__':
    app.run(debug=True, port=8051)
