import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import db_is_reachable
from app.documents.routes import router as documents_router
from app.documents.service import init_db
from app.ingest.routes import router as ingest_router
from app.render.routes import router as render_router
from app.tts.routes import router as tts_router

# Uvicorn only configures its own loggers; without this, the app's warnings
# (LLM retries, timeouts, failed chunks) are silently dropped.
logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="text-to-audiobook API", lifespan=lifespan)
app.include_router(ingest_router)
app.include_router(documents_router)
app.include_router(render_router)
app.include_router(tts_router)


@app.get("/health")
def health():
    """Liveness check used by the web app to show backend + database status."""
    db_ok = db_is_reachable()
    return {"status": "ok" if db_ok else "degraded", "database": db_ok}
