#!/usr/bin/env python3
"""
Generate Monthly Stock Picks from S&P 500 Universe
This script runs the monthly analysis pipeline to generate stock picks
for the upcoming month based on the S&P 500 ticker universe.

Usage:        logger.info(f"\u2705 Analysis complete: {len(results.get('detailed', []))} picks generated")
        
        # Save results to CSV
        timestamp = datetime.now().strftime('%Y%m%d')
        output_file = os.path.join(output_dir, f'picks_{timestamp}.csv')
        
        df = pd.DataFrame(results['detailed'])
        
        # Rank by composite score (descending)
        if 'composite' in df.columns or 'composite_score' in df.columns:
            score_col = 'composite' if 'composite' in df.columns else 'composite_score'
            df = df.sort_values(score_col, ascending=False, na_position='last').reset_index(drop=True)
            df['rank'] = range(1, len(df) + 1)
            # Take only top N
            df = df.head(topn)
            logger.info(f"\u2705 Ranked and filtered to top {topn} picks")
        
        df.to_csv(output_file, index=False)
        logger.info(f"\u2705 Saved picks to: {output_file}")on3 run_monthly_picks.py [--output-dir DIR] [--topn N]
"""
import os
import sys
import argparse
from datetime import datetime
import pandas as pd
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Project paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
GRADIO_DIR = os.path.join(PROJECT_ROOT, 'Gradio')  # Capital G
GRADIO_DIR_ALT = os.path.join(PROJECT_ROOT, 'gradio_app')

# Add paths in priority order
for path in [GRADIO_DIR, GRADIO_DIR_ALT, BASE_DIR, PROJECT_ROOT]:
    if os.path.exists(path) and path not in sys.path:
        sys.path.insert(0, path)
        logger.debug(f"Added to sys.path: {path}")

def get_sp500_tickers():
    """
    Get S&P 500 ticker list from multiple sources
    """
    logger.info("Fetching S&P 500 ticker universe...")
    
    # Try to get from Wikipedia
    try:
        import pandas as pd
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        tables = pd.read_html(url)
        sp500_df = tables[0]
        tickers = sp500_df['Symbol'].str.replace('.', '-').tolist()
        logger.info(f"✅ Loaded {len(tickers)} tickers from Wikipedia")
        return tickers
    except Exception as e:
        logger.warning(f"Failed to load from Wikipedia: {e}")
    
    # Fallback: Try yfinance S&P 500 list
    try:
        import yfinance as yf
        sp500 = yf.Ticker("^GSPC")
        # This won't work directly, so we'll use a hardcoded list
        raise NotImplementedError("yfinance doesn't provide constituent list")
    except Exception:
        pass
    
    # Fallback: Comprehensive S&P 500 list (503 tickers as of Sept 2025)
    logger.warning("Using fallback S&P 500 ticker list (503 tickers)")
    fallback_tickers = [
        'A', 'AAL', 'AAPL', 'ABBV', 'ABNB', 'ABT', 'ACGL', 'ACN', 'ADBE', 'ADI',
        'ADM', 'ADP', 'ADSK', 'AEE', 'AEP', 'AES', 'AFL', 'AIG', 'AIZ', 'AJG',
        'AKAM', 'ALB', 'ALGN', 'ALL', 'ALLE', 'AMAT', 'AMCR', 'AMD', 'AME', 'AMGN',
        'AMP', 'AMT', 'AMZN', 'ANET', 'ANSS', 'AON', 'AOS', 'APA', 'APD', 'APH',
        'APTV', 'ARE', 'ATO', 'AVB', 'AVGO', 'AVY', 'AWK', 'AXON', 'AXP', 'AZO',
        'BA', 'BAC', 'BALL', 'BAX', 'BBWI', 'BBY', 'BDX', 'BEN', 'BF-B', 'BG',
        'BIIB', 'BIO', 'BK', 'BKNG', 'BKR', 'BLDR', 'BLK', 'BMY', 'BR', 'BRK-B',
        'BRO', 'BSX', 'BWA', 'BX', 'BXP', 'C', 'CAG', 'CAH', 'CARR', 'CAT',
        'CB', 'CBOE', 'CBRE', 'CCI', 'CCL', 'CDNS', 'CDW', 'CE', 'CEG', 'CF',
        'CFG', 'CHD', 'CHRW', 'CHTR', 'CI', 'CINF', 'CL', 'CLX', 'CMA', 'CMCSA',
        'CME', 'CMG', 'CMI', 'CMS', 'CNC', 'CNP', 'COF', 'COO', 'COP', 'COR',
        'COST', 'CPAY', 'CPB', 'CPRT', 'CPT', 'CRL', 'CRM', 'CSCO', 'CSGP', 'CSX',
        'CTAS', 'CTLT', 'CTRA', 'CTSH', 'CTVA', 'CVS', 'CVX', 'CZR', 'D', 'DAL',
        'DAY', 'DD', 'DE', 'DECK', 'DFS', 'DG', 'DGX', 'DHI', 'DHR', 'DIS',
        'DLR', 'DLTR', 'DOC', 'DOV', 'DOW', 'DPZ', 'DRI', 'DTE', 'DUK', 'DVA',
        'DVN', 'DXCM', 'EA', 'EBAY', 'ECL', 'ED', 'EFX', 'EG', 'EIX', 'EL',
        'ELV', 'EMN', 'EMR', 'ENPH', 'EOG', 'EPAM', 'EQIX', 'EQR', 'EQT', 'ES',
        'ESS', 'ETN', 'ETR', 'ETSY', 'EVRG', 'EW', 'EXC', 'EXPD', 'EXPE', 'EXR',
        'F', 'FANG', 'FAST', 'FCX', 'FDS', 'FDX', 'FE', 'FFIV', 'FI', 'FICO',
        'FIS', 'FITB', 'FMC', 'FOX', 'FOXA', 'FRT', 'FSLR', 'FTNT', 'FTV', 'GD',
        'GDDY', 'GE', 'GEHC', 'GEN', 'GEV', 'GILD', 'GIS', 'GL', 'GLW', 'GM',
        'GNRC', 'GOOG', 'GOOGL', 'GPC', 'GPN', 'GRMN', 'GS', 'GWW', 'HAL', 'HAS',
        'HBAN', 'HCA', 'HD', 'HES', 'HIG', 'HII', 'HLT', 'HOLX', 'HON', 'HPE',
        'HPQ', 'HRL', 'HSIC', 'HST', 'HSY', 'HUBB', 'HUM', 'HWM', 'IBM', 'ICE',
        'IDXX', 'IEX', 'IFF', 'INCY', 'INTC', 'INTU', 'INVH', 'IP', 'IPG', 'IQV',
        'IR', 'IRM', 'ISRG', 'IT', 'ITW', 'IVZ', 'J', 'JBHT', 'JBL', 'JCI',
        'JKHY', 'JNJ', 'JNPR', 'JPM', 'K', 'KDP', 'KEY', 'KEYS', 'KHC', 'KIM',
        'KKR', 'KLAC', 'KMB', 'KMI', 'KMX', 'KO', 'KR', 'KVUE', 'L', 'LDOS',
        'LEN', 'LH', 'LHX', 'LIN', 'LKQ', 'LLY', 'LMT', 'LNT', 'LOW', 'LRCX',
        'LULU', 'LUV', 'LVS', 'LW', 'LYB', 'LYV', 'MA', 'MAA', 'MAR', 'MAS',
        'MCD', 'MCHP', 'MCK', 'MCO', 'MDLZ', 'MDT', 'MET', 'META', 'MGM', 'MHK',
        'MKC', 'MKTX', 'MLM', 'MMC', 'MMM', 'MNST', 'MO', 'MOH', 'MOS', 'MPC',
        'MPWR', 'MRK', 'MRNA', 'MRO', 'MS', 'MSCI', 'MSFT', 'MSI', 'MTB', 'MTCH',
        'MTD', 'MU', 'NCLH', 'NDAQ', 'NDSN', 'NEE', 'NEM', 'NFLX', 'NI', 'NKE',
        'NOC', 'NOW', 'NRG', 'NSC', 'NTAP', 'NTRS', 'NUE', 'NVDA', 'NVR', 'NWS',
        'NWSA', 'NXPI', 'O', 'ODFL', 'OKE', 'OMC', 'ON', 'ORCL', 'ORLY', 'OTIS',
        'OXY', 'PANW', 'PARA', 'PAYC', 'PAYX', 'PCAR', 'PCG', 'PEG', 'PEP', 'PFE',
        'PFG', 'PG', 'PGR', 'PH', 'PHM', 'PKG', 'PLD', 'PM', 'PNC', 'PNR',
        'PNW', 'PODD', 'POOL', 'PPG', 'PPL', 'PRU', 'PSA', 'PSX', 'PTC', 'PWR',
        'PYPL', 'QCOM', 'QRVO', 'RCL', 'REG', 'REGN', 'RF', 'RJF', 'RL', 'RMD',
        'ROK', 'ROL', 'ROP', 'ROST', 'RSG', 'RTX', 'RVTY', 'SBAC', 'SBUX', 'SCHW',
        'SHW', 'SJM', 'SLB', 'SMCI', 'SNA', 'SNPS', 'SO', 'SPG', 'SPGI', 'SRE',
        'STE', 'STLD', 'STT', 'STX', 'STZ', 'SWK', 'SWKS', 'SYF', 'SYK', 'SYY',
        'T', 'TAP', 'TDG', 'TDY', 'TECH', 'TEL', 'TER', 'TFC', 'TFX', 'TGT',
        'TJX', 'TMO', 'TMUS', 'TPR', 'TRGP', 'TRMB', 'TROW', 'TRV', 'TSCO', 'TSLA',
        'TSN', 'TT', 'TTWO', 'TXN', 'TXT', 'TYL', 'UAL', 'UBER', 'UDR', 'UHS',
        'ULTA', 'UNH', 'UNP', 'UPS', 'URI', 'USB', 'V', 'VICI', 'VLO', 'VLTO',
        'VMC', 'VRSK', 'VRSN', 'VRTX', 'VST', 'VTR', 'VTRS', 'VZ', 'WAB', 'WAT',
        'WBA', 'WBD', 'WDC', 'WEC', 'WELL', 'WFC', 'WM', 'WMB', 'WMT', 'WRB',
        'WRK', 'WST', 'WTW', 'WY', 'WYNN', 'XEL', 'XOM', 'XYL', 'YUM', 'ZBH',
        'ZBRA', 'ZTS'
    ]
    return fallback_tickers

def run_monthly_analysis(tickers, output_dir, topn=25):
    """
    Run the monthly picks analysis pipeline
    """
    logger.info(f"Running monthly analysis for {len(tickers)} tickers...")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Top N picks: {topn}")
    
    # Directly import and use the trusted pipeline script
    try:
        from pipelines.compute_market_trends import compute_and_write
        logger.info("✅ Loaded `compute_and_write` from pipeline.")
    except Exception as e:
        logger.error(f"❌ Failed to import pipeline script: {e}")
        return None

    try:
        # Run the analysis
        logger.info("Starting full analysis...")
        # The pipeline script writes a JSON file and returns its path
        result_path = compute_and_write(tickers=tickers)
        
        # Load the results from the generated JSON
        import json
        with open(result_path, 'r') as f:
            results = json.load(f)
        
        if not results or not results.get('detailed'):
            logger.error("❌ Analysis returned no results")
            return None
        
        logger.info(f"✅ Analysis complete: {len(results.get('detailed', []))} picks generated")
        
        # Save results to CSV
        timestamp = datetime.now().strftime('%Y%m%d')
        output_file = os.path.join(output_dir, f'picks_{timestamp}.csv')
        
        df = pd.DataFrame(results['detailed'])
        
        # Rank by composite score (descending)
        if 'composite_score' in df.columns:
            score_col = 'composite_score'
        elif 'composite' in df.columns:
            score_col = 'composite'
        else:
            score_col = None
        
        if score_col:
            df = df.sort_values(score_col, ascending=False, na_position='last').reset_index(drop=True)
            df.insert(0, 'rank', range(1, len(df) + 1))
            # Filter to top N
            df = df.head(topn)
            logger.info(f"✅ Ranked by {score_col} and filtered to top {topn} picks")
        
        # ============= SPRINT 1: TRADE ENRICHMENT =============
        logger.info("Enriching picks with trade sizing and slippage estimates...")
        try:
            from utils import trade_utils
            
            # Portfolio parameters for sizing (can be made configurable)
            portfolio_value = 100000  # $100K default portfolio
            
            # Initialize new columns
            df['position_size_dollars'] = 0.0
            df['expected_slippage_pct'] = 0.0
            df['predicted_return_net'] = 0.0
            df['liquidity_flag'] = 'UNKNOWN'
            
            for idx, row in df.iterrows():
                ticker = row.get('ticker')
                price = row.get('price', 100)  # Default if missing
                volatility = row.get('vol_60_ann', 0.25)  # Use vol_60_ann or default 25%
                
                # Estimate expected return from composite score (simple heuristic)
                # Higher score = higher expected return
                if score_col and score_col in row:
                    # Scale score to expected return (0-100 score -> 0-20% return)
                    normalized_score = min(max(row[score_col], 0), 100)
                    prediction = (normalized_score / 100) * 0.20  # 0-20% range
                else:
                    prediction = 0.05  # Default 5% if no score
                
                # Get ADV from avg_vol or estimate from vol_today
                adv_shares = row.get('avg_vol', row.get('vol_today', 1000000))
                adv_dollars = adv_shares * price
                
                # Compute position size
                try:
                    sizing = trade_utils.compute_position_size(
                        prediction=prediction,
                        volatility=volatility,
                        max_notional=portfolio_value,
                        adv=adv_dollars,
                        method='volatility'
                    )
                    df.at[idx, 'position_size_dollars'] = sizing['position_size_dollars']
                except Exception as e:
                    logger.warning(f"Could not size {ticker}: {e}")
                    df.at[idx, 'position_size_dollars'] = portfolio_value * 0.05  # Default 5%
                
                # Estimate slippage
                try:
                    spread_pct = 0.001  # Assume 10 bps spread
                    slippage = trade_utils.estimate_slippage(
                        position_size=df.at[idx, 'position_size_dollars'],
                        adv=adv_dollars,
                        spread_pct=spread_pct,
                        is_buy=True
                    )
                    df.at[idx, 'expected_slippage_pct'] = slippage['slippage_pct']
                    
                    # Net return = predicted - slippage
                    df.at[idx, 'predicted_return_net'] = prediction - (slippage['slippage_pct'] / 100)
                except Exception as e:
                    logger.warning(f"Could not estimate slippage for {ticker}: {e}")
                    df.at[idx, 'expected_slippage_pct'] = 0.05
                    df.at[idx, 'predicted_return_net'] = prediction - 0.0005
                
                # Compute liquidity flag
                try:
                    liq_flag = trade_utils.compute_liquidity_flag(
                        adv=adv_dollars,
                        spread_pct=spread_pct
                    )
                    df.at[idx, 'liquidity_flag'] = liq_flag['flag']
                except Exception as e:
                    logger.warning(f"Could not compute liquidity flag for {ticker}: {e}")
                    df.at[idx, 'liquidity_flag'] = 'UNKNOWN'
            
            logger.info(f"✅ Trade enrichment complete for {len(df)} picks")
        except Exception as e:
            logger.error(f"❌ Trade enrichment failed: {e}")
            logger.warning("Continuing without trade enrichment...")
        # ============= END TRADE ENRICHMENT =============
        
        # Select and reorder key columns for better readability
        # Keep most useful columns, drop excessive technical fields
        priority_cols = ['rank', 'ticker', score_col if score_col else 'composite_score', 
                        'price', 'sma20', 'sma50', 'sma200', 'rsi', 'macd_hist',
                        'rel_strength', 'beta', 'avg_vol', 'vol_today', 'vol_surge',
                        'momentum_12m', 'vol_60_ann', 'earnings_soon', 'earnings_date',
                        'news_headlines', 'options_signal', 'score_breakdown']
        
        # Keep columns that exist
        cols_to_save = [col for col in priority_cols if col in df.columns]
        
        # Add any remaining important columns not in priority list
        remaining_cols = [col for col in df.columns if col not in cols_to_save 
                         and not col.endswith('_score')  # Exclude individual sub-scores
                         and col not in ['stock_ret_1d', 'sp_ret_1d', 'stock_ret_5d', 'sp_ret_5d',
                                        'stock_ret_20d', 'sp_ret_20d', 'rel_perf_weighted']]
        
        cols_to_save.extend(remaining_cols)
        df_save = df[cols_to_save]
        
        df_save.to_csv(output_file, index=False)
        logger.info(f"✅ Saved {len(df_save)} picks with {len(cols_to_save)} columns to: {output_file}")
        
        # Save brief text if available
        if results.get('brief_text'):
            brief_file = os.path.join(output_dir, f'market_brief_{timestamp}.txt')
            with open(brief_file, 'w') as f:
                f.write(results['brief_text'])
            logger.info(f"✅ Saved brief to: {brief_file}")
            # Also write canonical brief filenames expected by the Dash loader
            try:
                canonical_txt = os.path.join(output_dir, 'market_brief.txt')
                with open(canonical_txt, 'w', encoding='utf-8') as cf:
                    cf.write(results['brief_text'])
                logger.info(f"✅ Wrote canonical brief text to: {canonical_txt}")

                # Also write a small market_brief.json with metadata so loaders can read it
                try:
                    import json
                    canonical_json = os.path.join(output_dir, 'market_brief.json')
                    meta = {
                        'generated_at': datetime.now().isoformat(),
                        'brief_text': results.get('brief_text')
                    }
                    with open(canonical_json, 'w', encoding='utf-8') as jf:
                        json.dump(meta, jf, ensure_ascii=False, indent=2)
                    logger.info(f"✅ Wrote canonical brief JSON to: {canonical_json}")
                except Exception:
                    logger.warning('Could not write market_brief.json (non-fatal)')
            except Exception:
                logger.warning('Could not write canonical brief files (non-fatal)')
        
        return output_file
        
    except Exception as e:
        logger.error(f"❌ Error running analysis: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    parser = argparse.ArgumentParser(description='Generate monthly stock picks from S&P 500')
    parser.add_argument('--output-dir', default='models/full_run',
                       help='Output directory for picks CSV (default: models/full_run)')
    parser.add_argument('--topn', type=int, default=25,
                       help='Number of top picks to generate (default: 25)')
    parser.add_argument('--tickers-file', type=str, default=None,
                       help='Optional: Path to file with custom ticker list (one per line)')
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    output_dir = os.path.join(BASE_DIR, args.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info("=" * 60)
    logger.info("MONTHLY PICKS GENERATOR - S&P 500 Universe")
    logger.info("=" * 60)
    
    # Get ticker universe
    if args.tickers_file and os.path.exists(args.tickers_file):
        logger.info(f"Loading tickers from: {args.tickers_file}")
        with open(args.tickers_file, 'r') as f:
            tickers = [line.strip() for line in f if line.strip()]
        logger.info(f"✅ Loaded {len(tickers)} tickers from file")
    else:
        tickers = get_sp500_tickers()
    
    # Run the analysis
    output_file = run_monthly_analysis(tickers, output_dir, args.topn)
    
    if output_file:
        logger.info("\n" + "=" * 60)
        logger.info("✅ SUCCESS!")
        logger.info("=" * 60)
        logger.info(f"Monthly picks saved to: {output_file}")
        logger.info(f"\nTo view the picks, restart the monthly dashboard:")
        logger.info(f"  pkill -f monthly_picks_flask.py")
        logger.info(f"  python3 monthly_picks_flask.py > /tmp/monthly_flask.log 2>&1 &")
        logger.info(f"\nOr restart all dashboards:")
        logger.info(f"  ./start")
        logger.info(f"\nThen visit: http://localhost:8052")
        return 0
    else:
        logger.error("\n" + "=" * 60)
        logger.error("❌ FAILED")
        logger.error("=" * 60)
        logger.error("Could not generate monthly picks. Check logs above for details.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
