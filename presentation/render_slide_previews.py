"""Render simple PNG previews for slides using slide definitions and available images.

Creates `presentation/output_slides/slide_{i:02d}.png` for each slide.

Requires: pillow, pyyaml
Run:
  python presentation/render_slide_previews.py presentation/slides_definition.yaml presentation/output_slides
"""
import sys
import os
from PIL import Image, ImageDraw, ImageFont
import yaml


def load_slides(yaml_path):
    with open(yaml_path, 'r', encoding='utf-8') as f:
        doc = yaml.safe_load(f)
    return doc.get('slides', [])


def fit_image_to_canvas(img, canvas_size):
    # Resize while maintaining aspect ratio and fill background white
    canvas_w, canvas_h = canvas_size
    img_w, img_h = img.size
    ratio = min(canvas_w / img_w, canvas_h / img_h)
    new_w = int(img_w * ratio)
    new_h = int(img_h * ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    canvas = Image.new('RGB', canvas_size, 'white')
    x = (canvas_w - new_w) // 2
    y = (canvas_h - new_h) // 2
    canvas.paste(img, (x, y))
    return canvas


def render_preview(slide, out_path, canvas_size=(1920, 1080)):
    title = slide.get('title', '')
    bullets = slide.get('bullets', []) or []
    image_path = slide.get('image') or (slide.get('images') and slide.get('images')[0])

    # Two-column layout: left for text (40% width), right for image (60% width)
    canvas_w, canvas_h = canvas_size
    left_w = int(canvas_w * 0.42)
    right_w = canvas_w - left_w - 80
    padding = 40

    # Prepare canvas and draw
    canvas = Image.new('RGB', canvas_size, 'white')
    draw = ImageDraw.Draw(canvas)

    # Right column image area
    if image_path and os.path.exists(image_path) and not slide.get('image_only', False):
        try:
            img = Image.open(image_path).convert('RGB')
            # fit image to right column area
            img_ratio = min(right_w / img.width, (canvas_h - 2 * padding) / img.height)
            new_w = int(img.width * img_ratio)
            new_h = int(img.height * img_ratio)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            img_x = left_w + padding + (right_w - new_w) // 2
            img_y = padding + (canvas_h - 2 * padding - new_h) // 2
            canvas.paste(img, (img_x, img_y))
        except Exception:
            pass

    # If image_only requested, place the image full-bleed and overlay title if present
    if slide.get('image_only', False):
        if image_path and os.path.exists(image_path):
            try:
                img = Image.open(image_path).convert('RGB')
                img_canvas = fit_image_to_canvas(img, canvas_size)
                canvas.paste(img_canvas)
            except Exception:
                pass
        # overlay title at top if present
        try:
            font_title = ImageFont.truetype('DejaVuSans-Bold.ttf', 54)
        except Exception:
            font_title = ImageFont.load_default()
        if title:
            draw.rectangle([(0, 0), (canvas_w, 100)], fill=(10, 24, 34, 200))
            draw.text((40, 28), title, font=font_title, fill='white')
        canvas.save(out_path, 'PNG')
        return

    # Fonts
    try:
        font_title = ImageFont.truetype('DejaVuSans-Bold.ttf', 54)
        font_bullet = ImageFont.truetype('DejaVuSans.ttf', 34)
    except Exception:
        font_title = ImageFont.load_default()
        font_bullet = ImageFont.load_default()


    # Left column: draw title and bullets on a light background box
    left_box = (padding, padding, left_w - padding, canvas_h - padding)
    draw.rectangle([(left_box[0]-10, left_box[1]-10), (left_box[2]+10, left_box[3]+10)], fill=(245, 247, 250))
    # Title
    draw.text((left_box[0]+10, left_box[1]+8), title, font=font_title, fill=(10, 24, 34))

    # Bullets
    y = left_box[1] + 80
    for b in bullets[:8]:
        draw.text((left_box[0]+10, y), u'• ' + b, font=font_bullet, fill=(40, 40, 40))
        y += 46

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    canvas.save(out_path, 'PNG')


def main():
    if len(sys.argv) < 3:
        print('Usage: render_slide_previews.py slides_definition.yaml out_dir')
        sys.exit(1)
    yaml_path = sys.argv[1]
    out_dir = sys.argv[2]
    slides = load_slides(yaml_path)
    os.makedirs(out_dir, exist_ok=True)
    for i, s in enumerate(slides, start=1):
        out_path = os.path.join(out_dir, f'slide_{i:02d}.png')
        render_preview(s, out_path)
        print('Wrote', out_path)


if __name__ == '__main__':
    main()
