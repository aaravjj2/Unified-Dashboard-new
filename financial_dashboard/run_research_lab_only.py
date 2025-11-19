"""
Lightweight wrapper to run Research Lab specific clicker tests (tests 2-5) from clicker_research_lab.py
Produces a log file `research_lab_only_output.log`.
"""
import sys
import time
from pathlib import Path

LOG = Path(__file__).with_name('research_lab_only_output.log')

# We'll import functions by executing parts of the existing script in a controlled way.
# The full clicker_research_lab.py is designed as top-level functions; we'll call the specific tests.

import clicker_research_lab as cr

with open(LOG, 'w') as f:
    def out(s=''):
        ts = time.strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"[{ts}] {s}\n")
        f.flush()
        print(s)

    out('RESEARCH LAB ONLY TEST SUITE START')

    try:
        out('\nRunning TEST 2 (Real Data Integration)')
        ok2 = cr.test_2_research_lab_real_data()
        out('TEST 2 PASSED' if ok2 else 'TEST 2 FAILED')

        out('\nRunning TEST 3 (Factor-Based Scenarios)')
        ok3 = cr.test_3_factor_scenarios()
        out('TEST 3 PASSED' if ok3 else 'TEST 3 FAILED')

        out('\nRunning TEST 4 (Historical Presets)')
        ok4 = cr.test_4_historical_presets()
        out('TEST 4 PASSED' if ok4 else 'TEST 4 FAILED')

        out('\nRunning TEST 5 (Portfolio Integration)')
        ok5 = cr.test_5_portfolio_integration()
        out('TEST 5 PASSED' if ok5 else 'TEST 5 FAILED')

        passed = sum([1 for v in (ok2, ok3, ok4, ok5) if v])
        out(f"\nSUMMARY: {passed}/4 tests passed")
    except Exception as e:
        out(f'ERROR running tests: {e}')
        raise

    out('\nRESEARCH LAB ONLY TEST SUITE COMPLETE')
