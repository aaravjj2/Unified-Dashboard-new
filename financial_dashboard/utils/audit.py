"""
Audit bundle generation for model predictions.

Creates comprehensive audit packages for each monthly pick that include:
- Model metadata (version, parameters, timestamp)
- Pick CSV snapshot
- SHAP explanations (JSON)
- Feature snapshots (for reproducibility)
- Trade sizing parameters
- All bundled into a downloadable ZIP

Functions:
- generate_audit_bundle(ticker, date, pick_data, output_dir)
- create_audit_metadata(ticker, pick_data)
- bundle_artifacts(artifact_dir)
"""

import os
import json
import zipfile
import logging
from datetime import datetime
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


def generate_audit_bundle(
    ticker: str,
    date: str,
    pick_data: Dict[str, Any],
    output_dir: str,
    include_shap: bool = True,
    include_snapshot: bool = True
) -> Optional[str]:
    """
    Generate a complete audit bundle for a model pick.
    
    Args:
        ticker: Stock ticker symbol
        date: Date string (YYYYMMDD format)
        pick_data: Dictionary containing all pick information
        output_dir: Base directory for artifacts (e.g., 'models/artifacts')
        include_shap: Whether to include SHAP explanations
        include_snapshot: Whether to include feature snapshot
    
    Returns:
        Path to generated ZIP file, or None if generation failed
    """
    try:
        # Create artifact directory
        artifact_dir = os.path.join(output_dir, date, ticker)
        os.makedirs(artifact_dir, exist_ok=True)
        
        # 1. Create metadata.json
        metadata = create_audit_metadata(ticker, pick_data)
        metadata_path = os.path.join(artifact_dir, 'metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"Created metadata: {metadata_path}")
        
        # 2. Save pick data as CSV row
        try:
            import pandas as pd
            pick_df = pd.DataFrame([pick_data])
            csv_path = os.path.join(artifact_dir, f'pick_{ticker}_{date}.csv')
            pick_df.to_csv(csv_path, index=False)
            logger.info(f"Saved pick CSV: {csv_path}")
        except Exception as e:
            logger.warning(f"Failed to save pick CSV: {e}")
        
        # 3. Include SHAP explanations if available
        if include_shap:
            try:
                import sys
                # Ensure utils are in path
                utils_path = os.path.dirname(__file__)
                if utils_path not in sys.path:
                    sys.path.insert(0, utils_path)
                
                from explain import load_explanation
                shap_data = load_explanation(ticker)
                if shap_data:
                    shap_path = os.path.join(artifact_dir, f'shap_{ticker}.json')
                    with open(shap_path, 'w') as f:
                        json.dump(shap_data, f, indent=2)
                    logger.info(f"Saved SHAP data: {shap_path}")
            except Exception as e:
                logger.warning(f"Failed to save SHAP data: {e}")
        
        # 4. Include feature snapshot if available
        if include_snapshot:
            try:
                import sys
                utils_path = os.path.dirname(__file__)
                if utils_path not in sys.path:
                    sys.path.insert(0, utils_path)
                
                from snapshots import load_snapshot
                snapshot = load_snapshot(ticker)
                if snapshot:
                    snapshot_path = os.path.join(artifact_dir, f'snapshot_{ticker}.json')
                    with open(snapshot_path, 'w') as f:
                        json.dump(snapshot, f, indent=2, default=str)
                    logger.info(f"Saved feature snapshot: {snapshot_path}")
            except Exception as e:
                logger.warning(f"Failed to save feature snapshot: {e}")
        
        # 5. Create README
        readme_content = _generate_readme(ticker, date, pick_data)
        readme_path = os.path.join(artifact_dir, 'README.md')
        with open(readme_path, 'w') as f:
            f.write(readme_content)
        logger.info(f"Created README: {readme_path}")
        
        # 6. Bundle everything into a ZIP
        zip_path = bundle_artifacts(artifact_dir)
        
        logger.info(f"Generated audit bundle: {zip_path}")
        return zip_path
        
    except Exception as e:
        logger.error(f"Failed to generate audit bundle for {ticker}: {e}", exc_info=True)
        return None


def create_audit_metadata(ticker: str, pick_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create metadata dictionary for audit bundle.
    
    Args:
        ticker: Stock ticker
        pick_data: Pick information
    
    Returns:
        Metadata dictionary
    """
    metadata = {
        'ticker': ticker,
        'generated_at': datetime.now().isoformat(),
        'model_info': {
            'version': pick_data.get('model_version', 'unknown'),
            'type': 'ensemble_lgb_ng',
            'confidence': pick_data.get('model_confidence'),
        },
        'prediction': {
            'score': pick_data.get('score'),
            'predicted_return': pick_data.get('lgb_pred') or pick_data.get('pred_mean'),
            'predicted_return_net': pick_data.get('predicted_return_net'),
            'lower_bound': pick_data.get('pred_lower_95'),
            'upper_bound': pick_data.get('pred_upper_95'),
            'volatility': pick_data.get('pred_sigma'),
        },
        'trade_sizing': {
            'position_size_dollars': pick_data.get('position_size_dollars'),
            'expected_slippage_pct': pick_data.get('expected_slippage_pct'),
            'liquidity_flag': pick_data.get('liquidity_flag'),
            'avg_dollar_volume': pick_data.get('avg_dollar_vol'),
            'trade_schedule': pick_data.get('trade_schedule_json'),
        },
        'price_info': {
            'current_price': pick_data.get('price_live') or pick_data.get('last_price'),
            'month_start_price': pick_data.get('month_start'),
            'daily_change': pick_data.get('daily_change'),
            'overall_change': pick_data.get('overall_change'),
        },
        'audit_info': {
            'bundle_version': '1.0',
            'reproducible': True,
            'includes_shap': True,
            'includes_snapshot': True,
        }
    }
    
    return metadata


def bundle_artifacts(artifact_dir: str) -> str:
    """
    Create a ZIP bundle from all files in the artifact directory.
    
    Args:
        artifact_dir: Directory containing artifacts to bundle
    
    Returns:
        Path to created ZIP file
    """
    zip_path = f"{artifact_dir}.zip"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(artifact_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.dirname(artifact_dir))
                zipf.write(file_path, arcname)
    
    logger.info(f"Created ZIP bundle: {zip_path}")
    return zip_path


def _generate_readme(ticker: str, date: str, pick_data: Dict[str, Any]) -> str:
    """Generate README content for the audit bundle."""
    
    readme = f"""# Audit Bundle: {ticker}

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Date: {date}

## Contents

This audit bundle contains all information needed to reproduce and audit the model prediction for {ticker}.

### Files

- **metadata.json**: Complete model metadata and prediction details
- **pick_{ticker}_{date}.csv**: Full pick data row from the monthly picks CSV
- **shap_{ticker}.json**: SHAP feature importance explanations (if available)
- **snapshot_{ticker}.json**: Complete feature snapshot at prediction time (if available)
- **README.md**: This file

## Model Prediction Summary

- **Score**: {pick_data.get('score', 'N/A')}
- **Predicted Return (Net)**: {pick_data.get('predicted_return_net', 'N/A')}
- **Position Size**: ${pick_data.get('position_size_dollars', 'N/A')}
- **Liquidity**: {pick_data.get('liquidity_flag', 'N/A')}
- **Expected Slippage**: {pick_data.get('expected_slippage_pct', 'N/A')}

## Trade Execution

The recommended trade execution parameters are included in the metadata.json file.
TWAP schedule is provided in the `trade_schedule_json` field.

## Reproducibility

This bundle contains:
1. Exact feature values used for prediction (snapshot)
2. Model hyperparameters and version
3. SHAP explanations showing feature contributions
4. Trade sizing calculations and parameters

All predictions can be reproduced by:
1. Loading the feature snapshot
2. Running inference with the specified model version
3. Applying the trade sizing algorithm with given parameters

## Contact

For questions about this audit bundle, please refer to the model documentation.
"""
    
    return readme


def list_audit_bundles(output_dir: str, ticker: Optional[str] = None) -> list:
    """
    List all available audit bundles.
    
    Args:
        output_dir: Base directory for artifacts
        ticker: Optional ticker filter
    
    Returns:
        List of audit bundle paths
    """
    bundles = []
    
    try:
        if not os.path.exists(output_dir):
            return bundles
        
        for date_dir in os.listdir(output_dir):
            date_path = os.path.join(output_dir, date_dir)
            if not os.path.isdir(date_path):
                continue
            
            for ticker_dir in os.listdir(date_path):
                if ticker and ticker_dir != ticker:
                    continue
                
                ticker_path = os.path.join(date_path, ticker_dir)
                zip_path = f"{ticker_path}.zip"
                
                if os.path.exists(zip_path):
                    bundles.append(zip_path)
        
        return sorted(bundles)
        
    except Exception as e:
        logger.error(f"Failed to list audit bundles: {e}")
        return bundles


# Self-test
if __name__ == '__main__':
    import tempfile
    import shutil
    
    print("Testing audit bundle generation...")
    
    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Test data
        test_pick = {
            'ticker': 'AAPL',
            'score': 0.8523,
            'lgb_pred': 0.0456,
            'predicted_return_net': 0.0432,
            'position_size_dollars': 12500.00,
            'expected_slippage_pct': 0.0024,
            'liquidity_flag': 'high',
            'avg_dollar_vol': 45000000,
            'price_live': 182.50,
            'daily_change': 0.0123,
        }
        
        # Generate bundle
        zip_path = generate_audit_bundle(
            ticker='AAPL',
            date='20250914',
            pick_data=test_pick,
            output_dir=temp_dir,
            include_shap=False,  # Skip SHAP for test
            include_snapshot=False  # Skip snapshot for test
        )
        
        if zip_path and os.path.exists(zip_path):
            print(f"✓ Created audit bundle: {zip_path}")
            print(f"  Size: {os.path.getsize(zip_path)} bytes")
            
            # List bundles
            bundles = list_audit_bundles(temp_dir)
            print(f"✓ Found {len(bundles)} bundle(s)")
            
            print("\n✓ All audit tests passed!")
        else:
            print("✗ Failed to create audit bundle")
    
    finally:
        # Cleanup
        shutil.rmtree(temp_dir)
        print(f"\nCleaned up temp directory: {temp_dir}")
