"""FastAPI app entry point."""

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from routers.dialogue import router as dialogue_router

load_dotenv(override=True)  # local .env wins over shell env in dev

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Realm of Ashes API", version="1.0.0", lifespan=lifespan)


# CORS
_origins_env = os.getenv("ALLOWED_ORIGINS", "")
origins = [o.strip() for o in _origins_env.split(",") if o.strip()]
if not origins:
    origins = [
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(dialogue_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/")
async def root() -> dict:
    return {"service": "Realm of Ashes API", "docs": "/docs"}
