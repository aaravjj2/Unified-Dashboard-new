import os
import re

# Files/dirs where direct yfinance usage is allowed (docs, tests that mock it, debug)
ALLOWED_PATH_SUBSTR = [
    'financial_dashboard/docs',
    'tests/',
    'debug',
    'financial_dashboard/serving/triton',
    '.hypothesis',
    'data_ingestion/ingest_market_data.py'  # this module gates yfinance behind env var
]

# Allowlist additional modules that intentionally expose `yf` or gate yfinance
ALLOWED_PATH_SUBSTR += [
    'financial_dashboard/serving/serving_client.py',
    'financial_dashboard/services/alpha_sim/engine.py',
    'debug_yfinance_greeks.py'
]

PATTERN = re.compile(r"(^|\s)(import\s+yfinance\b|from\s+yfinance\b|\byf\s*=\s*|\byfinance\.)")


def test_no_direct_yfinance_imports_in_tabs_and_services():
    """
    Ensure no direct yfinance imports exist in `financial_dashboard/tabs` or
    `financial_dashboard/services` directories. Other parts of the repo may
    intentionally reference yfinance (scripts, legacy tools, tests).
    """
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    offenders = []
    targets = [
        os.path.join(root, 'financial_dashboard', 'tabs'),
        os.path.join(root, 'financial_dashboard', 'services')
    ]

    for target in targets:
        for dirpath, dirnames, filenames in os.walk(target):
            for fname in filenames:
                if not fname.endswith('.py'):
                    continue
                fpath = os.path.join(dirpath, fname)
                rel = os.path.relpath(fpath, root)
                # Skip allowed paths within these folders
                if any(sub in rel.replace('\\','/') for sub in ALLOWED_PATH_SUBSTR):
                    continue
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        text = f.read()
                    if PATTERN.search(text):
                        offenders.append(rel)
                except Exception:
                    continue

    assert not offenders, f"Found direct yfinance usages in files: {offenders}"
