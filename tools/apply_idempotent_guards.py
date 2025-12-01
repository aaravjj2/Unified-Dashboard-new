#!/usr/bin/env python3
"""
Apply idempotent callback registration guards to all tab modules.

This script adds global _callbacks_registered guards to prevent
duplicate callback registrations across hot-reloads.
"""
import re
from pathlib import Path


TABS_TO_FIX = [
    ('strategy_lab', 'financial_dashboard/tabs/strategy_lab/callbacks.py', 17),
    ('portfolio', 'financial_dashboard/tabs/portfolio_positions.py', 15),
    ('volatility_lab', 'financial_dashboard/tabs/volatility_lab_modular/callbacks.py', 14),
    ('attribution_lab', 'financial_dashboard/tabs/attribution_analysis.py', 26),
    ('market_forecast', 'financial_dashboard/tabs/market_forecast_rebuild.py', 7),
    ('options_lab', 'financial_dashboard/tabs/options_lab/__init__.py', 19),
]


def add_idempotent_guard(file_path, module_name, expected_callbacks):
    """Add idempotent registration guard to a callback module."""
    
    file_path = Path(file_path)
    if not file_path.exists():
        print(f"⚠️  {file_path} not found, skipping")
        return False
    
    content = file_path.read_text()
    
    # Check if already has guard
    if '_callbacks_registered' in content:
        print(f"✓ {module_name}: Already has guard")
        return False
    
    # Find register_callbacks function
    register_pattern = r'(def register_callbacks\(app[^)]*\):)\s*\n(\s*"""[^"]*""")?'
    match = re.search(register_pattern, content)
    
    if not match:
        print(f"❌ {module_name}: Could not find register_callbacks function")
        return False
    
    # Build guard code
    guard_code = f'''

# Idempotent registration guard
_callbacks_registered = False


def register_callbacks(app):
    """
    Register all {module_name} callbacks (idempotent).
    
    Uses module-level guard to prevent duplicate registrations.
    """
    global _callbacks_registered
    
    if _callbacks_registered:
        logger.info(f"🔒 {module_name} callbacks already registered, skipping")
        return
    
    logger.info(f"📝 Registering {module_name} callbacks...")
'''
    
    # Replace function definition
    content = re.sub(
        register_pattern,
        guard_code.lstrip(),
        content,
        count=1
    )
    
    # Add completion marker at end of function
    # Find the last line of register_callbacks (usually a logger.info or return)
    completion_pattern = r'(logger\.info\(["\'].*Registered.*callbacks.*["\']\))'
    completion_match = re.search(completion_pattern, content)
    
    if completion_match:
        content = re.sub(
            completion_pattern,
            f'''_callbacks_registered = True
    logger.info(f"✅ {module_name} callbacks registered successfully ({expected_callbacks} callbacks)")''',
            content,
            count=1
        )
    else:
        # Add at end of function if no logger.info found
        # This is trickier - would need AST parsing
        print(f"⚠️  {module_name}: Could not find completion marker, manual fix needed")
        return False
    
    # Write back
    file_path.write_text(content)
    print(f"✅ {module_name}: Added idempotent guard")
    return True


def main():
    """Apply guards to all tabs."""
    print("=" * 80)
    print("APPLYING IDEMPOTENT CALLBACK GUARDS")
    print("=" * 80)
    
    fixed = []
    skipped = []
    failed = []
    
    for module_name, file_path, cb_count in TABS_TO_FIX:
        result = add_idempotent_guard(file_path, module_name, cb_count)
        if result:
            fixed.append(module_name)
        elif Path(file_path).exists() and '_callbacks_registered' in Path(file_path).read_text():
            skipped.append(module_name)
        else:
            failed.append(module_name)
    
    print("\n" + "=" * 80)
    print(f"SUMMARY")
    print("=" * 80)
    print(f"Fixed: {len(fixed)}")
    print(f"Skipped (already has guard): {len(skipped)}")
    print(f"Failed: {len(failed)}")
    
    if fixed:
        print(f"\nFixed modules: {', '.join(fixed)}")
    if failed:
        print(f"\nFailed modules: {', '.join(failed)}")


if __name__ == '__main__':
    main()
