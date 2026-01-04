from PIL import Image
import os

INPUT_DIR = 'proof_shots'
OUT_FILE = 'proof_shots/proof_comparison.pdf'

imgs = []
for fname in sorted(os.listdir(INPUT_DIR)):
    if fname.lower().endswith('.png'):
        path = os.path.join(INPUT_DIR, fname)
        img = Image.open(path).convert('RGB')
        imgs.append(img)

if not imgs:
    print('No images found to create PDF')
else:
    first, rest = imgs[0], imgs[1:]
    first.save(OUT_FILE, save_all=True, append_images=rest, quality=95)
    print(f'PDF saved to {OUT_FILE}')
