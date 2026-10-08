"""Admin handlers workflows."""
import json
import logging
import time

from app import database as db
from app.core import config
from app.core.config import ADMIN_USER_ID
from app.core.constants import WELCOME_DEFAULT
from .keyboards import back_keyboard, main_menu
from .states import GROUP_MESSAGE_STATES, GROUP_SELECTIONS, STATES, WORKFLOWS
from .transport import (
    answer_callback_query,
    edit_inline_message,
    read_env,
    send_inline_message,
    send_message,
    telegram,
    write_env,
)
from .auto_reply import show_auto_reply_menu, show_auto_reply_rules
from .backup import send_database_export, show_database_info, show_database_menu
from .customers import show_customer_detail, show_customers, show_unanswered
from .groups import handle_group_message_state, notify_group_message_results, request_group_message, show_groups
from .logs import show_logs
from .messaging import (
    ask_message_content,
    ask_send_recipient,
    begin_schedule_workflow,
    begin_send_workflow,
    handle_workflow_message,
    show_send_group_selection,
)
from .navigation import start
from .permissions import is_admin
from .statistics import show_statistics

OFFSET = 0


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

    if data == "main_menu":
        answer_callback_query(callback_id)
        WORKFLOWS.pop(user_id, None)
        GROUP_MESSAGE_STATES.pop(user_id, None)
        start(chat_id)
        return

    if data == "noop":
        answer_callback_query(callback_id)
        return

    if data.startswith("customers_page:"):
        answer_callback_query(callback_id)
        show_customers(chat_id, int(data.partition(":")[2]), user_id)
        return

    if data.startswith("customer_open:"):
        answer_callback_query(callback_id)
        show_customer_detail(chat_id, int(data.partition(":")[2]))
        return

    if data.startswith("customer_status:"):
        customer_id = int(data.partition(":")[2])
        answer_callback_query(callback_id)
        send_inline_message(
            chat_id,
            "Mijoz statusini tanlang:",
            [
                [{"text": "🆕 New", "callback_data": f"status_set:{customer_id}:new"}],
                [{"text": "🟡 Interested", "callback_data": f"status_set:{customer_id}:interested"}],
                [{"text": "🟢 Registered", "callback_data": f"status_set:{customer_id}:registered"}],
                [{"text": "🔴 Not interested", "callback_data": f"status_set:{customer_id}:not_interested"}],
                [{"text": "⬅️ Mijoz", "callback_data": f"customer_open:{customer_id}"}],
            ],
        )
        return

    if data.startswith("status_set:"):
        _, customer_id_text, status = data.split(":", 2)
        if status not in {"new", "interested", "registered", "not_interested"}:
            answer_callback_query(callback_id, "Status noto‘g‘ri.", True)
            return
        customer_id = int(customer_id_text)
        customer = db.get_customer_by_id(customer_id)
        db.set_customer_status(customer_id, status)
        db.add_log(
            "customer_status_changed",
            "customer",
            customer["telegram_id"] if customer else customer_id,
            {"status": status},
            user_id,
        )
        answer_callback_query(callback_id, "Status saqlandi.")
        show_customer_detail(chat_id, customer_id)
        return

    if data.startswith("customer_tag:"):
        customer_id = int(data.partition(":")[2])
        WORKFLOWS[user_id] = {
            "kind": "customer_tag",
            "stage": "customer_tag",
            "chat_id": chat_id,
            "customer_id": customer_id,
        }
        answer_callback_query(callback_id)
        send_message(chat_id, "Yangi tag nomini yuboring:", back_keyboard())
        return

    if data.startswith("customer_tag_remove:"):
        _, customer_id_text, tag_id_text = data.split(":", 2)
        customer_id = int(customer_id_text)
        db.remove_customer_tag(customer_id, int(tag_id_text))
        customer = db.get_customer_by_id(customer_id)
        db.add_log(
            "customer_tag_removed",
            "customer",
            customer["telegram_id"] if customer else customer_id,
            {"tag_id": int(tag_id_text)},
            user_id,
        )
        answer_callback_query(callback_id, "Tag o‘chirildi.")
        show_customer_detail(chat_id, customer_id)
        return

    if data.startswith("customer_reply:") or data.startswith("unanswered_reply:"):
        customer_id = int(data.partition(":")[2])
        customer = db.get_customer_by_id(customer_id)
        if not customer:
            answer_callback_query(callback_id, "Mijoz topilmadi.", True)
            return
        WORKFLOWS[user_id] = {
            "kind": "customer_reply",
            "stage": "customer_reply",
            "chat_id": chat_id,
            "customer_id": customer_id,
        }
        answer_callback_query(callback_id)
        send_message(
            chat_id,
            f"🆔 {customer['telegram_id']} uchun javobingizni yozing:",
            back_keyboard(),
        )
        return

    if data.startswith("unanswered_page:"):
        answer_callback_query(callback_id)
        show_unanswered(chat_id, int(data.partition(":")[2]))
        return

    if data == "auto_menu":
        answer_callback_query(callback_id)
        show_auto_reply_menu(chat_id)
        return

    if data == "auto_welcome":
        answer_callback_query(callback_id)
        show_welcome(chat_id)
        return

    if data == "auto_add":
        WORKFLOWS[user_id] = {
            "kind": "auto_reply",
            "stage": "auto_keyword",
            "chat_id": chat_id,
        }
        answer_callback_query(callback_id)
        send_message(chat_id, "Yangi keyword yuboring:", back_keyboard())
        return

    if data == "auto_list":
        answer_callback_query(callback_id)
        show_auto_reply_rules(chat_id)
        return

    if data == "auto_global_toggle":
        enabled = (db.get_setting("auto_reply_enabled", "true") or "true").lower() != "true"
        db.set_setting("auto_reply_enabled", str(enabled).lower())
        db.add_log(
            "settings_changed",
            "setting",
            "auto_reply_enabled",
            {"enabled": enabled},
            user_id,
        )
        answer_callback_query(callback_id, "Keyword javoblari holati yangilandi.")
        show_auto_reply_menu(chat_id)
        return

    if data.startswith("auto_toggle:"):
        _, rule_id, enabled = data.split(":")
        db.set_auto_reply_rule_enabled(int(rule_id), enabled == "1")
        db.add_log(
            "settings_changed",
            "auto_reply_rule",
            rule_id,
            {"enabled": enabled == "1"},
            user_id,
        )
        answer_callback_query(callback_id, "Keyword holati yangilandi.")
        show_auto_reply_rules(chat_id)
        return

    if data.startswith("auto_delete:"):
        rule_id = int(data.partition(":")[2])
        db.delete_auto_reply_rule(rule_id)
        db.add_log("auto_reply_rule_deleted", "auto_reply_rule", rule_id, {}, user_id)
        answer_callback_query(callback_id, "Keyword o‘chirildi.")
        show_auto_reply_rules(chat_id)
        return

    if data.startswith("logs_page:"):
        answer_callback_query(callback_id)
        show_logs(chat_id, int(data.partition(":")[2]))
        return

    if data == "send_confirm":
        workflow = WORKFLOWS.get(user_id)
        if not workflow or workflow.get("kind") != "send" or workflow.get("stage") != "confirm":
            answer_callback_query(callback_id, "Tasdiqlash holati topilmadi.", True)
            return
        queued = 0
        for recipient_id in workflow["recipients"]:
            db.enqueue_outgoing_message(
                user_id,
                workflow["recipient_type"],
                recipient_id,
                workflow["message_type"],
                workflow.get("text"),
                workflow.get("media_path"),
                workflow.get("caption"),
            )
            queued += 1
        db.add_log(
            "message_queued",
            workflow["recipient_type"],
            ",".join(map(str, workflow["recipients"])),
            {"message_type": workflow["message_type"], "count": queued},
            user_id,
        )
        WORKFLOWS.pop(user_id, None)
        answer_callback_query(callback_id, "Xabar navbatga qo‘shildi.")
        edit_inline_message(chat_id, message_id, f"✅ {queued} ta recipient uchun navbatga qo‘shildi.")
        return

    if data.startswith("send_type:"):
        workflow = WORKFLOWS.get(user_id)
        if not workflow or workflow.get("kind") != "send":
            answer_callback_query(callback_id, "Xabar yuborish holati topilmadi.", True)
            return
        message_type = data.partition(":")[2]
        if message_type not in {"text", "photo", "video", "document"}:
            answer_callback_query(callback_id, "Xabar turi noto‘g‘ri.", True)
            return
        workflow["message_type"] = message_type
        answer_callback_query(callback_id)
        ask_send_recipient(chat_id, user_id)
        return

    if data.startswith("send_recipient:"):
        workflow = WORKFLOWS.get(user_id)
        if not workflow:
            answer_callback_query(callback_id, "Holat topilmadi.", True)
            return
        recipient_type = data.partition(":")[2]
        if recipient_type not in {"user", "group"}:
            answer_callback_query(callback_id, "Recipient turi noto‘g‘ri.", True)
            return
        workflow["recipient_type"] = recipient_type
        if workflow["recipient_type"] == "user":
            workflow["stage"] = "user_id"
            answer_callback_query(callback_id)
            send_message(chat_id, "🆔 Telegram User ID kiriting:", back_keyboard())
        else:
            workflow["recipients"] = []
            workflow["stage"] = "groups"
            answer_callback_query(callback_id)
            show_send_group_selection(chat_id, user_id)
        return

    if data.startswith("send_group:"):
        workflow = WORKFLOWS.get(user_id)
        if not workflow or workflow.get("kind") != "send":
            answer_callback_query(callback_id, "Xabar yuborish holati topilmadi.", True)
            return
        telegram_id = int(data.partition(":")[2])
        selected = workflow.setdefault("recipients", [])
        if telegram_id in selected:
            selected.remove(telegram_id)
        else:
            selected.append(telegram_id)
        answer_callback_query(callback_id)
        show_send_group_selection(chat_id, user_id)
        return

    if data == "send_groups_done":
        workflow = WORKFLOWS.get(user_id)
        if not workflow or not workflow.get("recipients"):
            answer_callback_query(callback_id, "Kamida bitta guruh tanlang.", True)
            return
        answer_callback_query(callback_id)
        ask_message_content(chat_id, workflow)
        return

    if data == "workflow_cancel":
        WORKFLOWS.pop(user_id, None)
        answer_callback_query(callback_id, "Bekor qilindi.")
        edit_inline_message(chat_id, message_id, "❌ Amal bekor qilindi.")
        return

    if data.startswith("schedule_recipient:"):
        workflow = WORKFLOWS.get(user_id)
        if not workflow or workflow.get("kind") != "schedule":
            answer_callback_query(callback_id, "Rejalashtirish holati topilmadi.", True)
            return
        recipient_type = data.partition(":")[2]
        if recipient_type not in {"user", "group"}:
            answer_callback_query(callback_id, "Recipient turi noto‘g‘ri.", True)
            return
        workflow["recipient_type"] = recipient_type
        workflow["stage"] = "recipient_id"
        answer_callback_query(callback_id)
        send_message(
            chat_id,
            "🆔 Telegram User ID yoki Group ID kiriting:",
            back_keyboard(),
        )
        return

    if data.startswith("schedule_type:"):
        workflow = WORKFLOWS.get(user_id)
        if not workflow or workflow.get("kind") != "schedule":
            answer_callback_query(callback_id, "Rejalashtirish holati topilmadi.", True)
            return
        message_type = data.partition(":")[2]
        if message_type not in {"text", "photo", "video", "document"}:
            answer_callback_query(callback_id, "Xabar turi noto‘g‘ri.", True)
            return
        workflow["message_type"] = message_type
        answer_callback_query(callback_id)
        ask_message_content(chat_id, workflow)
        return

    if data == "schedule_confirm":
        workflow = WORKFLOWS.get(user_id)
        if (
            not workflow
            or workflow.get("kind") != "schedule"
            or workflow.get("stage") != "schedule_confirm"
        ):
            answer_callback_query(callback_id, "Tasdiqlash holati topilmadi.", True)
            return
        task_id = db.create_scheduled_message(
            user_id,
            workflow["recipient_type"],
            workflow["recipient_id"],
            workflow.get("text"),
            workflow["run_at"],
            message_type=workflow["message_type"],
            media_path=workflow.get("media_path"),
            caption=workflow.get("caption"),
        )
        db.add_log(
            "scheduled_message_created",
            workflow["recipient_type"],
            workflow["recipient_id"],
            {"scheduled_message_id": task_id},
            user_id,
        )
        WORKFLOWS.pop(user_id, None)
        answer_callback_query(callback_id, "Rejalashtirildi.")
        edit_inline_message(chat_id, message_id, f"✅ Xabar rejalashtirildi. ID: {task_id}")
        return

    if data in ("report_user_id", "report_time"):
        WORKFLOWS[user_id] = {
            "kind": "report_settings",
            "stage": data,
            "chat_id": chat_id,
        }
        answer_callback_query(callback_id)
        prompt = (
            "Telegram User ID kiriting:"
            if data == "report_user_id"
            else f"Vaqtni HH:MM kiriting (timezone: {config.REPORT_TIMEZONE}):"
        )
        send_message(chat_id, prompt, back_keyboard())
        return

    if data == "backup_export":
        answer_callback_query(callback_id)
        send_database_export(chat_id, requested_by=user_id)
        return

    if data == "backup_send":
        target = (
            config.BACKUP_USER_ID
            or ADMIN_USER_ID
            or user_id
        )
        answer_callback_query(callback_id)
        send_database_export(chat_id, target, user_id, backup=True)
        return

    if data == "database_info":
        answer_callback_query(callback_id)
        show_database_info(chat_id)
        return

    answer_callback_query(callback_id, "Noma’lum amal.", True)

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
        db.add_log("settings_changed", "setting", "monitor_minutes", {}, user_id)

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
        db.add_log("settings_changed", "setting", "welcome_message", {}, user_id)

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
        WORKFLOWS.pop(user_id, None)
        start(chat_id)
        return

    if text == "/menu":
        GROUP_MESSAGE_STATES.pop(user_id, None)
        WORKFLOWS.pop(user_id, None)
        start(chat_id)
        return
    if text == "/cancel":
        WORKFLOWS.pop(user_id, None)
        GROUP_MESSAGE_STATES.pop(user_id, None)
        STATES.pop(chat_id, None)
        send_message(chat_id, "Amal bekor qilindi.", main_menu())
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

    if text in ("🤖 Avtojavob", "💬 Avtojavob"):
        show_auto_reply_menu(chat_id)
        return

    if text == "📋 Guruhlar":
        show_groups(chat_id, user_id)
        return

    if text == "👥 Mijozlar":
        WORKFLOWS.pop(user_id, None)
        show_customers(chat_id, 0, user_id)
        return

    if text == "🚨 Javobsizlar":
        WORKFLOWS.pop(user_id, None)
        show_unanswered(chat_id)
        return

    if text == "📅 Rejalashtirish":
        begin_schedule_workflow(chat_id, user_id)
        return

    if text == "📨 Xabar yuborish":
        begin_send_workflow(chat_id, user_id)
        return

    if text == "🏷 Status / Tag":
        show_customers(chat_id, 0, user_id)
        return

    if text == "📊 Statistika":
        show_statistics(chat_id)
        return

    if text == "📊 Hisobot sozlamalari":
        send_inline_message(
            chat_id,
            "📊 Hisobot sozlamalari",
            [
                [{"text": "🆔 Qabul qiluvchi ID", "callback_data": "report_user_id"}],
                [{"text": "⏰ Hisobot vaqti", "callback_data": "report_time"}],
                [{"text": "⬅️ Orqaga", "callback_data": "main_menu"}],
            ],
        )
        return

    if text == "📋 Loglar":
        show_logs(chat_id)
        return

    if text in ("💾 Database", "🗄️ Database"):
        show_database_menu(chat_id)
        return

    if text == "📊 Holat":
        show_status(chat_id)
        return

    if text == "💬 Avtojavob sozlamasi":
        show_welcome(chat_id)
        return

    if handle_workflow_message(message, user_id, chat_id):
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
