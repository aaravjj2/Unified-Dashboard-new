from src.utils.secrets import load_local_env, get_quandl_key
import requests
load_local_env()
key = get_quandl_key()
print("QUANDL key present?", bool(key))
if key:
    try:
        r = requests.get(f'https://data.nasdaq.com/api/v3/datasets/WIKI/AAPL.json?api_key={key}', timeout=10)
        print('status', r.status_code, r.reason)
        print(r.text[:400])
    except Exception as e:
        print('error', e)
else:
    print('no key to test')
