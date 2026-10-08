"""Scheduled messages database operations."""
from datetime import datetime, timedelta

from psycopg2.extras import RealDictCursor

from .connection import get_db

def create_scheduled_message(
    requested_by,
    recipient_type,
    recipient_id,
    text,
    run_at,
    repeat="once",
    message_type="text",
    media_path=None,
    caption=None,
):
    group_id = recipient_id if recipient_type == "group" else None
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute(
                """INSERT INTO scheduled_messages
                (group_telegram_id,text,run_at,repeat,enabled,recipient_type,recipient_id,
                 message_type,media_path,caption)
                VALUES(%s,%s,%s,%s,TRUE,%s,%s,%s,%s,%s) RETURNING id""",
                (
                    group_id,
                    text or caption or "",
                    run_at,
                    repeat,
                    recipient_type,
                    recipient_id,
                    message_type,
                    media_path,
                    caption,
                ),
            )
            return cur.fetchone()[0]

def claim_due_scheduled(now_value):
    with get_db() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """WITH due AS (
                    SELECT id FROM scheduled_messages
                    WHERE enabled=TRUE AND run_at<=%s
                    AND (last_run_at IS NULL OR last_run_at<>run_at)
                    ORDER BY run_at,id
                    LIMIT 20 FOR UPDATE SKIP LOCKED
                )
                UPDATE scheduled_messages AS scheduled
                SET last_run_at=scheduled.run_at
                FROM due WHERE scheduled.id=due.id
                RETURNING scheduled.*""",
                (now_value,),
            )
            return cur.fetchall()

def advance_scheduled_message(row_id, sent):
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute(
                "SELECT run_at,repeat FROM scheduled_messages WHERE id=%s",
                (row_id,),
            )
            row = cur.fetchone()
            if not row:
                return
            run_at, repeat = row
            if not sent or repeat == "once":
                cur.execute(
                    "UPDATE scheduled_messages SET enabled=FALSE WHERE id=%s",
                    (row_id,),
                )
                return
            run_at_dt = datetime.fromisoformat(run_at)
            days = 1 if repeat == "daily" else 7
            cur.execute(
                """UPDATE scheduled_messages SET run_at=%s,last_run_at=NULL
                WHERE id=%s""",
                ((run_at_dt + timedelta(days=days)).isoformat(), row_id),
            )

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
