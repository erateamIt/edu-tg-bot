"""Tags database operations."""
from psycopg2.extras import RealDictCursor

from .connection import get_db, now_iso

def list_customer_tags(customer_id):
    with get_db() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT t.id, t.name FROM tags t
                JOIN customer_tags ct ON ct.tag_id=t.id
                WHERE ct.customer_id=%s ORDER BY t.name""",
                (customer_id,),
            )
            return cur.fetchall()

def add_customer_tag(customer_id, name):
    name = name.strip()
    current = now_iso()
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute(
                """INSERT INTO tags(name,created_at) VALUES(%s,%s)
                ON CONFLICT(name) DO UPDATE SET name=EXCLUDED.name
                RETURNING id""",
                (name, current),
            )
            tag_id = cur.fetchone()[0]
            cur.execute(
                """INSERT INTO customer_tags(customer_id,tag_id,created_at)
                VALUES(%s,%s,%s) ON CONFLICT(customer_id,tag_id) DO NOTHING""",
                (customer_id, tag_id, current),
            )
            cur.execute(
                "UPDATE customers SET updated_at=%s WHERE id=%s",
                (current, customer_id),
            )

def remove_customer_tag(customer_id, tag_id):
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute(
                "DELETE FROM customer_tags WHERE customer_id=%s AND tag_id=%s",
                (customer_id, tag_id),
            )
