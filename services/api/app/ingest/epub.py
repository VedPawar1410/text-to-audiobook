"""EPUB → markdown text, which the normal text parser then reads.

An EPUB is a zip of XHTML files. Its package file (the OPF) lists them in reading order (the
"spine") and holds the title and author. Chapters are real <h1>-<h6> headings, so most of the
guesswork a paste or PDF needs disappears. What we skip: navigation and contents pages, page
numbers (<span epub:type="pagebreak">), footnotes, copyright pages, tables, and Project
Gutenberg's licence sections.

Uses only the standard library. An EPUB comes from a stranger, so: XML with entity
declarations is refused ("billion laughs"), the uncompressed text size is capped (zip bombs),
and DRM-encrypted books get a clear error instead of garbage.
"""

import io
import posixpath
import re
import zipfile
from html.parser import HTMLParser
from urllib.parse import unquote
from xml.etree import ElementTree

from app.ingest import IngestError

MAX_TEXT_BYTES = 100 * 1024 * 1024  # uncompressed XHTML; a long novel is ~1-5 MB
NS = {
    "container": "urn:oasis:names:tc:opendocument:xmlns:container",
    "opf": "http://www.idpf.org/2007/opf",
    "dc": "http://purl.org/dc/elements/1.1/",
    "enc": "http://www.w3.org/2001/04/xmlenc#",
}
# EPUB 3 structural semantics (epub:type) and roles that are never part of the story
SKIP_TYPES = {"toc", "landmarks", "page-list", "pagebreak", "noteref", "footnote", "footnotes", "endnote",
              "endnotes", "rearnote", "rearnotes", "copyright-page", "index"}  # fmt: skip
SKIP_TAGS = {"head", "script", "style", "nav", "table", "svg", "math", "figure", "aside", "sup"}
BLOCK_TAGS = {"p", "div", "li", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "dd", "dt"}
VOID_TAGS = {"br", "hr", "img", "meta", "link", "input", "source", "wbr", "col", "area", "base", "embed"}


def _skip(tag: str, attrs: dict[str, str | None]) -> bool:
    types = set(((attrs.get("epub:type") or "") + " " + (attrs.get("role") or "").replace("doc-", "")).split())
    element_id = attrs.get("id") or ""
    classes = (attrs.get("class") or "").split()
    return (
        tag in SKIP_TAGS
        or bool(types & SKIP_TYPES)
        or element_id.startswith(("pg-header", "pg-footer"))  # Project Gutenberg licence
        or "pagenum" in classes  # Gutenberg's "[Pg 12]" page markers
    )


class _Blocks(HTMLParser):
    """Collect (kind, text) blocks: kind is "h1".."h6", "p", "li" or "quote"."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks: list[tuple[str, str]] = []
        self.stack: list[tuple[str, bool]] = []  # (tag, skipped)
        self.skip_depth = 0
        self.quote_depth = 0
        self.kind = "p"
        self.text: list[str] = []

    def _flush(self) -> None:
        text = re.sub(r"\s+", " ", "".join(self.text)).strip()
        if text:
            self.blocks.append(("quote" if self.quote_depth and self.kind == "p" else self.kind, text))
        self.text = []
        self.kind = "p"

    def handle_starttag(self, tag, attrs):
        if tag in VOID_TAGS:
            if tag == "br" and not self.skip_depth:
                self.text.append(" ")
            return
        skipped = self.skip_depth > 0 or _skip(tag, dict(attrs))
        self.stack.append((tag, skipped))
        if skipped:
            self.skip_depth += 1
            return
        if tag in BLOCK_TAGS:
            self._flush()
            if tag == "blockquote":
                self.quote_depth += 1
            self.kind = tag if tag[0] == "h" else ("li" if tag == "li" else "p")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in VOID_TAGS or not any(open_tag == tag for open_tag, _ in self.stack):
            return
        while self.stack:  # close up to the matching tag (XHTML is well-formed; be forgiving anyway)
            open_tag, skipped = self.stack.pop()
            if skipped:
                self.skip_depth -= 1
            elif open_tag in BLOCK_TAGS:
                self._flush()
                if open_tag == "blockquote":
                    self.quote_depth -= 1
            if open_tag == tag:
                break

    def handle_data(self, data):
        if not self.skip_depth:
            self.text.append(data)

    def close(self):
        super().close()
        self._flush()


def _xml(archive: zipfile.ZipFile, name: str) -> ElementTree.Element:
    data = archive.read(name)
    if b"<!ENTITY" in data:
        raise IngestError("This EPUB contains XML that isn't allowed.")
    return ElementTree.fromstring(data)


def _is_drm_protected(archive: zipfile.ZipFile) -> bool:
    """encryption.xml also lists harmless font obfuscation; DRM encrypts the text itself."""
    if "META-INF/encryption.xml" not in archive.namelist():
        return False
    encryption = _xml(archive, "META-INF/encryption.xml")
    uris = [ref.get("URI", "") for ref in encryption.iter(f"{{{NS['enc']}}}CipherReference")]
    return any(uri.lower().endswith((".xhtml", ".html", ".htm", ".xml")) for uri in uris)


def _kept_heading(blocks: list[tuple[str, str]], index: int, title: str | None) -> bool:
    kind, text = blocks[index]
    if (title and text.lower() == title.lower()) or re.match(r"^by\s", text, re.IGNORECASE):
        return False  # the book's own title page: it's metadata, not a chapter
    if re.fullmatch(r"(?:table of )?contents", text, re.IGNORECASE):
        return False  # the list under it is navigation and already skipped
    following = blocks[index + 1][0] if index + 1 < len(blocks) else None
    # Nothing to read before the next heading of the same level: a part-title or contents page
    return following is not None and not (following[0] == "h" and int(following[1]) <= int(kind[1]))


def _markdown(blocks: list[tuple[str, str]], title: str | None) -> str:
    """Headings become "##"/"###" by their depth in this book (the shallowest kept is a chapter)."""
    kept = {i for i, (kind, _) in enumerate(blocks) if kind[0] == "h" and _kept_heading(blocks, i, title)}
    levels = sorted({int(blocks[i][0][1]) for i in kept})
    lines: list[str] = []
    for index, (kind, text) in enumerate(blocks):
        if kind[0] == "h":
            if index not in kept:
                continue
            depth = min(levels.index(int(kind[1])), 1)
            lines.append(f"{'#' * (2 + depth)} {text}")
        elif kind == "li":
            lines.append(f"- {text}")
        elif kind == "quote":
            lines.append(f"> {text}")
        else:
            lines.append(text)
    return "\n\n".join(lines)


def text_from_epub(data: bytes) -> tuple[str, str | None, str | None]:
    """Return (the book as markdown, title, author)."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
        rootfile = _xml(archive, "META-INF/container.xml").find(".//container:rootfile", NS)
        if rootfile is None:
            raise IngestError("This EPUB has no package file.")
        opf_path = rootfile.get("full-path", "")
        package = _xml(archive, opf_path)
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as error:
        raise IngestError("This file isn't a readable EPUB.") from error
    if _is_drm_protected(archive):
        raise IngestError("This EPUB is DRM-protected. Only DRM-free EPUBs can be read.")

    title = (package.findtext(".//dc:title", default="", namespaces=NS) or "").strip() or None
    author = (package.findtext(".//dc:creator", default="", namespaces=NS) or "").strip() or None

    base = posixpath.dirname(opf_path)
    manifest = {item.get("id"): item for item in package.iterfind("opf:manifest/opf:item", NS)}
    documents = []
    for itemref in package.iterfind("opf:spine/opf:itemref", NS):
        item = manifest.get(itemref.get("idref"))
        if item is None or itemref.get("linear") == "no" or "nav" in (item.get("properties") or "").split():
            continue
        documents.append(posixpath.normpath(posixpath.join(base, unquote(item.get("href", "")))))

    names = set(archive.namelist())
    if sum(archive.getinfo(name).file_size for name in documents if name in names) > MAX_TEXT_BYTES:
        raise IngestError("This EPUB is too large to read.")

    blocks: list[tuple[str, str]] = []
    for name in documents:
        if name not in names:
            continue  # a broken spine entry: skip it rather than fail the whole book
        parser = _Blocks()
        parser.feed(archive.read(name).decode("utf-8", errors="replace"))
        parser.close()
        blocks += parser.blocks

    if not blocks:
        raise IngestError("No readable text found in this EPUB.")
    return _markdown(blocks, title), title, author
