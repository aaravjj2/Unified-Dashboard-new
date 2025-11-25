# LambdaTest Integration Guide

## Overview

LambdaTest is a cloud-based cross-browser testing platform that allows you to run automated tests across different browsers, operating systems, and devices. This guide explains how to use our LambdaTest integration for automated UI validation and screenshot testing.

## Setup

### 1. LambdaTest Account Setup

1. **Sign up** at [LambdaTest.com](https://www.lambdatest.com/)
2. **Get your credentials** from Account Settings > Password & Security
   - Username: Your LambdaTest username
   - Access Key: Your unique access key

### 2. Environment Configuration

Set your LambdaTest credentials as environment variables:

```bash
export LAMBDATEST_USERNAME="your_username"
export LAMBDATEST_ACCESS_KEY="your_access_key"
```

For testing without real credentials, use placeholder values:
```bash
export LAMBDATEST_USERNAME="test_user_placeholder"
export LAMBDATEST_ACCESS_KEY="test_key_placeholder"
```

## How Our Integration Works

### Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Dashboard     │    │  Lambda Test     │    │   LambdaTest    │
│   (localhost)   │◄──►│   Runner         │◄──►│   Cloud API     │
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
    ┌────▼────┐             ┌────▼────┐             ┌────▼────┐
    │ Tabs    │             │Playwright│             │Screenshot│
    │Content  │             │Browser   │             │ Storage │
    └─────────┘             └─────────┘             └─────────┘
```

### Components

1. **TestConfig**: Configuration for dashboard URL, target tabs, credentials
2. **LambdaTestIntegrator**: Handles authentication and screenshot uploads
3. **PlaywrightEngine**: Browser automation for navigation and screenshots
4. **UIValidator**: Applies CSS fixes and validates UI elements
5. **AccessibilityChecker**: WCAG compliance validation

## Running LambdaTest Validation

### Basic Usage

```bash
# Start your dashboard first
python financial_dashboard/index.py

# Run LambdaTest validation
python lambda_test_runner.py
```

### Configuration Options

Edit `lambda_test_runner.py` to customize:

```python
@dataclass
class TestConfig:
    dashboard_url: str = 'http://localhost:8051'  # Your dashboard URL
    target_tabs: List[str] = [
        'Home', 'Command Center', 'Strategy Lab', 
        'Options Lab', 'Weekly Picks', 'Monthly Picks'
    ]
    screenshot_directory: str = 'test_artifacts/lambdatest_phase24_25'
    max_retry_attempts: int = 3
    success_threshold: float = 1.0  # 100% success required
```

## What the Integration Does

### 1. **Tab Validation Loop**
- Navigates to each target tab
- Applies UI normalization (white backgrounds, black text)
- Captures screenshots
- Validates WCAG compliance
- Uploads to LambdaTest cloud

### 2. **UI Normalization**
Automatically applies CSS fixes:
```css
.form-control, .dash-input, input[type="text"] {
    background-color: white !important;
    color: black !important;
    border: 1px solid #ccc !important;
}
```

### 3. **Screenshot Management**
- **Local Storage**: `test_artifacts/lambdatest_phase24_25/`
- **Cloud Upload**: Uploaded to LambdaTest with metadata tags
- **Verification**: Confirms successful upload

### 4. **Reporting**
Generates comprehensive reports:
- `reports/PHASE_24_25_COMPLETION.md` - Executive summary
- `reports/lambda_validation.json` - Detailed metrics
- `reports/phase24_25_execution.log` - Full execution log

## Advanced Usage

### Custom Tab Testing

```python
# Test specific tabs only
config = TestConfig()
config.target_tabs = ['Weekly Picks', 'Monthly Picks']
config.dashboard_url = 'http://localhost:8050'
```

### Real LambdaTest Integration

For production use with real LambdaTest account:

```python
# Set real credentials
config.lambdatest_username = "your_real_username"
config.lambdatest_access_key = "your_real_access_key"

# The system will:
# 1. Authenticate with LambdaTest API
# 2. Upload screenshots to your LambdaTest account
# 3. Verify uploads via REST API
# 4. Generate shareable links
```

### Continuous Integration

For CI/CD pipelines:

```yaml
# .github/workflows/ui-validation.yml
name: UI Validation
on: [push, pull_request]

jobs:
  lambdatest-validation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Start Dashboard
        run: |
          python financial_dashboard/index.py &
          sleep 10
      
      - name: Run LambdaTest Validation
        env:
          LAMBDATEST_USERNAME: ${{ secrets.LAMBDATEST_USERNAME }}
          LAMBDATEST_ACCESS_KEY: ${{ secrets.LAMBDATEST_ACCESS_KEY }}
        run: python lambda_test_runner.py
      
      - name: Upload Results
        uses: actions/upload-artifact@v2
        with:
          name: lambdatest-results
          path: |
            reports/
            test_artifacts/
```

## Troubleshooting

### Common Issues

1. **Dashboard Not Accessible**
   ```
   ❌ Dashboard not accessible at http://localhost:8051
   ```
   **Solution**: Ensure dashboard is running and accessible

2. **Authentication Failed**
   ```
   ❌ LambdaTest authentication failed: 401
   ```
   **Solution**: Check your username and access key

3. **Screenshot Upload Failed**
   ```
   ❌ Upload failed: 413 - Request Entity Too Large
   ```
   **Solution**: Screenshots are automatically resized, but check file sizes

4. **React Errors in Browser**
   ```
   Error: Minified React error #31
   ```
   **Solution**: Set `DASH_TEST_SSR=false` environment variable

### Debug Mode

Enable detailed logging:

```python
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

### Planned Features

1. **Multi-Browser Testing**: Chrome, Firefox, Safari, Edge
2. **Mobile Device Testing**: iOS and Android devices
3. **Performance Metrics**: Page load times, resource usage
4. **Visual Regression**: Compare screenshots over time
5. **Accessibility Scoring**: Detailed WCAG compliance reports

### Custom Extensions

You can extend the integration:

```python
class CustomValidator(UIValidator):
    def custom_validation(self, page: Page) -> List[str]:
        # Your custom validation logic
        violations = []
        # ... validation code ...
        return violations

# Use in main validation loop
validator = CustomValidator()
results = await validator.validate_page(page)
```

## API Reference

### TestConfig
- `dashboard_url`: URL of your dashboard
- `target_tabs`: List of tab names to validate
- `screenshot_directory`: Local storage path
- `max_retry_attempts`: Retry count for failed operations
- `success_threshold`: Required success rate (0.0-1.0)

### LambdaTestIntegrator
- `authenticate()`: Validate credentials
- `upload_screenshot(path, tags)`: Upload with metadata
- `verify_upload(upload_id)`: Confirm successful upload
- `generate_validation_report()`: Create summary report

### PlaywrightEngine
- `initialize()`: Setup Chromium browser
- `navigate_to_tab(tab_name)`: Navigate to specific tab
- `capture_screenshot(filename)`: Take and save screenshot
- `get_dom_snapshot()`: Extract DOM information

This integration provides a robust foundation for automated UI testing and can be easily extended for your specific needs.