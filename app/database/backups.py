"""Backups database operations."""
from psycopg2.extras import RealDictCursor

from .connection import get_db

def _all_rows(cur, table):
    cur.execute(f"SELECT * FROM {table}")
    return [dict(row) for row in cur.fetchall()]

def export_database():
    """Loyiha jadvallarini bitta JSON obyektga yig'adi.

    Bu funksiya admin botdagi '🗄️ Database' tugmasi orqali ishlatiladi.
    """
    tables = [
        "customers",
        "messages",
        "groups_",
        "scheduled_messages",
        "settings",
        "group_message_jobs",
        "tags",
        "customer_tags",
        "auto_reply_rules",
        "outgoing_messages",
        "logs",
    ]
    result = {}
    with get_db() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            for table in tables:
                result[table] = _all_rows(cur, table)
            result["settings"] = [
                row for row in result["settings"]
                if not any(
                    secret in row["key"].lower()
                    for secret in ("password", "token", "api_hash", "secret")
                )
            ]
    return result

def database_info():
    tables = [
        "customers", "messages", "groups_", "scheduled_messages", "settings",
        "group_message_jobs", "tags", "customer_tags", "auto_reply_rules",
        "outgoing_messages", "logs",
    ]
    with get_db() as con:
        with con.cursor() as cur:
            counts = {}
            for table in tables:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cur.fetchone()[0]
            return counts
