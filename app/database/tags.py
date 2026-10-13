"""Tags database operations."""
import re

from psycopg2.extras import RealDictCursor

from .connection import get_db, now_iso


def slugify(value):
    if value is None:
        return None
    slug = value.strip().lower()
    slug = slug.replace("’", "'").replace("‘", "'").replace("ʻ", "'")
    slug = slug.replace("о'", "o'").replace("o’", "o'").replace("o‘", "o'")
    slug = re.sub(r"[^a-z0-9_\s-]", "", slug)
    slug = slug.replace(" ", "_").replace("-", "_")
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "tag"


def ensure_tag(name, slug=None, description=None):
    text = (name or "").strip()
    if not text:
        return None
    tag_slug = (slug or slugify(text) or "tag").strip()
    current = now_iso()
    with get_db() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO tags(name, slug, description, created_at)
                VALUES(%s, %s, %s, %s)
                ON CONFLICT(name) DO UPDATE SET
                    slug = EXCLUDED.slug,
                    description = COALESCE(tags.description, EXCLUDED.description)
                RETURNING id, name, slug, description""",
                (text, tag_slug, description, current),
            )
            row = cur.fetchone()
            if row is None:
                cur.execute(
                    "SELECT id, name, slug, description FROM tags WHERE name=%s",
                    (text,),
                )
                row = cur.fetchone()
            return dict(row) if row else None


def list_customer_tags(customer_id):
    with get_db() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT t.id, t.name, t.slug, ct.source, ct.confidence
                FROM tags t
                JOIN customer_tags ct ON ct.tag_id=t.id
                WHERE ct.customer_id=%s ORDER BY t.name""",
                (customer_id,),
            )
            return cur.fetchall()


def add_customer_tag(customer_id, name, source="manual", confidence=None, slug=None):
    name = (name or "").strip()
    if not name:
        return None
    current = now_iso()
    tag = ensure_tag(name, slug=slug)
    if not tag:
        return None
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute(
                """INSERT INTO customer_tags(customer_id, tag_id, source, confidence, created_at)
                VALUES(%s, %s, %s, %s, %s)
                ON CONFLICT(customer_id, tag_id) DO UPDATE SET
                    source = CASE
                        WHEN customer_tags.source = 'manual' THEN customer_tags.source
                        ELSE EXCLUDED.source
                    END,
                    confidence = CASE
                        WHEN customer_tags.source = 'manual' THEN customer_tags.confidence
                        ELSE COALESCE(EXCLUDED.confidence, customer_tags.confidence)
                    END,
                    created_at = CASE
                        WHEN customer_tags.source = 'manual' THEN customer_tags.created_at
                        ELSE EXCLUDED.created_at
                    END
                RETURNING tag_id""",
                (customer_id, tag["id"], source or "manual", confidence, current),
            )
            cur.execute(
                "UPDATE customers SET updated_at=%s WHERE id=%s",
                (current, customer_id),
            )
    return tag


def remove_customer_tag(customer_id, tag_id):
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute(
                "DELETE FROM customer_tags WHERE customer_id=%s AND tag_id=%s",
                (customer_id, tag_id),
            )


def list_tags():
    with get_db() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM tags ORDER BY name")
            return cur.fetchall()


def get_tag_by_slug(slug):
    with get_db() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM tags WHERE slug=%s", (slug,))
            return cur.fetchone()


def count_tag_customers(tag_id):
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM customer_tags WHERE tag_id=%s",
                (tag_id,),
            )
            row = cur.fetchone()
            return row[0] if row else 0
