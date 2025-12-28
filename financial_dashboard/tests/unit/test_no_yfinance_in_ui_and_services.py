import re
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _find_yfinance_usages(search_paths):
    pattern = re.compile(r"\bimport\s+yfinance\b|\byf\.Ticker\b|\byf\.download\b|\byfinance\b")
    matches = []
    for sp in search_paths:
        p = ROOT / sp
        if not p.exists():
            continue
        for py in p.rglob('*.py'):
            try:
                txt = py.read_text(encoding='utf-8')
            except Exception:
                continue
            for i, line in enumerate(txt.splitlines(), start=1):
                if pattern.search(line):
                    matches.append((str(py.relative_to(ROOT)), i, line.strip()))
    return matches


def test_no_yfinance_in_tabs_and_services():
    """Fail if direct yfinance usage exists in UI tabs or service adapters.

    This enforces the plan requirement: UI callbacks and service adapters must
    use the shared `fetch_historical_data`/PriceClient instead of direct yfinance
    calls. Tests may still use yfinance in their fixtures; this test only checks
    `financial_dashboard/tabs` and `financial_dashboard/services`.
    """
    search_paths = [Path('financial_dashboard') / 'tabs', Path('financial_dashboard') / 'services']
    # Normalize to string paths relative to repo root
    search_paths = [str(p) for p in search_paths]
    matches = _find_yfinance_usages(search_paths)
    if matches:
        msg_lines = [f"Found direct yfinance usage in {len(matches)} places:"]
        for f, ln, code in matches:
            msg_lines.append(f" - {f}:{ln}: {code}")
        raise AssertionError('\n'.join(msg_lines))
