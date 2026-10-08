"""Central logging configuration for application processes."""
import logging

from .config import PROJECT_ROOT


def configure_logging():
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "telegram.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )
