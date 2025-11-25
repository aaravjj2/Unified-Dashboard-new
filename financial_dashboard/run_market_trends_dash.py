from dash import Dash
import modules.market_trends_new as mt_new
import os

app = Dash(__name__)
# Allow callbacks to reference components that may be added dynamically
app.config.suppress_callback_exceptions = True
app.layout = mt_new.layout
mt_new.register_callbacks(app)

if __name__ == '__main__':
    # Run with debug off in production-ish runner; prefer DASH_PORT, fall back to MT_PORT for compatibility.
    port = int(os.environ.get('DASH_PORT', os.environ.get('MT_PORT', '8050')))
    app.run(debug=False, port=port)
