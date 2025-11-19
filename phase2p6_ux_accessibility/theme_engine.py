"""Theme engine: load themes from JSON, compute auto-contrast text color, and provide a style dict

Simple API:
  load_theme(name) -> dict
  get_text_color(bg_hex) -> '#000000' or '#FFFFFF' based on luminance threshold
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Dict

ROOT = Path(__file__).parent
CONFIG_PATH = ROOT / "theme_config.json"


def _hex_to_rgb(hex_color: str):
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _relative_luminance(rgb):
    # sRGB to linear and luminance per WCAG
    def chan(c):
        c = c / 255.0
        return c/12.92 if c <= 0.03928 else ((c+0.055)/1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)


def contrast_ratio(hex1: str, hex2: str) -> float:
    l1 = _relative_luminance(_hex_to_rgb(hex1))
    l2 = _relative_luminance(_hex_to_rgb(hex2))
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


class ThemeEngine:
    def __init__(self, config_path: Path | str = None):
        self.config_path = Path(config_path) if config_path else CONFIG_PATH
        self._load()

    def _load(self):
        with open(self.config_path, 'r', encoding='utf8') as f:
            self.config = json.load(f)

    def list_themes(self):
        return list(self.config.get('themes', {}).keys())

    def load_theme(self, name: str) -> Dict:
        t = self.config.get('themes', {}).get(name)
        if not t:
            raise KeyError(f"Theme '{name}' not found")
        # Auto enforce accessible text color for surface/background
        bg = t.get('background')
        text = t.get('text')
        # Ensure text is either pure black or white based on contrast
        auto_text = get_auto_text_color(bg)
        t['text'] = auto_text
        return {**self.config.get('fonts', {}), **t}


def get_auto_text_color(bg_hex: str) -> str:
    # Decide between pure black or pure white to maximize contrast
    black = '#000000'
    white = '#FFFFFF'
    cb = contrast_ratio(bg_hex, black)
    cw = contrast_ratio(bg_hex, white)
    return black if cb >= cw else white


if __name__ == '__main__':
    te = ThemeEngine()
    for name in te.list_themes():
        print(name, te.load_theme(name))
