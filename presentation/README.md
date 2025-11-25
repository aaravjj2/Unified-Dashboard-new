Presentation generation instructions

1. Install dependencies in your Python environment:

```bash
pip install python-pptx pyyaml
```

2. Generate the PPTX using the provided script:

```bash
python presentation/build_presentation.py presentation/slides_definition.yaml SharkTank_Pitch.pptx
```

3. Result: `SharkTank_Pitch.pptx` will be created in the current directory.

4. (Optional) Upload to Google Slides:
   - Open Google Drive ➜ New ➜ File upload ➜ upload `SharkTank_Pitch.pptx`
   - Once uploaded, right-click the file and choose "Open with → Google Slides" to convert.

Notes:
- The slide content is stored in `presentation/slides_definition.yaml`. Edit this file to adjust slide text and speaker notes.
- The script uses `python-pptx` which requires a standard CPython environment.

Embedding images

- To embed images into slides, add an `image:` or `images:` field to a slide in `slides_definition.yaml`. For example:

```yaml
   - type: bullets
      title: "Our Solution"
      bullets:
         - "Interactive Dash app"
      image: presentation/assets/options_lab_after_click.png
      notes: "Show Options Lab"
```

- For full-slide visuals (large screenshots), set `full_image: true` and `image_only: true` to create an image-only slide:

```yaml
   - type: bullets
      title: "Vol Surface"
      image: presentation/assets/vol_surface.png
      image_only: true
      full_image: true
      notes: "Short GIF or static image of vol-surface"
```

- Place image assets in `presentation/assets/` and reference them with relative paths.
