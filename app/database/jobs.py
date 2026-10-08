"""Jobs database operations."""
from psycopg2.extras import Json, RealDictCursor

from .connection import get_db, now_iso

def enqueue_outgoing_message(
    requested_by,
    recipient_type,
    recipient_id,
    message_type="text",
    text=None,
    media_path=None,
    caption=None,
):
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute(
                """INSERT INTO outgoing_messages
                (requested_by,recipient_type,recipient_id,message_type,text,media_path,caption,created_at)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                (
                    requested_by,
                    recipient_type,
                    recipient_id,
                    message_type,
                    text,
                    media_path,
                    caption,
                    now_iso(),
                ),
            )
            return cur.fetchone()[0]

def claim_outgoing_message():
    with get_db() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """WITH next_job AS (
                    SELECT id FROM outgoing_messages
                    WHERE status='pending'
                    ORDER BY created_at,id
                    LIMIT 1 FOR UPDATE SKIP LOCKED
                )
                UPDATE outgoing_messages AS job SET status='processing'
                FROM next_job WHERE job.id=next_job.id
                RETURNING job.*"""
            )
            return cur.fetchone()

def finish_outgoing_message(job_id, error=None):
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute(
                """UPDATE outgoing_messages SET status=%s,error=%s,sent_at=%s
                WHERE id=%s""",
                (
                    "failed" if error else "sent",
                    error,
                    now_iso(),
                    job_id,
                ),
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
