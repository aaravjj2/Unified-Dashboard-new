"""
Quick test of the stock picker pipeline.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from financial_dashboard.picker.universe import StockUniverse
from financial_dashboard.picker.ensemble_picker import EnsemblePicker


def test_picker_small():
    """Test picker with a small universe."""
    print("\n" + "="*60)
    print("TESTING STOCK PICKER PIPELINE")
    print("="*60)
    
    # Small test universe
    test_universe = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AMD', 'NFLX', 'COST']
    
    print(f"\n1. Testing with {len(test_universe)} stocks: {test_universe}")
    
    # Create picker
    picker = EnsemblePicker()
    print("✓ Created EnsemblePicker")
    
    # Generate picks
    print(f"\n2. Generating top 5 picks...")
    picks = picker.generate_picks(test_universe, n=5, parallel=True)
    
    print(f"\n✓ Generated {len(picks)} picks!")
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    
    for idx, row in picks.iterrows():
        print(f"\n#{row['rank']} {row['ticker']} - Score: {row['combined_score']:.1f}/100")
        print(f"   Momentum: {row['momentum_score']:.1f} | Sentiment: {row['sentiment_score']:.1f}")
        print(f"   Fundamental: {row['fundamental_score']:.1f} | Technical: {row['technical_score']:.1f}")
        print(f"   Rationale: {row['rationale'][:100]}...")
    
    print("\n" + "="*60)
    print("✅ PIPELINE TEST PASSED!")
    print("="*60)
    
    return True


if __name__ == "__main__":
    test_picker_small()
