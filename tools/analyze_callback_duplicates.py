#!/usr/bin/env python3
"""
Analyze callback registrations for duplicates.
This script imports the app and examines the callback_map for duplicate Output IDs.
"""
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def analyze_callbacks():
    """Analyze the app's callback_map for duplicates."""
    result = {
        'total_callbacks': 0,
        'duplicate_outputs': [],
        'callback_map_keys': [],
        'output_id_map': {},
        'errors': []
    }
    
    try:
        # Import the app factory
        from financial_dashboard.app import create_app
        
        # Create app instance
        print("Creating app instance...")
        app = create_app()
        
        # Get callback map
        callback_map = getattr(app, 'callback_map', {})
        result['total_callbacks'] = len(callback_map)
        result['callback_map_keys'] = list(callback_map.keys())[:500]
        
        print(f"Found {len(callback_map)} registered callbacks")
        
        # Analyze outputs
        output_id_to_callbacks = {}
        
        for callback_id, callback_spec in callback_map.items():
            # Extract output information
            outputs = callback_spec.get('output', [])
            if not isinstance(outputs, list):
                outputs = [outputs]
            
            for output in outputs:
                # Get output ID string
                if hasattr(output, 'component_id'):
                    output_id = f"{output.component_id}.{output.component_property}"
                else:
                    output_id = str(output)
                
                if output_id not in output_id_to_callbacks:
                    output_id_to_callbacks[output_id] = []
                output_id_to_callbacks[output_id].append({
                    'callback_id': callback_id,
                    'callback_spec': str(callback_spec)[:200]  # Truncate for readability
                })
        
        # Find duplicates
        for output_id, callbacks in output_id_to_callbacks.items():
            result['output_id_map'][output_id] = len(callbacks)
            if len(callbacks) > 1:
                result['duplicate_outputs'].append({
                    'output_id': output_id,
                    'count': len(callbacks),
                    'callbacks': callbacks
                })
        
        print(f"Found {len(result['duplicate_outputs'])} duplicate outputs")
        
    except Exception as e:
        import traceback
        result['errors'].append({
            'error': str(e),
            'traceback': traceback.format_exc()
        })
        print(f"ERROR: {e}")
        traceback.print_exc()
    
    return result


if __name__ == '__main__':
    print("=" * 70)
    print("Callback Duplicate Analysis")
    print("=" * 70)
    
    results = analyze_callbacks()
    
    # Save to JSON
    output_file = 'reports/systemfix/diagnostics/duplicate_callbacks.json'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")
    print("\nSummary:")
    print(f"  Total callbacks: {results['total_callbacks']}")
    print(f"  Duplicate outputs: {len(results['duplicate_outputs'])}")
    print(f"  Errors: {len(results['errors'])}")
    
    if results['duplicate_outputs']:
        print("\nDuplicate Outputs:")
        for dup in results['duplicate_outputs'][:10]:  # Show first 10
            print(f"  - {dup['output_id']}: {dup['count']} registrations")
    
    sys.exit(0 if not results['duplicate_outputs'] else 1)
