"""Messages database operations."""
from psycopg2.extras import RealDictCursor

from .connection import get_db, now_iso

def get_unanswered_page(page=0, page_size=5):
    offset = max(0, page) * page_size
    with get_db() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT * FROM (
                    SELECT DISTINCT ON (c.id)
                        c.id, c.telegram_id, c.username, c.first_name, c.last_name,
                        m.id AS message_db_id, m.text AS pending_text,
                        m.sent_at AS pending_sent_at
                    FROM customers c
                    JOIN messages m ON m.customer_id=c.id
                    WHERE m.direction='in' AND m.answered=FALSE
                    ORDER BY c.id, m.id DESC
                ) pending
                ORDER BY pending_sent_at
                LIMIT %s OFFSET %s""",
                (page_size, offset),
            )
            return cur.fetchall()

def count_unanswered():
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute(
                """SELECT COUNT(*) FROM (
                    SELECT DISTINCT m.customer_id
                    FROM messages m
                    WHERE m.direction='in' AND m.answered=FALSE
                ) pending"""
            )
            return cur.fetchone()[0]

def record_customer_reply(customer_id, text, telegram_message_id, sent_at, auto_reply=False):
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute(
                """INSERT INTO messages
                (customer_id,telegram_message_id,direction,text,sent_at,answered,auto_reply)
                SELECT %s,%s,'out',%s,%s,TRUE,%s
                WHERE NOT EXISTS (
                    SELECT 1 FROM messages
                    WHERE customer_id=%s AND telegram_message_id=%s AND direction='out'
                )""",
                (
                    customer_id, telegram_message_id, text, sent_at, bool(auto_reply),
                    customer_id, telegram_message_id,
                ),
            )
            cur.execute(
                """UPDATE messages SET answered=TRUE
                WHERE customer_id=%s AND direction='in' AND answered=FALSE""",
                (customer_id,),
            )
            cur.execute(
                "UPDATE customers SET status='answered',updated_at=%s WHERE id=%s",
                (sent_at, customer_id),
            )

def add_message(
    customer_id,
    telegram_message_id,
    direction,
    text,
    sent_at,
    answered=False,
    auto_reply=False,
):
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute(
                """INSERT INTO messages
                (customer_id,telegram_message_id,direction,text,sent_at,answered,auto_reply)
                VALUES(%s,%s,%s,%s,%s,%s,%s)""",
                (customer_id, telegram_message_id, direction, text, sent_at, answered, auto_reply),
            )

def mark_customer_waiting(customer_id):
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute(
                "UPDATE customers SET status='waiting', updated_at=%s WHERE id=%s",
                (now_iso(), customer_id),
            )

def get_unanswered():
    with get_db() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""SELECT c.*, m.id AS message_db_id, m.text AS pending_text, m.sent_at AS pending_sent_at
                FROM customers c
                JOIN messages m ON m.customer_id=c.id
                WHERE m.direction='in' AND m.answered=FALSE
                AND m.id=(SELECT MAX(m2.id) FROM messages m2
                          WHERE m2.customer_id=c.id AND m2.direction='in' AND m2.answered=FALSE)
                ORDER BY m.sent_at ASC""")
            return cur.fetchall()

def mark_customer_overdue(customer_id):
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute(
                "UPDATE customers SET status='overdue',updated_at=%s WHERE id=%s",
                (now_iso(), customer_id),
            )

def list_messages(customer_id, limit=200):
    with get_db() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM messages WHERE customer_id=%s ORDER BY sent_at ASC LIMIT %s",
                (customer_id, limit),
            )
            return cur.fetchall()
