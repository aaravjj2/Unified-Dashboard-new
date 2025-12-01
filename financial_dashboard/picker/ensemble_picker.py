"""
Ensemble Picker - Combine scores from all modules and generate top picks.
"""

import pandas as pd
import logging
from datetime import datetime, date
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from .momentum_scorer import MomentumScorer
from .sentiment_scorer import SentimentScorer
from .fundamental_scorer import FundamentalScorer
from .technical_scorer import TechnicalScorer

logger = logging.getLogger(__name__)


class EnsemblePicker:
    """Combine multiple scorers to generate stock picks."""
    
    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None
    ):
        """
        Initialize ensemble picker.
        
        Args:
            weights: Dict of weights for each scorer
                    Default: {'momentum': 0.35, 'sentiment': 0.25, 
                             'fundamental': 0.25, 'technical': 0.15}
        """
        self.weights = weights or {
            'momentum': 0.35,
            'sentiment': 0.25,
            'fundamental': 0.25,
            'technical': 0.15
        }
        
        self.momentum_scorer = MomentumScorer()
        self.sentiment_scorer = SentimentScorer()
        self.fundamental_scorer = FundamentalScorer()
        self.technical_scorer = TechnicalScorer()
    
    def score_stock(self, ticker: str) -> Dict:
        """
        Score a single stock using all factors.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dict with all scores and rationale
        """
        try:
            # Get scores from all modules
            momentum_score = self.momentum_scorer.score(ticker)
            sentiment_score = self.sentiment_scorer.score(ticker)
            fundamental_score = self.fundamental_scorer.score(ticker)
            technical_score = self.technical_scorer.score(ticker)
            
            # Calculate combined score (weighted average)
            combined_score = (
                momentum_score * self.weights['momentum'] +
                sentiment_score * self.weights['sentiment'] +
                fundamental_score * self.weights['fundamental'] +
                technical_score * self.weights['technical']
            )
            
            # Generate rationale
            rationale = self._generate_rationale(
                ticker,
                momentum_score,
                sentiment_score,
                fundamental_score,
                technical_score,
                combined_score
            )
            
            return {
                'ticker': ticker,
                'combined_score': round(combined_score, 1),
                'momentum_score': round(momentum_score, 1),
                'sentiment_score': round(sentiment_score, 1),
                'fundamental_score': round(fundamental_score, 1),
                'technical_score': round(technical_score, 1),
                'rationale': rationale
            }
            
        except Exception as e:
            logger.error(f"Error scoring {ticker}: {e}")
            return {
                'ticker': ticker,
                'combined_score': 0,
                'momentum_score': 0,
                'sentiment_score': 0,
                'fundamental_score': 0,
                'technical_score': 0,
                'rationale': f"Error: {str(e)}"
            }
    
    def generate_picks(
        self,
        universe: List[str],
        n: int = 20,
        parallel: bool = True
    ) -> pd.DataFrame:
        """
        Generate top N stock picks from universe.
        
        Args:
            universe: List of tickers to analyze
            n: Number of top picks to return
            parallel: Use parallel processing (faster)
            
        Returns:
            DataFrame with top N picks ranked by combined score
        """
        logger.info(f"Generating picks from universe of {len(universe)} stocks...")
        
        # Score all stocks
        results = []
        
        if parallel:
            # Parallel processing for speed
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {executor.submit(self.score_stock, ticker): ticker 
                          for ticker in universe}
                
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        if result['combined_score'] > 0:
                            results.append(result)
                    except Exception as e:
                        ticker = futures[future]
                        logger.error(f"Failed to score {ticker}: {e}")
        else:
            # Sequential processing
            for ticker in universe:
                try:
                    result = self.score_stock(ticker)
                    if result['combined_score'] > 0:
                        results.append(result)
                except Exception as e:
                    logger.error(f"Failed to score {ticker}: {e}")
        
        # Convert to DataFrame
        df = pd.DataFrame(results)
        
        if df.empty:
            logger.warning("No stocks scored successfully!")
            return df
        
        # Sort by combined score (descending)
        df = df.sort_values('combined_score', ascending=False).reset_index(drop=True)
        
        # Take top N
        df = df.head(n)
        
        # Add rank column
        df.insert(0, 'rank', range(1, len(df) + 1))
        
        # Add generated timestamp
        df['generated_at'] = datetime.now()
        
        logger.info(f"✓ Generated {len(df)} picks (top scorer: {df.iloc[0]['ticker']} with {df.iloc[0]['combined_score']:.1f})")
        
        return df
    
    def generate_weekly_picks(self, universe: List[str], n: int = 20) -> pd.DataFrame:
        """Generate weekly picks."""
        picks = self.generate_picks(universe, n=n)
        
        # Add week_start_date
        today = date.today()
        # Find Monday of current week
        week_start = today - pd.Timedelta(days=today.weekday())
        picks['week_start_date'] = week_start
        
        return picks
    
    def generate_monthly_picks(self, universe: List[str], n: int = 20) -> pd.DataFrame:
        """Generate monthly picks."""
        picks = self.generate_picks(universe, n=n)
        
        # Add month_start_date
        today = date.today()
        month_start = date(today.year, today.month, 1)
        picks['month_start_date'] = month_start
        
        return picks
    
    def _generate_rationale(
        self,
        ticker: str,
        momentum: float,
        sentiment: float,
        fundamental: float,
        technical: float,
        combined: float
    ) -> str:
        """Generate human-readable rationale for pick."""
        
        # Find strongest factor
        scores = {
            'momentum': momentum,
            'sentiment': sentiment,
            'fundamental': fundamental,
            'technical': technical
        }
        
        strongest = max(scores, key=scores.get)
        strongest_score = scores[strongest]
        
        # Build rationale
        reasons = []
        
        if momentum >= 70:
            reasons.append(f"strong momentum ({momentum:.0f}/100)")
        elif momentum >= 60:
            reasons.append(f"positive momentum ({momentum:.0f}/100)")
        
        if sentiment >= 70:
            reasons.append(f"bullish sentiment ({sentiment:.0f}/100)")
        elif sentiment >= 60:
            reasons.append(f"favorable sentiment ({sentiment:.0f}/100)")
        
        if fundamental >= 70:
            reasons.append(f"solid fundamentals ({fundamental:.0f}/100)")
        elif fundamental >= 60:
            reasons.append(f"healthy fundamentals ({fundamental:.0f}/100)")
        
        if technical >= 70:
            reasons.append(f"strong technicals ({technical:.0f}/100)")
        elif technical >= 60:
            reasons.append(f"positive technicals ({technical:.0f}/100)")
        
        if not reasons:
            reasons.append(f"balanced across factors")
        
        rationale = f"{ticker} selected for " + ", ".join(reasons) + f". Combined score: {combined:.0f}/100."
        
        return rationale


def save_weekly_picks(picks: pd.DataFrame, week_start: date):
    """Save weekly picks to database."""
    try:
        from utils import db_utils
        
        engine = db_utils._DB.get_engine()
        if engine is None:
            logger.warning("No database connection, cannot save picks")
            return
        
        # Prepare data for insertion
        picks_copy = picks.copy()
        picks_copy['week_start_date'] = week_start
        
        # Insert into database
        picks_copy.to_sql(
            'weekly_picks_production',
            engine,
            if_exists='append',
            index=False
        )
        
        logger.info(f"✓ Saved {len(picks)} weekly picks to database for week {week_start}")
        
    except Exception as e:
        logger.error(f"Failed to save weekly picks: {e}")


def save_monthly_picks(picks: pd.DataFrame, month_start: date):
    """Save monthly picks to database."""
    try:
        from utils import db_utils
        
        engine = db_utils._DB.get_engine()
        if engine is None:
            logger.warning("No database connection, cannot save picks")
            return
        
        # Prepare data for insertion
        picks_copy = picks.copy()
        picks_copy['month_start_date'] = month_start
        
        # Insert into database
        picks_copy.to_sql(
            'monthly_picks_production',
            engine,
            if_exists='append',
            index=False
        )
        
        logger.info(f"✓ Saved {len(picks)} monthly picks to database for month {month_start}")
        
    except Exception as e:
        logger.error(f"Failed to save monthly picks: {e}")
