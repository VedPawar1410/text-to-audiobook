"""The real Gemini, end to end. Opt-in (uses your key and quota):

    RUN_LLM_TESTS=1 uv run pytest tests/test_director_live.py
"""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.skipif(os.environ.get("RUN_LLM_TESTS") != "1", reason="calls the real Gemini API")

client = TestClient(app)
SCREENPLAY = (Path(__file__).parent / "fixtures" / "citadel_screenplay.txt").read_text()


def test_real_director_on_the_screenplay_fixture():
    parsed = client.post("/ingest/text", json={"text": SCREENPLAY}).json()
    document_id = client.post("/documents", json=parsed).json()["id"]

    client.post(f"/documents/{document_id}/direct")
    body = client.get(f"/documents/{document_id}").json()

    assert body["status"] == "directed", body["error"]
    assert body["genre"] in {"screenplay", "scifi_action", "fantasy"}
    assert {"NARRATOR", "KANG", "THOR"} <= {p["cast_id"] for p in body["personas"]}
    segments = [seg for s in body["sections"] for seg in s["segments"] if seg["text"]]
    assert len({seg["emotion"] for seg in segments}) >= 2  # it actually directed, not all defaults
