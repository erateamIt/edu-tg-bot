"""Logs database operations."""
from psycopg2.extras import Json, RealDictCursor

from .connection import get_db, now_iso

def add_log(action, target_type=None, target_id=None, details=None, admin_user_id=None):
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute(
                """INSERT INTO logs
                (admin_user_id,action,target_type,target_id,details,created_at)
                VALUES(%s,%s,%s,%s,%s,%s)""",
                (
                    admin_user_id,
                    action,
                    target_type,
                    str(target_id) if target_id is not None else None,
                    Json(details or {}),
                    now_iso(),
                ),
            )

def list_logs_page(page=0, page_size=8):
    offset = max(0, page) * page_size
    with get_db() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM logs ORDER BY id DESC LIMIT %s OFFSET %s",
                (page_size, offset),
            )
            return cur.fetchall()
