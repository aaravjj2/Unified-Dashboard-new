#!/usr/bin/env python3
"""
MISSION A3 ENV HOTFIX - Environment Validation CLI
Validates that all required API keys are present before application startup.
Used as Docker healthcheck and pre-flight validation.

Usage:
    python scripts/verify_env.py
    
Exit codes:
    0: All required keys present
    1: Missing keys or validation failed
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from financial_dashboard.utils.load_env import load_environment
except ImportError:
    # Fallback if module not importable
    print("❌ Cannot import load_env module")
    print("   Ensure financial_dashboard package is installed")
    sys.exit(1)


def main():
    """Main validation routine."""
    print("=" * 70)
    print(" MISSION A3 ENV HOTFIX - Environment Validation")
    print("=" * 70)
    
    try:
        # Load and validate environment
        result = load_environment(raise_on_missing=False)
        
        # Print sources
        print(f"\n📂 Loaded from: {', '.join(result['sources']) if result['sources'] else 'OS environment only'}")
        
        # Check each required key
        print(f"\n🔑 Required Keys ({len(result['present_keys']) + len(result['missing_keys'])} total):")
        print("-" * 70)
        
        for key in sorted(result['present_keys']):
            value = os.getenv(key, '')
            masked = value[:8] + '...' + value[-4:] if len(value) > 12 else '***'
            print(f"  ✅ {key:25} = {masked}")
        
        for key in sorted(result['missing_keys']):
            print(f"  ❌ {key:25} = NOT SET")
        
        # Print provider status
        print(f"\n🌐 API Provider Status:")
        print("-" * 70)
        for provider, available in sorted(result['providers'].items()):
            status = "✅ READY" if available else "❌ NOT CONFIGURED"
            print(f"  {provider:20} {status}")
        
        # Final verdict
        print("\n" + "=" * 70)
        if result['valid']:
            print("✅ VALIDATION PASSED - All required keys present")
            print("=" * 70)
            return 0
        else:
            print("❌ VALIDATION FAILED - Missing keys:")
            for key in result['missing_keys']:
                print(f"   - {key}")
            print("=" * 70)
            print("\n💡 Fix:")
            print("   1. Add keys to keys.env or doppler.env")
            print("   2. Or set environment variables directly")
            print("   3. Run 'doppler setup' if using Doppler")
            return 1
            
    except Exception as e:
        print(f"\n❌ VALIDATION ERROR: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
