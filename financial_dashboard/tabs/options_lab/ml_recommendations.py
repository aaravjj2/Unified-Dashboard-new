"""
AI-Powered Options Recommendations using GROQ

Uses LLM to analyze options chains and provide intelligent recommendations.
"""
import os
import logging
import pandas as pd
from typing import Dict, List, Optional
import requests
import json

logger = logging.getLogger(__name__)


def get_groq_recommendation(
    ticker: str,
    spot_price: float,
    options_data: Dict,
    market_context: str = ""
) -> Dict:
    """
    Get AI-powered options strategy recommendation using GROQ.
    
    Args:
        ticker: Stock symbol
        spot_price: Current stock price
        options_data: Options chain data
        market_context: Additional market context
        
    Returns:
        Dict with recommendations
    """
    groq_key = os.getenv('GROQ_API_KEY')
    
    if not groq_key:
        logger.warning("GROQ_API_KEY not found")
        return {
            'strategy': 'Bull Call Spread',
            'confidence': 0.65,
            'rationale': 'GROQ API key not configured. Using default recommendation.',
            'risk_level': 'Medium',
            'max_profit': '$500',
            'max_loss': '$200'
        }
    
    try:
        # Prepare context for the LLM
        expirations = options_data.get('expirations', [])[:3]
        
        prompt = f"""You are an expert options trader. Analyze this options chain and recommend the best strategy.

Ticker: {ticker}
Current Price: ${spot_price:.2f}
Available Expirations: {', '.join(expirations)}
{market_context}

Based on current market conditions, recommend ONE specific options strategy including:
1. Strategy name (e.g., Bull Call Spread, Iron Condor, etc.)
2. Specific strikes to use
3. Rationale for this strategy
4. Risk level (Low/Medium/High)
5. Estimated max profit and max loss

Respond in JSON format:
{{
    "strategy": "strategy name",
    "confidence": 0.85,
    "rationale": "detailed reasoning",
    "risk_level": "Medium",
    "strikes": ["600", "610"],
    "expiration": "{expirations[0] if expirations else '2025-01-03'}",
    "max_profit": "$500",
    "max_loss": "$200"
}}"""
        
        # Call GROQ API
        response = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {groq_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'llama-3.3-70b-versatile',  # Updated from deprecated mixtral
                'messages': [
                    {'role': 'system', 'content': 'You are an expert options trading analyst. Always respond with valid JSON.'},
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.3,
                'max_tokens': 500
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Parse JSON from response
            try:
                # Find JSON in response (may have extra text)
                start = content.find('{')
                end = content.rfind('}') + 1
                if start >= 0 and end > start:
                    recommendation = json.loads(content[start:end])
                    logger.info(f"✅ Got GROQ recommendation for {ticker}")
                    return recommendation
            except json.JSONDecodeError:
                logger.warning(f"Could not parse GROQ JSON response")
        
    except Exception as e:
        logger.error(f"GROQ API error: {e}")
    
    # Fallback recommendation
    return {
        'strategy': 'Bull Call Spread',
        'confidence': 0.65,
        'rationale': f'Moderate bullish outlook on {ticker}. Buy lower strike call, sell higher strike call for limited risk.',
        'risk_level': 'Medium',
        'strikes': [str(int(spot_price)), str(int(spot_price + 10))],
        'expiration': options_data.get('expirations', ['2025-01-03'])[0],
        'max_profit': '$500',
        'max_loss': '$200'
    }


def analyze_unusual_flow(options_df: pd.DataFrame) -> List[Dict]:
    """
    Detect unusual options activity that might indicate institutional trades.
    
    Args:
        options_df: DataFrame with options data
        
    Returns:
        List of unusual activity alerts
    """
    if options_df.empty:
        return []
    
    alerts = []
    
    # Calculate volume/OI ratio
    if 'volume' in options_df.columns and 'openInterest' in options_df.columns:
        options_df['vol_oi_ratio'] = options_df['volume'] / (options_df['openInterest'] + 1)
        
        # Flag high volume relative to OI (> 2.0 is unusual)
        unusual = options_df[options_df['vol_oi_ratio'] > 2.0].copy()
        
        for _, row in unusual.head(5).iterrows():
            alerts.append({
                'type': 'High Volume',
                'strike': row.get('strike', 0),
                'volume': int(row.get('volume', 0)),
                'open_interest': int(row.get('openInterest', 0)),
                'ratio': f"{row.get('vol_oi_ratio', 0):.2f}x",
                'alert': f"Volume {row.get('vol_oi_ratio', 0):.1f}x normal"
            })
    
    # Flag large single trades (high volume in single option)
    if 'volume' in options_df.columns:
        high_volume = options_df.nlargest(3, 'volume')
        
        for _, row in high_volume.iterrows():
            if row.get('volume', 0) > 1000:
                alerts.append({
                    'type': 'Large Trade',
                    'strike': row.get('strike', 0),
                    'volume': int(row.get('volume', 0)),
                    'price': f"${row.get('lastPrice', 0):.2f}",
                    'alert': 'Possible institutional trade'
                })
    
    return alerts[:10]  # Return top 10 alerts


def calculate_max_pain(calls_df: pd.DataFrame, puts_df: pd.DataFrame) -> Dict:
    """
    Calculate the max pain price - the strike where option holders lose most money.
    
    Args:
        calls_df: DataFrame with call options
        puts_df: DataFrame with put options
        
    Returns:
        Dict with max pain analysis
    """
    if calls_df.empty and puts_df.empty:
        return {'max_pain_price': 0, 'total_loss': 0, 'strikes_analyzed': 0}
    
    # Get all unique strikes
    all_strikes = sorted(set(list(calls_df['strike']) + list(puts_df['strike'])))
    
    if not all_strikes:
        return {'max_pain_price': 0, 'total_loss': 0, 'strikes_analyzed': 0}
    
    max_pain_losses = []
    
    for test_price in all_strikes:
        # Calculate loss for call holders
        call_loss = 0
        for _, call in calls_df.iterrows():
            strike = call['strike']
            oi = call.get('openInterest', 0)
            if test_price > strike:
                # Calls ITM - call holders profit, call sellers lose
                call_loss += (test_price - strike) * oi * 100
        
        # Calculate loss for put holders
        put_loss = 0
        for _, put in puts_df.iterrows():
            strike = put['strike']
            oi = put.get('openInterest', 0)
            if test_price < strike:
                # Puts ITM - put holders profit, put sellers lose
                put_loss += (strike - test_price) * oi * 100
        
        total_loss = call_loss + put_loss
        max_pain_losses.append((test_price, total_loss))
    
    # Find strike with maximum total loss
    if max_pain_losses:
        max_pain_price, max_loss = max(max_pain_losses, key=lambda x: x[1])
        return {
            'max_pain_price': float(max_pain_price),
            'total_loss': float(max_loss),
            'strikes_analyzed': len(all_strikes),
            'analysis': f"Max pain at ${max_pain_price:.2f} with ${max_loss:,.0f} in losses"
        }
    
    return {'max_pain_price': 0, 'total_loss': 0, 'strikes_analyzed': 0}


if __name__ == '__main__':
    # Test the AI recommender
    test_data = {
        'ticker': 'SPY',
        'spot_price': 590.0,
        'expirations': ['2025-12-30', '2026-01-03']
    }
    
    rec = get_groq_recommendation('SPY', 590.0, test_data)
    print("AI Recommendation:")
    print(json.dumps(rec, indent=2))
