"""Environment-backed application configuration."""
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env", override=True)

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))
MONITOR_MINUTES = int(os.getenv("MONITOR_MINUTES", "5"))
REPORT_USER_ID = int(os.getenv("REPORT_USER_ID", "0"))
REPORT_TIME = os.getenv("REPORT_TIME", "21:00")
REPORT_TIMEZONE = os.getenv("REPORT_TIMEZONE", "Asia/Tashkent")
BACKUP_USER_ID = int(os.getenv("BACKUP_USER_ID", "0"))

PANEL_HOST = os.getenv("PANEL_HOST", "127.0.0.1")
PANEL_PORT = int(os.getenv("PANEL_PORT", "8000"))
PANEL_TOKEN = os.getenv("PANEL_TOKEN", "").strip()
SESSION_NAME = os.getenv("SESSION_NAME", "education_center")
WELCOME_MESSAGE = os.getenv("WELCOME_MESSAGE", "")
AUTO_TAG_ENABLED = os.getenv("AUTO_TAG_ENABLED", "true").strip().lower() == "true"
AUTO_TAG_MIN_CONFIDENCE = float(os.getenv("AUTO_TAG_MIN_CONFIDENCE", "0.70"))
AUTO_TAG_AI_ENABLED = os.getenv("AUTO_TAG_AI_ENABLED", "false").strip().lower() == "true"

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "education_center")
DB_USER = os.getenv("DB_USER", "education_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

if not API_ID or not API_HASH:
    raise RuntimeError("API_ID va API_HASH .env faylida sozlanmagan.")

if not DB_PASSWORD:
    raise RuntimeError("DB_PASSWORD .env faylida sozlanmagan.")

__all__ = [
    "API_ID", "API_HASH", "ADMIN_CHAT_ID", "ADMIN_USER_ID",
    "MONITOR_MINUTES", "REPORT_USER_ID", "REPORT_TIME", "REPORT_TIMEZONE",
    "BACKUP_USER_ID", "PANEL_HOST", "PANEL_PORT", "PANEL_TOKEN",
    "SESSION_NAME", "WELCOME_MESSAGE", "AUTO_TAG_ENABLED",
    "AUTO_TAG_MIN_CONFIDENCE", "AUTO_TAG_AI_ENABLED", "DB_HOST", "DB_PORT",
    "DB_NAME", "DB_USER", "DB_PASSWORD", "PROJECT_ROOT",
]
