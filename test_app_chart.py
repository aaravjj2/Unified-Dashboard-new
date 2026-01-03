
import sys
import os
import pandas as pd
sys.path.insert(0, '/home/aarav/Unified-Dashboard')

try:
    from financial_dashboard.dash.components.charting import render_tv_chart, generate_mock_ohlcv
    print("✅ Imports successful")
    
    df = generate_mock_ohlcv('SPY', days=10)
    print("✅ Mock data generated")
    
    layout = render_tv_chart(df, 'SPY')
    print("✅ render_tv_chart executed successfully")
    # print(layout)
    
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
