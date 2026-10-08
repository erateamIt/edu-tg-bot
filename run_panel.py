"""Start the FastAPI management panel."""
import uvicorn

from app import database as db
from app.core import config
from app.core.logging_config import configure_logging
from app.panel.app import app


if __name__ == "__main__":
    configure_logging()
    db.init_db()
    uvicorn.run(app, host=config.PANEL_HOST, port=config.PANEL_PORT, reload=False)
