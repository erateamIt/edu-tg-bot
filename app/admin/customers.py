"""Admin customers workflows."""
from datetime import datetime, timezone

from app import database as db
from .keyboards import main_menu
from .transport import send_inline_message, send_message


def ago(value):
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        seconds = max(0, int((datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds()))
    except (TypeError, ValueError):
        return str(value or "—")
    if seconds < 60:
        return f"{seconds} soniya oldin"
    if seconds < 3600:
        return f"{seconds // 60} daqiqa oldin"
    if seconds < 86400:
        return f"{seconds // 3600} soat oldin"
    return f"{seconds // 86400} kun oldin"

def customer_status_label(status):
    labels = {
        "new": "🆕 New",
        "waiting": "🚨 Waiting",
        "overdue": "🔴 Javobsiz",
        "answered": "✅ Answered",
        "interested": "🟡 Interested",
        "registered": "🟢 Registered",
        "not_interested": "🔴 Not interested",
    }
    return labels.get(status, status or "—")

def show_customers(chat_id, page=0, user_id=None):
    page_size = 5
    total = db.count_customers()
    pages = max(1, (total + page_size - 1) // page_size)
    page = max(0, min(page, pages - 1))
    customers = db.list_customers_page(page, page_size)
    lines = [
        "👥 Mijozlar",
        f"Jami: {total} | Yangi: {db.count_new_customers()}",
        "",
    ]
    keyboard = []
    for customer in customers:
        name = " ".join(
            part for part in (customer["first_name"], customer["last_name"]) if part
        ) or "Nomsiz mijoz"
        username = f"@{customer['username']}" if customer["username"] else "username yo‘q"
        lines.extend([
            f"👤 {name}",
            f"🆔 {customer['telegram_id']} | 🔗 {username}",
            f"💬 {customer['last_message'] or '—'}",
            f"🕐 {ago(customer['last_message_at'])}",
            f"🏷 {', '.join(customer['tags']) or 'tag yo‘q'} | "
            f"{customer_status_label(customer['lead_status'])}",
            "",
        ])
        keyboard.append([{
            "text": f"👤 {name[:35]}",
            "callback_data": f"customer_open:{customer['id']}",
        }])
    if not customers:
        lines.append("Hozircha mijoz yo‘q.")
    nav = []
    if page > 0:
        nav.append({"text": "⬅️", "callback_data": f"customers_page:{page - 1}"})
    nav.append({"text": f"{page + 1}/{pages}", "callback_data": "noop"})
    if page + 1 < pages:
        nav.append({"text": "➡️", "callback_data": f"customers_page:{page + 1}"})
    keyboard.append(nav)
    keyboard.append([{"text": "⬅️ Orqaga", "callback_data": "main_menu"}])
    send_inline_message(chat_id, "\n".join(lines), keyboard)

def show_customer_detail(chat_id, customer_id):
    customer = db.get_customer(customer_id)
    if not customer:
        send_message(chat_id, "Mijoz topilmadi.", main_menu())
        return
    name = " ".join(
        part for part in (customer["first_name"], customer["last_name"]) if part
    ) or "Nomsiz mijoz"
    username = f"@{customer['username']}" if customer["username"] else "username yo‘q"
    tag_rows = db.list_customer_tags(customer_id)
    tag_summary = ", ".join(
        f"{tag['name']} ({'🤖 Automatic' if (tag.get('source') or 'manual') in {'keyword', 'ai'} else '👨‍💼 Manual'})"
        for tag in tag_rows
    ) if tag_rows else "yo‘q"
    text = (
        f"👤 {name}\n🆔 {customer['telegram_id']}\n🔗 {username}\n\n"
        f"Status: {customer_status_label(customer['lead_status'])}\n"
        f"Tags: {tag_summary}\n\n"
        f"Oxirgi xabar: {customer['last_message'] or '—'}\n"
        f"Vaqt: {ago(customer['last_message_at'])}"
    )
    keyboard = [
        [
            {"text": "🏷 Tag", "callback_data": f"customer_tag:{customer_id}"},
            {"text": "🔄 Status", "callback_data": f"customer_status:{customer_id}"},
        ],
        [{"text": "💬 Message", "callback_data": f"customer_reply:{customer_id}"}],
        *[
            [{
                "text": f"🗑 {tag['name'][:30]}",
                "callback_data": f"customer_tag_remove:{customer_id}:{tag['id']}",
            }]
            for tag in db.list_customer_tags(customer_id)
        ],
        [{"text": "⬅️ Mijozlar", "callback_data": "customers_page:0"}],
    ]
    send_inline_message(chat_id, text, keyboard)

def show_unanswered(chat_id, page=0):
    page_size = 5
    total = db.count_unanswered()
    pages = max(1, (total + page_size - 1) // page_size)
    page = max(0, min(page, pages - 1))
    rows = db.get_unanswered_page(page, page_size)
    lines = [f"🚨 Javobsizlar: {total}", ""]
    keyboard = []
    for row in rows:
        name = " ".join(
            part for part in (row["first_name"], row["last_name"]) if part
        ) or "Nomsiz mijoz"
        lines.extend([
            f"👤 {name}\n🆔 {row['telegram_id']}",
            f"💬 {row['pending_text'] or '—'}",
            f"⏱ {ago(row['pending_sent_at'])}",
            "",
        ])
        keyboard.append([{
            "text": f"💬 Javob berish: {name[:30]}",
            "callback_data": f"unanswered_reply:{row['id']}",
        }])
    if not rows:
        lines.append("Javobsiz xabarlar yo‘q.")
    nav = []
    if page:
        nav.append({"text": "⬅️", "callback_data": f"unanswered_page:{page - 1}"})
    nav.append({"text": f"{page + 1}/{pages}", "callback_data": "noop"})
    if page + 1 < pages:
        nav.append({"text": "➡️", "callback_data": f"unanswered_page:{page + 1}"})
    keyboard.extend([nav, [{"text": "⬅️ Orqaga", "callback_data": "main_menu"}]])
    send_inline_message(chat_id, "\n".join(lines), keyboard)
