import os
import sys
import logging

# Setup paths like index.py
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

PROJECT_ROOT = os.path.dirname(APP_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print(f"sys.path: {sys.path}")

try:
    from components.chatbot_ui import create_chatbot_ui, create_floating_action_button
    print("✅ Import successful via 'from components.chatbot_ui'")
except ImportError as e:
    print(f"❌ Import failed via 'from components.chatbot_ui': {e}")

try:
    from financial_dashboard.components.chatbot_ui import create_chatbot_ui
    print("✅ Import successful via 'from financial_dashboard.components.chatbot_ui'")
except ImportError as e:
    print(f"❌ Import failed via 'from financial_dashboard.components.chatbot_ui': {e}")
