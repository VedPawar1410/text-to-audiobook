"""Turn pasted text, an uploaded file or a web link into a ParsedDocument.

Nothing is stored yet; saving documents arrives with the director in PR 5.
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, HttpUrl

from app.ingest import IngestError
from app.ingest.files import TEXT_EXTENSIONS, decode_text
from app.ingest.pdf import text_from_pdf
from app.ingest.url import text_from_url
from app.structure import parse_text
from app.structure.models import ParsedDocument

router = APIRouter(prefix="/ingest", tags=["ingest"])

MAX_UPLOAD_BYTES = 25 * 1024 * 1024


class TextIn(BaseModel):
    text: str = Field(min_length=1)  # deliberately no maximum length
    title: str | None = None


class UrlIn(BaseModel):
    url: HttpUrl


def _parse(text: str, title: str | None) -> ParsedDocument:
    document = parse_text(text, title=title)
    if document.stats.words == 0:
        raise HTTPException(status_code=422, detail="No readable text found.")
    return document


@router.post("/text", response_model=ParsedDocument)
def ingest_text(body: TextIn):
    return _parse(body.text, body.title)


def _file_to_text(name: str, data: bytes) -> tuple[str, str | None]:
    extension = Path(name).suffix.lower()
    if extension in TEXT_EXTENSIONS:
        return decode_text(data), Path(name).stem
    if extension == ".pdf":
        text, title = text_from_pdf(data)
        return text, title or Path(name).stem
    raise HTTPException(status_code=415, detail="Supported files: .txt, .md and .pdf")


@router.post("/file", response_model=ParsedDocument)
async def ingest_file(file: UploadFile):
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Files are limited to 25 MB.")
    try:
        # PDF extraction and parsing are CPU work: keep them off the event loop
        text, title = await run_in_threadpool(_file_to_text, file.filename or "upload.txt", data)
        return await run_in_threadpool(_parse, text, title)
    except IngestError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/url", response_model=ParsedDocument)
def ingest_url(body: UrlIn):
    try:
        text, title = text_from_url(str(body.url))
    except IngestError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return _parse(text, title)
