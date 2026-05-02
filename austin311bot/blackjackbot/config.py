import os

# Telegram Bot Token (Mandatory)
# Use BLACKJACK_BOT_TOKEN for consistency in Fly secrets
BOT_TOKEN = os.getenv("BLACKJACK_BOT_TOKEN", os.getenv("BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"))

# Webhook Settings
USE_WEBHOOK = os.getenv("USE_WEBHOOK", "False").lower() == "true"
WEBHOOK_IP = os.getenv("WEBHOOK_IP", "0.0.0.0")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8080"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
CERTPATH = os.getenv("CERTPATH", "")

# App Settings
LOGLEVEL = os.getenv("LOGLEVEL", "INFO")

# Database Path
# Defaulting to shared volume path for All-Telegram-Bots deployment
DATABASE_PATH = os.getenv("DATABASE_PATH", "/data/blackjack_users.db")
