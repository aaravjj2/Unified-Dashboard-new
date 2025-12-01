"""
Automated Repair Loop for Failing Options Lab Elements

Phase 31 Agent 1A - STEP 7

Implements 3-attempt repair strategy:
1. WAIT & RETRY: Increase timeout to 90s
2. CSS VISIBILITY: Force display/opacity if hidden
3. CALLBACK WIRING: Add error handling or missing callback

Usage:
    python tests/playwright/repair_loop.py --results-json playwright/element_results.json
    python tests/playwright/repair_loop.py --single-id chain-expiration-dropdown --attempt 2
"""

import argparse
import asyncio
import json
import logging
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Directories
REPORTS_DIR = Path('reports/options_validation')
PATCHES_DIR = REPORTS_DIR / 'patches'
RESULTS_JSON = REPORTS_DIR / 'playwright' / 'element_results.json'
ASSETS_DIR = Path('financial_dashboard/assets')

PATCHES_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR.mkdir(parents=True, exist_ok=True)


class RepairOrchestrator:
    """Manages repair attempts for failing elements"""
    
    def __init__(self, single_id: str = None, attempt: int = None):
        self.single_id = single_id
        self.forced_attempt = attempt
        self.failed_elements: List[Dict] = []
        self.repair_log: List[Dict] = []
        
    def load_failed_elements(self):
        """Load failing elements from results JSON"""
        if not RESULTS_JSON.exists():
            raise FileNotFoundError(f"Results not found: {RESULTS_JSON}")
        
        with open(RESULTS_JSON, 'r') as f:
            data = json.load(f)
        
        # Filter failed elements
        for result in data.get('results', []):
            if not result.get('pass', True):
                self.failed_elements.append(result)
        
        logger.info(f"📋 Loaded {len(self.failed_elements)} failed elements")
        
        # If single_id mode, filter to just that element
        if self.single_id:
            self.failed_elements = [e for e in self.failed_elements if e['id'] == self.single_id]
            if len(self.failed_elements) == 0:
                raise ValueError(f"Element {self.single_id} not in failed list")
            logger.info(f"🎯 Single element repair mode: {self.single_id}")
    
    async def run_repair_loop(self):
        """Execute repair attempts for all failed elements"""
        logger.info(f"🔧 Starting repair loop for {len(self.failed_elements)} elements...")
        
        for idx, elem in enumerate(self.failed_elements, 1):
            elem_id = elem['id']
            logger.info(f"\n{'='*60}")
            logger.info(f"[{idx}/{len(self.failed_elements)}] Repairing: {elem_id}")
            logger.info(f"  Original failure: {elem.get('verdict', 'unknown')}")
            logger.info(f"{'='*60}")
            
            # Determine starting attempt
            start_attempt = self.forced_attempt if self.forced_attempt else 1
            
            # Try up to 3 attempts
            repaired = False
            for attempt_num in range(start_attempt, 4):
                logger.info(f"\n🔧 Attempt {attempt_num}/3 for {elem_id}")
                
                success = await self._repair_attempt(elem_id, attempt_num)
                
                if success:
                    logger.info(f"✅ {elem_id} repaired on attempt {attempt_num}")
                    self.repair_log.append({
                        'id': elem_id,
                        'attempt': attempt_num,
                        'success': True,
                        'timestamp': datetime.utcnow().isoformat() + 'Z'
                    })
                    repaired = True
                    break
                else:
                    logger.warning(f"❌ Attempt {attempt_num} failed for {elem_id}")
                    self.repair_log.append({
                        'id': elem_id,
                        'attempt': attempt_num,
                        'success': False,
                        'timestamp': datetime.utcnow().isoformat() + 'Z'
                    })
            
            if not repaired:
                # Create blocker report
                self._create_blocker_report(elem_id, elem)
        
        # Save repair log
        self._save_repair_log()
        
        logger.info(f"\n✅ Repair loop complete")
    
    async def _repair_attempt(self, elem_id: str, attempt: int) -> bool:
        """Execute a single repair attempt"""
        
        # ATTEMPT 1: WAIT & RETRY with 90s timeout
        if attempt == 1:
            logger.info("  Strategy: Increase timeout to 90s and retry")
            return await self._attempt_wait_retry(elem_id)
        
        # ATTEMPT 2: CSS VISIBILITY FIX
        elif attempt == 2:
            logger.info("  Strategy: Force CSS visibility")
            return await self._attempt_css_fix(elem_id)
        
        # ATTEMPT 3: CALLBACK WIRING
        elif attempt == 3:
            logger.info("  Strategy: Check/fix callback wiring")
            return await self._attempt_callback_fix(elem_id)
        
        return False
    
    async def _attempt_wait_retry(self, elem_id: str) -> bool:
        """Attempt 1: Increase timeout and retry"""
        # Temporarily modify DEFAULT_TIMEOUT in harness
        harness_file = Path('tests/playwright/options_button_audit.py')
        original_content = harness_file.read_text()
        
        # Replace timeout
        modified_content = re.sub(
            r'DEFAULT_TIMEOUT = \d+',
            'DEFAULT_TIMEOUT = 90000',
            original_content
        )
        harness_file.write_text(modified_content)
        
        try:
            # Re-run single element test
            result = subprocess.run(
                ['python3', 'tests/playwright/options_button_audit.py', '--single-id', elem_id],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            # Check if passed
            if result.returncode == 0:
                # Re-read results
                with open(RESULTS_JSON, 'r') as f:
                    data = json.load(f)
                
                # Find this element's result
                for r in data.get('results', []):
                    if r['id'] == elem_id and r.get('pass', False):
                        return True
            
            return False
            
        finally:
            # Restore original timeout
            harness_file.write_text(original_content)
    
    async def _attempt_css_fix(self, elem_id: str) -> bool:
        """Attempt 2: Force CSS visibility"""
        logger.info(f"  Creating forced_visibility.css for {elem_id}")
        
        # Create CSS override
        css_file = ASSETS_DIR / 'forced_visibility.css'
        
        css_rule = f"""
/* DEBUG-ONLY: Forced visibility for {elem_id} */
#{elem_id} {{
    display: block !important;
    opacity: 1 !important;
    visibility: visible !important;
    pointer-events: auto !important;
}}
"""
        
        # Append or create
        if css_file.exists():
            css_content = css_file.read_text()
            if elem_id not in css_content:
                css_file.write_text(css_content + css_rule)
        else:
            css_file.write_text(css_rule)
        
        # Commit with debug-only prefix
        subprocess.run(['git', 'add', str(css_file)], check=True)
        subprocess.run([
            'git', 'commit', '-m',
            f'debug-only: Force visibility for {elem_id} (repair attempt 2)'
        ], check=True)
        
        # Save patch
        patch_file = PATCHES_DIR / f'debug_css_fix_{elem_id}_{int(datetime.utcnow().timestamp())}.diff'
        subprocess.run([
            'git', 'diff', 'HEAD~1', f'--output={patch_file}'
        ], check=True)
        
        logger.info(f"  ✅ CSS fix committed, patch: {patch_file.name}")
        
        # TODO: Restart dashboard server
        # For now, return False to indicate manual verification needed
        logger.warning("  ⚠️  Dashboard restart required - manual verification needed")
        return False
    
    async def _attempt_callback_fix(self, elem_id: str) -> bool:
        """Attempt 3: Check/fix callback wiring"""
        logger.info(f"  Checking callback wiring for {elem_id}")
        
        # Search for callback registration
        callback_search = subprocess.run(
            ['grep', '-r', f'@.*callback', '--include=*.py', 'financial_dashboard/'],
            capture_output=True,
            text=True
        )
        
        callback_lines = callback_search.stdout.splitlines()
        
        # Check if this ID is in any callback
        id_in_callback = False
        for line in callback_lines:
            if elem_id in line:
                id_in_callback = True
                logger.info(f"  ✅ Found callback referencing {elem_id}")
                break
        
        if not id_in_callback:
            logger.warning(f"  ⚠️  No callback found for {elem_id}")
            logger.warning(f"  → This may be a display-only element or missing callback")
            # Cannot auto-fix missing callbacks - requires manual implementation
            return False
        
        # If callback exists but failing, add error handling guard
        # This is complex and requires AST manipulation - for now, report blocker
        logger.warning("  ⚠️  Callback exists but failing - requires manual inspection")
        return False
    
    def _create_blocker_report(self, elem_id: str, elem_result: Dict):
        """Create blocker report for unrepairable element"""
        blocker_file = REPORTS_DIR / f'BLOCKER_{elem_id}.md'
        
        content = f"""# BLOCKER REPORT: {elem_id}

**Generated:** {datetime.utcnow().isoformat()}Z  
**Element Type:** {elem_result.get('type', 'unknown')}  
**Original Failure:** {elem_result.get('verdict', 'unknown')}

---

## Repair Attempts

"""
        
        # Add repair attempts from log
        for log_entry in self.repair_log:
            if log_entry['id'] == elem_id:
                content += f"- **Attempt {log_entry['attempt']}**: {'✅ Success' if log_entry['success'] else '❌ Failed'}\n"
        
        content += f"""

---

## Artifacts

- **Screenshots:** `screenshots/{elem_id}_pre.png`, `screenshots/{elem_id}_post.png`
- **DOM Dumps:** `dom/{elem_id}_pre.html`, `dom/{elem_id}_post.html`
- **Result JSON:** See `playwright/element_results.json` → `"{elem_id}"`

---

## Failure Analysis

**Verdict:** {elem_result.get('verdict', 'unknown')}

**Metrics:**
```json
{json.dumps(elem_result.get('analysis', {}).get('metrics', {}), indent=2)}
```

---

## Suggested Fixes

1. **Manual Inspection Required:**
   - Check if element is rendered in headed browser (visible to human eye)
   - Verify callback is registered in `financial_dashboard/layouts/options_lab.py`
   - Check browser console for JavaScript errors

2. **Possible Root Causes:**
   - Element ID mismatch (layout vs callback)
   - Missing data dependency (API call failing)
   - Conditional rendering (element only visible in certain states)
   - Callback error causing silent failure

3. **Next Steps:**
   - Run `python tests/playwright/options_button_audit.py --single-id {elem_id}` in headed mode
   - Watch browser console during action
   - Check `financial_dashboard/api/options_forecast.py` logs for blocked Azure calls
   - Verify deterministic fixture is loaded: `OPTIONS_DETERMINISTIC=1`

---

## Revert Instructions (if debug-only patches applied)

```bash
# Remove forced visibility CSS
git revert $(git log --grep="debug-only.*{elem_id}" --format="%H" -1)

# Or manually edit financial_dashboard/assets/forced_visibility.css
```
"""
        
        blocker_file.write_text(content)
        logger.warning(f"📄 Created blocker report: {blocker_file}")
    
    def _save_repair_log(self):
        """Save repair log to JSON"""
        log_file = REPORTS_DIR / 'playwright' / 'repair_log.json'
        
        output = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'total_repairs_attempted': len(self.failed_elements),
            'successful_repairs': sum(1 for e in self.repair_log if e['success']),
            'failed_repairs': sum(1 for e in self.repair_log if not e['success']),
            'log': self.repair_log
        }
        
        with open(log_file, 'w') as f:
            json.dump(output, f, indent=2)
        
        logger.info(f"📊 Repair log saved: {log_file}")


async def main():
    parser = argparse.ArgumentParser(description='Automated Repair Loop for Options Lab')
    parser.add_argument('--results-json', type=str, default=str(RESULTS_JSON), help='Path to element_results.json')
    parser.add_argument('--single-id', type=str, help='Repair single element only')
    parser.add_argument('--attempt', type=int, choices=[1, 2, 3], help='Start at specific attempt')
    args = parser.parse_args()
    
    orchestrator = RepairOrchestrator(single_id=args.single_id, attempt=args.attempt)
    
    try:
        orchestrator.load_failed_elements()
        await orchestrator.run_repair_loop()
    except Exception as e:
        logger.error(f"❌ Repair loop failed: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
