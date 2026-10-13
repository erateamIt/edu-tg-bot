"""Customers database operations."""
from datetime import datetime, timezone

from psycopg2.extras import RealDictCursor

from .connection import get_db, now_iso

def upsert_customer(tg_id, username, first_name, last_name, phone, text, sent_at):
    with get_db() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM customers WHERE telegram_id=%s", (tg_id,))
            row = cur.fetchone()
            if row:
                cur.execute(
                    """UPDATE customers SET username=%s, first_name=%s, last_name=%s,
                    phone=COALESCE(%s,phone), last_message=%s, last_message_at=%s,
                    updated_at=%s WHERE telegram_id=%s""",
                    (username, first_name, last_name, phone, text, sent_at, sent_at, tg_id),
                )
                return row["id"], False

            cur.execute(
                """INSERT INTO customers
                (telegram_id,username,first_name,last_name,phone,status,first_message,last_message,last_message_at,created_at,updated_at)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id""",
                (tg_id, username, first_name, last_name, phone, "waiting",
                 text, text, sent_at, sent_at, sent_at),
            )
            return cur.fetchone()["id"], True

def count_customers():
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM customers")
            return cur.fetchone()[0]

def count_new_customers():
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute(
                """SELECT COUNT(*) FROM customers
                WHERE created_at::timestamptz >= %s::timestamptz""",
                (datetime.now(timezone.utc).date().isoformat(),),
            )
            return cur.fetchone()[0]

def list_customers_page(page=0, page_size=5):
    offset = max(0, page) * page_size
    with get_db() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT c.*,
                    COALESCE(array_agg(t.name) FILTER (WHERE t.name IS NOT NULL), '{}') AS tags
                FROM customers c
                LEFT JOIN customer_tags ct ON ct.customer_id=c.id
                LEFT JOIN tags t ON t.id=ct.tag_id
                GROUP BY c.id
                ORDER BY c.updated_at DESC, c.id DESC
                LIMIT %s OFFSET %s""",
                (page_size, offset),
            )
            return cur.fetchall()

def get_customer(customer_id):
    with get_db() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT c.*,
                    COALESCE(array_agg(t.name) FILTER (WHERE t.name IS NOT NULL), '{}') AS tags
                FROM customers c
                LEFT JOIN customer_tags ct ON ct.customer_id=c.id
                LEFT JOIN tags t ON t.id=ct.tag_id
                WHERE c.id=%s
                GROUP BY c.id""",
                (customer_id,),
            )
            return cur.fetchone()

def get_customer_by_id(customer_id):
    with get_db() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM customers WHERE id=%s", (customer_id,))
            return cur.fetchone()

def get_customer_by_telegram_id(telegram_id):
    with get_db() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM customers WHERE telegram_id=%s", (telegram_id,))
            return cur.fetchone()

def list_customers(limit=100):
    with get_db() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM customers ORDER BY updated_at DESC LIMIT %s", (limit,))
            return cur.fetchall()

def set_customer_status(customer_id, status, status_source="manual"):
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute(
                "UPDATE customers SET lead_status=%s, status_source=%s, updated_at=%s WHERE id=%s",
                (status, status_source, now_iso(), customer_id),
            )
