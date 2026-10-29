import pytest

from app.ingest import IngestError
from app.ingest.url import ensure_public_url, text_from_html
from app.structure import parse_text


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:8000/health",
        "http://127.0.0.1/",
        "http://10.0.0.5/admin",
        "http://192.168.1.1/",
        "http://169.254.169.254/latest/meta-data/",  # cloud metadata endpoint
        "http://[::1]/",
    ],
)
def test_private_and_local_addresses_are_blocked(url):
    with pytest.raises(IngestError, match="private or local"):
        ensure_public_url(url)


@pytest.mark.parametrize("url", ["ftp://example.com/file.txt", "file:///etc/passwd", "not a url"])
def test_non_http_urls_are_rejected(url):
    with pytest.raises(IngestError, match="http"):
        ensure_public_url(url)


ARTICLE = """
<html><head><title>The Kang Dynasty, Explained | Some Site</title></head>
<body>
  <nav><a href="/">Home</a> <a href="/news">News</a> <a href="/login">Sign in</a></nav>
  <article>
    <h1>The Kang Dynasty, Explained</h1>
    <p>Every timeline ends. That is the premise of the story, and it shapes everything
       that follows in the council's long war across the multiverse.</p>
    <h2>Who is Kang?</h2>
    <p>Kang is a conqueror from the far future who has seen every possible ending, and he
       has decided which one he prefers. His variants form a council of rulers.</p>
    <p>The heroes, scattered and outnumbered, must find a single way to win.</p>
  </article>
  <footer>Copyright 2026. Subscribe to our newsletter for more stories.</footer>
</body></html>
"""


def test_article_text_is_extracted_without_page_chrome():
    text, title = text_from_html(ARTICLE, "https://example.com/kang")

    assert title.startswith("The Kang Dynasty, Explained")
    assert "Every timeline ends." in text
    assert "Sign in" not in text and "newsletter" not in text


def test_wikipedia_edit_links_and_markdown_escapes_are_removed():
    html = """<html><body><article>
      <h2>Publication history<span>[<a href="/edit">edit</a>]</span></h2>
      <p>Kang first appeared in Fantastic Four #19 [1963], written by Stan Lee and Jack Kirby,
         and has returned many times since then across the long history of the comics.</p>
    </article></body></html>"""

    text, _ = text_from_html(html)
    blocks = [b.text for s in parse_text(text).sections for b in s.blocks]

    assert not any("edit" in b for b in blocks)
    assert not any("\\" in b for b in blocks)
    assert any("Fantastic Four #19 [1963]" in b for b in blocks)


def test_article_headings_survive_as_sections():
    text, _ = text_from_html(ARTICLE, "https://example.com/kang")

    doc = parse_text(text)

    assert "Who is Kang?" in [s.title for s in doc.sections]
