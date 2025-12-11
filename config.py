import os
from pathlib import Path

# Load .env file if exists (for local development)
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv not installed (Lambda environment)

# Google sheets configuration
APPS_SCRIPT_URL = os.environ.get("APPS_SCRIPT_URL", "")

# Firebase Configuration
KEY_PATH = os.environ.get("KEY_PATH", "")

# WhatsApp API Configuration
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "")
BOT_PHONE_NUMBER = os.environ.get("BOT_PHONE_NUMBER", "")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "")

# Beit Leah URL
BEIT_LEAH_URL = os.environ.get("BEIT_LEAH_URL", "")