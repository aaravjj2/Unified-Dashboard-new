"""
Market Trends E2E Job Trigger Test

Purpose: Reproduce the manual failure where job trigger produces "Job not found" error.
This test MUST fail to prove the issue exists before implementing a fix.

Zero-tolerance criteria:
- Test must click the actual UI control that triggers analysis
- Test must capture the job ID (or absence thereof)
- Test must verify job status via backend API
- On failure, screenshot and logs must be captured
"""
import pytest
import requests
import time
from playwright.sync_api import Page, expect


BASE_URL = "http://localhost:8050"


def test_market_trends_run_analysis_job_e2e(page: Page):
    """
    E2E test: Click "Run Full Analysis" button and verify job is created and trackable.
    
    Expected to FAIL initially (reproducing manual failure).
    """
    page.goto(BASE_URL)
    page.wait_for_selector('a:has-text("Market Trends")', timeout=10000)
    
    # Navigate to Market Trends tab
    page.locator('a:has-text("Market Trends")').click()
    page.wait_for_selector('h3:has-text("Market Trends")', timeout=10000)
    
    print("📍 Market Trends page loaded")
    
    # Wait for UI to fully render
    page.wait_for_timeout(2000)
    
    # Attempt to locate the Run Analysis button (try multiple selectors)
    run_button = None
    selectors_to_try = [
        'button[data-test="run-analysis"]',
        'button:has-text("Run Full Analysis")',
        'button:has-text("Run Analysis")',
        '#run-btn',
        'button#run-btn',
    ]
    
    for selector in selectors_to_try:
        if page.locator(selector).count() > 0:
            run_button = page.locator(selector)
            print(f"✓ Found run button with selector: {selector}")
            break
    
    assert run_button is not None, "CRITICAL: Could not find Run Analysis button with any known selector"
    
    # Verify button is visible and enabled
    expect(run_button).to_be_visible(timeout=5000)
    expect(run_button).to_be_enabled()
    
    print("📍 About to click Run Full Analysis button...")
    
    # Click the button to trigger job
    run_button.click()
    
    print("✓ Button clicked, waiting for job response...")
    
    # Wait for UI response - look for job ID display or error message
    page.wait_for_timeout(3000)
    
    # Capture screenshot immediately after button click
    page.screenshot(path='test-artifacts/market_trends_run_analysis_job_attempt.png', full_page=True)
    
    # Try to locate job ID in UI (multiple possible locations)
    job_id = None
    job_id_selectors = [
        '#status',  # Primary status div where "Started job ..." message appears
        '[data-testid="job-id"]',
        '[data-job-id]',
        'text=/Job ID:.*/',
        'text=/job.*[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/',  # UUID pattern
        'text=/job_[0-9]+/',  # Timestamp pattern: job_1729635984670
        'text=/Started job/',  # Look for status message
    ]
    
    for selector in job_id_selectors:
        if page.locator(selector).count() > 0:
            job_text = page.locator(selector).first.inner_text()
            print(f"✓ Found job ID element with selector '{selector}': {job_text}")
            # Extract UUID pattern
            import re
            uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
            match = re.search(uuid_pattern, job_text)
            if match:
                job_id = match.group(0)
                print(f"✓ Extracted job ID (UUID): {job_id}")
                break
            # Try timestamp pattern: job_1729635984670
            timestamp_pattern = r'job_\d{13}'
            match = re.search(timestamp_pattern, job_text)
            if match:
                job_id = match.group(0)
                print(f"✓ Extracted job ID (timestamp): {job_id}")
                break
    
    # Check for error toasts/messages
    error_messages = []
    error_selectors = [
        '[role="alert"]',
        '.notification',
        '.error-message',
        'text=/error/i',
        'text=/not found/i',
    ]
    
    for selector in error_selectors:
        if page.locator(selector).count() > 0:
            for i in range(page.locator(selector).count()):
                error_text = page.locator(selector).nth(i).inner_text()
                if error_text.strip():
                    error_messages.append(error_text)
    
    if error_messages:
        print(f"⚠️  ERROR MESSAGES DETECTED: {error_messages}")
    
    # CRITICAL ASSERTION 1: Job ID must be present
    assert job_id is not None, (
        f"FAILURE: No job ID found in UI after clicking Run Analysis.\n"
        f"Error messages: {error_messages}\n"
        f"Screenshot saved to: test-artifacts/market_trends_run_analysis_job_attempt.png"
    )
    
    print(f"✓ Job ID captured from UI: {job_id}")
    
    # CRITICAL ASSERTION 2: Job must be trackable via backend API
    job_status_url = f"{BASE_URL}/api/jobs/{job_id}"
    
    print(f"📍 Checking job status at: {job_status_url}")
    
    # Allow backend time to register job
    time.sleep(2)
    
    try:
        response = requests.get(job_status_url, timeout=10)
        print(f"✓ Job status API response: {response.status_code}")
        print(f"✓ Response body: {response.text[:500]}")
        
        # CRITICAL ASSERTION 3: Job endpoint must return 200
        assert response.status_code == 200, (
            f"FAILURE: Job status endpoint returned {response.status_code} instead of 200.\n"
            f"Job ID: {job_id}\n"
            f"Response: {response.text}\n"
            f"This indicates job was not properly registered in backend."
        )
        
        job_data = response.json()
        
        # CRITICAL ASSERTION 4: Job must have a status field
        assert "status" in job_data, (
            f"FAILURE: Job response missing 'status' field.\n"
            f"Job ID: {job_id}\n"
            f"Response: {job_data}"
        )
        
        print(f"✅ SUCCESS: Job {job_id} found with status: {job_data.get('status')}")
        
    except requests.exceptions.RequestException as e:
        pytest.fail(
            f"FAILURE: Could not connect to job status API.\n"
            f"Job ID: {job_id}\n"
            f"URL: {job_status_url}\n"
            f"Error: {str(e)}"
        )
    
    # If we got here, all assertions passed
    page.screenshot(path='test-artifacts/market_trends_run_analysis_job_success.png', full_page=True)
