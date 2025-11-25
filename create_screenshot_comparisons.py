#!/usr/bin/env python3
"""
Extract and compare the main content area from Weekly/Monthly Picks screenshots
to show the actual differences between them
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

SCREENSHOT_DIR = Path("snapshots/phase12_playwright_snapshots")
OUTPUT_DIR = Path("snapshots/screenshot_comparisons")
OUTPUT_DIR.mkdir(exist_ok=True)

def create_annotated_screenshot(image_path, annotations, output_path):
    """Add annotations to screenshot highlighting key areas"""
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)
    
    # Try to use a font, fallback to default if not available
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Draw annotations
    for ann in annotations:
        if ann['type'] == 'box':
            # Draw bounding box
            draw.rectangle(ann['coords'], outline=ann['color'], width=5)
        elif ann['type'] == 'label':
            # Draw label text with background
            text = ann['text']
            bbox = draw.textbbox((0, 0), text, font=font_small)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x, y = ann['position']
            # Background rectangle
            draw.rectangle(
                [x-10, y-5, x + text_width + 10, y + text_height + 5],
                fill=ann.get('bg_color', 'yellow'),
                outline='black',
                width=2
            )
            # Text
            draw.text(ann['position'], text, fill=ann.get('color', 'black'), font=font_small)
    
    img.save(output_path)
    print(f"✅ Created annotated screenshot: {output_path}")
    return img

def create_side_by_side_comparison(images, labels, output_path):
    """Create side-by-side comparison of screenshots"""
    # Load images
    imgs = [Image.open(img) for img in images]
    
    # Resize to same height (use smallest height)
    min_height = min(img.height for img in imgs)
    resized = []
    for img in imgs:
        if img.height > min_height:
            aspect = img.width / img.height
            new_width = int(min_height * aspect)
            resized.append(img.resize((new_width, min_height)))
        else:
            resized.append(img)
    
    # Create combined image
    total_width = sum(img.width for img in resized) + (len(resized) - 1) * 20  # 20px gap
    combined = Image.new('RGB', (total_width, min_height + 80), 'white')
    
    # Paste images side by side
    x_offset = 0
    for img, label in zip(resized, labels):
        combined.paste(img, (x_offset, 80))
        x_offset += img.width + 20
    
    # Add labels at top
    draw = ImageDraw.Draw(combined)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
    except:
        font = ImageFont.load_default()
    
    x_offset = 0
    for img, label in zip(resized, labels):
        draw.text((x_offset + 20, 20), label, fill='black', font=font)
        x_offset += img.width + 20
    
    combined.save(output_path)
    print(f"✅ Created comparison: {output_path}")

def extract_main_content_area(image_path, crop_coords, output_path):
    """Extract just the main content panel from screenshot"""
    img = Image.open(image_path)
    cropped = img.crop(crop_coords)
    cropped.save(output_path)
    print(f"✅ Extracted main content: {output_path}")
    return cropped

if __name__ == "__main__":
    print("🎨 Creating Screenshot Comparisons\n")
    
    # Main content area is roughly:
    # Top: 200px (below nav)
    # Left: 50px
    # Right: 1870px
    # Bottom: varies
    
    main_content_coords = (50, 200, 1870, 1000)  # x1, y1, x2, y2
    
    # Extract main content from each Picks tab
    print("\n1. Extracting main content areas...")
    weekly_main = extract_main_content_area(
        SCREENSHOT_DIR / "weekly_picks.png",
        main_content_coords,
        OUTPUT_DIR / "weekly_picks_content.png"
    )
    
    monthly_main = extract_main_content_area(
        SCREENSHOT_DIR / "monthly_picks.png",
        main_content_coords,
        OUTPUT_DIR / "monthly_picks_content.png"
    )
    
    forecast_main = extract_main_content_area(
        SCREENSHOT_DIR / "market_forecast.png",
        (50, 200, 1870, 1200),
        OUTPUT_DIR / "market_forecast_content.png"
    )
    
    # Create side-by-side comparison
    print("\n2. Creating side-by-side comparison...")
    create_side_by_side_comparison(
        [
            OUTPUT_DIR / "weekly_picks_content.png",
            OUTPUT_DIR / "monthly_picks_content.png",
            OUTPUT_DIR / "market_forecast_content.png"
        ],
        [
            "Weekly Picks (20 stocks)",
            "Monthly Picks (10 stocks)",
            "Market Forecast (ML predictions)"
        ],
        OUTPUT_DIR / "picks_forecast_comparison.png"
    )
    
    # Create annotated versions highlighting key differences
    print("\n3. Creating annotated screenshots...")
    
    weekly_annotations = [
        {
            'type': 'box',
            'coords': (100, 250, 1800, 400),
            'color': 'green'
        },
        {
            'type': 'label',
            'text': '📊 Weekly Picks Dashboard',
            'position': (100, 210),
            'bg_color': 'lightgreen',
            'color': 'darkgreen'
        },
        {
            'type': 'box',
            'coords': (100, 450, 800, 550),
            'color': 'blue'
        },
        {
            'type': 'label',
            'text': '🔄 Refresh Prices Button',
            'position': (100, 560),
            'bg_color': 'lightblue',
            'color': 'darkblue'
        },
        {
            'type': 'box',
            'coords': (100, 600, 1800, 1200),
            'color': 'orange'
        },
        {
            'type': 'label',
            'text': 'Stock Table: ASTS, SNDK, RGTI, ... (20 stocks)',
            'position': (100, 1210),
            'bg_color': 'lightyellow',
            'color': 'darkorange'
        }
    ]
    
    create_annotated_screenshot(
        SCREENSHOT_DIR / "weekly_picks.png",
        weekly_annotations,
        OUTPUT_DIR / "weekly_picks_annotated.png"
    )
    
    monthly_annotations = [
        {
            'type': 'box',
            'coords': (100, 250, 1800, 400),
            'color': 'purple'
        },
        {
            'type': 'label',
            'text': '📊 Monthly Stock Picks',
            'position': (100, 210),
            'bg_color': 'lavender',
            'color': 'purple'
        },
        {
            'type': 'box',
            'coords': (100, 600, 1800, 1200),
            'color': 'red'
        },
        {
            'type': 'label',
            'text': 'Stock Table: GEV, NEM, ETSY, ... (10 stocks)',
            'position': (100, 1210),
            'bg_color': 'lightpink',
            'color': 'darkred'
        }
    ]
    
    create_annotated_screenshot(
        SCREENSHOT_DIR / "monthly_picks.png",
        monthly_annotations,
        OUTPUT_DIR / "monthly_picks_annotated.png"
    )
    
    print("\n" + "="*80)
    print("✅ SCREENSHOT COMPARISON COMPLETE")
    print("="*80)
    print(f"\nOutput directory: {OUTPUT_DIR}/")
    print("\nGenerated files:")
    print("  1. weekly_picks_content.png - Extracted main content")
    print("  2. monthly_picks_content.png - Extracted main content")
    print("  3. market_forecast_content.png - Extracted main content")
    print("  4. picks_forecast_comparison.png - Side-by-side comparison")
    print("  5. weekly_picks_annotated.png - Annotated full screenshot")
    print("  6. monthly_picks_annotated.png - Annotated full screenshot")
    print("\nView comparison:")
    print(f"  {OUTPUT_DIR}/picks_forecast_comparison.png")
    print("="*80)
