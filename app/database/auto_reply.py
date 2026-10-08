"""Auto reply database operations."""
from psycopg2.extras import RealDictCursor

from .connection import get_db, now_iso

def list_auto_reply_rules():
    with get_db() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM auto_reply_rules ORDER BY keyword")
            return cur.fetchall()

def add_auto_reply_rule(keyword, response):
    current = now_iso()
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute(
                """INSERT INTO auto_reply_rules(keyword,response,created_at,updated_at)
                VALUES(%s,%s,%s,%s)
                ON CONFLICT(keyword) DO UPDATE SET response=EXCLUDED.response,
                enabled=TRUE, updated_at=EXCLUDED.updated_at RETURNING id""",
                (keyword.strip(), response, current, current),
            )
            return cur.fetchone()[0]

def get_matching_auto_reply(text):
    with get_db() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT * FROM auto_reply_rules
                WHERE enabled=TRUE AND POSITION(LOWER(keyword) IN LOWER(%s)) > 0
                ORDER BY LENGTH(keyword) DESC, id
                LIMIT 1""",
                (text,),
            )
            return cur.fetchone()

def set_auto_reply_rule_enabled(rule_id, enabled):
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute(
                "UPDATE auto_reply_rules SET enabled=%s,updated_at=%s WHERE id=%s",
                (bool(enabled), now_iso(), rule_id),
            )

def delete_auto_reply_rule(rule_id):
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute("DELETE FROM auto_reply_rules WHERE id=%s", (rule_id,))
