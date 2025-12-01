#!/usr/bin/env python3
"""Capture callback map state from running Dash app."""
import json
import sys
import requests
from pathlib import Path

def capture_callback_map():
    """Query the running dashboard for callback registration state."""
    try:
        # Try to import the running app
        sys.path.insert(0, '/home/aarav/unified-dashboard')
        
        # Import after path modification
        from financial_dashboard.app import app
        
        callback_map = getattr(app, 'callback_map', {})
        
        result = {
            'total_callbacks': len(callback_map),
            'callback_ids': list(callback_map.keys())[:500],  # First 500
            'callback_details': {}
        }
        
        # Collect details for each callback
        for cb_id, cb_info in list(callback_map.items())[:100]:  # First 100 detailed
            result['callback_details'][cb_id] = {
                'outputs': str(getattr(cb_info, 'outputs', [])),
                'inputs': str(getattr(cb_info, 'inputs', [])),
                'state': str(getattr(cb_info, 'state', []))
            }
        
        return result
        
    except Exception as e:
        return {
            'error': str(e),
            'error_type': type(e).__name__,
            'total_callbacks': 0,
            'callback_ids': []
        }

if __name__ == '__main__':
    result = capture_callback_map()
    print(json.dumps(result, indent=2))
