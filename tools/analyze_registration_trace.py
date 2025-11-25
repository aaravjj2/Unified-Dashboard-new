#!/usr/bin/env python3
"""Analyze callback registration trace for duplicate patterns."""
import json
from pathlib import Path
from collections import defaultdict


def analyze_trace(trace_path):
    """Parse trace log and identify duplicate registration patterns."""
    registrations = []
    duplicates_by_output = defaultdict(list)
    duplicates_by_module = defaultdict(int)
    
    # Load trace entries
    with open(trace_path, 'r') as f:
        for line in f:
            if line.strip():
                entry = json.loads(line)
                registrations.append(entry)
    
    # Find duplicates
    duplicates = [r for r in registrations if r.get('is_duplicate')]
    
    print("=" * 80)
    print(f"CALLBACK REGISTRATION TRACE ANALYSIS")
    print("=" * 80)
    print(f"Total registrations: {len(registrations)}")
    print(f"Unique registrations: {len(registrations) - len(duplicates)}")
    print(f"Duplicate registrations: {len(duplicates)}")
    print()
    
    # Group duplicates by output ID
    for dup in duplicates:
        for output_id in dup['outputs']:
            duplicates_by_output[output_id].append({
                'file': dup['caller']['filename'],
                'line': dup['caller']['lineno'],
                'function': dup['caller']['function'],
                'timestamp': dup['timestamp']
            })
    
    # Group by module
    for dup in duplicates:
        module = Path(dup['caller']['filename']).stem
        duplicates_by_module[module] += 1
    
    # Print duplicate summary
    if duplicates:
        print("=" * 80)
        print("DUPLICATES BY OUTPUT ID:")
        print("=" * 80)
        for output_id, locations in sorted(duplicates_by_output.items(), 
                                          key=lambda x: len(x[1]), reverse=True)[:20]:
            print(f"\n{output_id}: {len(locations)} duplicates")
            for loc in locations:
                print(f"  - {Path(loc['file']).name}:{loc['line']} in {loc['function']}()")
        
        print("\n" + "=" * 80)
        print("DUPLICATES BY MODULE:")
        print("=" * 80)
        for module, count in sorted(duplicates_by_module.items(), 
                                   key=lambda x: x[1], reverse=True):
            print(f"{module}: {count}")
    
    # Detailed duplicate analysis
    print("\n" + "=" * 80)
    print("DETAILED DUPLICATE PATTERNS:")
    print("=" * 80)
    
    # Find callback IDs registered multiple times
    for output_id, locations in sorted(duplicates_by_output.items(),
                                      key=lambda x: len(x[1]), reverse=True)[:10]:
        print(f"\n🔴 {output_id} - {len(locations)} duplicate registrations:")
        
        # Find first registration
        first_reg = next((r for r in registrations 
                         if output_id in r['outputs'] and not r.get('is_duplicate')), None)
        
        if first_reg:
            print(f"  ✅ First registered: {Path(first_reg['caller']['filename']).name}:"
                  f"{first_reg['caller']['lineno']} in {first_reg['caller']['function']}()")
        
        for i, loc in enumerate(locations, 1):
            print(f"  ❌ Duplicate {i}: {Path(loc['file']).name}:{loc['line']} "
                  f"in {loc['function']}()")
    
    # Save detailed JSON report
    report = {
        'summary': {
            'total_registrations': len(registrations),
            'unique_registrations': len(registrations) - len(duplicates),
            'duplicate_registrations': len(duplicates)
        },
        'duplicates_by_output': {
            output_id: [
                {
                    'file': loc['file'],
                    'line': loc['line'],
                    'function': loc['function']
                }
                for loc in locs
            ]
            for output_id, locs in duplicates_by_output.items()
        },
        'duplicates_by_module': dict(duplicates_by_module),
        'all_duplicates': duplicates
    }
    
    report_path = Path(trace_path).parent / 'trace_analysis_report.json'
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: {report_path}")
    
    return report


if __name__ == '__main__':
    trace_path = 'reports/duplicates_fix/diagnostics/callback_registration_trace.log'
    report = analyze_trace(trace_path)
