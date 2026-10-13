"""Private incoming customer-message handling."""
import logging

from app import database as db
from app.auto_tag import auto_tag_customer
from app.core import config
from .client import AUTO_REPLY_IDS
from app.utils.datetime import iso

log = logging.getLogger("userbot")

async def incoming_handler(event):
    # Faqat private chatlar: guruh va kanallardagi incoming xabarlar mijoz sifatida olinmaydi.
    if not event.is_private:
        return

    sender = await event.get_sender()
    if not sender or getattr(sender, "bot", False):
        return

    text = (event.raw_text or "").strip()
    if not text:
        return

    sent_at = iso(event.message.date)
    customer_id, is_new = db.upsert_customer(
        sender.id,
        getattr(sender, "username", None),
        getattr(sender, "first_name", None),
        getattr(sender, "last_name", None),
        getattr(sender, "phone", None),
        text,
        sent_at
    )
    db.add_message(customer_id, event.message.id, "in", text, sent_at)
    db.mark_customer_waiting(customer_id)
    db.add_log(
        "customer_created" if is_new else "customer_message_received",
        "user",
        sender.id,
    )

    try:
        auto_tag_customer(customer_id, text)
    except Exception:
        log.exception("Automatic tagging failed for customer=%s", customer_id)

    log.info("New customer message: tg_id=%s", sender.id)

    rules_enabled = (
        db.get_setting("auto_reply_enabled", "true") or "true"
    ).lower() == "true"
    rule = db.get_matching_auto_reply(text) if rules_enabled else None
    welcome = db.get_setting("welcome_message", "") or config.WELCOME_MESSAGE
    response = rule["response"] if rule else (welcome if is_new else "")
    if response:
        try:
            sent = await event.respond(response)
            AUTO_REPLY_IDS.add(sent.id)
            db.add_message(
                customer_id,
                sent.id,
                "out",
                response,
                iso(),
                answered=True,
                auto_reply=True,
            )
            db.add_log(
                "auto_reply",
                "user",
                sender.id,
                {"keyword": rule["keyword"] if rule else None},
            )
        except FloodWaitError as e:
            log.warning("AutoReply FloodWait: %s sec", e.seconds)
        except Exception:
            log.exception("AutoReply message failed")
