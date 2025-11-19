"""Simple onboarding progress manager.

Persists a tiny JSON file at /user_state/onboarding_progress.json and offers helpers.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict

ROOT = Path(__file__).parent
USER_STATE_DIR = ROOT / 'user_state'
USER_STATE_DIR.mkdir(parents=True, exist_ok=True)
PROGRESS_PATH = USER_STATE_DIR / 'onboarding_progress.json'

DEFAULT = {
    "first_run": True,
    "steps": {
        "welcome_seen": False,
        "theme_toggled": False,
        "tour_completed": False,
        "data_loaded": False
    }
}


def _ensure():
    if not PROGRESS_PATH.exists():
        with open(PROGRESS_PATH, 'w', encoding='utf8') as f:
            json.dump(DEFAULT, f, indent=2)


def get_progress() -> Dict:
    _ensure()
    with open(PROGRESS_PATH, 'r', encoding='utf8') as f:
        return json.load(f)


def set_step(step: str, value: bool = True) -> None:
    p = get_progress()
    if 'steps' not in p:
        p['steps'] = {}
    p['steps'][step] = value
    p['first_run'] = False
    with open(PROGRESS_PATH, 'w', encoding='utf8') as f:
        json.dump(p, f, indent=2)


def reset_progress() -> None:
    with open(PROGRESS_PATH, 'w', encoding='utf8') as f:
        json.dump(DEFAULT, f, indent=2)


if __name__ == '__main__':
    print('Onboarding progress path:', PROGRESS_PATH)
    print(get_progress())
