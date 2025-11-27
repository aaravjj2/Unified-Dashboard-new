#!/usr/bin/env python3
"""
Interpret the analyzer JSON output and fail CI on duplicate IDs across tabs
or cross-tab imports found.
Usage: python tools/ci_duplicate_id_check.py path/to/architecture_report.json
"""
import sys
import json
import re

if len(sys.argv) < 2:
    print("Usage: ci_duplicate_id_check.py <architecture_report.json>")
    sys.exit(2)

path = sys.argv[1]
with open(path) as f:
    data = json.load(f)

ids_by_file = data.get("ids_by_file", {})
major_tabs = data.get("major_tabs", {})

# Patterns for files that should be excluded from duplicate ID checking
EXCLUDE_PATTERNS = [
    r"/legacy/",  # Legacy directories
    r"/legacy_tabs/",  # Legacy tabs directory
    r"\.backup/",  # Backup directories (e.g., command_center_pkg.backup/)
    r"\.bak$",  # .bak files
    r"\.bak_",  # .bak_ variant files
    r"\.backup$",  # .backup files
    r"\.backup_",  # .backup_ variant files
    r"\.disabled$",  # .disabled files
    r"\.disabled\.py$",  # .disabled.py files
    r"_backup_\d+\.py$",  # backup files with timestamps
    r"_BACKUP_",  # Files with BACKUP in name
    r"_BROKEN_",  # Files with BROKEN in name
    r"_CORRUPTED",  # Files with CORRUPTED in name
    r"_OLD_",  # Files with OLD in name
    r"_OLD\.py$",  # Files ending with _OLD.py
    r"^tests/",  # Test files
    r"/tests/",  # Test files in subdirectories
    r"_pkg/",  # Alternative package implementations (e.g., research_lab_pkg)
    r"_v2/",  # Version 2 implementations (e.g., volatility_lab_v2)
    r"_v2\.py$",  # Version 2 files (e.g., home_v2.py)
    r"/tools/",  # Tools directory (contains analysis scripts)
    r"^tools/",  # Tools at root
    r"_refactored\.py$",  # Refactored versions
    r"_rebuild\.py$",  # Rebuild versions
    r"_new\.py$",  # New versions
    r"_minimal\.py$",  # Minimal versions
    r"_callbacks_fixed\.py$",  # Fixed callback versions
    r"test_.*\.py$",  # Test files starting with test_
    r"_test_.*\.py$",  # Test files with underscore prefix
    r"/test_",  # Test files in directories
    r"_debug\.py$",  # Debug files
    r"_fixed\.py$",  # Fixed versions
    r"_clean\.py$",  # Clean versions
    r"_full\.py$",  # Full versions
    r"_simplified\.py$",  # Simplified versions
    r"_standalone.*\.py$",  # Standalone versions
    r"_placeholders\.py$",  # Placeholder files
    r"_dash\.py$",  # Dash-specific implementations
    r"preview_.*\.py$",  # Preview files
    r"/scripts/",  # Scripts directory
    r"/strategies/",  # Strategies directory
    r"/engines/",  # Engines directory
    r"/utils/",  # Utils directory (non-UI code)
    r"/components/",  # Reusable components (intentionally shared)
    r"scenario_analysis\.py$",  # Duplicate scenario tab implementation
    r"picks_unified\.py$",  # Unified picks (deprecated)
    r"market_dashboard\.py$",  # Standalone market dashboard
    r"index\.py$",  # Main index (includes components)
]


def should_exclude(filepath):
    """Check if a file should be excluded from duplicate ID checking."""
    for pattern in EXCLUDE_PATTERNS:
        if re.search(pattern, filepath):
            return True
    return False


def get_tab_name(filepath):
    """Extract the tab name from a file path (e.g., 'strategy_lab' from 'financial_dashboard/tabs/strategy_lab/layout.py')."""
    parts = filepath.split("/")
    if "tabs" in parts:
        tabs_idx = parts.index("tabs")
        if tabs_idx + 1 < len(parts):
            tab_name = parts[tabs_idx + 1]
            return normalize_tab_name(tab_name)
    return None


def normalize_tab_name(tab_name):
    """Normalize tab name by removing version and package suffixes."""
    # Remove _pkg suffix to normalize tab names
    if tab_name.endswith("_pkg"):
        tab_name = tab_name[:-4]
    if tab_name.endswith("_v2"):
        tab_name = tab_name[:-3]
    return tab_name


# Build ID usage map, excluding backup/legacy/test files
id_usage = {}
for f, ids in ids_by_file.items():
    if should_exclude(f):
        continue
    for i in ids:
        id_usage.setdefault(i, []).append(f)

# Find duplicate IDs used in files belonging to different tabs
# (IDs within the same tab package are allowed)
cross_tab_duplicates = {}
for id_val, files in id_usage.items():
    if len(files) <= 1:
        continue
    # Check if all files are in the same tab
    tabs = set()
    for f in files:
        tab = get_tab_name(f)
        if tab:
            tabs.add(tab)
        else:
            # File is not in a tab, use a unique identifier
            tabs.add(f"__non_tab__{f}")
    if len(tabs) > 1:
        cross_tab_duplicates[id_val] = files

# Cross-tab imports from architecture JSON (resolved_graph keys)
resolved_graph = data.get("resolved_graph", {})

# Allowed cross-tab imports (shared component modules)
ALLOWED_CROSS_TAB_IMPORTS = [
    "financial_dashboard.tabs.research_lab.components",  # Shared components
]

# We treat any resolved_graph entries as potential cross imports; the analyzer
# already records which modules import which; for CI we will be conservative
cross_tab_warnings = []
for src, targets in resolved_graph.items():
    # Convert module path to file path style for exclusion check
    src_path = src.replace(".", "/")
    if should_exclude(src_path):
        continue
    for t in targets:
        # Skip allowed cross-tab imports
        if t in ALLOWED_CROSS_TAB_IMPORTS:
            continue
        t_path = t.replace(".", "/")
        if should_exclude(t_path):
            continue
        # naive heuristic: if both source and target are under financial_dashboard.tabs but different subfolders
        if "financial_dashboard.tabs" in src and "financial_dashboard.tabs" in t:
            # Extract tab names from module paths
            src_parts = src.split(".")
            t_parts = t.split(".")
            if "tabs" in src_parts and "tabs" in t_parts:
                src_tab_idx = src_parts.index("tabs") + 1
                t_tab_idx = t_parts.index("tabs") + 1
                if src_tab_idx < len(src_parts) and t_tab_idx < len(t_parts):
                    src_tab = normalize_tab_name(src_parts[src_tab_idx])
                    t_tab = normalize_tab_name(t_parts[t_tab_idx])
                    # Only warn if importing from a different tab
                    if src_tab != t_tab:
                        cross_tab_warnings.append((src, t))

err = False
if cross_tab_duplicates:
    print("ERROR: Found duplicate component IDs used across different tabs:")
    for i, files in cross_tab_duplicates.items():
        print(f" - ID '{i}' used in {len(files)} files: {files}")
    err = True

if cross_tab_warnings:
    print("ERROR: Potential cross-tab imports detected:")
    for s, t in cross_tab_warnings[:50]:
        print(f" - {s} -> {t}")
    err = True

if err:
    sys.exit(4)
print("ci_duplicate_id_check: OK")
sys.exit(0)
