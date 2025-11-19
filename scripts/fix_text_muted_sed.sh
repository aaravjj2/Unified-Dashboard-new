#!/bin/bash
#
# Global Text Muted Fix (Sed-Based)
# 
# Replaces all className="...text-muted..." with explicit black text styling.
# Uses sed for reliable pattern matching across all tab files.
#
# Author: Autonomous Lead Engineer (Agent v2)
# Date: October 28, 2025
#

set -e  # Exit on error

echo "======================================================================"
echo "GLOBAL TEXT-MUTED FIX (Sed-Based)"
echo "======================================================================"
echo ""

# Files to process (active tabs only, no backups)
declare -a FILES=(
    "financial_dashboard/tabs/home_lab/layout.py"
    "financial_dashboard/tabs/attribution_lab/layout.py"
    "financial_dashboard/tabs/research_lab/layout.py"
    "financial_dashboard/tabs/options_lab/layout.py"
    "financial_dashboard/tabs/strategy_lab/layout.py"
    "financial_dashboard/tabs/home.py"
    "financial_dashboard/tabs/attribution_tab.py"
    "financial_dashboard/tabs/portfolio_tab.py"
    "financial_dashboard/tabs/volatility_lab.py"
    "financial_dashboard/tabs/market_forecast.py"
    "financial_dashboard/tabs/options_lab.py"
    "financial_dashboard/tabs/analysis_hub_refactored.py"
)

total_fixes=0
files_modified=0

# Process each file
for file in "${FILES[@]}"; do
    if [[ ! -f "$file" ]]; then
        echo "⚠️  SKIP: $file (not found)"
        echo ""
        continue
    fi
    
    echo "Processing: $file"
    
    # Count text-muted occurrences BEFORE
    before_count=$(grep -c 'text-muted' "$file" 2>/dev/null || echo "0")
    
    if [[ "$before_count" == "0" ]]; then
        echo "  ✓ OK: No text-muted found"
        echo ""
        continue
    fi
    
    # Create backup
    cp "$file" "${file}.bak_text_muted"
    
    # Pattern 1: className="text-muted only_other_classes" → className="only_other_classes", style={'color': '#000000'}
    # Pattern 2: className="other text-muted more" → className="other more", style={'color': '#000000'}
    sed -i -E 's/className="([^"]*)text-muted([^"]*)"([^,]*)[,]?/className="\1\2", style={'\''color'\'': '\''#000000'\''}/g' "$file"
    
    # Clean up double spaces in className
    sed -i -E 's/className="  +/className="/g' "$file"
    sed -i -E 's/  +"/"/g' "$file"
    
    # If className is now empty, remove it
    sed -i 's/className="",\s*//' "$file"
    
    # Count text-muted occurrences AFTER
    after_count=$(grep -c 'text-muted' "$file" 2>/dev/null || echo "0")
    
    fixes_made=$((before_count - after_count))
    
    if [[ "$fixes_made" -gt "0" ]]; then
        echo "  ✅ FIXED: $fixes_made replacements"
        ((total_fixes+=fixes_made))
        ((files_modified++))
    else
        echo "  ⚠️  Pattern didn't match (manual review needed)"
        # Restore from backup
        mv "${file}.bak_text_muted" "$file"
    fi
    
    echo ""
done

echo "======================================================================"
echo "SUMMARY"
echo "======================================================================"
echo "Files Modified: $files_modified/${#FILES[@]}"
echo "Total Fixes: $total_fixes"
echo ""

if [[ $files_modified -gt 0 ]]; then
    echo "✅ Text-muted classes replaced with explicit black styling"
    echo ""
    echo "🔄 NEXT STEP: Restart dashboard"
    echo "   docker-compose restart dash_app"
else
    echo "⚠️  No automatic fixes applied (review backup files)"
fi

echo ""
