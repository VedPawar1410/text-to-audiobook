"""Snapshot one finished book from the local API into static files for the Vercel showcase.

    python3 scripts/export_showcase.py <document-id>

The local API must be running (./scripts/start.sh, or uvicorn on port 8000). This saves the same
read-only responses the web app fetches from /api (the book, its render status, chapter manifests
and MP3s, the voice list, a health check) under apps/web/public/demo/. A build with
NEXT_PUBLIC_DEMO=1 serves /api/... from these files (see apps/web/next.config.ts), so the
reader and player work with no backend at all.

Only the chosen book is exported: the library list is filtered to it, so nothing else in the
local library ends up in the public repo. Use public-domain text only. Standard library only.
"""

import json
import shutil
import sys
import urllib.request
from pathlib import Path

API = "http://127.0.0.1:8000"
OUT = Path(__file__).resolve().parent.parent / "apps" / "web" / "public" / "demo"


def get(path: str) -> bytes:
    with urllib.request.urlopen(f"{API}{path}", timeout=60) as response:
        return response.read()


def get_json(path: str):
    return json.loads(get(path))


def write(relative: str, data: bytes) -> None:
    target = OUT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    print(f"  {relative}  ({len(data) / 1024:,.0f} KB)")


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    book = sys.argv[1]

    document = get_json(f"/documents/{book}")
    render = get_json(f"/documents/{book}/render")
    if document["status"] != "directed" or not render["chapters"]:
        sys.exit("That book isn't directed and recorded yet.")
    if any(chapter["status"] != "ready" or chapter["stale"] for chapter in render["chapters"]):
        sys.exit("Some chapters aren't recorded (or are out of date): record the book fully first.")
    if render["job"] and render["job"]["status"] in ("queued", "rendering"):
        sys.exit("A recording is still running.")

    if OUT.exists():
        shutil.rmtree(OUT)  # a fresh snapshot each time: no leftovers from an earlier book
    print(f"Exporting {document['title']!r} to {OUT}")
    summary = next(d for d in get_json("/documents") if d["id"] == book)
    write("health.json", json.dumps({"status": "ok", "database": True}).encode())
    write("documents.json", json.dumps([summary]).encode())
    write(f"documents/{book}.json", json.dumps(document).encode())
    write(f"documents/{book}/render.json", json.dumps(render).encode())
    write("tts/voices.json", get("/tts/voices"))
    for chapter in render["chapters"]:
        base = f"/documents/{book}/chapters/{chapter['section_id']}"
        write(f"documents/{book}/chapters/{chapter['section_id']}/manifest.json", get(f"{base}/manifest"))
        write(f"documents/{book}/chapters/{chapter['section_id']}/audio.mp3", get(f"{base}/audio"))
    print("Done. Build with NEXT_PUBLIC_DEMO=1 to serve it.")
    print(f"If this is a different book, set SHOWCASE_BOOK = \"{book}\" in apps/web/src/lib/demo.ts.")


if __name__ == "__main__":
    main()
