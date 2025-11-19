"""CLI utility to run all UX diagnostics and emit a combined JSON report.

Usage: python ux_diagnostic_runner.py --out report.json
"""
from __future__ import annotations
import json
import time
from pathlib import Path
from .theme_accessibility_validator import validate_all
from .ui_diagnostic import UIDiagnostic, sample_components
from .onboarding_manager import get_progress, set_step, reset_progress

ROOT = Path(__file__).parent


def run_all() -> dict:
    start = time.perf_counter()
    theme_report = validate_all()
    ui = UIDiagnostic()
    ui_report = ui.run_for_components(sample_components())

    # onboarding persistence test
    reset_progress()
    p = get_progress()
    set_step('welcome_seen', True)
    p_after = get_progress()

    elapsed = time.perf_counter() - start

    report = {
        "timestamp": time.time(),
        "theme": theme_report,
        "ui": ui_report,
        "onboarding_before": p,
        "onboarding_after": p_after,
        "elapsed_seconds": round(elapsed, 3)
    }
    return report


if __name__ == '__main__':
    r = run_all()
    out = ROOT / 'docs' / 'phase2p6_ux_report.json'
    out.parent.mkdir(exist_ok=True)
    with open(out, 'w', encoding='utf8') as f:
        json.dump(r, f, indent=2)
    print('Report written to', out)
