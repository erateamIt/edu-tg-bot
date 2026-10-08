"""Admin statistics workflows."""
from datetime import datetime, timezone

from app import database as db
from .keyboards import main_menu
from .transport import send_message


def show_statistics(chat_id):
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    stats = db.get_daily_stats(start.isoformat(), now.isoformat())
    text = (
        "📊 Bugungi statistika\n\n"
        f"👥 Yangi mijozlar: {stats['new_customers']}\n"
        f"💬 Kelgan xabarlar: {stats['incoming_messages']}\n"
        f"🤖 AutoReply: {stats['auto_replies']}\n"
        f"👨‍💼 Admin javoblari: {stats['admin_replies']}\n"
        f"🚨 Javobsiz: {db.count_unanswered()}\n"
        f"📨 Yuborilgan: {stats['sent_messages']}\n"
        f"🖼 Media: {stats['sent_media']}\n"
        f"👥 Guruh xabarlari: {stats['group_messages']}\n"
        f"📈 Top keyword: {stats['top_inquiry']}\n"
        f"🏷 Top tag: {stats['top_tag']}"
    )
    send_message(chat_id, text, main_menu())
