"""Admin logs workflows."""
from datetime import datetime
import json
from app import database as db
from .transport import send_inline_message


def show_logs(chat_id, page=0):
    rows = db.list_logs_page(page, 8)
    lines = ["📋 LOG", ""]
    for row in rows:
        try:
            timestamp = datetime.fromisoformat(row["created_at"]).astimezone().strftime("%H:%M")
        except (TypeError, ValueError):
            timestamp = row["created_at"]
        details = row["details"] or {}
        lines.extend([
            f"🕐 {timestamp} | {row['action']}",
            f"👤 Admin: {row['admin_user_id'] or '—'}",
            f"🎯 {row['target_type'] or '—'}: {row['target_id'] or '—'}",
            f"ℹ️ {json.dumps(details, ensure_ascii=False)[:180]}",
            "----------------",
        ])
    if not rows:
        lines.append("Log topilmadi.")
    keyboard = []
    if page:
        keyboard.append([{"text": "⬅️ Oldingi", "callback_data": f"logs_page:{page - 1}"}])
    if len(rows) == 8:
        keyboard.append([{"text": "Keyingi ➡️", "callback_data": f"logs_page:{page + 1}"}])
    keyboard.append([{"text": "⬅️ Orqaga", "callback_data": "main_menu"}])
    send_inline_message(chat_id, "\n".join(lines), keyboard)
