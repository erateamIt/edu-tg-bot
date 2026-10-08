"""The single shared Telethon UserBot client and in-memory runtime state."""
from telethon import TelegramClient

from app.core import config

client = TelegramClient(config.SESSION_NAME, config.API_ID, config.API_HASH)
AUTO_REPLY_IDS = set()
OVERDUE_NOTIFIED = set()
