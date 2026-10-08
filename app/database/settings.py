"""Settings database operations."""
from psycopg2.extras import RealDictCursor

from .connection import get_db

def get_setting(key, default=None):
    with get_db() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT value FROM settings WHERE key=%s", (key,))
            row = cur.fetchone()
            return row["value"] if row else default

def set_setting(key, value):
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute(
                "INSERT INTO settings(key,value) VALUES(%s,%s) "
                "ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value",
                (key, str(value)),
            )
