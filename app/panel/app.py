"""FastAPI application factory and database startup hook."""
from app import database as db
from fastapi import FastAPI

from .routes import router

app = FastAPI(title="Education Telegram UserBot")
app.include_router(router)


@app.on_event("startup")
async def startup():
    db.init_db()
