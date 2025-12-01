"""Simple file-based lock helper for weekly pipeline runs.
Provides acquire_lock(name) -> bool and release_lock(name).
"""
import os
import time
import json
import psutil

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LOCK_DIR = os.path.join(BASE, 'locks')
os.makedirs(LOCK_DIR, exist_ok=True)

def _lock_path(name='weekly'):
    return os.path.join(LOCK_DIR, f"{name}.lock")

def acquire_lock(name='weekly', timeout=60*60):
    p = _lock_path(name)
    try:
        if os.path.exists(p):
            with open(p, 'r') as fh:
                info = json.load(fh)
            pid = info.get('pid')
            start = info.get('start', 0)
            # if process is alive and started recently, fail
            if pid and psutil.pid_exists(pid):
                return False
            # stale lock: remove
            try:
                os.remove(p)
            except Exception:
                pass
        info = {'pid': os.getpid(), 'start': time.time(), 'name': name}
        with open(p, 'w') as fh:
            json.dump(info, fh)
        return True
    except Exception:
        return False

def release_lock(name='weekly'):
    p = _lock_path(name)
    try:
        if os.path.exists(p):
            os.remove(p)
            return True
    except Exception:
        pass
    return False

def lock_status(name='weekly'):
    p = _lock_path(name)
    if not os.path.exists(p):
        return {'locked': False}
    try:
        import json
        with open(p, 'r') as fh:
            info = json.load(fh)
        pid = info.get('pid')
        info['alive'] = psutil.pid_exists(pid) if pid else False
        info['locked'] = True
        return info
    except Exception:
        return {'locked': True}
