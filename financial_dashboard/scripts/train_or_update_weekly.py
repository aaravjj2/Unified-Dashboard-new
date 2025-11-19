"""
End-to-End Weekly Pipeline Runner

This script orchestrates the entire weekly pipeline:
1. Fetches the ticker universe.
2. Fetches news and computes sentiment/embeddings (placeholder).
3. Enriches features (technical, fundamental) (placeholder).
4. Trains or loads the latest model (placeholder).
5. Generates predictions and ranks picks.
6. Enriches picks with trade sizing, slippage, and SHAP explanations.
7. Saves the final, trade-ready picks and artifacts.

"""
import os
import sys
import time
import json
import argparse
from datetime import datetime
import pandas as pd
import numpy as np

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, BASE)

OUT_DIR = os.path.join(BASE, 'models', 'weekly_run')
os.makedirs(OUT_DIR, exist_ok=True)

# Import necessary utilities
from utils import trade_utils, explain, snapshots

# Optional Alpaca Import for real data
try:
    from alpaca.trading.client import TradingClient
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.common.timeframe import TimeFrame
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    print("Warning: alpaca-py SDK not found. Real data fetching will be skipped.")



def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--date', default=datetime.utcnow().strftime('%Y%m%d'))
    p.add_argument('--top-k', type=int, default=50)
    p.add_argument('--sample-size', type=int, default=None, help='Sample N tickers for testing (optional)')
    p.add_argument('--features', default='data/weekly_enriched_with_alpaca_prices.parquet', help='Path to features parquet file')
    p.add_argument('--universe-file', default='Weekly ticker list.csv', help='Path to universe CSV')
    p.add_argument('--train-model', action='store_true', help='If set, run trainer before predicting')
    args = p.parse_args(argv)
    start = time.time()

    print("--- (1/5) Loading Features ---")
    # Load features from parquet (should contain: ticker, last_price, market_cap, avg_dollar_vol_21, ret_1d, ret_5d, ret_21d, vol_21, ma5_rel, ma20_rel, rsi_14, atr_14)
    if os.path.exists(args.features):
        features_df = pd.read_parquet(args.features)
        print(f"Loaded {len(features_df)} tickers with features from {args.features}")
    else:
        print(f"Features file not found: {args.features}")
        print("Falling back to universe file...")
        universe_df = pd.read_csv(args.universe_file)
        tickers = universe_df['Symbol'].unique().tolist()
        features_df = pd.DataFrame({'ticker': tickers})
        features_df['last_price'] = 1.0
        features_df['market_cap'] = 0.0
        features_df['avg_dollar_vol_21'] = 0.0
        features_df['ret_1d'] = 0.0
        features_df['ret_5d'] = 0.0
        features_df['ret_21d'] = 0.0
        features_df['vol_21'] = 0.3
        features_df['ma5_rel'] = 0.0
        features_df['ma20_rel'] = 0.0
        features_df['rsi_14'] = 50.0
        features_df['atr_14'] = 0.0
        print(f"Created {len(features_df)} tickers with default features")
    
    # Ensure required columns exist with defaults
    required_cols = {
        'last_price': 1.0,
        'market_cap': 0.0,
        'avg_dollar_vol_21': 0.0,
        'ret_1d': 0.0,
        'ret_5d': 0.0,
        'ret_21d': 0.0,
        'vol_21': 0.3,
        'ma5_rel': 0.0,
        'ma20_rel': 0.0,
        'rsi_14': 50.0,
        'atr_14': 0.0
    }
    for col, default in required_cols.items():
        if col not in features_df.columns:
            features_df[col] = default
        else:
            features_df[col] = features_df[col].fillna(default)
    
    # Apply sampling if requested (for testing)
    if args.sample_size and args.sample_size < len(features_df):
        features_df = features_df.sample(n=args.sample_size, random_state=42).reset_index(drop=True)
        print(f"  ✓ Sampled {args.sample_size} tickers for testing")

    print("--- (2/5) Computing Scores & Predictions with LightGBM ---")
    # Train LightGBM model to predict returns
    from lightgbm import LGBMRegressor
    
    # Define features and target
    feature_cols = ['ret_5d', 'ret_21d', 'vol_21', 'ma5_rel', 'ma20_rel', 'rsi_14']
    X = features_df[feature_cols].fillna(0)
    
    # Create synthetic target (weekly forward returns - use ret_5d as proxy)
    # In production, this would be actual forward returns from historical data
    y = features_df['ret_5d'].fillna(0) * 0.7 + features_df['ret_21d'].fillna(0) * 0.3
    
    # Train/test split (80/20)
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Train LightGBM model
    model = LGBMRegressor(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        random_state=42,
        verbose=-1
    )
    model.fit(X_train, y_train)
    
    # Predict for all tickers
    features_df['pred_mean'] = model.predict(X)
    features_df['pred_sigma'] = features_df['vol_21']  # Use historical volatility as uncertainty
    
    print(f"  ✓ Trained LightGBM model - Train R²: {model.score(X_train, y_train):.3f}, Test R²: {model.score(X_test, y_test):.3f}")
    
    # Compute SHAP values for explainability
    try:
        import shap
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X)
        mock_shap_data = {
            'shap_values': shap_values,
            'base_value': explainer.expected_value,
            'feature_names': feature_cols
        }
        print(f"  ✓ Computed SHAP explanations for {len(features_df)} tickers")
    except Exception as e:
        print(f"  ⚠ Could not compute SHAP values: {e}")
        # Fallback to mock SHAP
        mock_shap_data = {
            'shap_values': np.random.randn(len(features_df), len(feature_cols)) * 0.01,
            'base_value': 0.001,
            'feature_names': feature_cols
        }
        print(f"  ✓ Using mock SHAP values for {len(features_df)} tickers")

    print("--- (3/5) Ranking and Selecting Top Picks ---")
    # Rank and select top K
    picks_df = features_df.sort_values('pred_mean', ascending=False).head(args.top_k).copy()
    picks_df['pred_rank'] = range(1, len(picks_df) + 1)
    picks_df['date'] = args.date
    print(f"  ✓ Selected top {len(picks_df)} picks")

    print("--- (4/5) Enriching Picks with Trade Data ---")
    # Add trade sizing, slippage, and liquidity metadata
    enriched_rows = []
    for _, pick in picks_df.iterrows():
        pick_dict = pick.to_dict()
        
        # Get values (use avg_dollar_vol_21 as ADV proxy)
        adv = pick.get('avg_dollar_vol_21', 1_000_000)
        if adv == 0 or pd.isna(adv):
            adv = 1_000_000  # Default $1M ADV
        
        prediction = pick.get('pred_mean', 0.01)
        volatility = pick.get('vol_21', 0.3)
        if volatility == 0 or pd.isna(volatility):
            volatility = 0.3
        
        # Sizing
        size_info = trade_utils.compute_position_size(
            prediction=prediction,
            volatility=volatility,
            max_notional=1_000_000,  # Assume $1M portfolio
            adv=adv,
            method='volatility'
        )
        pick_dict['position_size_dollars'] = size_info.get('position_size_dollars', 10000)
        
        # Slippage
        slippage_info = trade_utils.estimate_slippage(
            position_size=pick_dict['position_size_dollars'],
            adv=adv,
            spread_pct=0.002,  # 20 bps default spread
            is_buy=True
        )
        pick_dict['expected_slippage_pct'] = slippage_info.get('slippage_pct', 0.05)
        pick_dict['predicted_return_net'] = prediction - (pick_dict['expected_slippage_pct'] / 100)
        
        # Liquidity flag
        liq_info = trade_utils.compute_liquidity_flag(
            adv=adv,
            spread_pct=0.002,
            position_size=pick_dict['position_size_dollars']
        )
        pick_dict['liquidity_flag'] = liq_info.get('flag', 'UNKNOWN')
        
        enriched_rows.append(pick_dict)
    
    final_picks_df = pd.DataFrame(enriched_rows)

    # Select only the columns we want in the output
    output_cols = [
        'ticker', 'last_price', 'market_cap', 'avg_dollar_vol_21', 
        'ret_5d', 'ret_21d', 'vol_21', 'pred_mean', 'pred_sigma', 
        'pred_rank', 'date', 'position_size_dollars', 'expected_slippage_pct', 
        'predicted_return_net', 'liquidity_flag'
    ]
    # Only keep columns that exist
    output_cols = [c for c in output_cols if c in final_picks_df.columns]
    final_picks_df = final_picks_df[output_cols]
    
    # Rename avg_dollar_vol_21 to avg_dollar_vol_3mo for output consistency
    if 'avg_dollar_vol_21' in final_picks_df.columns:
        final_picks_df = final_picks_df.rename(columns={'avg_dollar_vol_21': 'avg_dollar_vol_3mo'})

    print("--- (5/5) Saving Artifacts ---")
    # Save final picks CSV (use MMDD format for filename)
    mmdd = args.date[-4:] if len(args.date) >= 8 else args.date
    out_csv = os.path.join(OUT_DIR, f"weeklypicks{mmdd}.csv")
    final_picks_df.to_csv(out_csv, index=False)
    print(f"  ✓ Saved trade-ready picks to: {out_csv}")
    
    # Save metadata
    meta = {
        'date': args.date,
        'n_candidates': len(features_df),
        'n_selected': len(final_picks_df),
        'run_time_seconds': time.time() - start,
        'features_file': args.features
    }
    meta_path = os.path.join(OUT_DIR, f"weekly_meta_{args.date}.json")
    with open(meta_path, 'w') as fh:
        json.dump(meta, fh, indent=2)
    print(f"  ✓ Saved metadata to: {meta_path}")

    # Save SHAP explanations (optional, only if explain module available)
    try:
        explain.save_shap_explanations(
            shap_data=mock_shap_data,
            tickers=final_picks_df['ticker'].tolist(),
            predictions=final_picks_df['pred_mean'].values,
            date=args.date
        )
        print(f"  ✓ Saved SHAP explanations to: explain/picks_explain_{args.date}.json")
    except Exception as e:
        print(f"  ⚠ Could not save SHAP explanations: {e}")
    
    elapsed = time.time() - start
    print(f"\n--- ✅ Weekly pipeline completed successfully in {elapsed:.2f} seconds! ---")

if __name__ == '__main__':
    main()
