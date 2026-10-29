import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.tts import get_engine
from app.tts.base import RenderResult, Voice, WordTiming


class FakeEngine:
    """Stands in for Kokoro so API tests are fast and need no model."""

    name = "fake"

    def voices(self):
        return [Voice("af_test", "Test", "female", "American")]

    def render(self, text, voice, speed=1.0):
        audio = np.sin(np.linspace(0, 440, 2400)).astype(np.float32)  # 0.1s tone
        return RenderResult(audio, 24_000, [WordTiming(text, 0.0, 0.1)])


@pytest.fixture
def client():
    app.dependency_overrides[get_engine] = FakeEngine
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_voices_lists_engine_voices(client):
    response = client.get("/tts/voices")

    assert response.status_code == 200
    assert response.json() == [
        {"id": "af_test", "name": "Test", "gender": "female", "accent": "American"}
    ]


def test_preview_returns_wav_audio(client):
    response = client.post("/tts/preview", json={"text": "Hello.", "voice": "af_test"})

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.content[:4] == b"RIFF"


def test_preview_rejects_unknown_voice(client):
    response = client.post("/tts/preview", json={"text": "Hello.", "voice": "nope"})

    assert response.status_code == 404


@pytest.mark.parametrize(
    "body",
    [
        {"text": "", "voice": "af_test"},
        {"text": "x" * 501, "voice": "af_test"},
        {"text": "Hi.", "voice": "af_test", "speed": 3.0},
    ],
)
def test_preview_validates_input(client, body):
    assert client.post("/tts/preview", json=body).status_code == 422
