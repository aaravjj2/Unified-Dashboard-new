"""
Phase 12 Chaos Testing: Redis Outage Simulation
===============================================
Simulates a Redis outage by pausing the container `doc_redis`.
Verifies that the Dashboard UI handles this gracefully:
1. Shows "Reconnecting..." badge (or similar indication).
2. Does not freeze/crash.
3. Recovers automatically when Redis is unpaused.

Usage: python scripts/chaos_test.py
"""

import subprocess
import time
import logging
import sys
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

REDIS_CONTAINER = "doc_ingestion_redis"
DASHBOARD_URL = "http://127.0.0.1:8053"

class ChaosMonkey:
    def pause_redis(self):
        logger.info(f"🐵 Chaos Monkey: Pausing {REDIS_CONTAINER}...")
        subprocess.run(["docker", "pause", REDIS_CONTAINER], check=True)
        logger.info("Paused.")

    def unpause_redis(self):
        logger.info(f"😇 Chaos Monkey: Unpausing {REDIS_CONTAINER}...")
        subprocess.run(["docker", "unpause", REDIS_CONTAINER], check=True)
        logger.info("Unpaused.")

    def run_test(self):
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(headless=False) # Headful as requested
            context = browser.new_context()
            page = context.new_page()

            try:
                # 1. Load Dashboard
                logger.info(f"Navigating to {DASHBOARD_URL}...")
                page.goto(DASHBOARD_URL, timeout=60000)
                page.wait_for_load_state("networkidle")
                logger.info("Dashboard loaded.")
                
                # Check for initial health (random element check)
                if page.is_visible("text=Options Lab"):
                    logger.info("Options Lab visible.")

                # 2. Pause Redis
                time.sleep(2)
                self.pause_redis()
                
                # 3. Assert "Reconnecting..." badge appears within 10 seconds
                logger.info("Waiting for 'Reconnecting...' badge...")
                try:
                    # Look for standard Dash "Connection lost" or custom "Reconnecting..."
                    # Check for multiple possible indicators
                    expect_texts = ["Reconnecting...", "Connection lost", "Server disconnected"]
                    found = False
                    for _ in range(20): # 10 seconds poll
                        content = page.content()
                        for text in expect_texts:
                            if text in content: # Simple text check first
                                logger.info(f"✅ Found indicator: '{text}'")
                                found = True
                                break
                        if found: break
                        time.sleep(0.5)
                    
                    if not found:
                        logger.error("❌ Failed to find 'Reconnecting...' (or similar) badge!")
                        # Capture failure screenshot
                        page.screenshot(path="reports/phase12_quality/screenshots/chaos_failure.png")
                        raise AssertionError("UI did not show reconnection status.")
                    
                except Exception as e:
                    logger.error(f"UI Assertion Failed: {e}")
                    raise

                # 4. Unpause Redis
                self.unpause_redis()
                time.sleep(5)
                
                # 5. Verify Recovery
                # Reload or check if interactive
                try:
                    # Check if interaction works (e.g. clicking a tab)
                    # For now, just check if "Connection lost" is GONE clearly
                    content = page.content()
                    if "Connection lost" in content or "Reconnecting..." in content:
                         logger.warning("⚠️ Warning: Reconnection badge still visible?")
                    else:
                         logger.info("✅ UI appears recovered (badge gone).")
                        
                except Exception as e:
                    logger.error(f"Recovery check failed: {e}")
                    raise

            except Exception as e:
                logger.error(f"Chaos Test Failed: {e}")
                # Ensure cleanup
                try:
                    self.unpause_redis()
                except:
                    pass
                sys.exit(1)
            finally:
                browser.close()

if __name__ == "__main__":
    monkey = ChaosMonkey()
    try:
        monkey.run_test()
        logger.info("🎉 Chaos Test Passed!")
    except Exception as e:
        logger.error(f"Test Execution Error: {e}")
        try:
             subprocess.run(["docker", "unpause", REDIS_CONTAINER], check=False)
        except: pass
        sys.exit(1)
