"""Admin messaging workflows."""
import logging
import mimetypes
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from app import database as db
from app.core import config
from .keyboards import back_keyboard, main_menu
from .states import MEDIA_DIR, WORKFLOWS
from .transport import (
    BOT_TOKEN,
    send_inline_message,
    send_message,
    telegram,
)
from .customers import show_customer_detail


def begin_send_workflow(chat_id, user_id):
    WORKFLOWS[user_id] = {"kind": "send", "stage": "type", "chat_id": chat_id}
    send_inline_message(
        chat_id,
        "📨 Xabar yuborish turini tanlang:",
        [
            [{"text": "📝 Text", "callback_data": "send_type:text"}],
            [{"text": "🖼 Rasm", "callback_data": "send_type:photo"}],
            [{"text": "🎥 Video", "callback_data": "send_type:video"}],
            [{"text": "📄 Fayl", "callback_data": "send_type:document"}],
            [{"text": "❌ Bekor qilish", "callback_data": "workflow_cancel"}],
        ],
    )

def ask_send_recipient(chat_id, user_id):
    workflow = WORKFLOWS[user_id]
    workflow["stage"] = "recipient_type"
    send_inline_message(
        chat_id,
        "Kimga yuborilsin?",
        [
            [{"text": "🆔 Telegram User ID", "callback_data": "send_recipient:user"}],
            [{"text": "📋 Guruhlar", "callback_data": "send_recipient:group"}],
            [{"text": "❌ Bekor qilish", "callback_data": "workflow_cancel"}],
        ],
    )

def show_send_group_selection(chat_id, user_id):
    groups = db.get_groups()
    workflow = WORKFLOWS[user_id]
    selected = set(workflow.setdefault("recipients", []))
    keyboard = []
    for group in groups:
        checked = group["telegram_id"] in selected
        keyboard.append([{
            "text": f"{'✅' if checked else '☐'} {group['title'][:45]}",
            "callback_data": f"send_group:{group['telegram_id']}",
        }])
    keyboard.extend([
        [{"text": "Davom etish ➡️", "callback_data": "send_groups_done"}],
        [{"text": "❌ Bekor qilish", "callback_data": "workflow_cancel"}],
    ])
    send_inline_message(
        chat_id,
        f"📋 Guruh tanlang (tanlangan: {len(selected)}):",
        keyboard,
    )

def ask_message_content(chat_id, workflow):
    workflow["stage"] = "content"
    kind = workflow.get("message_type", "text")
    prompt = {
        "text": "Xabar matnini yuboring:",
        "photo": "Rasmni yuboring (caption ixtiyoriy):",
        "video": "Videoni yuboring (caption ixtiyoriy):",
        "document": "Faylni yuboring (caption ixtiyoriy):",
    }[kind]
    send_message(chat_id, prompt, back_keyboard())

def download_telegram_media(message, expected_type):
    file_id = None
    filename = None
    if expected_type == "photo" and message.get("photo"):
        file_id = message["photo"][-1]["file_id"]
        filename = "photo.jpg"
    elif expected_type == "video" and message.get("video"):
        file_id = message["video"]["file_id"]
        filename = message["video"].get("file_name") or "video.mp4"
    elif expected_type == "document" and message.get("document"):
        document = message["document"]
        file_id = document["file_id"]
        filename = document.get("file_name") or "document"
    if not file_id:
        raise ValueError(f"Telegram {expected_type} file is required")

    file_info = telegram("getFile", {"file_id": file_id})
    if not file_info or not file_info.get("file_path"):
        raise RuntimeError("Telegram fayl manzilini bermadi")
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(filename).suffix or mimetypes.guess_extension(
        message.get(expected_type, {}).get("mime_type", "")
    ) or ""
    path = (MEDIA_DIR / f"{uuid.uuid4().hex}{suffix}").resolve()
    request = urllib.request.Request(
        f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info['file_path']}"
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        path.write_bytes(response.read())
    return str(path), filename, message.get("caption", "")

def confirm_send_workflow(chat_id, user_id):
    workflow = WORKFLOWS[user_id]
    recipients = workflow["recipients"]
    recipient_type = workflow["recipient_type"]
    names = []
    if recipient_type == "group":
        for telegram_id in recipients:
            group = db.get_group_by_telegram_id(telegram_id)
            names.append(group["title"] if group else str(telegram_id))
    else:
        names = [str(recipients[0])]
    preview = workflow.get("text") or workflow.get("caption") or ""
    file_label = Path(workflow["media_path"]).name if workflow.get("media_path") else ""
    workflow["stage"] = "confirm"
    send_inline_message(
        chat_id,
        "📨 Xabarni yuborish\n\n"
        f"Recipient: {', '.join(names)}\n"
        f"Media: {file_label or 'text'}\n"
        f"Caption/xabar: {preview or '—'}",
        [[
            {"text": "✅ Yuborish", "callback_data": "send_confirm"},
            {"text": "❌ Bekor qilish", "callback_data": "workflow_cancel"},
        ]],
    )

def begin_schedule_workflow(chat_id, user_id):
    WORKFLOWS[user_id] = {"kind": "schedule", "stage": "recipient_type", "chat_id": chat_id}
    send_inline_message(
        chat_id,
        "📅 Kimga rejalashtirish?",
        [
            [{"text": "👤 User ID", "callback_data": "schedule_recipient:user"}],
            [{"text": "👥 Group ID", "callback_data": "schedule_recipient:group"}],
            [{"text": "❌ Bekor qilish", "callback_data": "workflow_cancel"}],
        ],
    )

def ask_schedule_type(chat_id, user_id):
    workflow = WORKFLOWS[user_id]
    workflow["stage"] = "type"
    send_inline_message(
        chat_id,
        "📨 Rejalashtirilgan xabar turi:",
        [
            [{"text": "📝 Text", "callback_data": "schedule_type:text"}],
            [{"text": "🖼 Rasm", "callback_data": "schedule_type:photo"}],
            [{"text": "🎥 Video", "callback_data": "schedule_type:video"}],
            [{"text": "📄 Fayl", "callback_data": "schedule_type:document"}],
            [{"text": "❌ Bekor qilish", "callback_data": "workflow_cancel"}],
        ],
    )

def handle_workflow_message(message, user_id, chat_id):
    workflow = WORKFLOWS.get(user_id)
    if not workflow or workflow.get("chat_id") != chat_id:
        return False

    text = (message.get("text") or "").strip()
    if text in ("/cancel", "⬅️ Orqaga"):
        WORKFLOWS.pop(user_id, None)
        send_message(chat_id, "Amal bekor qilindi.", main_menu())
        return True

    kind = workflow["kind"]
    stage = workflow["stage"]
    if stage in ("user_id", "recipient_id"):
        try:
            recipient_id = int(text)
        except ValueError:
            recipient_id = 0
        if stage == "user_id" and recipient_id <= 0:
            send_message(chat_id, "Iltimos, haqiqiy Telegram User ID raqamini yuboring.")
            return True
        if stage == "recipient_id" and workflow.get("recipient_type") == "user" and recipient_id <= 0:
            send_message(chat_id, "Iltimos, haqiqiy Telegram User ID raqamini yuboring.")
            return True
        if stage == "recipient_id" and workflow.get("recipient_type") == "group":
            if not db.get_group_by_telegram_id(recipient_id):
                send_message(chat_id, "Bu Group ID groups_ jadvalida topilmadi.")
                return True
        if not recipient_id:
            send_message(chat_id, "Recipient ID noto‘g‘ri.")
            return True
        workflow["recipient_id"] = recipient_id
        if kind == "send":
            workflow["recipients"] = [recipient_id]
            ask_message_content(chat_id, workflow)
        else:
            ask_schedule_type(chat_id, user_id)
        return True

    if stage == "content":
        message_type = workflow["message_type"]
        if message_type == "text":
            if not text:
                send_message(chat_id, "Xabar matni bo‘sh bo‘lmasin.")
                return True
            workflow["text"] = text
        else:
            try:
                media_path, filename, caption = download_telegram_media(
                    message, message_type
                )
            except Exception as error:
                logging.exception("Admin media download failed")
                send_message(chat_id, f"❌ Media qabul qilinmadi: {error}")
                return True
            workflow["media_path"] = media_path
            workflow["filename"] = filename
            workflow["caption"] = caption
        if kind == "send":
            confirm_send_workflow(chat_id, user_id)
        else:
            workflow["stage"] = "datetime"
            send_message(
                chat_id,
                "Sana va vaqtni yuboring (DD.MM.YYYY HH:MM), "
                f"timezone: {config.REPORT_TIMEZONE}.",
            )
        return True

    if stage == "datetime":
        try:
            local_zone = ZoneInfo(config.REPORT_TIMEZONE)
            local_time = datetime.strptime(text, "%d.%m.%Y %H:%M").replace(
                tzinfo=local_zone
            )
            if local_time <= datetime.now(local_zone):
                raise ValueError("Sana va vaqt kelajakda bo‘lishi kerak.")
        except (ValueError, KeyError) as error:
            send_message(
                chat_id,
                f"❌ Sana/vaqt noto‘g‘ri: {error}\n"
                "Masalan: 10.10.2026 18:30",
            )
            return True
        workflow["run_at"] = local_time.astimezone(timezone.utc).isoformat()
        workflow["stage"] = "schedule_confirm"
        target_type = workflow["recipient_type"]
        target_id = workflow["recipient_id"]
        preview = workflow.get("text") or workflow.get("caption") or ""
        send_inline_message(
            chat_id,
            "📅 Rejalashtirishni tasdiqlang\n\n"
            f"Recipient: {target_type} {target_id}\n"
            f"Vaqt: {local_time.strftime('%d.%m.%Y %H:%M')} "
            f"({config.REPORT_TIMEZONE})\n"
            f"Xabar: {preview or workflow.get('filename', 'media')}",
            [[
                {"text": "✅ Tasdiqlash", "callback_data": "schedule_confirm"},
                {"text": "❌ Bekor qilish", "callback_data": "workflow_cancel"},
            ]],
        )
        return True

    if stage == "customer_reply":
        if not text:
            send_message(chat_id, "Javob matni bo‘sh bo‘lmasin.")
            return True
        customer = db.get_customer_by_id(workflow["customer_id"])
        if not customer:
            WORKFLOWS.pop(user_id, None)
            send_message(chat_id, "Mijoz topilmadi.", main_menu())
            return True
        db.enqueue_outgoing_message(
            user_id,
            "user",
            customer["telegram_id"],
            text=text,
        )
        send_message(chat_id, "⏳ Javob UserBot navbatiga qo‘shildi.")
        WORKFLOWS.pop(user_id, None)
        return True

    if stage == "customer_tag":
        if not text:
            send_message(chat_id, "Tag bo‘sh bo‘lmasin.")
            return True
        customer_id = workflow["customer_id"]
        db.add_customer_tag(customer_id, text)
        customer = db.get_customer_by_id(customer_id)
        db.add_log(
            "customer_tag_added",
            "customer",
            customer["telegram_id"],
            {"tag": text},
            user_id,
        )
        WORKFLOWS.pop(user_id, None)
        show_customer_detail(chat_id, customer_id)
        return True

    if stage == "auto_keyword":
        if not text:
            send_message(chat_id, "Keyword bo‘sh bo‘lmasin.")
            return True
        workflow["keyword"] = text
        workflow["stage"] = "auto_response"
        send_message(chat_id, "Shu keyword uchun javob matnini yuboring:")
        return True

    if stage == "auto_response":
        if not text:
            send_message(chat_id, "Javob bo‘sh bo‘lmasin.")
            return True
        rule_id = db.add_auto_reply_rule(workflow["keyword"], text)
        db.add_log(
            "auto_reply_rule_created",
            "auto_reply_rule",
            rule_id,
            {"keyword": workflow["keyword"]},
            user_id,
        )
        WORKFLOWS.pop(user_id, None)
        send_message(chat_id, "✅ Keyword va javob saqlandi.", main_menu())
        return True

    if stage == "report_user_id":
        if not text.isdigit():
            send_message(chat_id, "Telegram User ID raqamini yuboring.")
            return True
        db.set_setting("report_user_id", text)
        db.add_log("settings_changed", "setting", "report_user_id", {}, user_id)
        WORKFLOWS.pop(user_id, None)
        send_message(chat_id, f"✅ Hisobot qabul qiluvchi ID: {text}", main_menu())
        return True

    if stage == "report_time":
        try:
            datetime.strptime(text, "%H:%M")
        except ValueError:
            send_message(chat_id, "Vaqtni HH:MM ko‘rinishida kiriting, masalan 21:00.")
            return True
        db.set_setting("report_time", text)
        db.add_log("settings_changed", "setting", "report_time", {}, user_id)
        WORKFLOWS.pop(user_id, None)
        send_message(chat_id, f"✅ Kunlik hisobot vaqti: {text}", main_menu())
        return True

    return False
