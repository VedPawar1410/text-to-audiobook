"""Ask the AI about the text, without leaving the reader. The answer streams."""

import uuid
from collections.abc import Callable
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.ask.prompts import SYSTEM, build_prompt
from app.db import get_db
from app.documents.routes import get_llm_factory
from app.llm import LLM, LLMError
from app.models import Document

router = APIRouter(prefix="/documents/{document_id}", tags=["ask"])

MAX_HISTORY = 8  # earlier turns sent back as context


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(max_length=4000)


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    selection: str | None = Field(default=None, max_length=4000)
    segment_id: int | None = None  # where the reader is, or where their selection starts
    history: list[Turn] = Field(default_factory=list, max_length=12)


@router.post("/ask")
def ask(
    document_id: uuid.UUID,
    body: AskIn,
    db: Session = Depends(get_db),
    llm_factory: Callable[[str | None], LLM] = Depends(get_llm_factory),
    x_llm_key: str | None = Header(default=None),
):
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    try:
        llm = llm_factory(x_llm_key)
    except LLMError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    # Built now, while the database session is open; the stream outlives the request handler
    history = [(t.role, t.text) for t in body.history[-MAX_HISTORY:]]
    prompt = build_prompt(document, body.question, body.selection, body.segment_id, history)

    def answer():
        try:
            yield from llm.stream_text(system=SYSTEM, prompt=prompt)
        except LLMError as error:
            # Headers (200) are already sent once streaming starts, so the error is part of the text
            yield f"\n\n({error})"

    return StreamingResponse(answer(), media_type="text/plain; charset=utf-8")
