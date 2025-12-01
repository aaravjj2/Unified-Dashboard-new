import sys
sys.path.insert(0, '/app/financial_dashboard')

from services.options_connector import get_options_chain, OptionsConnector
from volatility.iv_surface import calculate_iv_surface, interpolate_iv_surface
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

print("🧪 Testing IV Surface with 7+ day expiration\n")

# Get expirations
connector = OptionsConnector()
all_exps = connector.get_available_expirations('SPY')

# Filter >7 days
today = datetime.now()
min_date = today + timedelta(days=7)
filtered = [e for e in all_exps if datetime.strptime(e, '%Y-%m-%d') > min_date]

print(f"Total expirations: {len(all_exps)}")
print(f"Filtered (>7 days): {len(filtered)}")
print(f"Using: {filtered[0]}\n")

# Fetch options
exp = filtered[0]
calls, puts, src = get_options_chain('SPY', exp)
print(f"Calls: {len(calls)}, Puts: {len(puts)}\n")

# Get price
price = yf.Ticker('SPY').history(period='1d')['Close'].iloc[-1]
print(f"SPY price: ${price:.2f}\n")

# Calculate IV
all_opts = pd.concat([calls, puts], ignore_index=True)
iv_df = calculate_iv_surface(all_opts, price)
valid = iv_df[iv_df['implied_vol'].notna()]

print(f"Valid IV: {len(valid)}/{len(iv_df)}")
print(f"TTE range: {valid['time_to_expiry'].min():.4f} - {valid['time_to_expiry'].max():.4f} years")
print(f"TTE unique values: {valid['time_to_expiry'].nunique()}\n")

if valid['time_to_expiry'].nunique() > 1:
    print("✅ MULTIPLE TTE - Surface OK!")
else:
    print("⚠️ SINGLE TTE - Surface will be flat")

# Interpolate
if len(valid) >= 4:
    strike_mesh, tte_mesh, iv_mesh = interpolate_iv_surface(valid, grid_size=30)
    if strike_mesh is not None:
        print(f"\n3D Mesh:")
        print(f"  Strikes: {strike_mesh.min():.0f} - {strike_mesh.max():.0f}")
        print(f"  TTE: {tte_mesh.min():.4f} - {tte_mesh.max():.4f}")
        print(f"  IV: {iv_mesh.min()*100:.1f}% - {iv_mesh.max()*100:.1f}%")
        print("\n🎯 Ready for Plotly!")
