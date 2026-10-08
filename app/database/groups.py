"""Groups database operations."""
from psycopg2.extras import RealDictCursor

from .connection import get_db, now_iso

def sync_group(tg_id, title, username):
    current = now_iso()
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute(
                """INSERT INTO groups_(telegram_id,title,username,enabled,created_at,updated_at)
                VALUES(%s,%s,%s,FALSE,%s,%s)
                ON CONFLICT(telegram_id) DO UPDATE SET title=EXCLUDED.title,
                username=EXCLUDED.username, updated_at=EXCLUDED.updated_at""",
                (tg_id, title, username, current, current),
            )

def list_groups():
    with get_db() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM groups_ ORDER BY title")
            return cur.fetchall()

def get_groups():
    return list_groups()

def get_group_by_telegram_id(telegram_id):
    with get_db() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM groups_ WHERE telegram_id=%s",
                (telegram_id,),
            )
            return cur.fetchone()

def set_group_enabled(tg_id, enabled):
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute(
                "UPDATE groups_ SET enabled=%s, updated_at=%s WHERE telegram_id=%s",
                (bool(enabled), now_iso(), tg_id),
            )
