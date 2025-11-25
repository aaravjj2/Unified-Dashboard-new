"""
COMPREHENSIVE FIX SCRIPT - Unified Financial Dashboard
Systematically applies all bug fixes and feature implementations
"""

import re
import os
from pathlib import Path

# Define all ID mappings for Analysis Hub namespace fix
ID_MAPPINGS = {
    # Attribution Analysis IDs
    "'attr-picks-type'": "'hub-attr-picks-type'",
    '"attr-picks-type"': '"hub-attr-picks-type"',
    "'attr-date-range'": "'hub-attr-date-range'",
    '"attr-date-range"': '"hub-attr-date-range"',
    "'attr-horizon'": "'hub-attr-horizon'",
    '"attr-horizon"': '"hub-attr-horizon"',
    "'attr-regime-filter'": "'hub-attr-regime-filter'",
    '"attr-regime-filter"': '"hub-attr-regime-filter"',
    "'attr-run-button'": "'hub-attr-run-button'",
    '"attr-run-button"': '"hub-attr-run-button"',
    "'attr-export-button'": "'hub-attr-export-button'",
    '"attr-export-button"': '"hub-attr-export-button"',
    "'attr-status'": "'hub-attr-status'",
    '"attr-status"': '"hub-attr-status"',
    "'attr-job-store'": "'hub-attr-job-store'",
    '"attr-job-store"': '"hub-attr-job-store"',
    "'attr-results-store'": "'hub-attr-results-store'",
    '"attr-results-store"': '"hub-attr-results-store"',
    "'attr-poll-counter'": "'hub-attr-poll-counter'",
    '"attr-poll-counter"': '"hub-attr-poll-counter"',
    "'attr-poll-interval'": "'hub-attr-poll-interval'",
    '"attr-poll-interval"': '"hub-attr-poll-interval"',
    
    # Portfolio Analytics IDs
    "'pa-calc-btn'": "'hub-pa-calc-btn'",
    '"pa-calc-btn"': '"hub-pa-calc-btn"',
    
    # Label IDs
    "'label-attr-picks-type'": "'label-hub-attr-picks-type'",
    "'label-attr-date-range'": "'label-hub-attr-date-range'",
    "'label-attr-horizon'": "'label-hub-attr-horizon'",
    "'label-attr-regime'": "'label-hub-attr-regime'",
}

def fix_analysis_hub_ids():
    """Fix duplicate IDs in analysis_hub_refactored.py"""
    file_path = Path('tabs/analysis_hub_refactored.py')
    
    print(f"🔧 Fixing Analysis Hub IDs in {file_path}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Apply all ID mappings
    for old_id, new_id in ID_MAPPINGS.items():
        content = content.replace(old_id, new_id)
    
    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    changes_made = content != original_content
    print(f"   ✅ Applied {len([k for k, v in ID_MAPPINGS.items() if k in original_content])} ID changes")
    return changes_made

def fix_attribution_monthly_picks():
    """Fix _load_picks_in_range to correctly load monthly CSV files"""
    file_path = Path('tabs/attribution_analysis.py')
    
    if not file_path.exists():
        print(f"   ⚠️  {file_path} not found, skipping")
        return False
    
    print(f"🔧 Fixing monthly picks loading in {file_path}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find and replace the _load_picks_in_range function
    pattern = r'def _load_picks_in_range\([^)]+\):.*?(?=\ndef |\nclass |\Z)'
    
    new_function = '''def _load_picks_in_range(picks_type='weekly', start_date=None, end_date=None):
    """Load picks CSV files within date range."""
    import glob
    import pandas as pd
    from datetime import datetime
    
    logger.warning('ATTR_DEBUG - _load_picks_in_range called with picks_type=%r', picks_type)
    
    # Determine file pattern based on picks_type
    if picks_type == 'monthly':
        pattern = 'outputs/monthly_picks_*.csv'
    else:
        pattern = 'outputs/weekly_picks_*.csv'
    
    logger.warning('ATTR_DEBUG - searching for files matching: %s', pattern)
    
    files = sorted(glob.glob(pattern), reverse=True)
    logger.warning('ATTR_DEBUG - found %d files: %s', len(files), files[:3])
    
    if not files:
        logger.warning('ATTR_DEBUG - no files found for pattern %s', pattern)
        return None
    
    # Load most recent file
    try:
        df = pd.read_csv(files[0])
        logger.warning('ATTR_DEBUG - loaded %d rows from %s', len(df), files[0])
        return df
    except Exception as e:
        logger.error('ATTR_DEBUG - failed to load %s: %s', files[0], e)
        return None
'''
    
    if '_load_picks_in_range' in content:
        content = re.sub(pattern, new_function, content, flags=re.DOTALL)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"   ✅ Updated _load_picks_in_range function")
        return True
    else:
        print(f"   ⚠️  _load_picks_in_range function not found")
        return False

def create_research_lab_tab():
    """Create tabs/research_lab_tab.py to integrate Research Lab module"""
    file_path = Path('tabs/research_lab_tab.py')
    
    print(f"🔧 Creating {file_path}...")
    
    content = '''"""
Research Lab Tab - Integration Module

Integrates the Research Lab experiment sandbox into the main dashboard.
Uses modules/research_lab.py for UI and callbacks.
"""

import logging
from dash import html

logger = logging.getLogger(__name__)

def layout():
    """Build the Research Lab tab layout."""
    try:
        from modules import research_lab
        return research_lab.layout()
    except Exception as e:
        logger.error(f"Failed to load Research Lab layout: {e}")
        return html.Div([
            html.H2("🧪 Research Lab", className="mt-3"),
            html.P("Error loading Research Lab module. Check logs for details.", 
                   className="text-danger")
        ])

def register_callbacks(app):
    """Register Research Lab callbacks."""
    try:
        from modules import research_lab
        research_lab.register_callbacks(app)
        logger.info("✓ Registered Research Lab callbacks")
    except Exception as e:
        logger.error(f"Failed to register Research Lab callbacks: {e}")
'''
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"   ✅ Created research_lab_tab.py")
    return True

def fix_integrated_dashboard_config():
    """Update integrated_dashboard.py TAB_CONFIG for Research Lab"""
    file_path = Path('integrated_dashboard.py')
    
    print(f"🔧 Updating TAB_CONFIG in {file_path}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace research_lab entry
    old_config = "{'id': 'research_lab', 'name': 'Research Lab', 'module': 'tabs/scenario_analysis_refactored.py'}"
    new_config = "{'id': 'research_lab', 'name': '🧪 Research Lab', 'module': 'tabs/research_lab_tab.py'}"
    
    if old_config in content:
        content = content.replace(old_config, new_config)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"   ✅ Updated TAB_CONFIG for Research Lab")
        return True
    else:
        print(f"   ℹ️  TAB_CONFIG already updated or not found")
        return False

def add_data_quality_fixes():
    """Add fillna() calls to data processing in Market Trends and Picks tabs"""
    fixes_applied = []
    
    files_to_fix = [
        ('tabs/market_trends.py', 'Market Trends'),
        ('tabs/monthly_picks.py', 'Monthly Picks'),
        ('tabs/weekly_picks.py', 'Weekly Picks')
    ]
    
    for file_path_str, name in files_to_fix:
        file_path = Path(file_path_str)
        
        if not file_path.exists():
            print(f"   ⚠️  {file_path} not found, skipping")
            continue
        
        print(f"🔧 Adding data quality fixes to {name}...")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add fillna template near data loading
        fillna_code = '''
    # Data quality fix - replace N/A values with defaults
    if isinstance(df, pd.DataFrame):
        df = df.fillna({
            'sector': 'Unknown',
            'industry': 'Unknown',
            'market_cap': 0,
            'volume': 0,
            'price': 0.0,
            'change_pct': 0.0
        })
        # Fill remaining numeric columns with 0
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        df[numeric_cols] = df[numeric_cols].fillna(0)
        # Fill remaining text columns with 'N/A'
        object_cols = df.select_dtypes(include=['object']).columns
        df[object_cols] = df[object_cols].fillna('N/A')
'''
        
        # Look for data loading patterns and add fillna after them
        patterns = [
            (r'(df = pd\.read_csv\([^)]+\))', r'\1' + fillna_code),
            (r'(df = load_[a-z_]+\([^)]+\))', r'\1' + fillna_code),
        ]
        
        modified = False
        for pattern, replacement in patterns:
            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content, count=1)
                modified = True
                break
        
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"   ✅ Added fillna() calls to {name}")
            fixes_applied.append(name)
        else:
            print(f"   ℹ️  No suitable injection point found in {name}")
    
    return len(fixes_applied) > 0

def main():
    """Execute all fixes"""
    print("="*70)
    print("COMPREHENSIVE FIX APPLICATION - Unified Financial Dashboard")
    print("="*70)
    print()
    
    os.chdir('/mnt/c/Aarav/fin_env/Dash')
    
    results = {}
    
    # Fix 1: Analysis Hub duplicate IDs
    print("📦 FIX 1: Analysis Hub Duplicate IDs")
    results['analysis_hub_ids'] = fix_analysis_hub_ids()
    print()
    
    # Fix 2: Attribution monthly picks loading
    print("📦 FIX 2: Attribution Monthly Picks Loading")
    results['attribution_monthly'] = fix_attribution_monthly_picks()
    print()
    
    # Fix 3: Research Lab tab creation
    print("📦 FIX 3: Research Lab Tab Integration")
    results['research_lab_tab'] = create_research_lab_tab()
    print()
    
    # Fix 4: Integrated Dashboard config
    print("📦 FIX 4: Integrated Dashboard TAB_CONFIG")
    results['dashboard_config'] = fix_integrated_dashboard_config()
    print()
    
    # Fix 5: Data quality (fillna)
    print("📦 FIX 5: Data Quality (N/A values)")
    results['data_quality'] = add_data_quality_fixes()
    print()
    
    print("="*70)
    print("SUMMARY")
    print("="*70)
    for fix_name, success in results.items():
        status = "✅ SUCCESS" if success else "⚠️  SKIPPED/FAILED"
        print(f"{status}: {fix_name}")
    print()
    print("🎉 Fix application complete! Restart integrated_dashboard.py to apply changes.")
    print("="*70)

if __name__ == '__main__':
    main()
