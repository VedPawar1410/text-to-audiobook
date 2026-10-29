TEXT_EXTENSIONS = {".txt", ".text", ".md", ".markdown"}


def decode_text(data: bytes) -> str:
    """Decode an uploaded text file: UTF-8 (with or without BOM), else Windows-1252."""
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")
