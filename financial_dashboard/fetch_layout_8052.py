import urllib.request
import sys
u = 'http://127.0.0.1:8052/_dash-layout'
print('fetching', u)
try:
    with urllib.request.urlopen(u, timeout=10) as r:
        text = r.read().decode('utf-8')
    with open('_dash_layout_forecast_standalone.json', 'w', encoding='utf-8') as f:
        f.write(text)
    print('SAVED', len(text))
except Exception as e:
    print('ERROR', e)
    sys.exit(2)
