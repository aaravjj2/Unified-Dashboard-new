import zipfile
import os
import sys

pptx_path = sys.argv[1] if len(sys.argv) > 1 else 'SharkTank_Pitch.pptx'
out_dir = sys.argv[2] if len(sys.argv) > 2 else 'presentation/output_media'

os.makedirs(out_dir, exist_ok=True)
with zipfile.ZipFile(pptx_path, 'r') as z:
    media_files = [f for f in z.namelist() if f.startswith('ppt/media/')]
    for mf in media_files:
        fn = os.path.basename(mf)
        target = os.path.join(out_dir, fn)
        with z.open(mf) as src, open(target, 'wb') as dst:
            dst.write(src.read())
print('Extracted', len(media_files), 'media files to', out_dir)
