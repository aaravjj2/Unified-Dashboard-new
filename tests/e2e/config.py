"""
E2E Testing Configuration
==========================
Central configuration for all end-to-end tests.
"""
import os
from pathlib import Path

# Dashboard URL
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:8051")

# Test output directory
TEST_OUTPUT_DIR = Path(__file__).parent.parent.parent / ".test-output"
TEST_OUTPUT_DIR.mkdir(exist_ok=True)

# Local LLM configuration (Ollama)
LLM_URL = os.getenv("LLM_URL", "http://localhost:11434/api/generate")
LLM_MODEL = os.getenv("LLM_MODEL", "mistral:7b")  # Changed to available model

# Playwright configuration
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
TIMEOUT = int(os.getenv("TEST_TIMEOUT", "60000"))  # milliseconds
VIEWPORT_WIDTH = 1920
VIEWPORT_HEIGHT = 1080

# Test areas mapping
TEST_AREAS = {
    "command_center": {
        "tab_text": "Command Center",
        "required_fields": ["portfolioValue", "todaysPnL", "marketStatus"],
        "output_file": TEST_OUTPUT_DIR / "command-center.json",
        "ai_output_file": TEST_OUTPUT_DIR / "command-center-ai.json"
    },
    "portfolio": {
        "tab_text": "Portfolio",
        "required_fields": ["sharpe", "drawdown", "beta", "positionsCount"],
        "output_file": TEST_OUTPUT_DIR / "portfolio.json",
        "ai_output_file": TEST_OUTPUT_DIR / "portfolio-ai.json"
    },
    "volatility": {
        "tab_text": "Volatility Lab",
        "required_fields": ["ivSurfaceDataExists", "colorLegendVisible"],
        "output_file": TEST_OUTPUT_DIR / "volatility.json",
        "ai_output_file": TEST_OUTPUT_DIR / "volatility-ai.json"
    },
    "options": {
        "tab_text": "Options Lab",
        "required_fields": ["chainRows", "greeksVisible", "mockDataLoaded"],
        "output_file": TEST_OUTPUT_DIR / "options.json",
        "ai_output_file": TEST_OUTPUT_DIR / "options-ai.json"
    }
}

print(f"✅ Test config loaded: {DASHBOARD_URL}")
print(f"   Output dir: {TEST_OUTPUT_DIR}")
print(f"   LLM: {LLM_URL} ({LLM_MODEL})")
