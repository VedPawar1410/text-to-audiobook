import io
from dataclasses import asdict

import soundfile as sf
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.tts import get_engine
from app.tts.base import TTSEngine

router = APIRouter(prefix="/tts", tags=["tts"])


class PreviewRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    voice: str
    speed: float = Field(default=1.0, ge=0.5, le=2.0)


@router.get("/voices")
def list_voices(engine: TTSEngine = Depends(get_engine)):
    return [asdict(v) for v in engine.voices()]


@router.post("/preview")
def preview(req: PreviewRequest, engine: TTSEngine = Depends(get_engine)):
    """A short sample in one voice; powers the "listen" buttons when casting."""
    if req.voice not in {v.id for v in engine.voices()}:
        raise HTTPException(status_code=404, detail=f"Unknown voice: {req.voice}")

    result = engine.render(req.text, req.voice, req.speed)
    buffer = io.BytesIO()
    sf.write(buffer, result.audio, result.sample_rate, format="WAV", subtype="PCM_16")
    return Response(content=buffer.getvalue(), media_type="audio/wav")
