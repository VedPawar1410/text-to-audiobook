from fastapi import FastAPI

from app.db import db_is_reachable

app = FastAPI(title="text-to-audiobook API")


@app.get("/health")
def health():
    """Liveness check used by the web app to show backend + database status."""
    db_ok = db_is_reachable()
    return {"status": "ok" if db_ok else "degraded", "database": db_ok}
