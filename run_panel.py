import uvicorn
import config
import db

if __name__ == "__main__":
    db.init_db()
    uvicorn.run("panel:app", host=config.PANEL_HOST, port=config.PANEL_PORT, reload=False)
