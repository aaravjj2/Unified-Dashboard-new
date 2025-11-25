"""
Hybrid Storage Manager
======================

Unified interface for saving/loading analytics bundles from:
- offline_portfolio_engine
- explainability_engine
- insight_comparator

Creates canonical bundle structure with manifest and integrity hashing.
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict


# Configuration
BUNDLE_BASE_DIR = Path(__file__).parent.parent.parent / "data" / "analytics_bundle"


@dataclass
class BundleManifest:
    """
    Manifest for analytics bundle.
    
    Tracks all files in bundle with integrity hashes.
    """
    bundle_id: str
    created_at: str
    portfolio_id: str
    analytics_version: str
    files: Dict[str, str]  # filename -> SHA256 hash
    metadata: Dict[str, Any]
    
    def to_json(self) -> dict:
        """Convert to JSON dict."""
        return asdict(self)
    
    @classmethod
    def from_json(cls, data: dict) -> 'BundleManifest':
        """Create from JSON dict."""
        return cls(**data)
    
    def compute_bundle_hash(self) -> str:
        """
        Compute aggregate hash of entire bundle.
        
        Returns:
            SHA256 hex digest of all file hashes combined
        """
        # Sort file hashes for deterministic ordering
        sorted_hashes = sorted(self.files.values())
        combined = ''.join(sorted_hashes)
        return hashlib.sha256(combined.encode()).hexdigest()


class HybridStorageManager:
    """
    Manager for analytics bundle persistence.
    
    Bundles together outputs from multiple analytics engines into
    a single dated directory with manifest and integrity checking.
    """
    
    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize storage manager.
        
        Args:
            base_dir: Base directory for bundles (defaults to BUNDLE_BASE_DIR)
        """
        self.base_dir = base_dir or BUNDLE_BASE_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def create_bundle(self, portfolio_id: str, bundle_date: Optional[str] = None) -> Path:
        """
        Create new analytics bundle directory.
        
        Args:
            portfolio_id: Portfolio identifier
            bundle_date: Date string YYYYMMDD (defaults to today)
        
        Returns:
            Path to created bundle directory
        """
        if bundle_date is None:
            bundle_date = datetime.utcnow().strftime("%Y%m%d")
        
        bundle_dir = self.base_dir / bundle_date / portfolio_id
        bundle_dir.mkdir(parents=True, exist_ok=True)
        
        return bundle_dir
    
    def save_analytics_bundle(
        self,
        portfolio_id: str,
        portfolio_analytics: Dict[str, Any],
        explainability_data: Optional[Dict[str, Any]] = None,
        forecast_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Save complete analytics bundle with manifest.
        
        Args:
            portfolio_id: Portfolio identifier
            portfolio_analytics: Portfolio analytics data
            explainability_data: Optional explainability data
            forecast_data: Optional forecast data
            metadata: Optional additional metadata
        
        Returns:
            Path to bundle directory
        """
        # Create bundle directory
        bundle_dir = self.create_bundle(portfolio_id)
        
        files_saved = {}
        
        # Save portfolio analytics
        portfolio_file = bundle_dir / "portfolio_analytics.json"
        self._write_json(portfolio_file, portfolio_analytics)
        files_saved["portfolio_analytics.json"] = self._compute_file_hash(portfolio_file)
        
        # Save explainability data if provided
        if explainability_data:
            explainability_file = bundle_dir / "explainability.json"
            self._write_json(explainability_file, explainability_data)
            files_saved["explainability.json"] = self._compute_file_hash(explainability_file)
        
        # Save forecast data if provided
        if forecast_data:
            forecast_file = bundle_dir / "forecast.json"
            self._write_json(forecast_file, forecast_data)
            files_saved["forecast.json"] = self._compute_file_hash(forecast_file)
        
        # Create manifest
        manifest = BundleManifest(
            bundle_id=f"{portfolio_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            created_at=datetime.utcnow().isoformat() + "Z",
            portfolio_id=portfolio_id,
            analytics_version="3.5.0",
            files=files_saved,
            metadata=metadata or {}
        )
        
        # Save manifest
        manifest_file = bundle_dir / "manifest.json"
        self._write_json(manifest_file, manifest.to_json())
        
        return bundle_dir
    
    def load_analytics_bundle(self, portfolio_id: str, bundle_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Load analytics bundle with integrity verification.
        
        Args:
            portfolio_id: Portfolio identifier
            bundle_date: Date string YYYYMMDD (defaults to latest)
        
        Returns:
            Dict with portfolio_analytics, explainability, forecast, manifest
        
        Raises:
            FileNotFoundError: If bundle not found
            ValueError: If integrity check fails
        """
        # Find bundle directory
        if bundle_date is None:
            bundle_dir = self._find_latest_bundle(portfolio_id)
        else:
            bundle_dir = self.base_dir / bundle_date / portfolio_id
        
        if not bundle_dir.exists():
            raise FileNotFoundError(f"Bundle not found: {bundle_dir}")
        
        # Load manifest
        manifest_file = bundle_dir / "manifest.json"
        if not manifest_file.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_file}")
        
        manifest_data = self._read_json(manifest_file)
        manifest = BundleManifest.from_json(manifest_data)
        
        # Verify file integrity
        self._verify_bundle_integrity(bundle_dir, manifest)
        
        # Load files
        result = {
            "manifest": manifest.to_json()
        }
        
        # Load portfolio analytics
        if "portfolio_analytics.json" in manifest.files:
            portfolio_file = bundle_dir / "portfolio_analytics.json"
            result["portfolio_analytics"] = self._read_json(portfolio_file)
        
        # Load explainability if present
        if "explainability.json" in manifest.files:
            explainability_file = bundle_dir / "explainability.json"
            result["explainability"] = self._read_json(explainability_file)
        
        # Load forecast if present
        if "forecast.json" in manifest.files:
            forecast_file = bundle_dir / "forecast.json"
            result["forecast"] = self._read_json(forecast_file)
        
        return result
    
    def list_bundles(self, portfolio_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all available bundles.
        
        Args:
            portfolio_id: Optional filter by portfolio ID
        
        Returns:
            List of bundle info dicts
        """
        bundles = []
        
        for date_dir in sorted(self.base_dir.iterdir()):
            if not date_dir.is_dir():
                continue
            
            for portfolio_dir in date_dir.iterdir():
                if not portfolio_dir.is_dir():
                    continue
                
                if portfolio_id and portfolio_dir.name != portfolio_id:
                    continue
                
                manifest_file = portfolio_dir / "manifest.json"
                if not manifest_file.exists():
                    continue
                
                try:
                    manifest_data = self._read_json(manifest_file)
                    bundles.append({
                        "bundle_id": manifest_data["bundle_id"],
                        "portfolio_id": manifest_data["portfolio_id"],
                        "created_at": manifest_data["created_at"],
                        "path": str(portfolio_dir),
                        "files": list(manifest_data["files"].keys())
                    })
                except Exception:
                    continue
        
        return bundles
    
    def delete_bundle(self, portfolio_id: str, bundle_date: str) -> bool:
        """
        Delete analytics bundle.
        
        Args:
            portfolio_id: Portfolio identifier
            bundle_date: Date string YYYYMMDD
        
        Returns:
            True if deleted, False if not found
        """
        bundle_dir = self.base_dir / bundle_date / portfolio_id
        
        if not bundle_dir.exists():
            return False
        
        # Delete all files in bundle
        for file in bundle_dir.iterdir():
            file.unlink()
        
        # Delete directory
        bundle_dir.rmdir()
        
        # Delete date directory if empty
        date_dir = bundle_dir.parent
        if date_dir.exists() and not any(date_dir.iterdir()):
            date_dir.rmdir()
        
        return True
    
    def _find_latest_bundle(self, portfolio_id: str) -> Path:
        """
        Find most recent bundle for portfolio.
        
        Args:
            portfolio_id: Portfolio identifier
        
        Returns:
            Path to latest bundle
        
        Raises:
            FileNotFoundError: If no bundles found
        """
        bundles = self.list_bundles(portfolio_id=portfolio_id)
        
        if not bundles:
            raise FileNotFoundError(f"No bundles found for portfolio: {portfolio_id}")
        
        # Sort by created_at timestamp
        latest = max(bundles, key=lambda b: b["created_at"])
        return Path(latest["path"])
    
    def _verify_bundle_integrity(self, bundle_dir: Path, manifest: BundleManifest) -> None:
        """
        Verify integrity of all files in bundle.
        
        Args:
            bundle_dir: Bundle directory
            manifest: Bundle manifest
        
        Raises:
            ValueError: If integrity check fails
        """
        for filename, expected_hash in manifest.files.items():
            filepath = bundle_dir / filename
            
            if not filepath.exists():
                raise ValueError(f"Missing file in bundle: {filename}")
            
            actual_hash = self._compute_file_hash(filepath)
            
            if actual_hash != expected_hash:
                raise ValueError(
                    f"Integrity check failed for {filename}: "
                    f"expected {expected_hash}, got {actual_hash}"
                )
    
    def _write_json(self, filepath: Path, data: Dict[str, Any]) -> None:
        """Write JSON to file."""
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _read_json(self, filepath: Path) -> Dict[str, Any]:
        """Read JSON from file."""
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def _compute_file_hash(self, filepath: Path) -> str:
        """
        Compute SHA256 hash of file.
        
        Args:
            filepath: Path to file
        
        Returns:
            Hex digest of SHA256 hash
        """
        sha256 = hashlib.sha256()
        
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        
        return sha256.hexdigest()


# Singleton instance
_global_manager: Optional[HybridStorageManager] = None


def get_global_manager() -> HybridStorageManager:
    """Get or create global storage manager instance."""
    global _global_manager
    if _global_manager is None:
        _global_manager = HybridStorageManager()
    return _global_manager


# Convenience functions

def save_analytics_bundle(**kwargs) -> Path:
    """Convenience wrapper for global manager save_analytics_bundle."""
    return get_global_manager().save_analytics_bundle(**kwargs)


def load_analytics_bundle(portfolio_id: str, bundle_date: Optional[str] = None) -> Dict[str, Any]:
    """Convenience wrapper for global manager load_analytics_bundle."""
    return get_global_manager().load_analytics_bundle(portfolio_id, bundle_date)


def list_bundles(portfolio_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Convenience wrapper for global manager list_bundles."""
    return get_global_manager().list_bundles(portfolio_id)
