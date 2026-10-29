"""Web article → plain text, via trafilatura (strips nav, ads, footers, comments).

The server fetches URLs on the user's behalf, so it refuses private and local
addresses (SSRF protection), re-checking every redirect hop.
Known POC limit: DNS could change between our check and the fetch (DNS rebinding).
"""

import ipaddress
import re
import socket
from urllib.parse import urljoin, urlsplit

import httpx
import trafilatura

from app.ingest import IngestError

TIMEOUT_SECONDS = 15
MAX_BYTES = 5_000_000
MAX_REDIRECTS = 5
USER_AGENT = "text-to-audiobook/0.1 (+https://github.com/VedPawar1410/text-to-audiobook)"


def ensure_public_url(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise IngestError("Only http(s) links are supported.")
    try:
        infos = socket.getaddrinfo(parts.hostname, parts.port or 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror as error:
        raise IngestError("Couldn't find that website.") from error
    for info in infos:
        if not ipaddress.ip_address(info[4][0]).is_global:
            raise IngestError("Links to private or local network addresses aren't allowed.")


def fetch_page(url: str) -> tuple[str, str, bool]:
    """Return (body, final_url, is_plain_text)."""
    headers = {"User-Agent": USER_AGENT}
    with httpx.Client(timeout=TIMEOUT_SECONDS, follow_redirects=False, headers=headers) as client:
        for _ in range(MAX_REDIRECTS + 1):
            ensure_public_url(url)
            try:
                with client.stream("GET", url) as response:
                    if response.is_redirect:
                        url = urljoin(url, response.headers["location"])
                        continue
                    if response.status_code >= 400:
                        raise IngestError(f"The page returned an error (HTTP {response.status_code}).")

                    content_type = response.headers.get("content-type", "")
                    is_plain = content_type.startswith("text/plain")
                    if "html" not in content_type and not is_plain:
                        raise IngestError("That link isn't a web page or text file.")

                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body += chunk
                        if len(body) > MAX_BYTES:
                            raise IngestError("That page is too large (over 5 MB).")
                    return body.decode(response.encoding or "utf-8", errors="replace"), url, is_plain
            except httpx.HTTPError as error:
                raise IngestError("Couldn't load that page.") from error
    raise IngestError("That link redirects too many times.")


def text_from_html(html: str, url: str | None = None) -> tuple[str, str | None]:
    """Return (article text as markdown, page title)."""
    text = trafilatura.extract(
        html,
        url=url,
        output_format="markdown",
        include_formatting=True,  # keeps headings as "#", so chapters/sections survive
        include_comments=False,
        include_tables=False,
        include_images=False,
        include_links=False,
        favor_recall=True,
    )
    if not text or not text.strip():
        raise IngestError("Couldn't find readable article text on that page.")
    text = re.sub(r"\\?\[edit\\?\]", "", text)  # Wikipedia's section "[edit]" links
    metadata = trafilatura.extract_metadata(html, default_url=url)
    return text, (metadata.title if metadata else None)


def text_from_url(url: str) -> tuple[str, str | None]:
    body, final_url, is_plain = fetch_page(url)
    return (body, None) if is_plain else text_from_html(body, final_url)
