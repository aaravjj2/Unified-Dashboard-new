import importlib
import traceback

try:
    mf = importlib.import_module('Gradio.market_forecast')
    print('Loaded module:', mf.__file__)
    res = mf.run_forecast_for_ticker('AAPL', days=3, light=True, save_dir='forecast_outputs')
    print('Result keys:', list(res.keys()))
    print('csv_path:', res.get('csv_path'))
    try:
        df = res.get('forecast_df')
        print('forecast_df type:', type(df))
        try:
            print(df.head().to_string())
        except Exception:
            print('Could not print DataFrame preview')
    except Exception:
        print('No forecast_df in result')
except Exception:
    traceback.print_exc()
