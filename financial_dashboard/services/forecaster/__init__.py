"""
FinGPT Forecaster Service - predict stock price movements using LLM.
Based on FinGPT-Forecaster pattern with news + fundamentals.
"""
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class FinGPTForecaster:
    """FinGPT-based stock price movement forecaster."""
    
    def __init__(self, model_adapter=None):
        """
        Initialize forecaster.
        
        Args:
            model_adapter: Model adapter for generation (if None, will create default)
        """
        self.model_adapter = model_adapter
    
    def forecast(
        self,
        ticker: str,
        start_date: str = None,
        n_weeks: int = 4,
        include_financials: bool = True
    ) -> Dict[str, Any]:
        """
        Generate price movement forecast for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start date for forecast (YYYY-MM-DD), defaults to today
            n_weeks: Number of past weeks to consider for news
            include_financials: Whether to include fundamental data
            
        Returns:
            Forecast dict with predictions, analysis, and provenance
        """
        if not start_date:
            start_date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"Generating forecast for {ticker} from {start_date}")
        
        try:
            # Step 1: Retrieve relevant news
            news_context = self._get_news_context(ticker, n_weeks)
            
            # Step 2: Get financials if requested
            financials_context = ""
            if include_financials:
                financials_context = self._get_financials_context(ticker)
            
            # Step 3: Build forecasting prompt
            prompt = self._build_forecast_prompt(
                ticker,
                start_date,
                news_context,
                financials_context
            )
            
            # Step 4: Get model adapter
            adapter = self._get_adapter()
            
            # Step 5: Generate forecast
            result = adapter.generate(prompt, max_tokens=512, temperature=0.3)
            forecast_text = result.get('text', 'Unable to generate forecast')
            
            # Step 6: Parse and format result
            parsed = self._parse_forecast(forecast_text)
            
            return {
                'ticker': ticker,
                'forecast_date': start_date,
                'prediction': parsed.get('prediction', 'neutral'),
                'confidence': parsed.get('confidence', 0.5),
                'analysis': parsed.get('analysis', forecast_text),
                'rationale': parsed.get('rationale', 'See analysis'),
                'provenance': {
                    'news_items': len(news_context.split('\n\n')) if news_context else 0,
                    'included_financials': include_financials,
                    'model': result.get('model', 'unknown')
                },
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Forecast failed: {e}")
            return {
                'ticker': ticker,
                'forecast_date': start_date,
                'prediction': 'error',
                'confidence': 0.0,
                'analysis': f'Forecast generation failed: {str(e)}',
                'error': str(e)
            }
    
    def _get_news_context(self, ticker: str, n_weeks: int) -> str:
        """Retrieve news context from RAG or other sources."""
        try:
            from financial_dashboard.services.rag import query_retriever
            
            # Query for ticker-specific news
            query = f"Recent news and analysis for {ticker}"
            results = query_retriever(query, top_k=5)
            
            if results:
                context_parts = []
                for i, doc in enumerate(results[:3]):
                    snippet = doc['text'][:300]
                    context_parts.append(f"[News {i+1}]: {snippet}")
                return "\n\n".join(context_parts)
            else:
                return f"(No recent news found for {ticker})"
                
        except Exception as e:
            logger.warning(f"Failed to retrieve news context: {e}")
            return f"(News context unavailable)"
    
    def _get_financials_context(self, ticker: str) -> str:
        """Get fundamental financial context."""
        # In a real implementation, would call financial data APIs
        # For now, return a template
        return f"""
Recent Financials for {ticker}:
- Revenue growth: Strong
- Profit margins: Healthy
- Valuation: Reasonable relative to peers
"""
    
    def _build_forecast_prompt(
        self,
        ticker: str,
        start_date: str,
        news_context: str,
        financials_context: str
    ) -> str:
        """Build the forecasting prompt."""
        prompt = f"""You are a financial analyst providing stock price movement forecasts.

Ticker: {ticker}
Forecast Date: {start_date}

Recent News:
{news_context}

{financials_context if financials_context else ""}

Based on the above information, provide a stock price movement forecast for the next week.

Your response MUST include:
1. PREDICTION: [up/down/neutral]
2. CONFIDENCE: [0.0-1.0]
3. ANALYSIS: [2-3 sentences explaining key drivers]
4. RATIONALE: [Brief justification]

Format your response clearly with these headings."""
        
        return prompt
    
    def _parse_forecast(self, text: str) -> Dict[str, Any]:
        """Parse the LLM forecast output."""
        result = {
            'prediction': 'neutral',
            'confidence': 0.5,
            'analysis': text,
            'rationale': ''
        }
        
        import re

        lines = text.split('\n')
        for line in lines:
            low = line.strip().lower()
            if 'prediction:' in low:
                if 'up' in low:
                    result['prediction'] = 'up'
                elif 'down' in low:
                    result['prediction'] = 'down'
                else:
                    result['prediction'] = 'neutral'

            if 'confidence:' in low:
                try:
                    # Extract numeric part and normalize
                    match = re.search(r"(\d+\.?\d*)", low)
                    if match:
                        conf = float(match.group(1))
                        # If confidence is expressed as percentage (e.g. 70 or '70%'), convert to 0-1
                        if '%' in low or conf > 1.0:
                            conf = conf / 100.0
                        # Clamp to [0.0, 1.0]
                        conf = max(0.0, min(conf, 1.0))
                        result['confidence'] = conf
                except Exception:
                    pass

            # Capture rationale if present
            if low.startswith('rationale:') or low.startswith('reason:'):
                # keep original casing for rationale extract
                parts = line.split(':', 1)
                if len(parts) > 1:
                    result['rationale'] = parts[1].strip()

            if low.startswith('analysis:') and not result.get('analysis'):
                parts = line.split(':', 1)
                if len(parts) > 1:
                    result['analysis'] = parts[1].strip()
        
        return result
    
    def _get_adapter(self):
        """Get or create model adapter."""
        if self.model_adapter:
            return self.model_adapter
        
        # Use configured adapter from model_config
        from financial_dashboard.services.model_config import get_default_adapter
        return get_default_adapter()


def run_forecast(
    ticker: str,
    start_date: str = None,
    n_weeks: int = 4,
    include_financials: bool = True,
    model_provider: str = None
) -> Dict[str, Any]:
    """
    Convenience function to run a forecast.
    
    Args:
        ticker: Stock ticker
        start_date: Forecast start date (YYYY-MM-DD)
        n_weeks: Weeks of news history
        include_financials: Include fundamental data
        model_provider: Model provider (openai, mock, etc.)
        
    Returns:
        Forecast result dict
    """
    # Get model adapter based on provider
    adapter = None
    if model_provider and model_provider != 'mock':
        try:
            from financial_dashboard.models.openai_adapter import OpenAIAdapter
            if model_provider == 'openai':
                adapter = OpenAIAdapter({
                    'name': 'openai',
                    'type': 'openai',
                    'model': 'gpt-4o-mini'
                })
        except:
            pass
    
    forecaster = FinGPTForecaster(model_adapter=adapter)
    return forecaster.forecast(ticker, start_date, n_weeks, include_financials)
