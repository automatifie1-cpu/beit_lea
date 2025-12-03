# WhatsApp API Configuration Template
# Copy this file to config.py and update with your actual values

WHATSAPP_TOKEN = "YOUR_WHATSAPP_TOKEN_HERE"
PHONE_NUMBER_ID = "YOUR_PHONE_NUMBER_ID_HERE"  
BOT_PHONE_NUMBER = "+YOUR_BOT_PHONE_NUMBER_HERE"
VERIFY_TOKEN = "YOUR_VERIFY_TOKEN_HERE"

# OpenAI API Configuration
OPENAI_API_KEY = "YOUR_OPENAI_API_KEY"
MODEL = "gpt-4-turbo"

# Redis Configuration (for shared state across Gunicorn workers)
# Leave as defaults for local development, update for production
REDIS_HOST = "localhost"  # or your Redis server IP
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_PASSWORD = None  # Set if your Redis requires authentication

# Server Configuration
PORT = 8000
DEBUG = True

# Instructions:
# 1. Copy this file: cp config_template.py config.py
# 2. Update config.py with your actual API credentials
# 3. Never commit config.py to git (it's in .gitignore)