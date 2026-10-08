"""Admin Bot startup entry point."""
from app import database as db
from app.core.logging_config import configure_logging
from .handlers import poll


def run():
    configure_logging()
    db.init_db()
    poll()
