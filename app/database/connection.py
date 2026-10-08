"""PostgreSQL connection and shared database helpers."""
from contextlib import contextmanager
from datetime import datetime, timezone

import psycopg2

from app.core import config


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
