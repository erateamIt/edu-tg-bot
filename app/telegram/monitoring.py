"""Unanswered-customer monitoring and daily report delivery."""
import asyncio
import logging
from datetime import datetime, timezone

from app import database as db
from app.core import config
from telethon.errors import FloodWaitError

from .client import OVERDUE_NOTIFIED, client

log = logging.getLogger("userbot")

async def notify_admin(text):
    if not config.ADMIN_CHAT_ID:
        log.warning("ADMIN_CHAT_ID sozlanmagan.")
        return
    try:
        await client.send_message(config.ADMIN_CHAT_ID, text)
    except FloodWaitError as e:
        log.warning("Admin notification FloodWait: %s sec", e.seconds)
        await asyncio.sleep(e.seconds)
        await client.send_message(config.ADMIN_CHAT_ID, text)

async def monitor_loop():
    while True:
        try:
            minutes = int(db.get_setting("monitor_minutes", str(config.MONITOR_MINUTES)))
            now = datetime.now(timezone.utc)
            for row in db.get_unanswered():
                try:
                    pending = datetime.fromisoformat(row["pending_sent_at"]).astimezone(timezone.utc)
                except Exception:
                    continue
                age = (now - pending).total_seconds() / 60
                if age >= minutes and row["id"] not in OVERDUE_NOTIFIED:
                    username = f"@{row['username']}" if row["username"] else "username yo‘q"
                    await notify_admin(
                        f"⚠️ JAVOBSIZ MIJOZ\n\n"
                        f"👤 {row['first_name'] or ''} {row['last_name'] or ''}\n"
                        f"🔗 {username}\n"
                        f"🆔 Telegram ID: {row['telegram_id']}\n\n"
                        f"💬 Xabar:\n{row['pending_text']}\n\n"
                        f"⏱ Javobsiz vaqt: {int(age)} daqiqa"
                    )
                    OVERDUE_NOTIFIED.add(row["id"])
                    db.mark_customer_overdue(row["id"])
        except Exception:
            log.exception("Monitoring loop error")
        await asyncio.sleep(15)
