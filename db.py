from contextlib import contextmanager
from datetime import datetime, timezone
import json

import psycopg2
from psycopg2.extras import Json, RealDictCursor

import config


def now_iso():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_db():
    con = psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        connect_timeout=10,
    )
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def init_db():
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id BIGSERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                phone TEXT,
                status TEXT NOT NULL DEFAULT 'new',
                first_message TEXT,
                last_message TEXT,
                last_message_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id BIGSERIAL PRIMARY KEY,
                customer_id BIGINT NOT NULL REFERENCES customers(id),
                telegram_message_id BIGINT,
                direction TEXT NOT NULL,
                text TEXT,
                sent_at TEXT NOT NULL,
                answered BOOLEAN NOT NULL DEFAULT FALSE,
                auto_reply BOOLEAN NOT NULL DEFAULT FALSE
            );

            CREATE TABLE IF NOT EXISTS groups_ (
                id BIGSERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                username TEXT,
                enabled BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS scheduled_messages (
                id BIGSERIAL PRIMARY KEY,
                group_telegram_id BIGINT NOT NULL,
                text TEXT NOT NULL,
                run_at TEXT NOT NULL,
                repeat TEXT NOT NULL DEFAULT 'once',
                enabled BOOLEAN NOT NULL DEFAULT TRUE,
                last_run_at TEXT
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS group_message_jobs (
                id BIGSERIAL PRIMARY KEY,
                requested_by BIGINT NOT NULL,
                group_telegram_ids BIGINT[] NOT NULL,
                text TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                results JSONB,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                notified BOOLEAN NOT NULL DEFAULT FALSE
            );

            CREATE INDEX IF NOT EXISTS idx_messages_customer ON messages(customer_id);
            CREATE INDEX IF NOT EXISTS idx_messages_sent_at ON messages(sent_at);
            CREATE INDEX IF NOT EXISTS idx_customers_status ON customers(status);
            CREATE INDEX IF NOT EXISTS idx_group_message_jobs_pending
                ON group_message_jobs(status, created_at);
            """)

            defaults = {
                "welcome_message": """Assalomu alaykum! 👋

O‘quv markazimizga xush kelibsiz.

📚 Kurslar:
• Ingliz tili
• IELTS
• Rus tili
• Matematika
• Python
• Frontend / Backend

💰 Kurs narxlari: 350 000 so‘mdan.
🕐 Darslar: 09:00–20:00
📍 Manzil: Samarqand shahri

Batafsil ma’lumot uchun kurs nomini yozing.""",
                "monitor_minutes": "5",
            }
            for key, value in defaults.items():
                cur.execute(
                    "INSERT INTO settings(key,value) VALUES(%s,%s) "
                    "ON CONFLICT(key) DO NOTHING",
                    (key, value),
                )


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


def mark_customer_answered(customer_id):
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute(
                "UPDATE customers SET status='answered', updated_at=%s WHERE id=%s",
                (now_iso(), customer_id),
            )
            cur.execute(
                "UPDATE messages SET answered=TRUE "
                "WHERE customer_id=%s AND direction='in' AND answered=FALSE",
                (customer_id,),
            )


def get_customer_by_telegram_id(telegram_id):
    with get_db() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM customers WHERE telegram_id=%s", (telegram_id,))
            return cur.fetchone()


def get_unanswered():
    with get_db() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""SELECT c.*, m.id AS message_db_id, m.text AS pending_text, m.sent_at AS pending_sent_at
                FROM customers c
                JOIN messages m ON m.customer_id=c.id
                WHERE c.status='waiting' AND m.direction='in' AND m.answered=FALSE
                AND m.id=(SELECT MAX(m2.id) FROM messages m2
                          WHERE m2.customer_id=c.id AND m2.direction='in' AND m2.answered=FALSE)
                ORDER BY m.sent_at ASC""")
            return cur.fetchall()


def set_customer_status(customer_id, status):
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute(
                "UPDATE customers SET status=%s, updated_at=%s WHERE id=%s",
                (status, now_iso(), customer_id),
            )


def list_customers(limit=100):
    with get_db() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM customers ORDER BY updated_at DESC LIMIT %s", (limit,))
            return cur.fetchall()


def list_messages(customer_id, limit=200):
    with get_db() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM messages WHERE customer_id=%s ORDER BY sent_at ASC LIMIT %s",
                (customer_id, limit),
            )
            return cur.fetchall()


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


def enabled_group_ids():
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute("SELECT telegram_id FROM groups_ WHERE enabled=TRUE")
            return [row[0] for row in cur.fetchall()]


def add_scheduled(group_id, text, run_at, repeat="once"):
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute(
                """INSERT INTO scheduled_messages(group_telegram_id,text,run_at,repeat)
                VALUES(%s,%s,%s,%s) RETURNING id""",
                (group_id, text, run_at, repeat),
            )
            return cur.fetchone()[0]


def list_scheduled():
    with get_db() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM scheduled_messages ORDER BY run_at")
            return cur.fetchall()


def due_scheduled(now_value):
    with get_db() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT * FROM scheduled_messages
                WHERE enabled=TRUE AND run_at<=%s
                AND (last_run_at IS NULL OR last_run_at<>run_at)""",
                (now_value,),
            )
            return cur.fetchall()


def mark_scheduled_run(row_id, run_at):
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute(
                "UPDATE scheduled_messages SET last_run_at=%s WHERE id=%s",
                (run_at, row_id),
            )


def disable_scheduled(row_id):
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute(
                "UPDATE scheduled_messages SET enabled=FALSE WHERE id=%s",
                (row_id,),
            )


def reschedule_scheduled(row_id, next_run):
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute(
                "UPDATE scheduled_messages SET run_at=%s, last_run_at=NULL WHERE id=%s",
                (next_run, row_id),
            )


def enqueue_group_message(requested_by, group_telegram_ids, text):
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute(
                """INSERT INTO group_message_jobs
                (requested_by,group_telegram_ids,text,created_at)
                VALUES(%s,%s,%s,%s) RETURNING id""",
                (requested_by, group_telegram_ids, text, now_iso()),
            )
            return cur.fetchone()[0]


def claim_group_message_job():
    with get_db() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """WITH next_job AS (
                    SELECT id FROM group_message_jobs
                    WHERE status='pending'
                    ORDER BY created_at, id
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                )
                UPDATE group_message_jobs AS job
                SET status='processing'
                FROM next_job
                WHERE job.id=next_job.id
                RETURNING job.*"""
            )
            return cur.fetchone()


def complete_group_message_job(job_id, results):
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute(
                """UPDATE group_message_jobs
                SET status='completed', results=%s, completed_at=%s
                WHERE id=%s""",
                (Json(results), now_iso(), job_id),
            )


def get_unnotified_group_message_jobs():
    with get_db() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT * FROM group_message_jobs
                WHERE status='completed' AND notified=FALSE
                ORDER BY completed_at, id"""
            )
            return cur.fetchall()


def mark_group_message_job_notified(job_id):
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute(
                "UPDATE group_message_jobs SET notified=TRUE WHERE id=%s",
                (job_id,),
            )


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
    ]
    result = {}
    with get_db() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            for table in tables:
                result[table] = _all_rows(cur, table)
    return result


def export_database_json():
    return json.dumps(export_database(), ensure_ascii=False, indent=2, default=str)
