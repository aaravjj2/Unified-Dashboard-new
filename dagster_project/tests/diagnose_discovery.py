#!/usr/bin/env python3
"""Diagnose file discovery issue by writing diagnostics to a log file."""
from pathlib import Path

# Determine repo root and data directory
repo_root = Path(__file__).resolve().parents[2]
data_dir = repo_root / "financial_dashboard" / "Financial_Data"

# Write diagnostics to a file
log_file = Path("/tmp/discovery_diagnostics.txt")
with open(log_file, "w") as f:
    f.write("=" * 80 + "\n")
    f.write("[FILE DISCOVERY DIAGNOSTICS]\n")
    f.write("=" * 80 + "\n\n")
    
    f.write(f"[1] Script location: {__file__}\n")
    f.write(f"[2] Resolved repo_root: {repo_root}\n")
    f.write(f"[3] Absolute repo_root path: {repo_root.absolute()}\n")
    f.write(f"[4] repo_root exists: {repo_root.exists()}\n")
    f.write(f"[5] repo_root is_dir: {repo_root.is_dir()}\n\n")
    
    f.write(f"[6] Computed data_dir path: {data_dir}\n")
    f.write(f"[7] Absolute data_dir path: {data_dir.absolute()}\n")
    f.write(f"[8] data_dir.exists() check: {data_dir.exists()}\n")
    
    if data_dir.exists():
        f.write(f"[9] data_dir.is_dir() check: {data_dir.is_dir()}\n\n")
        
        if data_dir.is_dir():
            # List what's actually in data_dir
            f.write("=" * 80 + "\n")
            f.write("[CONTENTS OF data_dir]\n")
            f.write("=" * 80 + "\n")
            try:
                all_items = list(data_dir.iterdir())
                f.write(f"Total items in {data_dir}: {len(all_items)}\n\n")
                for item in sorted(all_items):
                    item_type = "DIR" if item.is_dir() else "FILE"
                    f.write(f"  [{item_type}] {item.name}\n")
            except Exception as e:
                f.write(f"ERROR listing directory: {e}\n")
            
            # Now search for picks CSV files
            f.write("\n" + "=" * 80 + "\n")
            f.write("[PICKS CSV GLOB SEARCH]\n")
            f.write("=" * 80 + "\n")
            f.write(f"Pattern: '**/picks_*.csv'\n")
            f.write(f"Searching from: {data_dir}\n\n")
            
            picks = list(data_dir.glob("**/picks_*.csv"))
            f.write(f"Result: Found {len(picks)} picks_*.csv files\n\n")
            
            if picks:
                f.write("Files found:\n")
                for i, p in enumerate(picks, 1):
                    f.write(f"  {i}. {p.resolve()}\n")
            else:
                f.write("WARNING: No picks_*.csv files found!\n\n")
                
                # Try alternative search patterns
                f.write("Trying alternative patterns...\n")
                alt_patterns = ["picks_*.csv", "*/picks_*.csv", "**/picks*.csv", "**/*.csv"]
                for pattern in alt_patterns:
                    alt_results = list(data_dir.glob(pattern))
                    f.write(f"  Pattern '{pattern}': {len(alt_results)} files\n")
                    if alt_results:
                        for item in alt_results[:5]:  # show first 5
                            f.write(f"    - {item.name}\n")
            
            # Parquet search for comparison
            f.write("\n" + "=" * 80 + "\n")
            f.write("[PARQUET GLOB SEARCH - FOR COMPARISON]\n")
            f.write("=" * 80 + "\n")
            f.write(f"Pattern: '**/*.parquet'\n")
            f.write(f"Searching from: {data_dir}\n\n")
            
            parquets = list(data_dir.glob("**/*.parquet"))
            f.write(f"Result: Found {len(parquets)} *.parquet files\n\n")
            
            if parquets:
                f.write("Sample parquet files (first 10):\n")
                for i, p in enumerate(parquets[:10], 1):
                    f.write(f"  {i}. {p.resolve()}\n")
    else:
        f.write(f"[9] data_dir.is_dir() check: N/A (path does not exist)\n\n")
        
        # Try to find where Financial_Data might actually be
        f.write("=" * 80 + "\n")
        f.write("[SEARCHING FOR Financial_Data DIRECTORY]\n")
        f.write("=" * 80 + "\n")
        
        # Check if financial_dashboard exists at all
        fd_dir = repo_root / "financial_dashboard"
        f.write(f"Checking: {fd_dir}\n")
        f.write(f"  exists: {fd_dir.exists()}\n")
        if fd_dir.exists():
            f.write(f"  is_dir: {fd_dir.is_dir()}\n")
            if fd_dir.is_dir():
                f.write(f"  Contents:\n")
                for item in sorted(fd_dir.iterdir()):
                    item_type = "DIR" if item.is_dir() else "FILE"
                    f.write(f"    [{item_type}] {item.name}\n")

print(f"Diagnostics written to: {log_file}")
print("Reading diagnostics file...")
print()
with open(log_file, "r") as f:
    print(f.read())
