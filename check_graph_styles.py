#!/usr/bin/env python3
"""Check computed styles to verify graphs are in dark mode."""

from playwright.sync_api import sync_playwright
import time
import json

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        
        print("Loading dashboard...")
        page.goto("http://localhost:8050", wait_until="networkidle", timeout=60000)
        time.sleep(3)
        
        # Check computed styles
        results = []
        
        # Check dash-graph elements
        graph_check = page.evaluate('''
            () => {
                const graphs = document.querySelectorAll('.dash-graph');
                const results = [];
                graphs.forEach((g, i) => {
                    const style = getComputedStyle(g);
                    results.push({
                        index: i,
                        backgroundColor: style.backgroundColor,
                        color: style.color
                    });
                });
                return results;
            }
        ''')
        
        print("\n=== .dash-graph computed styles ===")
        for g in graph_check:
            bg = g['backgroundColor']
            is_dark = 'rgba(0, 0, 0' in bg or 'rgb(26, 26, 46)' in bg or bg == 'transparent'
            status = "✅ DARK" if is_dark else "❌ LIGHT"
            print(f"  Graph {g['index']}: bg={bg} {status}")
        
        # Check plotly SVG backgrounds
        svg_check = page.evaluate('''
            () => {
                const svgs = document.querySelectorAll('.js-plotly-plot .main-svg');
                const results = [];
                svgs.forEach((s, i) => {
                    const style = getComputedStyle(s);
                    const rect = s.querySelector('rect.bg');
                    let rectFill = 'N/A';
                    if (rect) {
                        rectFill = rect.getAttribute('fill') || getComputedStyle(rect).fill;
                    }
                    results.push({
                        index: i,
                        svgBg: style.backgroundColor,
                        rectFill: rectFill
                    });
                });
                return results;
            }
        ''')
        
        print("\n=== Plotly SVG backgrounds ===")
        for s in svg_check:
            fill = s['rectFill']
            is_dark = 'rgba(0' in str(fill) or 'transparent' in str(fill) or '#1' in str(fill) or '#0' in str(fill) or 'rgb(22' in str(fill)
            status = "✅ DARK" if is_dark else "❌ LIGHT"
            print(f"  SVG {s['index']}: fill={fill} {status}")
        
        # Check card backgrounds containing graphs
        card_check = page.evaluate('''
            () => {
                const cards = document.querySelectorAll('.card');
                const results = [];
                cards.forEach((c, i) => {
                    const hasGraph = c.querySelector('.dash-graph, .js-plotly-plot');
                    if (hasGraph) {
                        const style = getComputedStyle(c);
                        results.push({
                            index: i,
                            backgroundColor: style.backgroundColor,
                            hasGraph: true
                        });
                    }
                });
                return results;
            }
        ''')
        
        print("\n=== Cards containing graphs ===")
        for c in card_check:
            bg = c['backgroundColor']
            is_dark = 'rgb(26, 26, 46)' in bg or 'rgb(22,' in bg or 'rgba(0' in bg
            status = "✅ DARK" if is_dark else "❌ LIGHT (may need CSS :has() support)"
            print(f"  Card {c['index']}: bg={bg} {status}")
        
        # Check body/navbar for light theme
        body_check = page.evaluate('''
            () => {
                const body = document.body;
                const navbar = document.querySelector('.navbar');
                const bodyStyle = getComputedStyle(body);
                const navStyle = navbar ? getComputedStyle(navbar) : null;
                return {
                    bodyBg: bodyStyle.backgroundColor,
                    bodyColor: bodyStyle.color,
                    navBg: navStyle ? navStyle.backgroundColor : 'N/A'
                };
            }
        ''')
        
        print("\n=== UI Light Mode Check ===")
        print(f"  Body: bg={body_check['bodyBg']}, color={body_check['bodyColor']}")
        print(f"  Navbar: bg={body_check['navBg']}")
        
        body_bg = body_check['bodyBg']
        is_light = 'rgb(248,' in body_bg or 'rgb(255,' in body_bg or '#f' in body_bg.lower() or '#e' in body_bg.lower()
        print(f"\n  UI is {'✅ LIGHT MODE' if is_light else '❌ DARK MODE'}")
        
        browser.close()
        print("\n✅ Style check complete")

if __name__ == "__main__":
    main()
