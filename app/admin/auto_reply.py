"""Admin auto reply workflows."""
from app import database as db
from .transport import send_inline_message


def show_auto_reply_menu(chat_id):
    rules = db.list_auto_reply_rules()
    enabled = (db.get_setting("auto_reply_enabled", "true") or "true").lower() == "true"
    text = (
        "🤖 Avtojavob\n\n"
        f"Keyword javoblari: {'🟢 Yoqilgan' if enabled else '🔴 O‘chirilgan'}\n"
        "Oddiy welcome xabari keyword mos kelmaganda ishlaydi."
    )
    keyboard = [
        [{"text": "➕ Keyword qo‘shish", "callback_data": "auto_add"}],
        [{"text": "📋 Keywordlar", "callback_data": "auto_list"}],
        [{
            "text": "🔄 Keyword javoblarini o‘chirish" if enabled else "🔄 Keyword javoblarini yoqish",
            "callback_data": "auto_global_toggle",
        }],
        [{"text": "✏️ Welcome xabari", "callback_data": "auto_welcome"}],
        [{"text": "⬅️ Orqaga", "callback_data": "main_menu"}],
    ]
    if rules:
        text += f"\nFaol keyword qoidalari: {sum(bool(rule['enabled']) for rule in rules)}"
    send_inline_message(chat_id, text, keyboard)

def show_auto_reply_rules(chat_id):
    rules = db.list_auto_reply_rules()
    keyboard = []
    lines = ["📋 Keywordlar", ""]
    for rule in rules:
        status = "🟢" if rule["enabled"] else "🔴"
        lines.append(f"{status} {rule['keyword']} → {rule['response'][:100]}")
        keyboard.append([
            {
                "text": f"{'🔴' if rule['enabled'] else '🟢'} {rule['keyword'][:25]}",
                "callback_data": f"auto_toggle:{rule['id']}:{int(not rule['enabled'])}",
            },
            {
                "text": "🗑",
                "callback_data": f"auto_delete:{rule['id']}",
            },
        ])
    if not rules:
        lines.append("Keywordlar hali qo‘shilmagan.")
    keyboard.append([{"text": "⬅️ Orqaga", "callback_data": "auto_menu"}])
    send_inline_message(chat_id, "\n".join(lines), keyboard)
