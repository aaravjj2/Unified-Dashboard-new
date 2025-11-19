"""
Diagnostics Snapshot Loop - HTML Render Timing Verification

This script monitors the dashboard's HTML structure loading sequence:
1. Captures when div.tab-content becomes non-empty
2. Tracks when each Volatility Lab subtab first renders
3. Records Market Forecast tab load timing
4. Saves timeline to snapshots/html_load_timeline.json

Usage:
    python diagnostics_snapshot_loop.py
"""

import time
import json
import requests
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup

# Configuration
BASE_URL = "http://localhost:8050"
SNAPSHOT_DIR = Path("snapshots")
SNAPSHOT_DIR.mkdir(exist_ok=True)

TIMELINE_FILE = SNAPSHOT_DIR / "html_load_timeline.json"
DOM_DUMP_FILE = SNAPSHOT_DIR / "final_dom_dump.html"

# Timing configuration
MAX_WAIT_TIME = 120  # seconds
POLL_INTERVAL = 0.5  # seconds

# Elements to track
TRACKED_ELEMENTS = {
    'tab_content': {'selector': 'div.tab-content', 'description': 'Main tab container'},
    'market_forecast_tab': {'selector': '#tab-market_forecast', 'description': 'Market Forecast tab'},
    'volatility_lab_tab': {'selector': '#tab-volatility_lab', 'description': 'Volatility Lab tab'},
    'vol_hv_subtab': {'selector': '#vl-tabs', 'description': 'Volatility subtabs container'},
    'vol_hv_chart': {'selector': '#vl-hv-price', 'description': 'HV price chart'},
    'vol_iv_chart': {'selector': '#vl-iv-surface', 'description': 'IV surface chart'},
    'vol_corr_chart': {'selector': '#vl-corr-heat', 'description': 'Correlation heatmap'},
    'mf_returns_chart': {'selector': '#mf-returns-chart', 'description': 'Market Forecast returns chart'},
    'mf_volatility_chart': {'selector': '#mf-volatility-chart', 'description': 'Market Forecast volatility chart'},
}


def fetch_html():
    """Fetch current HTML from dashboard"""
    try:
        response = requests.get(BASE_URL, timeout=5)
        if response.status_code == 200:
            return response.text
        else:
            print(f"⚠️  HTTP {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
        return None


def check_element_exists(html, selector):
    """Check if element exists in HTML using CSS selector"""
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Handle ID selectors
        if selector.startswith('#'):
            elem_id = selector[1:]
            elements = soup.find_all(id=elem_id)
            return len(elements) > 0
        
        # Handle class selectors
        elif selector.startswith('.'):
            class_name = selector[1:]
            elements = soup.find_all(class_=class_name)
            return len(elements) > 0
        
        # Handle element.class selectors
        elif '.' in selector:
            tag, class_name = selector.split('.', 1)
            elements = soup.find_all(tag, class_=class_name)
            return len(elements) > 0
        
        # Handle plain tag selectors
        else:
            elements = soup.find_all(selector)
            return len(elements) > 0
    except Exception as e:
        print(f"⚠️  Error checking {selector}: {e}")
        return False


def run_snapshot_loop():
    """Main diagnostic loop"""
    print("=" * 80)
    print("DIAGNOSTICS SNAPSHOT LOOP - HTML RENDER TIMING")
    print("=" * 80)
    print(f"\nTarget URL: {BASE_URL}")
    print(f"Output: {TIMELINE_FILE}")
    print(f"Max wait: {MAX_WAIT_TIME}s\n")
    
    # Initialize timeline
    timeline = {
        'start_time': datetime.now().isoformat(),
        'base_url': BASE_URL,
        'elements_tracked': len(TRACKED_ELEMENTS),
        'events': [],
        'summary': {}
    }
    
    start_timestamp = time.time()
    found_elements = set()
    
    print("⏳ Monitoring HTML structure...\n")
    
    # Polling loop
    elapsed = 0
    while elapsed < MAX_WAIT_TIME:
        html = fetch_html()
        
        if html:
            # Check each tracked element
            for elem_id, elem_info in TRACKED_ELEMENTS.items():
                if elem_id not in found_elements:
                    if check_element_exists(html, elem_info['selector']):
                        # Element appeared!
                        event_time = time.time() - start_timestamp
                        event = {
                            'element_id': elem_id,
                            'selector': elem_info['selector'],
                            'description': elem_info['description'],
                            'timestamp': datetime.now().isoformat(),
                            'elapsed_seconds': round(event_time, 3)
                        }
                        timeline['events'].append(event)
                        found_elements.add(elem_id)
                        
                        print(f"✅ {event_time:6.2f}s - {elem_info['description']}")
            
            # Check if we found all elements
            if len(found_elements) == len(TRACKED_ELEMENTS):
                print(f"\n🎉 All elements found in {elapsed:.2f}s!")
                break
        
        time.sleep(POLL_INTERVAL)
        elapsed = time.time() - start_timestamp
    
    # Finalize timeline
    timeline['end_time'] = datetime.now().isoformat()
    timeline['total_elapsed'] = round(elapsed, 3)
    timeline['elements_found'] = len(found_elements)
    timeline['elements_missing'] = len(TRACKED_ELEMENTS) - len(found_elements)
    
    # Summary stats
    if timeline['events']:
        first_event = min(e['elapsed_seconds'] for e in timeline['events'])
        last_event = max(e['elapsed_seconds'] for e in timeline['events'])
        
        timeline['summary'] = {
            'first_element_at': f"{first_event:.3f}s",
            'last_element_at': f"{last_event:.3f}s",
            'total_load_time': f"{last_event:.3f}s",
            'completeness': f"{len(found_elements)}/{len(TRACKED_ELEMENTS)}"
        }
    
    # Identify missing elements
    missing = set(TRACKED_ELEMENTS.keys()) - found_elements
    if missing:
        timeline['missing_elements'] = [
            {
                'element_id': elem_id,
                'selector': TRACKED_ELEMENTS[elem_id]['selector'],
                'description': TRACKED_ELEMENTS[elem_id]['description']
            }
            for elem_id in missing
        ]
        
        print(f"\n⚠️  Missing elements ({len(missing)}):")
        for elem_id in missing:
            print(f"   - {TRACKED_ELEMENTS[elem_id]['description']}")
    
    # Save timeline
    with open(TIMELINE_FILE, 'w') as f:
        json.dump(timeline, f, indent=2)
    
    print(f"\n✅ Timeline saved to: {TIMELINE_FILE}")
    
    # Save final HTML DOM snapshot
    final_html = fetch_html()
    if final_html:
        with open(DOM_DUMP_FILE, 'w') as f:
            f.write(final_html)
        print(f"✅ Final DOM snapshot saved to: {DOM_DUMP_FILE}")
        print(f"   Size: {len(final_html)} bytes")
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total time: {timeline['total_elapsed']:.2f}s")
    print(f"Elements found: {timeline['elements_found']}/{len(TRACKED_ELEMENTS)}")
    
    if timeline.get('summary'):
        print(f"First element: {timeline['summary']['first_element_at']}")
        print(f"Last element: {timeline['summary']['last_element_at']}")
        print(f"Load time: {timeline['summary']['total_load_time']}")
    
    return timeline


if __name__ == "__main__":
    try:
        timeline = run_snapshot_loop()
        
        # Exit code based on completeness
        if timeline['elements_found'] == len(TRACKED_ELEMENTS):
            print("\n✅ All elements loaded successfully")
            exit(0)
        else:
            print(f"\n⚠️  Only {timeline['elements_found']}/{len(TRACKED_ELEMENTS)} elements found")
            exit(1)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        exit(2)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(3)
