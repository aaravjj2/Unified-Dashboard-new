import { test, expect } from '@playwright/test';

// Playwright E2E template for ML Integration Lab subtabs
// This is a scaffold: it checks tab rendering, basic interactions, and takes
// a snapshot. Replace selectors with project-specific ids when wiring.

test.describe('ML Integration Lab - render & basic interactions', () => {
  test('renders ML lab main page and subtabs', async ({ page }) => {
    // NB: Do not start or restart the app here. The test assumes a running
    // dashboard instance will be provided by the test harness.
    await page.goto('http://localhost:8050/ml_integration_lab');
    await expect(page).toHaveTitle(/Unified/i);

    // Check main container
    const main = await page.locator('#ml-integration-lab');
    await expect(main).toBeVisible({ timeout: 2000 });

    // Verify subtabs exist (placeholders)
    const subtabs = ['ML Predictions', 'Feature Importance', 'Model Metrics', 'Strategy Recommendations', 'User Feedback'];
    for (const label of subtabs) {
      await expect(page.getByText(label)).toHaveCount(1);
    }

    // Basic clicker: open Predictions and take snapshot
    await page.getByText('ML Predictions').click();
    await expect(page.getByText('ML Predictions')).toBeVisible();
    await page.screenshot({ path: 'tests/playwright/screenshots/ml_predictions_placeholder.png' });
  });
});
