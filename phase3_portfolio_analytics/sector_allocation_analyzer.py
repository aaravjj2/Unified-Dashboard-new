"""Sector Allocation Analyzer

Maps portfolio holdings to sectors and computes:
- Percentage allocation by sector
- Performance contribution by sector
- Sector concentration metrics
- Hierarchical sector breakdown

Uses a local sector mapping file (data/sector_mapping.json).
"""
from __future__ import annotations
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional


class SectorAllocationAnalyzer:
    """Analyzes portfolio allocation and performance by sector."""
    
    def __init__(self, sector_mapping_path: Optional[Path] = None):
        """Initialize with sector mapping file.
        
        Args:
            sector_mapping_path: Path to JSON file mapping ticker -> sector
        """
        if sector_mapping_path is None:
            # Default to data/sector_mapping.json
            sector_mapping_path = Path(__file__).parent.parent / 'data' / 'sector_mapping.json'
        
        self.sector_mapping_path = Path(sector_mapping_path)
        self.sector_map = self._load_sector_mapping()
    
    def _load_sector_mapping(self) -> Dict[str, str]:
        """Load sector mapping from JSON file."""
        if not self.sector_mapping_path.exists():
            # Return empty mapping if file doesn't exist
            return {}
        
        with open(self.sector_mapping_path, 'r', encoding='utf8') as f:
            return json.load(f)
    
    def get_sector(self, ticker: str) -> str:
        """Get sector for a ticker symbol.
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Sector name or 'Unknown' if not mapped
        """
        return self.sector_map.get(ticker.upper(), 'Unknown')
    
    def analyze_allocation(self, holdings: pd.DataFrame) -> Dict:
        """Analyze sector allocation from holdings.
        
        Args:
            holdings: DataFrame with columns ['ticker', 'shares', 'price', 'value']
        
        Returns:
            Dictionary with sector allocation analysis
        """
        if 'ticker' not in holdings.columns:
            raise ValueError("Holdings must have 'ticker' column")
        
        # Ensure value column exists
        if 'value' not in holdings.columns:
            if 'shares' in holdings.columns and 'price' in holdings.columns:
                holdings = holdings.copy()
                holdings['value'] = holdings['shares'] * holdings['price']
            else:
                raise ValueError("Holdings must have 'value' column or both 'shares' and 'price'")
        
        # Map tickers to sectors
        holdings = holdings.copy()
        holdings['sector'] = holdings['ticker'].apply(self.get_sector)
        
        # Aggregate by sector
        total_value = holdings['value'].sum()
        sector_agg = holdings.groupby('sector').agg({
            'value': 'sum',
            'ticker': 'count'
        }).rename(columns={'ticker': 'num_holdings'})
        
        sector_agg['allocation_pct'] = (sector_agg['value'] / total_value * 100).round(2)
        sector_agg = sector_agg.sort_values('value', ascending=False)
        
        # Calculate concentration metrics
        hhi = ((sector_agg['allocation_pct'] / 100) ** 2).sum()  # Herfindahl-Hirschman Index
        
        result = {
            "total_value": float(total_value),
            "num_sectors": len(sector_agg),
            "concentration_hhi": float(hhi),
            "sectors": []
        }
        
        for sector, row in sector_agg.iterrows():
            result["sectors"].append({
                "sector": str(sector),
                "value": float(row['value']),
                "allocation_pct": float(row['allocation_pct']),
                "num_holdings": int(row['num_holdings'])
            })
        
        return result
    
    def analyze_sector_performance(self, holdings: pd.DataFrame, 
                                   returns_data: Optional[pd.DataFrame] = None) -> Dict:
        """Analyze performance contribution by sector.
        
        Args:
            holdings: DataFrame with holdings info
            returns_data: Optional DataFrame with ticker returns
        
        Returns:
            Dictionary with sector performance breakdown
        """
        allocation = self.analyze_allocation(holdings)
        
        if returns_data is None:
            # Return allocation only
            return allocation
        
        # Add performance data if available
        if 'ticker' not in returns_data.columns or 'return' not in returns_data.columns:
            return allocation
        
        # Merge holdings with returns
        holdings_with_returns = holdings.merge(
            returns_data[['ticker', 'return']], 
            on='ticker', 
            how='left'
        )
        
        holdings_with_returns['sector'] = holdings_with_returns['ticker'].apply(self.get_sector)
        holdings_with_returns['contribution'] = (
            holdings_with_returns['value'] / holdings_with_returns['value'].sum() * 
            holdings_with_returns['return'].fillna(0)
        )
        
        sector_perf = holdings_with_returns.groupby('sector').agg({
            'return': 'mean',
            'contribution': 'sum',
            'value': 'sum'
        })
        
        # Update sectors with performance data
        for sector_info in allocation['sectors']:
            sector = sector_info['sector']
            if sector in sector_perf.index:
                sector_info['avg_return'] = float(sector_perf.loc[sector, 'return'])
                sector_info['contribution'] = float(sector_perf.loc[sector, 'contribution'])
        
        return allocation
    
    def get_top_sectors(self, holdings: pd.DataFrame, top_n: int = 5) -> List[Dict]:
        """Get top N sectors by allocation.
        
        Args:
            holdings: Portfolio holdings DataFrame
            top_n: Number of top sectors to return
        
        Returns:
            List of sector dictionaries
        """
        analysis = self.analyze_allocation(holdings)
        return analysis['sectors'][:top_n]


if __name__ == '__main__':
    # Quick test with sample data
    sample_holdings = pd.DataFrame({
        'ticker': ['AAPL', 'MSFT', 'GOOGL', 'JPM', 'XOM'],
        'shares': [100, 50, 25, 200, 150],
        'price': [175.0, 380.0, 140.0, 150.0, 110.0],
    })
    sample_holdings['value'] = sample_holdings['shares'] * sample_holdings['price']
    
    analyzer = SectorAllocationAnalyzer()
    result = analyzer.analyze_allocation(sample_holdings)
    
    print("Sector Allocation Analysis:")
    print(f"Total Value: ${result['total_value']:,.2f}")
    print(f"Number of Sectors: {result['num_sectors']}")
    print(f"Concentration (HHI): {result['concentration_hhi']:.3f}")
    print("\nSectors:")
    for s in result['sectors']:
        print(f"  {s['sector']}: {s['allocation_pct']}% (${s['value']:,.2f})")
