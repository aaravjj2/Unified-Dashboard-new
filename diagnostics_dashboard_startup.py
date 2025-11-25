#!/usr/bin/env python3
"""
Dashboard Startup Diagnostics Script

Purpose: Trace every module load, tab initialization, and callback registration
to identify the exact point of failure causing 500 errors or missing tabs.

Usage:
    python diagnostics_dashboard_startup.py 2>&1 | tee diagnostics_dashboard.log
"""

import sys
import os
import traceback
from pathlib import Path
from datetime import datetime

# Diagnostic logging
class DiagnosticLogger:
    def __init__(self):
        self.events = []
        self.errors = []
        self.start_time = datetime.now()
    
    def log(self, level, category, message):
        timestamp = (datetime.now() - self.start_time).total_seconds()
        event = f"[{timestamp:>7.3f}s] [{level:^7}] [{category:^20}] {message}"
        print(event)
        self.events.append(event)
    
    def info(self, category, message):
        self.log("INFO", category, message)
    
    def error(self, category, message):
        self.log("ERROR", category, message)
        self.errors.append(message)
    
    def success(self, category, message):
        self.log("SUCCESS", category, message)
    
    def separator(self, title=""):
        sep = "=" * 80
        if title:
            print(f"\n{sep}")
            print(f"  {title}")
            print(f"{sep}\n")
        else:
            print(sep)

diag = DiagnosticLogger()

# ============================================================================
# PHASE 0: ENVIRONMENT CHECK
# ============================================================================

diag.separator("PHASE 0: Environment & Dependencies Check")

diag.info("ENVIRONMENT", f"Python: {sys.version}")
diag.info("ENVIRONMENT", f"Working Dir: {os.getcwd()}")

# Check critical imports
critical_imports = [
    'dash',
    'dash_bootstrap_components',
    'plotly',
    'pandas',
    'numpy',
    'yfinance'
]

for module_name in critical_imports:
    try:
        __import__(module_name)
        diag.success("IMPORT", f"{module_name} ✓")
    except ImportError as e:
        diag.error("IMPORT", f"{module_name} FAILED: {e}")

# ============================================================================
# PHASE 1: INDEX MODULE IMPORT
# ============================================================================

diag.separator("PHASE 1: Loading Index Module")

try:
    diag.info("INDEX", "Importing financial_dashboard.index...")
    
    # Intercept tab loading
    import financial_dashboard.index as idx_module
    
    diag.success("INDEX", "Index module imported successfully")
    
    # Check for app object
    if hasattr(idx_module, 'app'):
        diag.success("INDEX", f"app object found: {type(idx_module.app)}")
    else:
        diag.error("INDEX", "No app object found in index module!")
    
    # Check for server object
    if hasattr(idx_module, 'server'):
        diag.success("INDEX", f"server object found: {type(idx_module.server)}")
    else:
        diag.info("INDEX", "No server object exported (may be inside main block)")

except Exception as e:
    diag.error("INDEX", f"Failed to import index: {e}")
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# PHASE 2: TAB CONFIGURATION ANALYSIS
# ============================================================================

diag.separator("PHASE 2: Tab Configuration Analysis")

try:
    # Check enabled tabs
    if hasattr(idx_module, 'enabled_tabs'):
        enabled = idx_module.enabled_tabs
        diag.info("TABS", f"Enabled tabs ({len(enabled)}): {enabled}")
    else:
        diag.error("TABS", "No enabled_tabs variable found")
        enabled = []
    
    # Check TAB_CONFIG
    if hasattr(idx_module, 'TAB_CONFIG'):
        config = idx_module.TAB_CONFIG
        diag.info("TABS", f"TAB_CONFIG has {len(config)} entries")
        
        for tab_cfg in config:
            tab_id = tab_cfg.get('id', 'UNKNOWN')
            tab_name = tab_cfg.get('name', 'UNKNOWN')
            is_enabled = tab_id in enabled if enabled else False
            
            status = "✓ ENABLED" if is_enabled else "○ DISABLED"
            diag.info("TAB-CONFIG", f"{status} | {tab_id:20} | {tab_name}")
    else:
        diag.error("TABS", "No TAB_CONFIG found")

except Exception as e:
    diag.error("TABS", f"Tab config analysis failed: {e}")
    traceback.print_exc()

# ============================================================================
# PHASE 3: ATTRIBUTION LAB SPECIFIC CHECKS
# ============================================================================

diag.separator("PHASE 3: Attribution Lab Module Integrity")

try:
    diag.info("ATTR-LAB", "Testing direct import of attribution_lab...")
    
    from financial_dashboard.tabs import attribution_lab
    
    diag.success("ATTR-LAB", "Module imported successfully")
    
    # Check exported symbols
    if hasattr(attribution_lab, 'layout'):
        diag.success("ATTR-LAB", f"layout function found: {type(attribution_lab.layout)}")
    else:
        diag.error("ATTR-LAB", "No layout function exported!")
    
    if hasattr(attribution_lab, 'register_callbacks'):
        diag.success("ATTR-LAB", f"register_callbacks found: {type(attribution_lab.register_callbacks)}")
    else:
        diag.error("ATTR-LAB", "No register_callbacks function exported!")
    
    # Test layout generation
    diag.info("ATTR-LAB", "Testing layout() call...")
    try:
        layout_result = attribution_lab.layout()
        diag.success("ATTR-LAB", f"Layout generated: {type(layout_result).__name__}")
    except Exception as e:
        diag.error("ATTR-LAB", f"Layout generation failed: {e}")
        traceback.print_exc()

except Exception as e:
    diag.error("ATTR-LAB", f"Module import failed: {e}")
    traceback.print_exc()

# ============================================================================
# PHASE 4: CALLBACK INSPECTION
# ============================================================================

diag.separator("PHASE 4: Callback Registry Inspection")

try:
    if hasattr(idx_module, 'app'):
        app = idx_module.app
        
        # Check if app has callback_map
        if hasattr(app, 'callback_map'):
            callback_count = len(app.callback_map)
            diag.info("CALLBACKS", f"Total callbacks registered: {callback_count}")
            
            # List callbacks related to attribution
            attr_callbacks = [
                cb_id for cb_id in app.callback_map.keys()
                if 'attr' in str(cb_id).lower()
            ]
            
            if attr_callbacks:
                diag.info("CALLBACKS", f"Attribution-related callbacks: {len(attr_callbacks)}")
                for cb_id in attr_callbacks[:5]:  # Show first 5
                    diag.info("CALLBACKS", f"  - {cb_id}")
            else:
                diag.error("CALLBACKS", "No attribution-related callbacks found!")
        else:
            diag.info("CALLBACKS", "callback_map not accessible (may be internal)")
    else:
        diag.error("CALLBACKS", "Cannot inspect - no app object")

except Exception as e:
    diag.error("CALLBACKS", f"Callback inspection failed: {e}")

# ============================================================================
# PHASE 5: LAYOUT STRUCTURE CHECK
# ============================================================================

diag.separator("PHASE 5: App Layout Structure")

try:
    if hasattr(idx_module, 'app'):
        app = idx_module.app
        
        if hasattr(app, 'layout'):
            layout = app.layout
            diag.success("LAYOUT", f"App layout exists: {type(layout).__name__}")
            
            # Try to extract tabs info
            layout_str = str(layout)
            if 'attribution_lab' in layout_str.lower():
                diag.success("LAYOUT", "Attribution Lab found in layout structure")
            else:
                diag.error("LAYOUT", "Attribution Lab NOT found in layout structure!")
            
            if 'tab-attribution_lab' in layout_str:
                diag.success("LAYOUT", "ID 'tab-attribution_lab' found in layout")
            else:
                diag.error("LAYOUT", "ID 'tab-attribution_lab' NOT found!")
                
        else:
            diag.error("LAYOUT", "App has no layout attribute!")
    else:
        diag.error("LAYOUT", "Cannot check - no app object")

except Exception as e:
    diag.error("LAYOUT", f"Layout check failed: {e}")

# ============================================================================
# PHASE 6: TEST SERVER START
# ============================================================================

diag.separator("PHASE 6: Test Server Startup")

try:
    if hasattr(idx_module, 'app'):
        app = idx_module.app
        
        diag.info("SERVER", "Attempting to extract Flask server...")
        
        if hasattr(app, 'server'):
            server = app.server
            diag.success("SERVER", f"Flask server accessible: {type(server).__name__}")
        else:
            diag.error("SERVER", "No server attribute on app!")
    
except Exception as e:
    diag.error("SERVER", f"Server extraction failed: {e}")

# ============================================================================
# FINAL SUMMARY
# ============================================================================

diag.separator("DIAGNOSTIC SUMMARY")

total_errors = len(diag.errors)
total_events = len(diag.events)

print(f"Total Events: {total_events}")
print(f"Total Errors: {total_errors}")
print()

if total_errors == 0:
    diag.success("SUMMARY", "✅ NO ERRORS DETECTED - Dashboard should be functional")
    exit_code = 0
else:
    diag.error("SUMMARY", f"❌ {total_errors} ERRORS DETECTED:")
    print()
    for i, error in enumerate(diag.errors, 1):
        print(f"  {i}. {error}")
    print()
    exit_code = 1

diag.separator()

# Save diagnostics
log_file = Path("diagnostics_dashboard.log")
with open(log_file, 'w') as f:
    f.write('\n'.join(diag.events))
    f.write(f"\n\nTotal Errors: {total_errors}\n")
    if diag.errors:
        f.write("\nError List:\n")
        for error in diag.errors:
            f.write(f"  - {error}\n")

diag.info("OUTPUT", f"Diagnostics saved to {log_file}")

sys.exit(exit_code)
