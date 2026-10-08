import asyncio
import logging
from datetime import datetime, timezone

import asyncio
import logging

from getpass import getpass
import qrcode

from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, SessionPasswordNeededError
from telethon.tl.types import Channel, Chat

import config
import db
from scheduler import scheduler_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.FileHandler("telegram.log"), logging.StreamHandler()]
)
log = logging.getLogger("userbot")

client = TelegramClient(config.SESSION_NAME, config.API_ID, config.API_HASH)

# Message IDs sent by our automatic welcome reply. They must not count as operator replies.
AUTO_REPLY_IDS = set()
OVERDUE_NOTIFIED = set()

def iso(dt=None):
    return (dt or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()

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

@client.on(events.NewMessage(incoming=True))
async def incoming_handler(event):
    # Faqat private chatlar: guruh va kanallardagi incoming xabarlar mijoz sifatida olinmaydi.
    if not event.is_private:
        return

    sender = await event.get_sender()
    if not sender or getattr(sender, "bot", False):
        return

    text = event.raw_text.strip()
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

    log.info("New customer message: tg_id=%s", sender.id)

    # Birinchi murojaatga avtomatik to'liq ma'lumot.
    if is_new:
        welcome = db.get_setting("welcome_message", "") or config.WELCOME_MESSAGE
        if welcome:
            try:
                sent = await event.respond(welcome)
                AUTO_REPLY_IDS.add(sent.id)
                db.add_message(
                    customer_id,
                    sent.id,
                    "out",
                    welcome,
                    iso(),
                    answered=True,
                    auto_reply=True,
                )
            except FloodWaitError as e:
                log.warning("Welcome FloodWait: %s sec", e.seconds)
            except Exception:
                log.exception("Welcome message failed")

@client.on(events.NewMessage(outgoing=True))
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
            db.add_message(customer["id"], event.message.id, "out", text, iso(), answered=True)
            db.mark_customer_answered(customer["id"])
            OVERDUE_NOTIFIED.discard(customer["id"])
            log.info("Operator replied: customer=%s", customer["telegram_id"])
    except Exception:
        log.exception("Outgoing message processing failed")

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
                    db.set_customer_status(row["id"], "overdue")
        except Exception:
            log.exception("Monitoring loop error")
        await asyncio.sleep(15)

async def sync_groups():
    try:
        async for dialog in client.iter_dialogs():
            entity = dialog.entity
            if is_group_entity(entity):
                db.sync_group(
                    dialog.id,
                    getattr(entity, "title", None) or dialog.name or str(dialog.id),
                    getattr(entity, "username", None),
                )
        log.info("Telegram groups synchronized.")
    except Exception:
        log.exception("Group synchronization failed")


def is_group_entity(entity):
    return isinstance(entity, Chat) or (
        isinstance(entity, Channel) and bool(entity.megagroup)
    )


@client.on(events.ChatAction())
async def group_chat_action_handler(event):
    try:
        entity = await event.get_chat()
        if is_group_entity(entity):
            db.sync_group(
                event.chat_id,
                getattr(entity, "title", None) or str(event.chat_id),
                getattr(entity, "username", None),
            )
    except Exception:
        log.exception("Group membership synchronization failed")


async def send_to_enabled_groups(text):
    sent = 0
    for tg_id in db.enabled_group_ids():
        try:
            await client.send_message(tg_id, text)
            sent += 1
            await asyncio.sleep(1)
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds)
        except Exception:
            log.exception("Group message failed: %s", tg_id)
    return sent


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


def print_qr(url):
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make(fit=True)

    print("\n" + "=" * 70)
    print("📱 TELEGRAM QR LOGIN")
    print(
        "Telegram → Settings → Devices → "
        "Link Desktop Device orqali QR kodni skaner qiling."
    )
    print("QR kodi:")
    qr.print_ascii(invert=True)
    print("QR URL:", url)
    print("=" * 70 + "\n")


async def login_with_qr():
    await client.connect()

    if await client.is_user_authorized():
        return

    while True:
        qr_login = await client.qr_login()
        print_qr(qr_login.url)

        try:
            await qr_login.wait()
            return

        except asyncio.TimeoutError:
            print("⏳ QR kodi muddati tugadi.")
            print("🔄 Yangi QR kodi yaratilmoqda...")
            continue

        except SessionPasswordNeededError:
            password = getpass("🔐 Telegram 2FA parolini kiriting: ")
            await client.sign_in(password=password)
            return

async def main():
    db.init_db()
    await login_with_qr()
    me = await client.get_me()
    log.info("Telegram connected as %s (%s)", getattr(me, "username", None), me.id)
    await sync_groups()
    asyncio.create_task(monitor_loop())
    asyncio.create_task(scheduler_loop(client))
    asyncio.create_task(group_message_job_loop())

    print("UserBot ishga tushdi.")
    print("Session:", config.SESSION_NAME + ".session")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
