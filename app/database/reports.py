"""Reports database operations."""
from psycopg2.extras import RealDictCursor

from .connection import get_db

def get_daily_stats(day_start, day_end):
    with get_db() as con:
        with con.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT
                    (SELECT COUNT(*) FROM customers
                     WHERE created_at::timestamptz >= %s::timestamptz
                       AND created_at::timestamptz < %s::timestamptz) AS new_customers,
                    (SELECT COUNT(*) FROM messages
                     WHERE direction='in'
                       AND sent_at::timestamptz >= %s::timestamptz
                       AND sent_at::timestamptz < %s::timestamptz) AS incoming_messages,
                    (SELECT COUNT(*) FROM messages
                     WHERE direction='out' AND auto_reply=TRUE
                       AND sent_at::timestamptz >= %s::timestamptz
                       AND sent_at::timestamptz < %s::timestamptz) AS auto_replies,
                    (SELECT COUNT(*) FROM messages
                     WHERE direction='out' AND auto_reply=FALSE
                       AND sent_at::timestamptz >= %s::timestamptz
                       AND sent_at::timestamptz < %s::timestamptz) AS admin_replies,
                    (SELECT COUNT(*) FROM outgoing_messages
                     WHERE status='sent' AND sent_at::timestamptz >= %s::timestamptz
                       AND sent_at::timestamptz < %s::timestamptz)
                    + (SELECT COUNT(*) FROM logs
                       WHERE action='scheduled_message_sent'
                         AND created_at::timestamptz >= %s::timestamptz
                         AND created_at::timestamptz < %s::timestamptz) AS sent_messages,
                    (SELECT COUNT(*) FROM outgoing_messages
                     WHERE status='sent' AND message_type<>'text'
                       AND sent_at::timestamptz >= %s::timestamptz
                       AND sent_at::timestamptz < %s::timestamptz)
                    + (SELECT COUNT(*) FROM logs
                       WHERE action='scheduled_message_sent'
                         AND details->>'message_type'<>'text'
                         AND created_at::timestamptz >= %s::timestamptz
                         AND created_at::timestamptz < %s::timestamptz) AS sent_media,
                    (SELECT COUNT(*) FROM outgoing_messages
                     WHERE status='sent' AND recipient_type='group'
                       AND sent_at::timestamptz >= %s::timestamptz
                       AND sent_at::timestamptz < %s::timestamptz)
                    + (SELECT COUNT(*) FROM logs
                       WHERE action='scheduled_message_sent' AND target_type='group'
                         AND created_at::timestamptz >= %s::timestamptz
                         AND created_at::timestamptz < %s::timestamptz) AS group_messages""",
                (
                    day_start, day_end, day_start, day_end, day_start, day_end,
                    day_start, day_end, day_start, day_end, day_start, day_end,
                    day_start, day_end, day_start, day_end, day_start, day_end,
                    day_start, day_end,
                ),
            )
            stats = dict(cur.fetchone())
            cur.execute(
                """SELECT keyword, COUNT(*) AS total FROM messages m
                JOIN auto_reply_rules r ON POSITION(LOWER(r.keyword) IN LOWER(m.text)) > 0
                WHERE m.direction='in'
                  AND m.sent_at::timestamptz >= %s::timestamptz
                  AND m.sent_at::timestamptz < %s::timestamptz
                GROUP BY keyword ORDER BY total DESC, keyword LIMIT 1""",
                (day_start, day_end),
            )
            row = cur.fetchone()
            stats["top_inquiry"] = row["keyword"] if row else "—"
            cur.execute(
                """SELECT t.name, COUNT(*) AS total FROM customer_tags ct
                JOIN tags t ON t.id=ct.tag_id
                WHERE ct.created_at::timestamptz >= %s::timestamptz
                  AND ct.created_at::timestamptz < %s::timestamptz
                GROUP BY t.name ORDER BY total DESC, t.name LIMIT 1""",
                (day_start, day_end),
            )
            row = cur.fetchone()
            stats["top_tag"] = row["name"] if row else "—"
            return stats

def claim_daily_report(report_date):
    key = "last_daily_report_date"
    with get_db() as con:
        with con.cursor() as cur:
            cur.execute(
                """INSERT INTO settings(key,value) VALUES(%s,%s)
                ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value
                WHERE settings.value<>EXCLUDED.value
                RETURNING value""",
                (key, report_date),
            )
            return cur.fetchone() is not None
