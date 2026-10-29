from fastapi import FastAPI

from app.db import db_is_reachable
from app.ingest.routes import router as ingest_router
from app.tts.routes import router as tts_router

app = FastAPI(title="text-to-audiobook API")
app.include_router(ingest_router)
app.include_router(tts_router)


@app.get("/health")
def health():
    """Liveness check used by the web app to show backend + database status."""
    db_ok = db_is_reachable()
    return {"status": "ok" if db_ok else "degraded", "database": db_ok}
