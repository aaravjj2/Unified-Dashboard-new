"""Small helper to schedule background jobs safely when the shared runner isn't available.

This module provides start_background_job_safe which prefers SH.start_background_job
but falls back to starting a daemon thread when SH is missing or not initialized
(common in some test or import ordering scenarios).
"""
import threading
import time
import logging
import traceback
try:
    import _shared as SH
except Exception:
    SH = None

logger = logging.getLogger(__name__)


def start_background_job_safe(target, args=(), kwargs=None, job_name=None):
    """Start a background job via SH if available, else run in a daemon thread.

    Returns a job id string. When falling back to a thread the returned id has
    the form 'local-thread-<timestamp>'.
    """
    if kwargs is None:
        kwargs = {}

    # Prefer SH.start_background_job when present
    try:
        if SH is not None and hasattr(SH, 'start_background_job'):
            try:
                return SH.start_background_job(target, args=args, kwargs=kwargs, job_name=job_name)
            except NameError as e:
                # Logging bug in _shared.py - job actually started successfully
                logger.warning(f"SH.start_background_job succeeded but raised NameError (logging bug): {e}")
                # Job was created successfully, extract job_id from JOBS dict
                if hasattr(SH, 'JOBS') and SH.JOBS:
                    return list(SH.JOBS.keys())[-1]
                # If can't get real ID, fall through to fallback
                logger.error("Could not extract job_id from SH.JOBS after NameError")
            except Exception:
                logger.exception("SH.start_background_job raised an exception, falling back to local thread")
    except Exception:
        # Defensive: if SH access raises for some reason, ignore and fallback
        logger.exception("Error checking SH.start_background_job, falling back to local thread")

    # Fallback: start a local daemon thread and return a synthetic job id.
    jid = f"local-thread-{int(time.time()*1000)}"

    def _runner():
        try:
            logger.info(f"[fallback-job] Starting local threaded job {jid} name={job_name}")
            target(*args, **(kwargs or {}))
            logger.info(f"[fallback-job] Completed local threaded job {jid}")
        except Exception:
            logger.error(f"[fallback-job] Exception in local threaded job {jid}: {traceback.format_exc()}")

    th = threading.Thread(target=_runner, daemon=True)
    th.start()
    return jid
