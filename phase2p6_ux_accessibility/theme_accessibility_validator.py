"""Validate theme colors for WCAG AA contrast compliance.

Produces a JSON-style report with ratios and pass/fail for normal text.
"""
from __future__ import annotations
import json
from pathlib import Path
from .theme_engine import contrast_ratio, ThemeEngine

ROOT = Path(__file__).parent


def validate_theme(theme_name: str) -> dict:
    te = ThemeEngine()
    try:
        theme = te.load_theme(theme_name)
    except KeyError:
        return {"theme": theme_name, "error": "not found"}

    bg = theme.get('background')
    surface = theme.get('surface')
    text = theme.get('text')

    r_bg_text = contrast_ratio(bg, text)
    r_surface_text = contrast_ratio(surface, text)

    # WCAG AA requires 4.5:1 for normal text, 3:1 for large text (not tracked here)
    pass_bg = r_bg_text >= 4.5
    pass_surface = r_surface_text >= 4.5

    report = {
        "theme": theme_name,
        "background": {"color": bg, "contrast_with_text": round(r_bg_text, 2), "pass": pass_bg},
        "surface": {"color": surface, "contrast_with_text": round(r_surface_text, 2), "pass": pass_surface}
    }
    return report


def validate_all() -> dict:
    te = ThemeEngine()
    res = {name: validate_theme(name) for name in te.list_themes()}
    return res


if __name__ == '__main__':
    out = validate_all()
    print(json.dumps(out, indent=2))
