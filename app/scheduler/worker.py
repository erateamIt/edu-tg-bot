"""PostgreSQL scheduled-message worker using the shared Telethon client."""
import asyncio
import logging
from datetime import datetime, timezone

from app import database as db
from telethon.errors import FloodWaitError

log = logging.getLogger("scheduler")

async def scheduler_loop(client):
    """PostgreSQL'dagi scheduled_messages jadvalini tekshiradi va xabarlarni yuboradi."""
    while True:
        try:
            now = datetime.now(timezone.utc)
            rows = db.claim_due_scheduled(now.isoformat())

            for row in rows:
                try:
                    target_id = row.get("recipient_id") or row["group_telegram_id"]
                    try:
                        await send_scheduled(client, row, target_id)
                    except FloodWaitError as error:
                        log.warning("Scheduled message FloodWait: %s sec", error.seconds)
                        await asyncio.sleep(error.seconds)
                        await send_scheduled(client, row, target_id)
                    db.advance_scheduled_message(row["id"], sent=True)
                    db.add_log(
                        "scheduled_message_sent",
                        row["recipient_type"],
                        target_id,
                        {
                            "scheduled_message_id": row["id"],
                            "message_type": row["message_type"],
                        },
                    )
                except Exception as error:
                    log.exception("Scheduled message failed: id=%s", row["id"])
                    db.advance_scheduled_message(row["id"], sent=False)
                    db.add_log(
                        "error",
                        row.get("recipient_type"),
                        row.get("recipient_id") or row.get("group_telegram_id"),
                        {"scheduled_message_id": row["id"], "reason": str(error)},
                    )
        except Exception:
            log.exception("Scheduler loop error")

        await asyncio.sleep(10)

async def send_scheduled(client, row, target_id):
    if row["message_type"] == "text":
        return await client.send_message(target_id, row["text"])
    if not row["media_path"]:
        raise ValueError("Scheduled media file path is missing")
    return await client.send_file(
        target_id,
        row["media_path"],
        caption=row.get("caption") or "",
        force_document=row["message_type"] == "document",
    )
