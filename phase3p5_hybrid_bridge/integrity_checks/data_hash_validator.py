"""
Data Hash Validator
===================

Integrity verification using SHA256 hashing.

Features:
- Validate analytics JSON/CSV before sync
- Compare manifest hashes with live recomputed hashes
- Quarantine corrupted data
"""

import hashlib
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict


# Configuration
QUARANTINE_DIR = Path(__file__).parent.parent.parent / "data" / "hybrid_cache" / "quarantine"


@dataclass
class ValidationResult:
    """Result of integrity validation."""
    filepath: str
    is_valid: bool
    expected_hash: Optional[str]
    actual_hash: Optional[str]
    error: Optional[str]
    validated_at: str
    
    def to_json(self) -> dict:
        """Convert to JSON dict."""
        return asdict(self)


class DataHashValidator:
    """
    Validator for data integrity using SHA256 hashing.
    
    Verifies that data files match their expected hashes and
    quarantines corrupted files for investigation.
    """
    
    def __init__(self, quarantine_dir: Optional[Path] = None):
        """
        Initialize validator.
        
        Args:
            quarantine_dir: Directory for quarantined files
        """
        self.quarantine_dir = quarantine_dir or QUARANTINE_DIR
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        
        # Statistics
        self.validations_performed = 0
        self.validations_passed = 0
        self.validations_failed = 0
        self.files_quarantined = 0
    
    def compute_hash(self, filepath: Path) -> str:
        """
        Compute SHA256 hash of file.
        
        Args:
            filepath: Path to file
        
        Returns:
            Hex digest of SHA256 hash
        
        Raises:
            IOError: If file cannot be read
        """
        sha256 = hashlib.sha256()
        
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        
        return sha256.hexdigest()
    
    def compute_json_hash(self, data: Dict[str, Any]) -> str:
        """
        Compute SHA256 hash of JSON data (canonical form).
        
        Args:
            data: JSON data dict
        
        Returns:
            Hex digest of SHA256 hash
        """
        # Create canonical JSON representation
        canonical = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    
    def validate_file(self, filepath: Path, expected_hash: str) -> ValidationResult:
        """
        Validate file integrity against expected hash.
        
        Args:
            filepath: Path to file
            expected_hash: Expected SHA256 hash
        
        Returns:
            ValidationResult with validation outcome
        """
        self.validations_performed += 1
        
        try:
            actual_hash = self.compute_hash(filepath)
            is_valid = actual_hash == expected_hash
            
            if is_valid:
                self.validations_passed += 1
            else:
                self.validations_failed += 1
            
            return ValidationResult(
                filepath=str(filepath),
                is_valid=is_valid,
                expected_hash=expected_hash,
                actual_hash=actual_hash,
                error=None if is_valid else f"Hash mismatch: expected {expected_hash}, got {actual_hash}",
                validated_at=datetime.utcnow().isoformat() + "Z"
            )
        
        except Exception as e:
            self.validations_failed += 1
            return ValidationResult(
                filepath=str(filepath),
                is_valid=False,
                expected_hash=expected_hash,
                actual_hash=None,
                error=f"Validation error: {str(e)}",
                validated_at=datetime.utcnow().isoformat() + "Z"
            )
    
    def validate_json(self, data: Dict[str, Any], expected_hash: str) -> ValidationResult:
        """
        Validate JSON data integrity against expected hash.
        
        Args:
            data: JSON data dict
            expected_hash: Expected SHA256 hash
        
        Returns:
            ValidationResult with validation outcome
        """
        self.validations_performed += 1
        
        try:
            actual_hash = self.compute_json_hash(data)
            is_valid = actual_hash == expected_hash
            
            if is_valid:
                self.validations_passed += 1
            else:
                self.validations_failed += 1
            
            return ValidationResult(
                filepath="<json_data>",
                is_valid=is_valid,
                expected_hash=expected_hash,
                actual_hash=actual_hash,
                error=None if is_valid else f"Hash mismatch: expected {expected_hash}, got {actual_hash}",
                validated_at=datetime.utcnow().isoformat() + "Z"
            )
        
        except Exception as e:
            self.validations_failed += 1
            return ValidationResult(
                filepath="<json_data>",
                is_valid=False,
                expected_hash=expected_hash,
                actual_hash=None,
                error=f"Validation error: {str(e)}",
                validated_at=datetime.utcnow().isoformat() + "Z"
            )
    
    def validate_manifest(self, manifest_path: Path) -> List[ValidationResult]:
        """
        Validate all files listed in manifest.
        
        Args:
            manifest_path: Path to manifest.json
        
        Returns:
            List of ValidationResult for each file
        """
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            return [ValidationResult(
                filepath=str(manifest_path),
                is_valid=False,
                expected_hash=None,
                actual_hash=None,
                error=f"Failed to read manifest: {e}",
                validated_at=datetime.utcnow().isoformat() + "Z"
            )]
        
        results = []
        bundle_dir = manifest_path.parent
        
        # Validate each file in manifest
        for filename, expected_hash in manifest.get("files", {}).items():
            filepath = bundle_dir / filename
            
            if not filepath.exists():
                results.append(ValidationResult(
                    filepath=str(filepath),
                    is_valid=False,
                    expected_hash=expected_hash,
                    actual_hash=None,
                    error="File not found",
                    validated_at=datetime.utcnow().isoformat() + "Z"
                ))
                self.validations_performed += 1
                self.validations_failed += 1
            else:
                results.append(self.validate_file(filepath, expected_hash))
        
        return results
    
    def quarantine_file(self, filepath: Path, reason: str, validation_result: Optional[ValidationResult] = None) -> Path:
        """
        Move file to quarantine directory.
        
        Args:
            filepath: Path to file
            reason: Reason for quarantine
            validation_result: Optional validation result
        
        Returns:
            Path to quarantined file
        """
        timestamp = int(datetime.utcnow().timestamp())
        quarantine_name = f"{filepath.stem}_{timestamp}{filepath.suffix}"
        quarantine_path = self.quarantine_dir / quarantine_name
        
        # Copy file to quarantine
        shutil.copy2(filepath, quarantine_path)
        
        # Create metadata file
        metadata = {
            "original_path": str(filepath),
            "quarantined_at": datetime.utcnow().isoformat() + "Z",
            "reason": reason
        }
        
        if validation_result:
            metadata["validation_result"] = validation_result.to_json()
        
        metadata_path = quarantine_path.with_suffix(quarantine_path.suffix + '.meta.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        self.files_quarantined += 1
        
        return quarantine_path
    
    def validate_and_quarantine(self, filepath: Path, expected_hash: str, auto_quarantine: bool = True) -> Tuple[ValidationResult, Optional[Path]]:
        """
        Validate file and optionally quarantine if invalid.
        
        Args:
            filepath: Path to file
            expected_hash: Expected hash
            auto_quarantine: Whether to auto-quarantine on failure
        
        Returns:
            Tuple of (ValidationResult, quarantine_path or None)
        """
        result = self.validate_file(filepath, expected_hash)
        
        quarantine_path = None
        if not result.is_valid and auto_quarantine:
            quarantine_path = self.quarantine_file(filepath, result.error or "Validation failed", result)
        
        return result, quarantine_path
    
    def list_quarantined_files(self) -> List[Dict[str, Any]]:
        """
        List all quarantined files with metadata.
        
        Returns:
            List of quarantine info dicts
        """
        quarantined = []
        
        for meta_file in self.quarantine_dir.glob("*.meta.json"):
            try:
                with open(meta_file, 'r') as f:
                    metadata = json.load(f)
                
                # Get corresponding data file
                data_file = meta_file.with_suffix('')  # Remove .meta.json
                
                quarantined.append({
                    "quarantine_path": str(data_file),
                    "metadata_path": str(meta_file),
                    "original_path": metadata.get("original_path"),
                    "quarantined_at": metadata.get("quarantined_at"),
                    "reason": metadata.get("reason"),
                    "exists": data_file.exists()
                })
            
            except Exception:
                continue
        
        return sorted(quarantined, key=lambda x: x["quarantined_at"], reverse=True)
    
    def restore_quarantined_file(self, quarantine_path: Path, restore_path: Optional[Path] = None) -> bool:
        """
        Restore quarantined file to original location or specified path.
        
        Args:
            quarantine_path: Path to quarantined file
            restore_path: Optional restore destination (defaults to original)
        
        Returns:
            True if successful
        """
        # Read metadata
        metadata_path = Path(str(quarantine_path) + '.meta.json')
        
        if not metadata_path.exists():
            return False
        
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Determine restore path
            if restore_path is None:
                restore_path = Path(metadata["original_path"])
            
            # Restore file
            restore_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(quarantine_path, restore_path)
            
            # Remove quarantine files
            quarantine_path.unlink()
            metadata_path.unlink()
            
            return True
        
        except Exception:
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get validator statistics.
        
        Returns:
            Dict with validation stats
        """
        success_rate = self.validations_passed / self.validations_performed if self.validations_performed > 0 else 0.0
        
        return {
            "validations_performed": self.validations_performed,
            "validations_passed": self.validations_passed,
            "validations_failed": self.validations_failed,
            "success_rate": success_rate,
            "files_quarantined": self.files_quarantined,
            "quarantine_count": len(list(self.quarantine_dir.glob("*.meta.json")))
        }


# Singleton instance
_global_validator: Optional[DataHashValidator] = None


def get_global_validator() -> DataHashValidator:
    """Get or create global validator instance."""
    global _global_validator
    if _global_validator is None:
        _global_validator = DataHashValidator()
    return _global_validator


# Convenience functions

def validate_file(filepath: Path, expected_hash: str) -> ValidationResult:
    """Convenience wrapper for global validator validate_file."""
    return get_global_validator().validate_file(filepath, expected_hash)


def validate_manifest(manifest_path: Path) -> List[ValidationResult]:
    """Convenience wrapper for global validator validate_manifest."""
    return get_global_validator().validate_manifest(manifest_path)


def compute_hash(filepath: Path) -> str:
    """Convenience wrapper for global validator compute_hash."""
    return get_global_validator().compute_hash(filepath)
