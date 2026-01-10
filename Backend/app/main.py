# app/main.py

from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core import db
from app.routers import items

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: ensure DB client is created and reachable
    client = db.getclient()
    try:
        # motor client supports an async admin command
        await client.admin.command("ping")
        print("Connected to MongoDB (ping success)")
    except Exception as e:
        print("MongoDB connection error on startup:", e)
        raise
    try:
        yield
    finally:
        # shutdown: close the client
        client.close()
        print("MongoDB client closed")

app = FastAPI(title="FastAPI + MongoDB (GridFS)", lifespan=lifespan)

app.include_router(items.router)
