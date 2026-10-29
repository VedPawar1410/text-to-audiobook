"""Build tiny real PDFs in tests, so PDF extraction is tested without binary fixtures."""


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def make_pdf(pages: list[list[tuple[float, float, str]]], title: str | None = None) -> bytes:
    """Each page is a list of (x, y, text) lines in points (US Letter, origin bottom-left)."""
    objects: list[bytes] = []

    def add(body: bytes) -> int:
        objects.append(body)
        return len(objects)  # 1-based object number

    catalog = add(b"")  # filled in once the page tree number is known
    pages_obj = add(b"")
    font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")

    page_numbers = []
    for lines in pages:
        stream = "".join(
            f"BT /F1 12 Tf {x:.1f} {y:.1f} Td ({_escape(text)}) Tj ET\n" for x, y, text in lines
        ).encode("latin-1")
        content = add(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"endstream")
        page_numbers.append(
            add(
                b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 612 792] "
                b"/Resources << /Font << /F1 %d 0 R >> >> /Contents %d 0 R >>"
                % (pages_obj, font, content)
            )
        )

    kids = b" ".join(b"%d 0 R" % n for n in page_numbers)
    objects[pages_obj - 1] = b"<< /Type /Pages /Kids [%s] /Count %d >>" % (kids, len(page_numbers))
    objects[catalog - 1] = b"<< /Type /Catalog /Pages %d 0 R >>" % pages_obj
    info = add(b"<< /Title (%s) >>" % _escape(title).encode("latin-1")) if title else None

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % off for off in offsets)
    trailer = b"/Size %d /Root %d 0 R" % (len(objects) + 1, catalog)
    if info:
        trailer += b" /Info %d 0 R" % info
    out += b"trailer\n<< %s >>\nstartxref\n%d\n%%%%EOF\n" % (trailer, xref)
    return bytes(out)


def page_of_lines(lines: list[str | tuple[int, str]], top: float = 740, leading: float = 14) -> list:
    """Lay out lines top-down. A line may be (indent_chars, text); "" leaves a blank gap."""
    placed, y = [], top
    for line in lines:
        indent, text = line if isinstance(line, tuple) else (0, line)
        if text:
            placed.append((72 + indent * 7.2, y, text))  # Courier 12pt is 7.2pt per char
        y -= leading
    return placed
