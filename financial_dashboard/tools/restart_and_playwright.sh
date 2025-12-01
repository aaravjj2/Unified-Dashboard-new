#!/usr/bin/env bash
# Restart the market dashboard with sanitized keys and run Playwright smoke test.
set -euo pipefail
# create sanitized env
python3 - <<PY
from pathlib import Path
p = Path('keys.env').read_text()
out = []
for line in p.splitlines():
    s=line.strip()
    if not s or s.startswith('#'):
        continue
    if '=' not in s:
        continue
    k,v = s.split('=',1)
    k=k.strip(); v=v.strip()
    if (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
        v = v[1:-1]
    out.append(f"{k}={v}")
Path('/tmp/keys.sanitized.env').write_text('\n'.join(out)+"\n")
print('wrote /tmp/keys.sanitized.env')
PY
# stop existing dashboard
pkill -f market_dashboard.py || true
sleep 1
# start the dashboard with sanitized env and log
set -o allexport; source /tmp/keys.sanitized.env; set +o allexport
nohup python3 -u /mnt/c/Aarav/fin_env/Dash/market_dashboard.py > /tmp/market_dashboard.log 2>&1 &
# wait a bit for server to start
sleep 2
# run playwright test harness
python3 -u dev_tools/playwright_tabs_test.py

echo "Playwright run complete. Artifacts in /tmp/dash_tab_screens and /tmp/market_dashboard.log"
