"""Admin groups workflows."""
from app import database as db
from .keyboards import back_keyboard, main_menu
from .states import GROUP_MESSAGE_STATES, GROUP_SELECTIONS
from .transport import send_inline_message, send_message


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
