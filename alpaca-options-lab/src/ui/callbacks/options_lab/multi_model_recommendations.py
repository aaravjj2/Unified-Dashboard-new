"""
Multi-Model AI Recommendations (GROQ-only version)
Uses GROQ API with multiple prompting strategies for robust analysis
No external paid API keys required - uses only GROQ_API_KEY
"""

import logging
import os
import asyncio
from typing import Dict, List, Any
import requests
from datetime import datetime

logger = logging.getLogger(__name__)


async def get_technical_analysis(ticker: str, spot_price: float, options_data: Dict) -> Dict:
    """Get technical analysis perspective using GROQ."""
    try:
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            return {'error': 'No API key', 'model': 'technical'}
        
        context = f"""As a technical analyst, analyze {ticker} at ${spot_price:.2f}.
        Focus on:
        1. Key support/resistance levels
        2. Technical indicators outlook (RSI, MACD)
        3. Recommended option strategy based on technicals
        Provide a 2-sentence recommendation."""
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': 'llama-3.3-70b-versatile',
            'messages': [{'role': 'user', 'content': context}],
            'temperature': 0.3,
            'max_tokens': 200
        }
        
        response = await asyncio.to_thread(
            requests.post,
            'https://api.groq.com/openai/v1/chat/completions',
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            recommendation = result['choices'][0]['message']['content']
            return {
                'model': 'technical',
                'recommendation': recommendation,
                'strategy': _extract_strategy(recommendation),
                'confidence': 0.75
            }
        return {'error': f"Status {response.status_code}", 'model': 'technical'}
            
    except Exception as e:
        logger.error(f"Technical analysis error: {e}")
        return {'error': str(e), 'model': 'technical'}


async def get_fundamental_analysis(ticker: str, spot_price: float, options_data: Dict) -> Dict:
    """Get fundamental analysis perspective using GROQ."""
    try:
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            return {'error': 'No API key', 'model': 'fundamental'}
        
        context = f"""As a fundamental analyst, analyze {ticker} at ${spot_price:.2f}.
        Focus on:
        1. Valuation perspective (overvalued/undervalued)
        2. Near-term catalysts (earnings, news)
        3. Recommended option strategy based on fundamentals
        Provide a 2-sentence recommendation."""
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': 'llama-3.3-70b-versatile',
            'messages': [{'role': 'user', 'content': context}],
            'temperature': 0.3,
            'max_tokens': 200
        }
        
        response = await asyncio.to_thread(
            requests.post,
            'https://api.groq.com/openai/v1/chat/completions',
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            recommendation = result['choices'][0]['message']['content']
            return {
                'model': 'fundamental',
                'recommendation': recommendation,
                'strategy': _extract_strategy(recommendation),
                'confidence': 0.75
            }
        return {'error': f"Status {response.status_code}", 'model': 'fundamental'}
            
    except Exception as e:
        logger.error(f"Fundamental analysis error: {e}")
        return {'error': str(e), 'model': 'fundamental'}


async def get_sentiment_analysis(ticker: str, spot_price: float, options_data: Dict) -> Dict:
    """Get sentiment-based analysis using GROQ."""
    try:
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            return {'error': 'No API key', 'model': 'sentiment'}
        
        # Get P/C ratio from options data
        pcr = "unknown"
        if options_data and 'chains' in options_data:
            total_call_vol = 0
            total_put_vol = 0
            for exp, chain in options_data.get('chains', {}).items():
                for c in chain.get('calls', []):
                    total_call_vol += c.get('volume', 0) or 0
                for p in chain.get('puts', []):
                    total_put_vol += p.get('volume', 0) or 0
            if total_call_vol > 0:
                pcr = f"{total_put_vol/total_call_vol:.2f}"
        
        context = f"""As a market sentiment analyst, analyze {ticker} at ${spot_price:.2f}.
        Put/Call ratio: {pcr}
        Focus on:
        1. Market sentiment interpretation
        2. Unusual options activity
        3. Recommended option strategy based on sentiment
        Provide a 2-sentence recommendation."""
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': 'llama-3.3-70b-versatile',
            'messages': [{'role': 'user', 'content': context}],
            'temperature': 0.3,
            'max_tokens': 200
        }
        
        response = await asyncio.to_thread(
            requests.post,
            'https://api.groq.com/openai/v1/chat/completions',
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            recommendation = result['choices'][0]['message']['content']
            return {
                'model': 'sentiment',
                'recommendation': recommendation,
                'strategy': _extract_strategy(recommendation),
                'confidence': 0.70
            }
        return {'error': f"Status {response.status_code}", 'model': 'sentiment'}
            
    except Exception as e:
        logger.error(f"Sentiment analysis error: {e}")
        return {'error': str(e), 'model': 'sentiment'}


def _extract_strategy(text: str) -> str:
    """Extract strategy type from recommendation text."""
    text_lower = text.lower()
    
    strategies = [
        ('iron condor', 'Iron Condor'),
        ('iron butterfly', 'Iron Butterfly'),
        ('bull call spread', 'Bull Call Spread'),
        ('bear put spread', 'Bear Put Spread'),
        ('covered call', 'Covered Call'),
        ('protective put', 'Protective Put'),
        ('straddle', 'Straddle'),
        ('strangle', 'Strangle'),
        ('calendar spread', 'Calendar Spread'),
        ('call', 'Long Call'),
        ('put', 'Long Put'),
        ('bullish', 'Bullish Strategy'),
        ('bearish', 'Bearish Strategy'),
        ('neutral', 'Neutral Strategy')
    ]
    
    for keyword, strategy in strategies:
        if keyword in text_lower:
            return strategy
    
    return 'Hold/Monitor'


def aggregate_recommendations(results: List[Dict]) -> Dict:
    """Aggregate multiple analysis perspectives into consensus."""
    valid_results = [r for r in results if 'error' not in r]
    
    if not valid_results:
        return {
            'consensus_strategy': 'Unable to analyze',
            'confidence_score': 0,
            'model_votes': {},
            'rationale': 'No valid analysis available',
            'recommendations': results
        }
    
    # Count strategy votes
    strategy_votes = {}
    for r in valid_results:
        strategy = r.get('strategy', 'Unknown')
        strategy_votes[strategy] = strategy_votes.get(strategy, 0) + 1
    
    # Get consensus
    if strategy_votes:
        consensus = max(strategy_votes.items(), key=lambda x: x[1])[0]
    else:
        consensus = 'Hold/Monitor'
    
    # Calculate confidence
    total_confidence = sum(r.get('confidence', 0.5) for r in valid_results)
    avg_confidence = total_confidence / len(valid_results) if valid_results else 0
    
    # Agreement bonus
    agreement_ratio = max(strategy_votes.values()) / len(valid_results) if strategy_votes else 0
    confidence_score = avg_confidence * (0.7 + 0.3 * agreement_ratio)
    
    # Build rationale
    rationales = [r.get('recommendation', '')[:100] for r in valid_results if r.get('recommendation')]
    combined_rationale = ' | '.join(rationales) if rationales else 'Multiple perspectives analyzed'
    
    return {
        'consensus_strategy': consensus,
        'confidence_score': confidence_score,
        'model_votes': {r['model']: r.get('strategy', 'N/A') for r in valid_results},
        'rationale': combined_rationale[:300],
        'recommendations': results,
        'models_used': [r['model'] for r in valid_results]
    }


async def get_multi_model_recommendations(ticker: str, spot_price: float, options_data: Dict) -> Dict:
    """
    Get recommendations from multiple analysis perspectives in parallel.
    Uses only GROQ API with different prompting strategies.
    """
    logger.info(f"Getting multi-perspective analysis for {ticker}")
    
    # Run all analyses in parallel
    tasks = [
        get_technical_analysis(ticker, spot_price, options_data),
        get_fundamental_analysis(ticker, spot_price, options_data),
        get_sentiment_analysis(ticker, spot_price, options_data),
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Convert exceptions to error dicts
    results = [
        r if isinstance(r, dict) else {'error': str(r), 'model': 'unknown'}
        for r in results
    ]
    
    # Aggregate results
    aggregated = aggregate_recommendations(results)
    
    logger.info(f"Multi-perspective consensus: {aggregated.get('consensus_strategy')} "
                f"(confidence: {aggregated.get('confidence_score', 0):.2f})")
    
    return aggregated
