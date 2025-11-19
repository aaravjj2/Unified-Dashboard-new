"""
Phase 6: Market Forecast Module

Provides forward-looking forecasts for stock tickers including:
- Expected return over various horizons (1-week, 1-month, 3-month)
- Volatility estimates
- Probability of positive movement
- Confidence intervals
- Integration with existing Market Trends and Portfolio data
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import os

logger = logging.getLogger(__name__)

# Configuration
FORECAST_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'forecasts')
os.makedirs(FORECAST_DIR, exist_ok=True)

# Forecast horizons (in days)
HORIZONS = {
    '1_week': 7,
    '1_month': 30,
    '3_month': 90
}


def calculate_forecast(
    ticker: str,
    horizon: str = '1_month',
    confidence: float = 0.95,
    use_cached: bool = True
) -> Optional[Dict]:
    """
    Calculate forecast for a single ticker.
    
    Args:
        ticker: Stock ticker symbol
        horizon: Forecast horizon ('1_week', '1_month', '3_month')
        confidence: Confidence level for intervals (0.90, 0.95, 0.99)
        use_cached: Whether to use cached historical data
    
    Returns:
        Dict with forecast metrics:
        {
            'ticker': str,
            'horizon': str,
            'horizon_days': int,
            'expected_return': float,  # Annualized expected return
            'expected_return_horizon': float,  # Expected return over horizon
            'volatility': float,  # Annualized volatility
            'probability_positive': float,  # P(return > 0)
            'confidence_interval': {
                'lower': float,
                'upper': float,
                'confidence': float
            },
            'current_price': float,
            'forecast_price_mean': float,
            'forecast_price_lower': float,
            'forecast_price_upper': float,
            'generated_at': str
        }
    """
    try:
        # Validate horizon
        if horizon not in HORIZONS:
            logger.error(f"Invalid horizon: {horizon}. Must be one of {list(HORIZONS.keys())}")
            return None
        
        horizon_days = HORIZONS[horizon]
        
        # Fetch historical data
        from utils.price_fetch import fetch_historical_data
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=252)  # 1 year lookback
        
        logger.info(f"Fetching data for {ticker} from {start_date.date()} to {end_date.date()}")
        
        hist_data = fetch_historical_data(
            tickers=[ticker],
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            use_alpaca=True
        )
        
        if hist_data.empty or ticker not in hist_data.columns:
            logger.error(f"No historical data available for {ticker}")
            return None
        
        prices = hist_data[ticker].dropna()
        
        if len(prices) < 30:
            logger.warning(f"Insufficient data for {ticker}: only {len(prices)} observations")
            return None
        
        # Calculate returns
        returns = prices.pct_change().dropna()
        
        # Compute forecast metrics
        current_price = float(prices.iloc[-1])
        
        # Annualized expected return (mean of daily returns * 252)
        expected_return_annual = float(returns.mean() * 252)
        
        # Expected return over horizon
        expected_return_horizon = expected_return_annual * (horizon_days / 252)
        
        # Annualized volatility (std of daily returns * sqrt(252))
        volatility_annual = float(returns.std() * np.sqrt(252))
        
        # Volatility over horizon
        volatility_horizon = volatility_annual * np.sqrt(horizon_days / 252)
        
        # Probability of positive return (using normal distribution assumption)
        # P(R > 0) = P(Z > -expected_return_horizon / volatility_horizon)
        from scipy import stats
        
        if volatility_horizon > 0:
            z_score = expected_return_horizon / volatility_horizon
            probability_positive = float(stats.norm.cdf(z_score))
        else:
            # If no volatility, use binary based on expected return sign
            probability_positive = 1.0 if expected_return_horizon > 0 else 0.0
        
        # Confidence intervals
        z_value = stats.norm.ppf((1 + confidence) / 2)
        
        lower_bound = expected_return_horizon - z_value * volatility_horizon
        upper_bound = expected_return_horizon + z_value * volatility_horizon
        
        # Forecast prices
        forecast_price_mean = current_price * (1 + expected_return_horizon)
        forecast_price_lower = current_price * (1 + lower_bound)
        forecast_price_upper = current_price * (1 + upper_bound)
        
        forecast = {
            'ticker': ticker,
            'horizon': horizon,
            'horizon_days': horizon_days,
            'expected_return': expected_return_annual,
            'expected_return_horizon': expected_return_horizon,
            'volatility': volatility_annual,
            'volatility_horizon': volatility_horizon,
            'probability_positive': probability_positive,
            'confidence_interval': {
                'lower': float(lower_bound),
                'upper': float(upper_bound),
                'confidence': confidence
            },
            'current_price': current_price,
            'forecast_price_mean': float(forecast_price_mean),
            'forecast_price_lower': float(forecast_price_lower),
            'forecast_price_upper': float(forecast_price_upper),
            'generated_at': datetime.now().isoformat(),
            'data_points': len(prices),
            'lookback_days': len(prices)
        }
        
        logger.info(f"✅ Forecast generated for {ticker}: E[R]={expected_return_horizon:.2%}, σ={volatility_horizon:.2%}, P(+)={probability_positive:.2%}")
        
        return forecast
        
    except Exception as e:
        logger.error(f"Error calculating forecast for {ticker}: {e}", exc_info=True)
        return None


def calculate_batch_forecasts(
    tickers: List[str],
    horizon: str = '1_month',
    confidence: float = 0.95
) -> Dict[str, Dict]:
    """
    Calculate forecasts for multiple tickers.
    
    Args:
        tickers: List of ticker symbols
        horizon: Forecast horizon
        confidence: Confidence level
    
    Returns:
        Dict mapping ticker to forecast dict
    """
    forecasts = {}
    
    logger.info(f"Calculating forecasts for {len(tickers)} tickers (horizon={horizon})")
    
    for ticker in tickers:
        forecast = calculate_forecast(ticker, horizon=horizon, confidence=confidence)
        if forecast:
            forecasts[ticker] = forecast
        else:
            logger.warning(f"Skipping {ticker} - forecast calculation failed")
    
    logger.info(f"✅ Generated {len(forecasts)}/{len(tickers)} forecasts successfully")
    
    return forecasts


def save_forecasts(
    forecasts: Dict[str, Dict],
    date: Optional[str] = None
) -> str:
    """
    Save forecasts to JSON file.
    
    Args:
        forecasts: Dict mapping ticker to forecast dict
        date: Date string (YYYYMMDD), defaults to today
    
    Returns:
        Path to saved file
    """
    if date is None:
        date = datetime.now().strftime('%Y%m%d')
    
    # Extract horizon from first forecast
    horizon = list(forecasts.values())[0]['horizon'] if forecasts else '1_month'
    
    filename = f'forecast_{horizon}_{date}.json'
    filepath = os.path.join(FORECAST_DIR, filename)
    
    output = {
        'generated_at': datetime.now().isoformat(),
        'date': date,
        'horizon': horizon,
        'num_tickers': len(forecasts),
        'forecasts': forecasts
    }
    
    with open(filepath, 'w') as f:
        json.dump(output, f, indent=2)
    
    logger.info(f"Saved forecasts to: {filepath}")
    return filepath


def load_forecasts(
    horizon: str = '1_month',
    date: Optional[str] = None
) -> Optional[Dict]:
    """
    Load forecasts from JSON file.
    
    Args:
        horizon: Forecast horizon
        date: Date string (YYYYMMDD), defaults to most recent
    
    Returns:
        Dict with forecasts or None if not found
    """
    if date:
        filename = f'forecast_{horizon}_{date}.json'
        filepath = os.path.join(FORECAST_DIR, filename)
    else:
        # Find most recent file for horizon
        files = [f for f in os.listdir(FORECAST_DIR) if f.startswith(f'forecast_{horizon}_') and f.endswith('.json')]
        if not files:
            logger.warning(f"No forecast files found for horizon={horizon}")
            return None
        files.sort(reverse=True)
        filepath = os.path.join(FORECAST_DIR, files[0])
    
    if not os.path.exists(filepath):
        logger.warning(f"Forecast file not found: {filepath}")
        return None
    
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load forecasts: {e}")
        return None


def get_or_generate_forecasts(
    tickers: List[str],
    horizon: str = '1_month',
    confidence: float = 0.95,
    force_regenerate: bool = False
) -> Dict[str, Dict]:
    """
    Get forecasts for tickers, generating if missing or outdated.
    
    Similar to get_or_generate_shap_data(), this checks for existing forecasts
    and regenerates if needed.
    
    Args:
        tickers: List of ticker symbols
        horizon: Forecast horizon
        confidence: Confidence level
        force_regenerate: Force regeneration even if file exists
    
    Returns:
        Dict mapping ticker to forecast dict
    """
    date = datetime.now().strftime('%Y%m%d')
    
    # Check if forecasts exist and are recent
    if not force_regenerate:
        existing = load_forecasts(horizon=horizon, date=date)
        if existing and 'forecasts' in existing:
            existing_tickers = set(existing['forecasts'].keys())
            requested_tickers = set(tickers)
            
            # If all requested tickers are present, return existing
            if requested_tickers.issubset(existing_tickers):
                logger.info(f"✓ Using existing forecasts from {date}")
                return existing['forecasts']
            else:
                missing = requested_tickers - existing_tickers
                logger.info(f"⚠️ Existing forecasts missing {len(missing)} tickers: {missing}")
    
    # Generate new forecasts
    logger.info(f"📊 Generating forecasts for {len(tickers)} tickers (horizon={horizon})...")
    forecasts = calculate_batch_forecasts(tickers, horizon=horizon, confidence=confidence)
    
    # Save to disk
    save_forecasts(forecasts, date=date)
    
    return forecasts


def format_forecast_table(forecasts: Dict[str, Dict]) -> pd.DataFrame:
    """
    Format forecasts as a table for display.
    
    Args:
        forecasts: Dict mapping ticker to forecast dict
    
    Returns:
        DataFrame with formatted forecast data
    """
    rows = []
    
    for ticker, forecast in forecasts.items():
        row = {
            'Ticker': ticker,
            'Current Price': f"${forecast['current_price']:.2f}",
            'Expected Return': f"{forecast['expected_return_horizon']:.2%}",
            'Volatility': f"{forecast['volatility_horizon']:.2%}",
            'Prob(+)': f"{forecast['probability_positive']:.1%}",
            'Forecast Price': f"${forecast['forecast_price_mean']:.2f}",
            'Lower Bound': f"${forecast['forecast_price_lower']:.2f}",
            'Upper Bound': f"${forecast['forecast_price_upper']:.2f}",
            'Horizon': forecast['horizon'].replace('_', ' ').title()
        }
        rows.append(row)
    
    df = pd.DataFrame(rows)
    
    # Sort by probability of positive movement (descending)
    forecasts_sorted = sorted(forecasts.items(), key=lambda x: x[1]['probability_positive'], reverse=True)
    df = df.set_index('Ticker')
    df = df.reindex([t for t, _ in forecasts_sorted])
    df = df.reset_index()
    
    return df


# ============================================================================
# Self-Test
# ============================================================================

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("Testing market_forecast.py module...\n")
    
    # Test 1: Single ticker forecast
    print("Test 1: Single ticker forecast")
    test_ticker = 'AAPL'
    forecast = calculate_forecast(test_ticker, horizon='1_month')
    
    if forecast:
        print(f"  ✓ Forecast for {test_ticker}:")
        print(f"    Expected Return (annual): {forecast['expected_return']:.2%}")
        print(f"    Expected Return (1-month): {forecast['expected_return_horizon']:.2%}")
        print(f"    Volatility: {forecast['volatility']:.2%}")
        print(f"    Probability(+): {forecast['probability_positive']:.1%}")
        print(f"    Current Price: ${forecast['current_price']:.2f}")
        print(f"    Forecast Price: ${forecast['forecast_price_mean']:.2f}")
    else:
        print(f"  ✗ Forecast failed for {test_ticker}")
    
    print()
    
    # Test 2: Batch forecasts
    print("Test 2: Batch forecasts")
    test_tickers = ['AAPL', 'MSFT', 'GOOGL']
    batch_forecasts = calculate_batch_forecasts(test_tickers, horizon='1_week')
    
    if batch_forecasts:
        print(f"  ✓ Generated {len(batch_forecasts)} forecasts:")
        for ticker, fc in batch_forecasts.items():
            print(f"    {ticker}: E[R]={fc['expected_return_horizon']:.2%}, P(+)={fc['probability_positive']:.1%}")
    else:
        print("  ✗ Batch forecast failed")
    
    print()
    
    # Test 3: Save and load
    print("Test 3: Persistence")
    if batch_forecasts:
        test_date = '20250102'
        filepath = save_forecasts(batch_forecasts, date=test_date)
        print(f"  ✓ Saved to: {os.path.basename(filepath)}")
        
        loaded = load_forecasts(horizon='1_week', date=test_date)
        if loaded and 'forecasts' in loaded:
            print(f"  ✓ Loaded {loaded['num_tickers']} forecasts")
            
            # Cleanup test file
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"  ✓ Cleaned up test file")
        else:
            print("  ✗ Load failed")
    
    print()
    
    # Test 4: Table formatting
    print("Test 4: Table formatting")
    if batch_forecasts:
        df = format_forecast_table(batch_forecasts)
        print(f"  ✓ Formatted table with {len(df)} rows x {len(df.columns)} columns")
        print(df.to_string(index=False))
    
    print()
    print("✅ Tests completed!")
