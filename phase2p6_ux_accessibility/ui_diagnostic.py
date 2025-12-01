"""UI diagnostics: perform responsive checks and detect potential layout drift.

Note: This module provides heuristic checks suitable for offline automated runs.
It simulates container widths for typical breakpoints and reports if configured
component minimum widths exceed container size (possible overflow).
"""
from __future__ import annotations
import json
from pathlib import Path
from .theme_engine import ThemeEngine

ROOT = Path(__file__).parent
CONFIG = ROOT / 'theme_config.json'


class UIDiagnostic:
    def __init__(self, config_path: Path | str = None):
        self.te = ThemeEngine(config_path)
        self.breakpoints = self.te.config.get('breakpoints', {})

    def run_for_components(self, components: dict) -> dict:
        """components: dict of {name: {min_width: int}}

        Returns report with percent of components that fit each breakpoint.
        """
        report = {}
        for bp_name, bp_px in self.breakpoints.items():
            fits = 0
            total = len(components)
            for comp, meta in components.items():
                minw = int(meta.get('min_width', 0))
                if minw <= bp_px:
                    fits += 1
            pct = (fits / total * 100) if total else 100
            report[bp_name] = {"breakpoint_px": bp_px, "fits": fits, "total": total, "percent_fit": round(pct, 1)}
        return report


def sample_components() -> dict:
    # Example; in real integration read from layout descriptors
    return {
        "market_trends": {"min_width": 320},
        "portfolio_summary": {"min_width": 420},
        "heatmap": {"min_width": 600},
        "beeswarm": {"min_width": 540},
        "event_panel": {"min_width": 280}
    }


if __name__ == '__main__':
    d = UIDiagnostic()
    comps = sample_components()
    print(json.dumps(d.run_for_components(comps), indent=2))
