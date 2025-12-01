#!/usr/bin/env bash
set -euo pipefail
PY=/usr/bin/env python3
$PY dev_tools/check_results_area.py
echo "post-change checks passed"
