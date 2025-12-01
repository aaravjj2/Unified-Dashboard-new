#!/usr/bin/env python3
"""Agent-2A standby integration runner

Polls for callback-fix markers and, upon detection, runs the headed Playwright
integration id->page scan and collects artifacts. Non-invasive: does not edit
any callback-defining files.

Usage: python tools/agent2a/standby_integration_runner.py
"""
import os
import time
import subprocess
import socket
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports" / "agent2a"
PLAYWRIGHT_SCAN = ROOT / "tests" / "playwright" / "id_page_scan_headed.py"
RUN_WITH_ADMIN = ROOT / "run_with_admin.py"
MOCK_BENTO = ROOT / "services" / "mock_bento" / "app.py"

POLL_INTERVAL = int(os.environ.get("AGENT2A_POLL_INTERVAL", 15))
TIMEOUT_SECONDS = int(os.environ.get("AGENT2A_TIMEOUT_SECONDS", 6 * 60 * 60))


def ensure_dirs():
    for p in (REPORTS / "patches", REPORTS / "diagnostics", REPORTS / "playwright", REPORTS / "logs", REPORTS / "integration_bundle", REPORTS / "readme"):
        p.mkdir(parents=True, exist_ok=True)


def port_open(host, port):
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except Exception:
        return False


def ensure_mock_bento():
    info_path = REPORTS / "diagnostics" / "mock_bento_pid.txt"
    # If port 5001 responds, try to capture PID via ss; else start service
    if port_open("127.0.0.1", 5001):
        # try to discover pid via ss
        try:
            out = subprocess.check_output(["ss", "-ltnp"]).decode(errors="ignore")
            for line in out.splitlines():
                if ":5001" in line:
                    # extract pid=NNNN
                    import re

                    m = re.search(r"pid=(\d+)", line)
                    if m:
                        pid = m.group(1)
                        info_path.write_text(pid + "\n")
                        return pid
        except Exception:
            pass
        info_path.write_text("running\n")
        return "running"

    # start mock bento
    logfile = REPORTS / "logs" / "mock_bento_standby.log"
    logfile.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["nohup", "python", str(MOCK_BENTO)]
    with open(logfile, "ab") as out:
        p = subprocess.Popen(cmd, stdout=out, stderr=out)
    time.sleep(1)
    pid = p.pid
    (REPORTS / "diagnostics").mkdir(exist_ok=True, parents=True)
    (REPORTS / "diagnostics" / "mock_bento_pid.txt").write_text(str(pid) + "\n")
    return pid


def ensure_run_with_admin():
    # ensure run_with_admin is running on 8029
    pidfile = REPORTS / "diagnostics" / "dash_with_admin_pid.txt"
    if port_open("127.0.0.1", 8029):
        # attempt to find pid
        try:
            out = subprocess.check_output(["pgrep", "-f", "run_with_admin.py"]).decode().strip()
            if out:
                pidfile.write_text(out.splitlines()[0] + "\n")
                return out.splitlines()[0]
        except Exception:
            pidfile.write_text("running\n")
            return "running"

    logfile = REPORTS / "logs" / "dash_with_admin_standby.log"
    with open(logfile, "ab") as out:
        p = subprocess.Popen(["nohup", "python", str(RUN_WITH_ADMIN)], stdout=out, stderr=out)
    time.sleep(1)
    pid = p.pid
    pidfile.parent.mkdir(parents=True, exist_ok=True)
    pidfile.write_text(str(pid) + "\n")
    return pid


def check_markers():
    # returns (found, marker_path or message)
    candidate1 = ROOT / "reports" / "duplicates_fix" / "PHASE_DUPLICATE_CALLBACKS_SUCCESS"
    candidate2 = ROOT / "CALLBACKS_FIXED"
    if candidate1.exists():
        return True, str(candidate1)
    if candidate2.exists():
        return True, str(candidate2)
    # also check for file with message CALLBACKS_FIXED:<hash>
    # also check for files named CALLBACKS_FIXED or CALLBACKS_FIXED:<hash> in repo root
    for p in ROOT.glob("CALLBACKS_FIXED*"):
        if p.exists():
            return True, str(p)
    return False, None


def run_playwright_scan(base_url="http://127.0.0.1:8029"):
    env = os.environ.copy()
    env["ADMIN_BASE"] = base_url
    out_dir = REPORTS / "playwright" / "id_scan"
    out_dir.mkdir(parents=True, exist_ok=True)
    log = REPORTS / "logs" / "standby_id_scan.log"
    with open(log, "ab") as f:
        # run the existing id scan script
        p = subprocess.Popen(["python3", str(PLAYWRIGHT_SCAN)], env=env, stdout=f, stderr=f)
        p.wait()
    return p.returncode


def run_integration_sequence():
    REPORTS.mkdir(parents=True, exist_ok=True)
    # Ensure admin dashboard helper running
    ensure_run_with_admin()
    # Ensure mock bento
    ensure_mock_bento()
    # Run Playwright id->page scan headed
    rc = run_playwright_scan(base_url="http://127.0.0.1:8029")
    (REPORTS / "diagnostics" / "integration_run_exit_code.txt").write_text(str(rc) + "\n")
    return rc


def main():
    ensure_dirs()
    # Ensure mock Bento now
    ensure_mock_bento()
    # Start admin helper if not running
    ensure_run_with_admin()

    start = time.time()
    deadline = start + TIMEOUT_SECONDS

    print(f"Agent-2A standby runner started. Polling every {POLL_INTERVAL}s until {TIMEOUT_SECONDS}s timeout.")
    while time.time() < deadline:
        found, marker = check_markers()
        if found:
            print("Marker detected:", marker)
            # run integration
            rc = run_integration_sequence()
            print("Integration run completed with rc=", rc)
            # save a final stamp
            (REPORTS / "diagnostics" / "integration_last_run.txt").write_text(f"marker={marker}\nrc={rc}\n")
            return 0
        time.sleep(POLL_INTERVAL)

    # timed out
    timeout_file = REPORTS / "diagnostics" / "STANDBY_TIMEOUT.md"
    timeout_file.write_text("Agent-2A standby timed out after polling for callback fixes.\n")
    print("Standby timed out; wrote diagnostics")
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
