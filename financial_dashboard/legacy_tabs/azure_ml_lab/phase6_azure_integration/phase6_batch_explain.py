"""
Phase 6 — Batch SHAP Orchestrator
===================================

Orchestrates batch SHAP explanation generation for entire portfolios.
Integrates with Phase 3 offline analytics and Phase 3.5 hybrid caching.

Key Features:
- Load portfolio tickers from offline_portfolio_engine.py
- Batch SHAP generation via AzureMLSHAPClient
- Parallel processing with cache optimization
- Aggregated feature importance ranking
- <8s SLA for 10 tickers with cache enabled
- Deterministic reproducibility in mock mode

Dependencies:
- Phase 3: offline_portfolio_engine (portfolio data source)
- Phase 6: explainability_azure (AzureMLSHAPClient)
- Phase 3.5: ExplainabilityContract, CacheRouter

Author: Agent 1A — Unified Financial Dashboard Team
Version: 1.0 (Phase 6)
"""

import logging
import time
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

import pandas as pd
import numpy as np

# Phase 6 Azure ML Integration
from .explainability_azure import (
    AzureMLSHAPClient,
    create_azure_shap_client,
    AZURE_ML_FEATURES
)

# Phase 3.5 Contracts
from phase3p5_hybrid_bridge.data_bridge.data_contracts import (
    ExplainabilityContract,
    ContractType
)

# Phase 3 Offline Analytics (portfolio data source)
# Note: This import is optional - CSV fallback available
PHASE3_AVAILABLE = False
OfflinePortfolioEngine = None

try:
    from financial_dashboard.offline_analytics.offline_portfolio_engine import (
        OfflinePortfolioEngine as _OfflinePortfolioEngine
    )
    OfflinePortfolioEngine = _OfflinePortfolioEngine
    PHASE3_AVAILABLE = True
except ImportError:
    logging.warning("⚠️ Phase 3 offline_portfolio_engine not available. Using CSV fallback.")


logger = logging.getLogger(__name__)


# =============================================================================
# BATCH SHAP RESULT AGGREGATION
# =============================================================================

@dataclass
class BatchSHAPResult:
    """
    Aggregated batch SHAP results for portfolio.
    
    Attributes:
        portfolio_id: Unique portfolio identifier
        timestamp: Batch execution timestamp
        tickers: List of tickers analyzed
        contracts: Dict of ticker → ExplainabilityContract
        aggregated_importance: Global feature importance across all tickers
        top_features: Top N features by aggregated importance
        execution_time_seconds: Total batch execution time
        cache_hit_rate: Percentage of cache hits
        errors: Dict of ticker → error message (if any)
        metadata: Additional metadata
    """
    portfolio_id: str
    timestamp: str
    tickers: List[str]
    contracts: Dict[str, ExplainabilityContract]
    aggregated_importance: Dict[str, float]
    top_features: List[Tuple[str, float]]  # (feature, importance)
    execution_time_seconds: float
    cache_hit_rate: float
    errors: Dict[str, str]
    metadata: Dict[str, Any]
    
    def to_json(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            'portfolio_id': self.portfolio_id,
            'timestamp': self.timestamp,
            'tickers': self.tickers,
            'contracts': {
                ticker: contract.to_json() 
                for ticker, contract in self.contracts.items()
            },
            'aggregated_importance': self.aggregated_importance,
            'top_features': self.top_features,
            'execution_time_seconds': self.execution_time_seconds,
            'cache_hit_rate': self.cache_hit_rate,
            'errors': self.errors,
            'metadata': self.metadata
        }
    
    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert to pandas DataFrame for analysis.
        
        Returns:
            DataFrame with columns: ticker, feature, shap_value, importance, rank
        """
        rows = []
        
        for ticker, contract in self.contracts.items():
            for feature, shap_val in contract.shap_values.items():
                importance = contract.feature_importance.get(feature, 0.0)
                rows.append({
                    'ticker': ticker,
                    'feature': feature,
                    'shap_value': shap_val,
                    'importance': importance,
                    'prediction': contract.prediction
                })
        
        df = pd.DataFrame(rows)
        
        # Add global rank
        if not df.empty:
            df['global_importance'] = df['feature'].map(self.aggregated_importance)
            df['global_rank'] = df.groupby('feature')['global_importance'].transform(
                lambda x: x.rank(ascending=False, method='min')
            )
        
        return df
    
    def get_top_features_by_ticker(self, top_n: int = 5) -> Dict[str, List[Tuple[str, float]]]:
        """
        Get top N features for each ticker.
        
        Args:
            top_n: Number of top features to return
        
        Returns:
            Dict of ticker → [(feature, importance), ...]
        """
        result = {}
        
        for ticker, contract in self.contracts.items():
            sorted_features = sorted(
                contract.feature_importance.items(),
                key=lambda x: x[1],
                reverse=True
            )[:top_n]
            result[ticker] = sorted_features
        
        return result

    @property
    def ticker_results(self) -> List[ExplainabilityContract]:
        """Backward-compatible alias returning list of ExplainabilityContract objects."""
        return list(self.contracts.values())

    @property
    def tickers_analyzed(self) -> List[str]:
        """Backward-compatible alias for tickers list."""
        return self.tickers

    @property
    def cache_hit_rate_pct(self) -> float:
        """Return cache hit rate in percent (alias)."""
        return float(self.cache_hit_rate)


# =============================================================================
# PORTFOLIO DATA LOADERS
# =============================================================================

def load_portfolio_from_phase3(
    portfolio_file: Optional[str] = None
) -> Tuple[List[str], Dict[str, Dict[str, float]]]:
    """
    Load portfolio tickers and feature vectors from Phase 3 offline analytics.
    
    Args:
        portfolio_file: Optional path to portfolio CSV (uses default if None)
    
    Returns:
        (tickers, feature_vectors) where feature_vectors is dict of ticker → features
    
    Raises:
        ImportError: If Phase 3 offline_portfolio_engine not available
        ValueError: If portfolio data invalid
    """
    if not PHASE3_AVAILABLE:
        raise ImportError(
            "Phase 3 offline_portfolio_engine not available. "
            "Install Phase 3 analytics modules or use load_portfolio_from_csv()."
        )
    
    logger.info("📂 Loading portfolio from Phase 3 offline analytics...")
    
    # Initialize Phase 3 engine
    engine = OfflinePortfolioEngine(portfolio_file=portfolio_file)
    
    # Get portfolio holdings
    holdings_df = engine.get_holdings()
    
    if holdings_df.empty:
        raise ValueError("Portfolio is empty. Check portfolio file.")
    
    tickers = holdings_df['ticker'].tolist()
    
    logger.info(f"✅ Loaded {len(tickers)} tickers from Phase 3: {tickers}")
    
    # Generate feature vectors for each ticker
    # Note: In production, these would come from market data pipeline
    # For Phase 6, we'll generate synthetic features for testing
    feature_vectors = {}
    
    for ticker in tickers:
        # Use ticker hash for deterministic feature generation
        import hashlib
        ticker_seed = int(hashlib.md5(ticker.encode()).hexdigest()[:8], 16) % 10000
        np.random.seed(ticker_seed)
        
        # Generate 28 features matching AZURE_ML_FEATURES
        features = {}
        for feat in AZURE_ML_FEATURES:
            if 'sector_' in feat:
                # One-hot encoding (0 or 1)
                features[feat] = float(np.random.choice([0, 1]))
            elif feat in ['RSI', 'ADX']:
                # Range [0, 100]
                features[feat] = np.random.uniform(0, 100)
            elif feat in ['PE_ratio', 'PB_ratio', 'PS_ratio']:
                # Positive ratios
                features[feat] = np.random.uniform(5, 50)
            elif feat == 'beta':
                # Beta around 1.0
                features[feat] = np.random.uniform(0.5, 1.5)
            elif feat == 'volatility_30d':
                # Volatility 10%-50%
                features[feat] = np.random.uniform(0.1, 0.5)
            else:
                # Generic normalized features
                features[feat] = np.random.randn()
        
        feature_vectors[ticker] = features
    
    return tickers, feature_vectors


def load_portfolio_from_csv(csv_path: str) -> Tuple[List[str], Dict[str, Dict[str, float]]]:
    """
    Load portfolio from CSV file (fallback when Phase 3 unavailable).
    
    Expected CSV format:
        ticker,shares,cost_basis
        AAPL,100,150.00
        MSFT,50,300.00
        ...
    
    Args:
        csv_path: Path to portfolio CSV file
    
    Returns:
        (tickers, feature_vectors)
    
    Raises:
        FileNotFoundError: If CSV not found
        ValueError: If CSV format invalid
    """
    logger.info(f"📂 Loading portfolio from CSV: {csv_path}")
    
    csv_file = Path(csv_path)
    if not csv_file.exists():
        raise FileNotFoundError(f"Portfolio CSV not found: {csv_path}")
    
    # Read CSV
    df = pd.read_csv(csv_file)
    
    if 'ticker' not in df.columns:
        raise ValueError("CSV must contain 'ticker' column")
    
    tickers = df['ticker'].dropna().unique().tolist()
    
    if not tickers:
        raise ValueError("No tickers found in CSV")
    
    logger.info(f"✅ Loaded {len(tickers)} tickers from CSV: {tickers}")
    
    # Generate synthetic feature vectors (same logic as Phase 3 loader)
    feature_vectors = {}
    
    for ticker in tickers:
        import hashlib
        ticker_seed = int(hashlib.md5(ticker.encode()).hexdigest()[:8], 16) % 10000
        np.random.seed(ticker_seed)
        
        features = {}
        for feat in AZURE_ML_FEATURES:
            if 'sector_' in feat:
                features[feat] = float(np.random.choice([0, 1]))
            elif feat in ['RSI', 'ADX']:
                features[feat] = np.random.uniform(0, 100)
            elif feat in ['PE_ratio', 'PB_ratio', 'PS_ratio']:
                features[feat] = np.random.uniform(5, 50)
            elif feat == 'beta':
                features[feat] = np.random.uniform(0.5, 1.5)
            elif feat == 'volatility_30d':
                features[feat] = np.random.uniform(0.1, 0.5)
            else:
                features[feat] = np.random.randn()
        
        feature_vectors[ticker] = features
    
    return tickers, feature_vectors


# =============================================================================
# BATCH SHAP ORCHESTRATOR
# =============================================================================

class BatchSHAPOrchestrator:
    """
    Orchestrates batch SHAP explanation generation for portfolios.
    
    Responsibilities:
    - Load portfolio tickers from Phase 3 or CSV
    - Generate feature vectors for all tickers
    - Call AzureMLSHAPClient.generate_batch_shap_explanation()
    - Aggregate feature importance across portfolio
    - Cache management and performance optimization
    - Generate BatchSHAPResult for UI consumption
    
    Attributes:
        shap_client: AzureMLSHAPClient instance
        portfolio_source: 'phase3' or 'csv'
        portfolio_file: Path to portfolio data
    """
    
    def __init__(self,
                 shap_client: Optional[AzureMLSHAPClient] = None,
                 portfolio_source: str = 'phase3',
                 portfolio_file: Optional[str] = None):
        """
        Initialize batch SHAP orchestrator.
        
        Args:
            shap_client: AzureMLSHAPClient instance (creates new if None)
            portfolio_source: 'phase3' (offline analytics) or 'csv' (CSV file)
            portfolio_file: Path to portfolio file (optional)
        """
        self.shap_client = shap_client or create_azure_shap_client()
        self.portfolio_source = portfolio_source
        self.portfolio_file = portfolio_file
        
        logger.info(
            f"🔧 BatchSHAPOrchestrator initialized "
            f"(source={portfolio_source}, mode={'MOCK' if self.shap_client.use_mock else 'AZURE'})"
        )
    
    def batch_explain_portfolio(
        self,
        portfolio_id: str = "default_portfolio",
        top_n_features: int = 10,
        use_cache: bool = True,
        max_workers: int = 4,
        portfolio_source: Optional[str] = None,
        csv_path: Optional[str] = None
    ) -> BatchSHAPResult:
        """
        Generate batch SHAP explanations for entire portfolio.
        
        This is the PRIMARY method for "Explain All Portfolio" button.
        
        Workflow:
        1. Load portfolio tickers and feature vectors
        2. Call AzureMLSHAPClient.generate_batch_shap_explanation()
        3. Aggregate feature importance across all tickers
        4. Rank features globally
        5. Return BatchSHAPResult for UI rendering
        
        Args:
            portfolio_id: Unique portfolio identifier
            top_n_features: Number of top features to highlight
            use_cache: Whether to use L1/L2/L3 caching
            max_workers: Number of parallel threads
        
        Returns:
            BatchSHAPResult with aggregated SHAP data
        
        Performance SLA:
            - <8s for 10 tickers (with cache hits)
            - <30s for 50 tickers (cold cache)
        
        Raises:
            ValueError: If portfolio empty or invalid
            RuntimeError: If batch SHAP generation fails
        """
        start_time = time.time()
        
        logger.info(
            f"🔄 Starting batch SHAP for portfolio '{portfolio_id}' "
            f"(top_n={top_n_features}, cache={use_cache}, workers={max_workers})"
        )
        
        # Step 1: Load portfolio
        try:
            # Runtime override for source/file (backwards compatibility)
            src = portfolio_source or self.portfolio_source
            file_path = csv_path or self.portfolio_file

            if src == 'phase3':
                tickers, feature_vectors = load_portfolio_from_phase3(file_path)
            elif src == 'csv':
                if not file_path:
                    raise ValueError("portfolio_file/csv_path required for CSV source")
                tickers, feature_vectors = load_portfolio_from_csv(file_path)
            else:
                raise ValueError(f"Invalid portfolio_source: {src}")
        
        except Exception as e:
            logger.error(f"❌ Failed to load portfolio: {e}")
            raise
        
        if not tickers:
            raise ValueError("Portfolio is empty")
        
        logger.info(f"📊 Portfolio loaded: {len(tickers)} tickers")
        
        # Step 2: Generate batch SHAP explanations
        try:
            contracts = self.shap_client.generate_batch_shap_explanation(
                tickers=tickers,
                feature_vectors=feature_vectors,
                use_cache=use_cache,
                max_workers=max_workers
            )
        
        except Exception as e:
            logger.error(f"❌ Batch SHAP generation failed: {e}")
            raise RuntimeError(f"Batch SHAP failed: {e}")
        
        # Step 3: Aggregate feature importance
        aggregated_importance = self._aggregate_feature_importance(contracts)
        
        # Step 4: Rank top features
        top_features = sorted(
            aggregated_importance.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n_features]
        
        # Step 5: Collect errors (tickers that failed)
        errors = {}
        for ticker in tickers:
            if ticker not in contracts:
                errors[ticker] = "SHAP generation failed (check logs)"
        
        # Step 6: Calculate metrics
        elapsed = time.time() - start_time
        
        telemetry = self.shap_client.get_telemetry()
        cache_hit_rate = telemetry.get('cache_hit_rate_pct', 0.0)
        
        # Step 7: Create result
        result = BatchSHAPResult(
            portfolio_id=portfolio_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            tickers=tickers,
            contracts=contracts,
            aggregated_importance=aggregated_importance,
            top_features=top_features,
            execution_time_seconds=elapsed,
            cache_hit_rate=cache_hit_rate,
            errors=errors,
            metadata={
                'total_tickers': len(tickers),
                'successful_tickers': len(contracts),
                'failed_tickers': len(errors),
                'using_mock': self.shap_client.use_mock,
                'max_workers': max_workers,
                'use_cache': use_cache
            }
        )
        
        # Log summary
        success_rate = len(contracts) / len(tickers) * 100 if tickers else 0
        
        logger.info(
            f"✅ Batch SHAP complete: {len(contracts)}/{len(tickers)} tickers "
            f"({success_rate:.1f}% success) in {elapsed:.2f}s "
            f"(avg={elapsed/len(tickers):.2f}s/ticker, cache_hit={cache_hit_rate:.1f}%)"
        )
        
        if errors:
            logger.warning(f"⚠️ Failed tickers: {list(errors.keys())}")
        
        return result
    
    def _aggregate_feature_importance(
        self,
        contracts: Dict[str, ExplainabilityContract]
    ) -> Dict[str, float]:
        """
        Aggregate feature importance across all tickers.
        
        Uses mean importance across portfolio as global importance metric.
        
        Args:
            contracts: Dict of ticker → ExplainabilityContract
        
        Returns:
            Dict of feature → aggregated importance (0-1 normalized)
        """
        if not contracts:
            return {}
        
        # Collect importance values per feature
        feature_importances = defaultdict(list)
        
        for contract in contracts.values():
            for feature, importance in contract.feature_importance.items():
                feature_importances[feature].append(importance)
        
        # Compute mean importance per feature
        aggregated: Dict[str, float] = {
            feature: float(np.mean(values))
            for feature, values in feature_importances.items()
        }
        
        # Normalize to [0, 1]
        max_importance = max(aggregated.values()) if aggregated else 1.0
        
        if max_importance > 0:
            aggregated = {
                feature: float(importance / max_importance)
                for feature, importance in aggregated.items()
            }
        
        return aggregated
    
    def save_batch_result(
        self,
        result: BatchSHAPResult,
        output_dir: str = "outputs/phase6_batch_shap"
    ) -> Dict[str, str]:
        """
        Save batch SHAP result to disk in multiple formats.
        
        Args:
            result: BatchSHAPResult to save
            output_dir: Output directory path
        
        Returns:
            Dict of format → file_path
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"batch_shap_{result.portfolio_id}_{timestamp_str}"
        
        saved_files = {}
        
        # Save JSON
        json_file = output_path / f"{base_name}.json"
        with open(json_file, 'w') as f:
            json.dump(result.to_json(), f, indent=2)
        saved_files['json'] = str(json_file)
        
        # Save DataFrame as CSV
        csv_file = output_path / f"{base_name}.csv"
        df = result.to_dataframe()
        df.to_csv(csv_file, index=False)
        saved_files['csv'] = str(csv_file)
        
        # Save summary markdown
        md_file = output_path / f"{base_name}_summary.md"
        with open(md_file, 'w') as f:
            f.write(self._generate_markdown_summary(result))
        saved_files['markdown'] = str(md_file)
        
        logger.info(f"💾 Batch SHAP result saved to {output_dir} (3 formats)")
        
        return saved_files
    
    def _generate_markdown_summary(self, result: BatchSHAPResult) -> str:
        """Generate Markdown summary of batch SHAP result."""
        lines = [
            f"# Batch SHAP Summary — {result.portfolio_id}",
            f"",
            f"**Timestamp:** {result.timestamp}  ",
            f"**Total Tickers:** {len(result.tickers)}  ",
            f"**Successful:** {len(result.contracts)}  ",
            f"**Failed:** {len(result.errors)}  ",
            f"**Execution Time:** {result.execution_time_seconds:.2f}s  ",
            f"**Cache Hit Rate:** {result.cache_hit_rate:.1f}%  ",
            f"",
            f"## Top {len(result.top_features)} Features (Global Importance)",
            f"",
            f"| Rank | Feature | Importance |",
            f"|------|---------|------------|"
        ]
        
        for rank, (feature, importance) in enumerate(result.top_features, 1):
            lines.append(f"| {rank} | {feature} | {importance:.4f} |")
        
        lines.extend([
            f"",
            f"## Portfolio Tickers",
            f"",
            f"**Analyzed:** {', '.join(sorted(result.contracts.keys()))}  ",
        ])
        
        if result.errors:
            lines.extend([
                f"",
                f"**Failed:** {', '.join(sorted(result.errors.keys()))}  ",
            ])
        
        lines.extend([
            f"",
            f"## Performance Metrics",
            f"",
            f"- Avg time per ticker: {result.execution_time_seconds / len(result.tickers):.2f}s",
            f"- Success rate: {len(result.contracts) / len(result.tickers) * 100:.1f}%",
            f"- Cache efficiency: {result.cache_hit_rate:.1f}%",
            f"- Mode: {'MOCK (offline)' if result.metadata.get('using_mock') else 'Azure ML (live)'}",
        ])
        
        return "\n".join(lines)


# =============================================================================
# PUBLIC API
# =============================================================================

def create_batch_orchestrator(
    shap_client: Optional[AzureMLSHAPClient] = None,
    portfolio_source: str = 'phase3',
    portfolio_file: Optional[str] = None
) -> BatchSHAPOrchestrator:
    """
    Factory function to create BatchSHAPOrchestrator instance.
    
    Args:
        shap_client: AzureMLSHAPClient instance (creates new if None)
        portfolio_source: 'phase3' or 'csv'
        portfolio_file: Optional portfolio file path
    
    Returns:
        Configured BatchSHAPOrchestrator instance
    """
    return BatchSHAPOrchestrator(
        shap_client=shap_client,
        portfolio_source=portfolio_source,
        portfolio_file=portfolio_file
    )


# =============================================================================
# COMMAND-LINE INTERFACE
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    parser = argparse.ArgumentParser(description="Batch SHAP Orchestrator for Portfolio")
    parser.add_argument(
        '--portfolio-id',
        default='test_portfolio',
        help='Portfolio identifier'
    )
    parser.add_argument(
        '--source',
        choices=['phase3', 'csv'],
        default='csv',
        help='Portfolio data source'
    )
    parser.add_argument(
        '--file',
        help='Path to portfolio file (CSV or Phase 3 file)'
    )
    parser.add_argument(
        '--top-n',
        type=int,
        default=10,
        help='Number of top features to display'
    )
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Disable caching'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=4,
        help='Number of parallel workers'
    )
    parser.add_argument(
        '--output-dir',
        default='outputs/phase6_batch_shap',
        help='Output directory for results'
    )
    
    args = parser.parse_args()
    
    print("=== Phase 6 Batch SHAP Orchestrator ===\n")
    
    # Create orchestrator
    orchestrator = create_batch_orchestrator(
        portfolio_source=args.source,
        portfolio_file=args.file
    )
    
    # Run batch SHAP
    try:
        result = orchestrator.batch_explain_portfolio(
            portfolio_id=args.portfolio_id,
            top_n_features=args.top_n,
            use_cache=not args.no_cache,
            max_workers=args.workers
        )
        
        # Print summary
        print("\n📊 Batch SHAP Results:")
        print(f"  Portfolio ID: {result.portfolio_id}")
        print(f"  Tickers Analyzed: {len(result.contracts)}/{len(result.tickers)}")
        print(f"  Execution Time: {result.execution_time_seconds:.2f}s")
        print(f"  Cache Hit Rate: {result.cache_hit_rate:.1f}%")
        print(f"\n🏆 Top {len(result.top_features)} Features:")
        
        for rank, (feature, importance) in enumerate(result.top_features, 1):
            print(f"    {rank}. {feature}: {importance:.4f}")
        
        # Save results
        saved_files = orchestrator.save_batch_result(result, args.output_dir)
        
        print(f"\n💾 Results saved:")
        for fmt, path in saved_files.items():
            print(f"  {fmt.upper()}: {path}")
        
        print("\n✅ Batch SHAP complete!")
    
    except Exception as e:
        print(f"\n❌ Batch SHAP failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
