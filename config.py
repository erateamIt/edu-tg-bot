import os
from dotenv import load_dotenv

load_dotenv(override=True)

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
PHONE_NUMBER = os.getenv("PHONE_NUMBER", "")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
MONITOR_MINUTES = int(os.getenv("MONITOR_MINUTES", "5"))

PANEL_HOST = os.getenv("PANEL_HOST", "127.0.0.1")
PANEL_PORT = int(os.getenv("PANEL_PORT", "8000"))
PANEL_TOKEN = os.getenv("PANEL_TOKEN", "change-this-token")
SESSION_NAME = os.getenv("SESSION_NAME", "education_center")
WELCOME_MESSAGE = os.getenv("WELCOME_MESSAGE", "")

# PostgreSQL
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "education_center")
DB_USER = os.getenv("DB_USER", "education_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

if not API_ID or not API_HASH:
    raise RuntimeError("API_ID va API_HASH .env faylida sozlanmagan.")

if not DB_PASSWORD:
    raise RuntimeError("DB_PASSWORD .env faylida sozlanmagan.")
