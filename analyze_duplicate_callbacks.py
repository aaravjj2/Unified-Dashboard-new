#!/usr/bin/env python3
"""
Comprehensive Duplicate Callback Analyzer
Extracts ALL duplicate callback errors from browser console and identifies exact output components.
"""

import asyncio
import re
from playwright.async_api import async_playwright
from collections import defaultdict

async def analyze_duplicates():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        duplicate_messages = []
        
        def capture_console(msg):
            text = msg.text
            if 'Duplicate callback outputs' in text:
                duplicate_messages.append(text)
        
        page.on('console', capture_console)
        
        try:
            print("🔍 Loading dashboard...")
            await page.goto('http://localhost:8051', wait_until='networkidle', timeout=60000)
            await asyncio.sleep(8)  # Extra time for all callbacks to register
            
            print(f"\n📊 DUPLICATE CALLBACK ANALYSIS")
            print("=" * 80)
            print(f"Total duplicate callback errors: {len(duplicate_messages)}")
            print("=" * 80)
            
            if not duplicate_messages:
                print("\n✅ SUCCESS! No duplicate callbacks found!")
                return
            
            # Parse output IDs from duplicate messages
            output_pattern = r'for output\(s\):\s+([^\s]+)'
            outputs_count = defaultdict(int)
            
            for msg in duplicate_messages:
                matches = re.findall(output_pattern, msg)
                for match in matches:
                    # Clean up the output ID (remove ellipsis and truncation)
                    clean_id = match.replace('…', '').replace('er', '')
                    outputs_count[clean_id] += 1
            
            # Group by prefix to identify tabs
            print(f"\n📋 DUPLICATE OUTPUTS BY TAB:")
            print("-" * 80)
            
            tab_groups = defaultdict(list)
            for output_id, count in sorted(outputs_count.items()):
                # Identify tab by prefix
                if output_id.startswith('trends-') or output_id.startswith('mt-'):
                    tab = 'Market Trends'
                elif output_id.startswith('mf-'):
                    tab = 'Market Forecast'
                elif output_id.startswith('wp-'):
                    tab = 'Weekly Picks'
                elif output_id.startswith('mp-'):
                    tab = 'Monthly Picks'
                elif output_id.startswith('portfolio-') or output_id.startswith('positions-'):
                    tab = 'Portfolio'
                elif output_id.startswith('opt-') or output_id.startswith('options-') or output_id.startswith('chain-'):
                    tab = 'Options Lab'
                elif output_id.startswith('vol-') or output_id.startswith('iv-'):
                    tab = 'Volatility Lab'
                elif output_id.startswith('strat-') or output_id.startswith('backtest-'):
                    tab = 'Strategy Lab'
                elif output_id.startswith('attr-') or output_id.startswith('perf-') or output_id.startswith('factors-'):
                    tab = 'Attribution Lab'
                elif output_id.startswith('research-') or output_id.startswith('brief-'):
                    tab = 'Research Lab'
                elif output_id.startswith('home-'):
                    tab = 'Home Lab'
                elif output_id.startswith('chatbot-'):
                    tab = 'Chatbot'
                else:
                    tab = 'Other/Unknown'
                
                tab_groups[tab].append((output_id, count))
            
            for tab, outputs in sorted(tab_groups.items()):
                print(f"\n🏷️  {tab}: {len(outputs)} duplicate outputs")
                for output_id, count in sorted(outputs, key=lambda x: -x[1])[:10]:
                    print(f"   - {output_id}: {count} duplicates")
            
            # Show first 5 full error messages
            print(f"\n📝 SAMPLE DUPLICATE ERRORS (first 5):")
            print("-" * 80)
            for i, msg in enumerate(duplicate_messages[:5], 1):
                print(f"\n[{i}] {msg[:300]}...")
            
            print(f"\n💡 SUMMARY:")
            print(f"   Total tabs with duplicates: {len(tab_groups)}")
            print(f"   Total unique output IDs: {len(outputs_count)}")
            print(f"   Total duplicate errors: {len(duplicate_messages)}")
            
        finally:
            await browser.close()

if __name__ == '__main__':
    asyncio.run(analyze_duplicates())
