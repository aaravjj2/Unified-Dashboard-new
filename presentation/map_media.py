import hashlib
import os

media_dir = 'presentation/output_media'
# Candidate source images referenced in slides_definition.yaml
candidates = [
    'screenshots/final/20251119_152942_00_initial.png',
    'screenshots/01_home.png',
    'snapshots/phase12_playwright_snapshots/market_forecast.png',
    'snapshots/screenshot_comparisons/market_forecast_content.png',
    'snapshots/phase12_playwright_snapshots/options_lab.png',
    'screenshots/02_options_lab.png',
    'options_lab_snapshots/options_lab_after_click.png',
    'snapshots/screenshot_comparisons/weekly_picks_annotated.png',
    'screenshots/final/20251119_152942_01_market_trends.png',
    'test-artifacts/home_snapshot.png',
    'options_lab_snapshots/market_forecast_options_initial.png'
]

def sha1(path):
    h = hashlib.sha1()
    with open(path, 'rb') as f:
        while True:
            b = f.read(8192)
            if not b:
                break
            h.update(b)
    return h.hexdigest()

media_hashes = {}
for f in sorted(os.listdir(media_dir)):
    p = os.path.join(media_dir, f)
    media_hashes[f] = sha1(p)

candidate_hashes = {}
for c in candidates:
    if os.path.exists(c):
        candidate_hashes[c] = sha1(c)

# Map media to candidate by matching hashes
mapping = {}
for mf,mh in media_hashes.items():
    found = [c for c,h in candidate_hashes.items() if h==mh]
    mapping[mf] = found

# Print results
print('Media files and candidate matches:')
for mf,found in mapping.items():
    print(f' - {mf}: matches -> {found}')

print('\nIf a media file lists empty matches, it likely originated from an image path not in the candidate list or was resized/processed by pptx.')
