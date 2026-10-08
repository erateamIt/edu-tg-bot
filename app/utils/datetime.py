"""Timezone-safe datetime helpers."""
from datetime import datetime, timezone


def iso(dt=None):
    return (dt or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
