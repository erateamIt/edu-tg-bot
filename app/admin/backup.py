"""Admin backup workflows."""
import json
import logging
import time

from app import database as db
from app.utils.files import write_json_export
from .keyboards import main_menu
from .transport import send_document, send_inline_message, send_message


def show_database_menu(chat_id):
    send_inline_message(
        chat_id,
        "💾 Database",
        [
            [{"text": "📤 JSON Export", "callback_data": "backup_export"}],
            [{"text": "💾 Backup", "callback_data": "backup_send"}],
            [{"text": "📊 Database info", "callback_data": "database_info"}],
            [{"text": "⬅️ Orqaga", "callback_data": "main_menu"}],
        ],
    )

def send_database_export(chat_id, recipient_id=None, requested_by=None, backup=False):
    try:
        data = db.export_database()
        content = json.dumps(data, ensure_ascii=False, indent=2, default=str)
        prefix = "education_backup" if backup else "education_export"
        filename = f"{prefix}_{time.strftime('%Y%m%d_%H%M%S')}.json"
        write_json_export(filename, content, backup=backup)
        target = recipient_id or chat_id
        if send_document(target, filename, content, "PostgreSQL JSON backup"):
            db.add_log(
                "backup_created",
                "user",
                target,
                {"filename": filename},
                requested_by,
            )
        elif target != chat_id:
            send_message(chat_id, "❌ Backup faylini yuborib bo‘lmadi.", main_menu())
    except Exception:
        logging.exception("Database export failed")
        send_message(chat_id, "❌ Database backup yaratilmadi.", main_menu())

def show_database_info(chat_id):
    counts = db.database_info()
    text = "📊 Database info\n\n" + "\n".join(
        f"{table}: {count}" for table, count in counts.items()
    )
    send_message(chat_id, text, main_menu())
