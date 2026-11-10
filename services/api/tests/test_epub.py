"""EPUB import (step 5 of the revive): structure from real headings, junk skipped, unsafe files refused."""

import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.ingest import IngestError
from app.ingest.epub import text_from_epub
from app.main import app
from app.structure import parse_text
from structure_eval.cases import _epub

STORY = "The lamp turned slowly above the harbour while the keeper wrote in the ledger."


def _import(data: bytes):
    text, title, author = text_from_epub(data)
    return parse_text(text, title=title, author=author)


def _blocks(document):
    return [(b.kind, b.text) for s in document.sections for b in s.blocks]


def test_chapters_come_from_real_headings_and_junk_is_skipped():
    documents = [
        ("cover.xhtml", "linear-no", "<p>Cover image</p>"),
        ("nav.xhtml", "nav", '<nav epub:type="toc"><h1>Contents</h1><ol><li>The Quay</li></ol></nav>'),
        ("title.xhtml", "", "<h1>Harbour Tales</h1><p>by Ana Ruiz</p>"),
        ("legal.xhtml", "", '<section epub:type="copyright-page"><p>All rights reserved.</p></section>'),
        ("c1.xhtml", "", (
            f'<h2>The Quay</h2><p>{STORY}<span epub:type="pagebreak">12</span> Then it rained.</p>'
            '<h3>Morning</h3><blockquote><p>Every tide returns.</p></blockquote>'
            '<p>She counted<sup>1</sup> the boats.</p><aside epub:type="footnote"><p>A note.</p></aside>'
        )),
        ("c2.xhtml", "", f"<h2>Night Crossing</h2><p>{STORY}</p><table><tr><td>Ship</td></tr></table>"),
    ]  # fmt: skip

    doc = _import(_epub(documents, "Harbour Tales", "Ana Ruiz"))

    assert (doc.title, doc.author) == ("Harbour Tales", "Ana Ruiz")
    assert [s.title for s in doc.sections] == ["The Quay", "Night Crossing"]
    assert _blocks(doc) == [
        ("heading", "The Quay"),
        ("paragraph", f"{STORY} Then it rained."),  # page number gone, paragraph whole
        ("heading", "Morning"),
        ("quote", "Every tide returns."),
        ("paragraph", "She counted the boats."),  # footnote marker and footnote gone
        ("heading", "Night Crossing"),
        ("paragraph", STORY),  # the table is skipped
    ]


def test_a_short_paragraph_in_a_structured_book_is_not_guessed_into_a_heading():
    documents = [("c1.xhtml", "", f"<h2>The Quay</h2><p>{STORY}</p><p>Morning Came Early</p><p>{STORY}</p>")]
    doc = _import(_epub(documents, "Harbour Tales", None))
    assert ("paragraph", "Morning Came Early") in _blocks(doc)


def test_a_converter_made_epub_without_headings_falls_back_to_the_text_rules():
    body = "".join(f'<p class="calibre2">{p}</p>' for p in ["My Plot", "Act One:", STORY, "Act Two:", STORY])
    doc = _import(_epub([("index_split_000.html", "", body)], "My Plot", "Unknown"))
    assert [s.title for s in doc.sections] == ["Act One:", "Act Two:"]
    assert doc.author is None  # Calibre's "Unknown" placeholder


def test_gutenberg_epub_licence_and_page_markers_are_skipped():
    body = (
        '<section id="pg-header"><p>The Project Gutenberg eBook of Harbour Tales</p></section>'
        f'<h2>I. THE QUAY</h2><p>{STORY} <span class="pagenum">[Pg 7]</span>More rain.</p>'
        '<section id="pg-footer"><p>Section 1. General terms of use.</p></section>'
    )
    doc = _import(_epub([("book.xhtml", "", body)], "Harbour Tales", "Ana Ruiz"))
    assert _blocks(doc) == [("heading", "I. THE QUAY"), ("paragraph", f"{STORY} More rain.")]


def _with_extra_file(data: bytes, name: str, content: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as source, zipfile.ZipFile(buffer, "w") as target:
        for item in source.infolist():
            target.writestr(item, source.read(item.filename))
        target.writestr(name, content)
    return buffer.getvalue()


def _encryption(uri: str) -> str:
    return (
        '<encryption xmlns="urn:oasis:names:tc:opendocument:xmlns:container" '
        'xmlns:enc="http://www.w3.org/2001/04/xmlenc#"><enc:EncryptedData>'
        f'<enc:CipherData><enc:CipherReference URI="{uri}"/></enc:CipherData></enc:EncryptedData></encryption>'
    )


def test_drm_protected_text_is_refused_but_font_obfuscation_is_fine():
    book = _epub([("c1.xhtml", "", f"<h2>The Quay</h2><p>{STORY}</p>")], "Harbour Tales", None)
    with pytest.raises(IngestError, match="DRM"):
        text_from_epub(_with_extra_file(book, "META-INF/encryption.xml", _encryption("OEBPS/c1.xhtml")))
    fonts = _with_extra_file(book, "META-INF/encryption.xml", _encryption("OEBPS/fonts/serif.otf"))
    assert STORY in text_from_epub(fonts)[0]


def test_unsafe_or_broken_files_are_refused():
    book = _epub([("c1.xhtml", "", "<p>x</p>")], "T", None)
    with zipfile.ZipFile(io.BytesIO(book)) as source:
        opf = source.read("OEBPS/content.opf").replace(b"<package", b'<!DOCTYPE p [<!ENTITY a "aaaa">]><package', 1)
    buffer = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(book)) as source, zipfile.ZipFile(buffer, "w") as target:
        for item in source.infolist():
            target.writestr(item, opf if item.filename == "OEBPS/content.opf" else source.read(item.filename))
    entity_bomb = buffer.getvalue()  # "billion laughs" starts with an entity declaration like this
    with pytest.raises(IngestError, match="isn't allowed"):
        text_from_epub(entity_bomb)
    with pytest.raises(IngestError, match="readable EPUB"):
        text_from_epub(b"not a zip at all")


def test_the_upload_route_accepts_epub():
    client = TestClient(app)
    book = _epub([("c1.xhtml", "", f"<h2>The Quay</h2><p>{STORY}</p>")], "Harbour Tales", "Ana Ruiz")

    response = client.post("/ingest/file", files={"file": ("tales.epub", book, "application/epub+zip")})
    broken = client.post("/ingest/file", files={"file": ("tales.epub", b"nope", "application/epub+zip")})

    assert response.status_code == 200
    assert (response.json()["title"], response.json()["author"]) == ("Harbour Tales", "Ana Ruiz")
    assert broken.status_code == 422
