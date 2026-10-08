"""Project-root data directories and safe JSON export persistence."""
import json
from pathlib import Path

from app.core.config import PROJECT_ROOT

BACKUP_DIR = PROJECT_ROOT / "data" / "backups"
EXPORT_DIR = PROJECT_ROOT / "data" / "exports"


def write_json_export(filename, content, *, backup=False):
    directory = BACKUP_DIR if backup else EXPORT_DIR
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / Path(filename).name
    destination.write_text(content, encoding="utf-8")
    return destination


def write_database_backup(data, filename):
    content = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    return write_json_export(filename, content, backup=True)
