"""Outgoing operator and queued message delivery through the shared client."""
import asyncio
import logging

from app import database as db
from telethon.errors import FloodWaitError

from .client import AUTO_REPLY_IDS, OVERDUE_NOTIFIED, client
from app.utils.datetime import iso

log = logging.getLogger("userbot")

async def outgoing_handler(event):
    # Admin/operator tomonidan mijozga yozilgan javobni aniqlash.
    if not event.is_private:
        return
    if event.message.id in AUTO_REPLY_IDS:
        AUTO_REPLY_IDS.discard(event.message.id)
        return

    me = await client.get_me()
    if not me or event.sender_id != me.id:
        return

    try:
        customer = db.get_customer_by_telegram_id(event.chat_id)
        if customer:
            text = event.raw_text.strip()
            db.record_customer_reply(customer["id"], text, event.message.id, iso())
            db.add_log("admin_reply", "user", customer["telegram_id"])
            OVERDUE_NOTIFIED.discard(customer["id"])
            log.info("Operator replied: customer=%s", customer["telegram_id"])
    except Exception:
        log.exception("Outgoing message processing failed")

async def group_message_job_loop():
    while True:
        try:
            job = db.claim_group_message_job()
            if not job:
                await asyncio.sleep(2)
                continue

            results = []
            for telegram_id in job["group_telegram_ids"]:
                group = db.get_group_by_telegram_id(telegram_id)
                title = group["title"] if group else str(telegram_id)
                try:
                    await client.send_message(telegram_id, job["text"])
                    results.append(
                        {"telegram_id": telegram_id, "title": title, "sent": True}
                    )
                    db.add_log(
                        "group_message_sent",
                        "group",
                        telegram_id,
                        {"group_message_job_id": job["id"]},
                        job["requested_by"],
                    )
                except Exception as error:
                    log.exception("Group message failed: %s", telegram_id)
                    results.append(
                        {
                            "telegram_id": telegram_id,
                            "title": title,
                            "sent": False,
                            "error": str(error) or error.__class__.__name__,
                        }
                    )

            db.complete_group_message_job(job["id"], results)
        except Exception:
            log.exception("Group message job processing failed")
            await asyncio.sleep(2)

async def outgoing_message_loop():
    while True:
        try:
            job = db.claim_outgoing_message()
            if not job:
                await asyncio.sleep(2)
                continue

            try:
                try:
                    sent = await send_outgoing_job(job)
                except FloodWaitError as error:
                    log.warning("Outgoing message FloodWait: %s sec", error.seconds)
                    await asyncio.sleep(error.seconds)
                    sent = await send_outgoing_job(job)

                db.finish_outgoing_message(job["id"])
                if job["recipient_type"] == "user":
                    customer = db.get_customer_by_telegram_id(job["recipient_id"])
                    if customer:
                        db.record_customer_reply(
                            customer["id"],
                            job["text"] or job["caption"] or "",
                            sent.id,
                            iso(),
                        )
                        OVERDUE_NOTIFIED.discard(customer["id"])
                        db.add_log(
                            "admin_reply",
                            "user",
                            job["recipient_id"],
                            {"outgoing_message_id": job["id"]},
                            job["requested_by"],
                        )

                action = (
                    "media_sent"
                    if job["message_type"] != "text"
                    else (
                        "group_message_sent"
                        if job["recipient_type"] == "group"
                        else "user_message_sent"
                    )
                )
                db.add_log(
                    action,
                    job["recipient_type"],
                    job["recipient_id"],
                    {"message_type": job["message_type"]},
                    job["requested_by"],
                )
                await client.send_message(
                    job["requested_by"],
                    f"✅ Xabar {job['recipient_type']} {job['recipient_id']} ga yuborildi.",
                )
            except Exception as error:
                await report_outgoing_failure(job, error)
        except Exception:
            log.exception("Outgoing message queue failed")
            await asyncio.sleep(2)

async def send_outgoing_job(job):
    if job["message_type"] == "text":
        return await client.send_message(job["recipient_id"], job["text"] or "")
    if not job["media_path"]:
        raise ValueError("Media file path is missing")
    return await client.send_file(
        job["recipient_id"],
        job["media_path"],
        caption=job["caption"] or "",
        force_document=job["message_type"] == "document",
    )

async def report_outgoing_failure(job, error):
    reason = str(error) or error.__class__.__name__
    db.finish_outgoing_message(job["id"], reason)
    db.add_log(
        "error",
        job["recipient_type"],
        job["recipient_id"],
        {"operation": "outgoing_message", "reason": reason},
        job["requested_by"],
    )
    try:
        await client.send_message(
            job["requested_by"],
            f"❌ Xabar yuborilmadi: {job['recipient_type']} "
            f"{job['recipient_id']}\nSabab: {reason}",
        )
    except Exception:
        log.exception("Failed to notify admin about outgoing message error")
