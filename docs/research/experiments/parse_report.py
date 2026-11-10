"""Run Narrate's parse_text on a text file and summarise the structure it finds."""
import sys
from app.structure import parse_text
doc = parse_text(open(sys.argv[1], encoding="utf-8").read())
print(f"title={doc.title!r} author={doc.author!r} format={doc.format} words={doc.stats.words} min={doc.stats.estimated_minutes} sections={len(doc.sections)}")
for i, s in enumerate(doc.sections[: int(sys.argv[2]) if len(sys.argv) > 2 else 99]):
    kinds = {}
    for b in s.blocks: kinds[b.kind] = kinds.get(b.kind, 0) + 1
    first = next((b.text for b in s.blocks if b.kind != "heading"), "")
    print(f"  [{i:2}] {str(s.title)[:42]:42} {sum(len(b.text.split()) for b in s.blocks):6}w {kinds}  | {first[:50]!r}")
