"""
admin panel kodlari
"""

import json
import logging
import os
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from dotenv import dotenv_values

import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | admin_bot | %(message)s",
)

ENV_PATH = Path(".env")
cfg = dotenv_values(ENV_PATH)

BOT_TOKEN = cfg.get("ADMIN_BOT_TOKEN", "")
ADMIN_USER_ID = int(cfg.get("ADMIN_USER_ID", "0") or 0)

if not BOT_TOKEN:
    raise RuntimeError(
        "ADMIN_BOT_TOKEN .env faylida sozlanmagan. "
        "BotFather tokenini kiriting."
    )

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
OFFSET = 0

# Foydalanuvchi qaysi bosqichda ekanini saqlaydi.
# Bu oddiy admin bot bo'lgani uchun faqat ruxsat berilgan admin ishlata oladi.
STATES = {}
GROUP_SELECTIONS = {}
GROUP_MESSAGE_STATES = {}

WELCOME_DEFAULT = """Assalomu alaykum! 👋

O‘quv markazimizga xush kelibsiz.

📚 Kurslar:
• Ingliz tili
• IELTS
• Rus tili
• Matematika
• Python
• Frontend / Backend

💰 Kurs narxlari: 350 000 so‘mdan.
🕐 Darslar: 09:00–20:00
📍 Manzil: Samarqand shahri

Batafsil ma’lumot uchun kurs nomini yozing."""


def telegram(method, data=None):
    """Telegram Bot API'ga POST so'rov yuboradi."""
    data = data or {}
    body = urllib.parse.urlencode(data).encode("utf-8")

    request = urllib.request.Request(
        f"{API_URL}/{method}",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
    except Exception:
        logging.exception("Telegram API request failed: %s", method)
        return None

    if not result.get("ok"):
        logging.error("Telegram API error: %s", result)
        return None

    return result.get("result")


def send_message(chat_id, text, keyboard=None):
    data = {
        "chat_id": chat_id,
        "text": text,
    }

    if keyboard is not None:
        data["reply_markup"] = json.dumps(
            {
                "keyboard": keyboard,
                "resize_keyboard": True,
                "one_time_keyboard": False,
            },
            ensure_ascii=False,
        )

    return telegram("sendMessage", data)


def send_inline_message(chat_id, text, keyboard):
    return telegram(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "reply_markup": json.dumps(
                {"inline_keyboard": keyboard},
                ensure_ascii=False,
            ),
        },
    )


def edit_inline_message(chat_id, message_id, text, keyboard=None):
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
    }
    if keyboard is not None:
        data["reply_markup"] = json.dumps(
            {"inline_keyboard": keyboard},
            ensure_ascii=False,
        )
    else:
        data["reply_markup"] = json.dumps({"inline_keyboard": []})
    return telegram("editMessageText", data)


def answer_callback_query(callback_query_id, text=None, show_alert=False):
    data = {"callback_query_id": callback_query_id}
    if text:
        data["text"] = text
    if show_alert:
        data["show_alert"] = "true"
    telegram("answerCallbackQuery", data)


def main_menu():
    return [
        ["⚙️ Telegram sozlamalari", "💬 Avtojavob"],
        ["📋 Guruhlar"],
        ["📊 Holat", "🆔 Mening ID"],
        ["💾 Database"],
    ]


def back_keyboard():
    # Har bir bo'lim ichida FAQAT Orqaga tugmasi chiqadi.
    return [["⬅️ Orqaga"]]


def is_admin(user_id):
    # ADMIN_USER_ID 0 bo'lsa vaqtincha barcha foydalanuvchilarga ruxsat beradi.
    # Production'da albatta o'z Telegram ID'ingizni yozing.
    return ADMIN_USER_ID == 0 or user_id == ADMIN_USER_ID


def read_env(key, default=""):
    values = dotenv_values(ENV_PATH)
    return values.get(key, default) or default


def write_env(updates):
    """Qiymatlarni .env ga yozadi va mavjud boshqa qiymatlarni saqlab qoladi."""
    values = {}

    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()

    for key, value in updates.items():
        values[key] = str(value)

    ENV_PATH.write_text(
        "\n".join(f"{key}={value}" for key, value in values.items()) + "\n",
        encoding="utf-8",
    )

    try:
        os.chmod(ENV_PATH, 0o600)
    except OSError:
        pass


def send_document(chat_id, filename, content, caption=""):
    """Telegram Bot API sendDocument uchun multipart/form-data yuboradi."""
    boundary = "----EducationBot" + uuid.uuid4().hex
    file_bytes = content.encode("utf-8") if isinstance(content, str) else content

    parts = []
    def field(name, value):
        parts.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n"
        .encode("utf-8")
        )

    field("chat_id", str(chat_id))
    if caption:
        field("caption", caption)

    parts.append(
        (f"--{boundary}\r\n"
         f'Content-Disposition: form-data; name="document"; filename="{filename}"\r\n'
         "Content-Type: application/json\r\n\r\n").encode("utf-8")
        + file_bytes
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))

    request = urllib.request.Request(
        f"{API_URL}/sendDocument",
        data=b"".join(parts),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
    except Exception:
        logging.exception("Telegram document upload failed")
        return None

    if not result.get("ok"):
        logging.error("Telegram API error: %s", result)
        return None
    return result.get("result")


def show_database(chat_id):
    """PostgreSQL dagi barcha jadvallarni bitta JSON fayl sifatida yuboradi."""
    try:
        data = db.export_database()
        counts = {name: len(rows) for name, rows in data.items()}
        content = json.dumps(data, ensure_ascii=False, indent=2, default=str)
        filename = f"database_{time.strftime('%Y%m%d_%H%M%S')}.json"
        caption = (
            "🗄️ PostgreSQL database\n\n"
            f"👥 customers: {counts['customers']}\n"
            f"💬 messages: {counts['messages']}\n"
            f"📢 groups: {counts['groups_']}\n"
            f"⏰ scheduled: {counts['scheduled_messages']}\n"
            f"📨 group message jobs: {counts['group_message_jobs']}\n"
            f"⚙️ settings: {counts['settings']}"
        )
        send_document(chat_id, filename, content, caption)
    except Exception:
        logging.exception("Database export failed")
        send_message(chat_id, "❌ PostgreSQL database ma'lumotlarini olishda xatolik yuz berdi.", main_menu())


def groups_view(user_id):
    groups = db.get_groups()
    group_ids = {group["telegram_id"] for group in groups}
    selected = GROUP_SELECTIONS.setdefault(user_id, set())
    selected.intersection_update(group_ids)

    if not groups:
        return "📋 Guruhlar topilmadi. UserBot guruhlarni sinxronlaganini tekshiring.", [
            [{"text": "⬅️ Orqaga", "callback_data": "groups_back"}]
        ]

    lines = ["📋 Guruhlar", ""]
    keyboard = []
    for index, group in enumerate(groups, start=1):
        is_selected = group["telegram_id"] in selected
        mark = "✅" if is_selected else "☐"
        lines.append(f"{index}. {mark} {group['title']}")
        label = group["title"]
        if len(label) > 56:
            label = label[:53] + "..."
        keyboard.append(
            [{
                "text": f"{mark} {label}",
                "callback_data": f"group_toggle:{group['telegram_id']}",
            }]
        )

    keyboard.extend([
        [{"text": "📨 Xabar yuborish", "callback_data": "groups_send"}],
        [{"text": "⬅️ Orqaga", "callback_data": "groups_back"}],
    ])
    return "\n".join(lines), keyboard


def show_groups(chat_id, user_id):
    text, keyboard = groups_view(user_id)
    send_inline_message(chat_id, text, keyboard)


def request_group_message(chat_id, user_id):
    selected_ids = sorted(GROUP_SELECTIONS.get(user_id, set()))
    if not selected_ids:
        send_message(chat_id, "Avval kamida bitta guruhni tanlang.", main_menu())
        return

    GROUP_MESSAGE_STATES[user_id] = {
        "state": "group_message",
        "chat_id": chat_id,
        "user_id": user_id,
        "group_telegram_ids": selected_ids,
    }
    send_message(
        chat_id,
        "Xabar matnini yuboring:",
        back_keyboard(),
    )


def handle_group_message_state(chat_id, user_id, text):
    state = GROUP_MESSAGE_STATES.get(user_id)
    if not state or state.get("chat_id") != chat_id:
        return False

    if text == "⬅️ Orqaga":
        GROUP_MESSAGE_STATES.pop(user_id, None)
        send_message(chat_id, "Xabar yuborish bekor qilindi.", main_menu())
        return True

    if not text.strip():
        send_message(chat_id, "Xabar bo‘sh bo‘lishi mumkin emas. Qaytadan yuboring.")
        return True

    state["state"] = "confirm_group_message"
    state["text"] = text
    groups = [
        db.get_group_by_telegram_id(tg_id)
        for tg_id in state["group_telegram_ids"]
    ]
    selected_names = [
        f"✅ {group['title']}" if group else f"✅ {tg_id}"
        for tg_id, group in zip(state["group_telegram_ids"], groups)
    ]
    confirmation = (
        "📨 Xabar yuborish\n\n"
        "Tanlangan guruhlar:\n"
        + "\n".join(selected_names)
        + f"\n\nXabar:\n{text}"
    )
    send_inline_message(
        chat_id,
        confirmation,
        [[
            {"text": "Tasdiqlash", "callback_data": "groups_confirm"},
            {"text": "❌ Bekor qilish", "callback_data": "groups_cancel"},
        ]],
    )
    return True


def handle_callback_query(callback):
    callback_id = callback.get("id")
    user_id = (callback.get("from") or {}).get("id")
    message = callback.get("message") or {}
    chat_id = (message.get("chat") or {}).get("id")
    message_id = message.get("message_id")
    data = callback.get("data", "")

    if not user_id or not chat_id:
        answer_callback_query(callback_id, "So‘rovni aniqlab bo‘lmadi.", True)
        return
    if not is_admin(user_id):
        answer_callback_query(callback_id, "Sizda admin huquqi yo‘q.", True)
        return

    if data.startswith("group_toggle:"):
        try:
            telegram_id = int(data.partition(":")[2])
        except ValueError:
            answer_callback_query(callback_id, "Guruh ID noto‘g‘ri.", True)
            return
        if not db.get_group_by_telegram_id(telegram_id):
            answer_callback_query(callback_id, "Guruh topilmadi.", True)
            return

        selected = GROUP_SELECTIONS.setdefault(user_id, set())
        if telegram_id in selected:
            selected.remove(telegram_id)
        else:
            selected.add(telegram_id)
        text, keyboard = groups_view(user_id)
        edit_inline_message(chat_id, message_id, text, keyboard)
        answer_callback_query(callback_id)
        return

    if data == "groups_send":
        if not GROUP_SELECTIONS.get(user_id):
            answer_callback_query(callback_id, "Avval kamida bitta guruhni tanlang.", True)
            return
        answer_callback_query(callback_id)
        request_group_message(chat_id, user_id)
        return

    if data == "groups_back":
        answer_callback_query(callback_id)
        STATES.pop(chat_id, None)
        GROUP_MESSAGE_STATES.pop(user_id, None)
        start(chat_id)
        return

    if data == "groups_cancel":
        state = GROUP_MESSAGE_STATES.get(user_id)
        if state and state.get("chat_id") == chat_id:
            GROUP_MESSAGE_STATES.pop(user_id, None)
        answer_callback_query(callback_id)
        edit_inline_message(chat_id, message_id, "❌ Xabar yuborish bekor qilindi.")
        send_message(chat_id, "Asosiy menyu:", main_menu())
        return

    if data == "groups_confirm":
        state = GROUP_MESSAGE_STATES.get(user_id)
        if (
            not state
            or state.get("state") != "confirm_group_message"
            or state.get("chat_id") != chat_id
        ):
            answer_callback_query(callback_id, "Tasdiqlash holati topilmadi.", True)
            return
        job_id = db.enqueue_group_message(
            user_id,
            state["group_telegram_ids"],
            state["text"],
        )
        GROUP_MESSAGE_STATES.pop(user_id, None)
        GROUP_SELECTIONS[user_id] = set()
        answer_callback_query(callback_id)
        edit_inline_message(
            chat_id,
            message_id,
            f"⏳ Xabar yuborish navbatga qo‘shildi (#{job_id}). UserBot natijani yuboradi.",
        )
        return

    answer_callback_query(callback_id, "Noma’lum amal.", True)


def notify_group_message_results():
    for job in db.get_unnotified_group_message_jobs():
        lines = []
        for result in job["results"] or []:
            if result["sent"]:
                lines.append(f"✅ {result['title']}")
            else:
                lines.append(
                    f"❌ {result['title']} — yuborilmadi\n"
                    f"Sabab: {result.get('error') or 'Noma’lum xatolik'}"
                )
        if not lines:
            lines.append("Xabar yuborish natijasi mavjud emas.")

        chunks = []
        current = ["📨 Guruh xabari yuborish natijasi:", ""]
        for line in lines:
            if sum(map(len, current)) + len(line) + len(current) > 3500:
                chunks.append("\n".join(current))
                current = ["📨 Guruh xabari yuborish natijasi:", ""]
            current.append(line)
        chunks.append("\n".join(current))

        delivered = True
        for index, chunk in enumerate(chunks):
            keyboard = main_menu() if index == len(chunks) - 1 else None
            if not send_message(job["requested_by"], chunk, keyboard):
                delivered = False
                break
        if delivered:
            db.mark_group_message_job_notified(job["id"])


def start(chat_id):
    STATES.pop(chat_id, None)

    send_message(
        chat_id,
        "🎓 <b>Education Center Admin Bot</b>\n\n"
        "Quyidagi menyudan kerakli bo‘limni tanlang.",
        main_menu(),
    )


def show_settings(chat_id):
    STATES[chat_id] = {"state": "api_id"}

    send_message(
        chat_id,
        "⚙️ <b>Telegram sozlamalari</b>\n\n"
        "1/5 — 🔑 <b>API ID</b>ni yuboring.\n\n"
        "Masalan:\n"
        "<code>12345678</code>\n\n"
        "API ID va API HASH: my.telegram.org → API development tools",
        back_keyboard(),
    )


def show_welcome(chat_id):
    STATES[chat_id] = {"state": "welcome"}

    current = db.get_setting("welcome_message", "") or read_env(
        "WELCOME_MESSAGE",
        WELCOME_DEFAULT,
    )

    send_message(
        chat_id,
        "💬 <b>Avtojavob sozlamalari</b>\n\n"
        "Quyidagi xabar yangi mijoz birinchi marta yozganda yuboriladi.\n\n"
        "Yangi xabar matnini yuboring.\n\n"
        f"📌 <b>Hozirgi matn:</b>\n{current}",
        back_keyboard(),
    )


def show_status(chat_id):
    db.init_db()

    welcome = db.get_setting("welcome_message", "")

    send_message(
        chat_id,
        "📊 <b>Bot holati</b>\n\n"
        f"🔑 API ID: <code>{read_env('API_ID', 'kiritilmagan')}</code>\n"
        f"📱 Telefon: <code>{read_env('PHONE_NUMBER', 'kiritilmagan')}</code>\n"
        f"👤 Admin ID: <code>{read_env('ADMIN_CHAT_ID', 'kiritilmagan')}</code>\n"
        f"⏱ Monitoring: <code>{read_env('MONITOR_MINUTES', '5')} daqiqa</code>\n"
        f"💬 Avtojavob: {'✅ sozlangan' if welcome else '❌ sozlanmagan'}\n\n"
        "🔐 API HASH xavfsizlik sababli ko‘rsatilmaydi.",
        main_menu(),
    )


def handle_state(chat_id, user_id, text):
    state_data = STATES.get(chat_id, {})
    state = state_data.get("state")

    if text == "⬅️ Orqaga":
        STATES.pop(chat_id, None)
        send_message(
            chat_id,
            "⬅️ Asosiy menyuga qaytdingiz.",
            main_menu(),
        )
        return

    if state == "api_id":
        if not text.isdigit():
            send_message(
                chat_id,
                "❌ API ID faqat raqamlardan iborat bo‘ladi.\n\n"
                "Qaytadan yuboring:",
                back_keyboard(),
            )
            return

        STATES[chat_id] = {
            "state": "api_hash",
            "api_id": text,
        }

        send_message(
            chat_id,
            "2/5 — 🔐 <b>API HASH</b>ni yuboring.\n\n"
            "Bu maxfiy ma'lumot.",
            back_keyboard(),
        )
        return

    if state == "api_hash":
        if not text.strip():
            send_message(
                chat_id,
                "❌ API HASH bo‘sh bo‘lishi mumkin emas.",
                back_keyboard(),
            )
            return

        STATES[chat_id]["state"] = "phone"
        STATES[chat_id]["api_hash"] = text.strip()

        send_message(
            chat_id,
            "3/5 — 📱 <b>Telegram telefon raqamini</b> yuboring.\n\n"
            "Masalan:\n"
            "<code>+998901234567</code>",
            back_keyboard(),
        )
        return

    if state == "phone":
        if not text.startswith("+") or not text[1:].replace(" ", "").isdigit():
            send_message(
                chat_id,
                "❌ Raqam noto‘g‘ri.\n\n"
                "Xalqaro formatda yuboring:\n"
                "<code>+998901234567</code>",
                back_keyboard(),
            )
            return

        STATES[chat_id]["state"] = "admin_id"
        STATES[chat_id]["phone"] = text.replace(" ", "")

        send_message(
            chat_id,
            "4/5 — 👤 <b>Admin Telegram ID</b>ni yuboring.\n\n"
            "Javobsiz mijoz haqida ogohlantirish shu ID'ga boradi.",
            back_keyboard(),
        )
        return

    if state == "admin_id":
        if not text.lstrip("-").isdigit():
            send_message(
                chat_id,
                "❌ Telegram ID faqat raqam bo‘lishi kerak.",
                back_keyboard(),
            )
            return

        STATES[chat_id]["state"] = "monitor"
        STATES[chat_id]["admin_id"] = text

        send_message(
            chat_id,
            "5/5 — ⏱ <b>Monitoring vaqtini</b> kiriting.\n\n"
            "Masalan: <code>5</code>\n\n"
            "Bu mijozga necha daqiqa javob berilmasa admin ogohlantirilishini bildiradi.",
            back_keyboard(),
        )
        return

    if state == "monitor":
        if not text.isdigit() or int(text) < 1:
            send_message(
                chat_id,
                "❌ 1 yoki undan katta butun son kiriting.",
                back_keyboard(),
            )
            return

        data = STATES.pop(chat_id)

        write_env(
            {
                "API_ID": data["api_id"],
                "API_HASH": data["api_hash"],
                "PHONE_NUMBER": data["phone"],
                "ADMIN_CHAT_ID": data["admin_id"],
                "MONITOR_MINUTES": text,
            }
        )

        db.set_setting("monitor_minutes", text)

        send_message(
            chat_id,
            "✅ <b>Telegram sozlamalari saqlandi.</b>\n\n"
            f"🔑 API ID: <code>{data['api_id']}</code>\n"
            f"📱 Telefon: <code>{data['phone']}</code>\n"
            f"👤 Admin ID: <code>{data['admin_id']}</code>\n"
            f"⏱ Monitoring: <code>{text} daqiqa</code>\n\n"
            "🔐 API HASH saqlandi, lekin xavfsizlik uchun ekranga chiqarilmadi.\n\n"
            "⚠️ UserBot yangi credentiallarni ishlatishi uchun "
            "<code>python bot.py</code>ni qayta ishga tushiring.",
            main_menu(),
        )
        return

    if state == "welcome":
        if not text.strip():
            send_message(
                chat_id,
                "❌ Xabar bo‘sh bo‘lishi mumkin emas.",
                back_keyboard(),
            )
            return

        db.init_db()
        db.set_setting("welcome_message", text)
        write_env({"WELCOME_MESSAGE": text})

        STATES.pop(chat_id, None)

        send_message(
            chat_id,
            "✅ <b>Avtomatik welcome xabar saqlandi.</b>\n\n"
            "Endi yangi mijoz birinchi marta yozganda UserBot shu xabarni yuboradi.",
            main_menu(),
        )
        return

    # Holat noma'lum bo'lsa.
    STATES.pop(chat_id, None)
    send_message(chat_id, "Menyu qayta tiklandi.", main_menu())


def handle_message(message):
    user = message.get("from") or {}
    chat = message.get("chat") or {}

    user_id = user.get("id")
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()

    if not user_id or not chat_id:
        return

    if not is_admin(user_id):
        send_message(chat_id, "⛔ Sizda admin huquqi yo‘q.")
        return

    if text == "/start":
        GROUP_MESSAGE_STATES.pop(user_id, None)
        start(chat_id)
        return

    if text == "/menu":
        GROUP_MESSAGE_STATES.pop(user_id, None)
        start(chat_id)
        return

    if text == "🆔 Mening ID":
        send_message(
            chat_id,
            f"🆔 Sizning Telegram ID: <code>{user_id}</code>",
            main_menu(),
        )
        return

    if text == "⚙️ Telegram sozlamalari":
        show_settings(chat_id)
        return

    if text == "💬 Avtojavob":
        show_welcome(chat_id)
        return

    if text == "📋 Guruhlar":
        show_groups(chat_id, user_id)
        return

    if text == "📊 Holat":
        show_status(chat_id)
        return

    if text in ("💾 Database", "🗄️ Database"):
        show_database(chat_id)
        return

    group_state = GROUP_MESSAGE_STATES.get(user_id)
    if group_state and group_state.get("chat_id") == chat_id:
        if group_state["state"] == "confirm_group_message":
            send_message(
                chat_id,
                "Tasdiqlash yoki bekor qilish tugmasini bosing.",
            )
        else:
            handle_group_message_state(chat_id, user_id, text)
        return

    if chat_id in STATES:
        handle_state(chat_id, user_id, text)
        return

    send_message(
        chat_id,
        "Menyudan bo‘lim tanlang:",
        main_menu(),
    )


def poll():
    global OFFSET

    logging.info("Admin Bot ishga tushdi.")

    while True:
        try:
            updates = telegram(
                "getUpdates",
                {
                    "offset": OFFSET,
                    "timeout": 30,
                    "allowed_updates": json.dumps(["message", "callback_query"]),
                },
            )

            if not updates:
                notify_group_message_results()
                continue

            for update in updates:
                OFFSET = update["update_id"] + 1

                message = update.get("message")
                if message:
                    try:
                        handle_message(message)
                    except Exception:
                        logging.exception("Message handling failed")
                callback = update.get("callback_query")
                if callback:
                    try:
                        handle_callback_query(callback)
                    except Exception:
                        logging.exception("Callback handling failed")
                        answer_callback_query(
                            callback.get("id"),
                            "Amalni bajarishda xatolik yuz berdi.",
                            True,
                        )
            notify_group_message_results()

        except KeyboardInterrupt:
            logging.info("Admin Bot to'xtatildi.")
            break
        except Exception:
            logging.exception("Polling error")
            time.sleep(3)


if __name__ == "__main__":
    db.init_db()
    poll()
