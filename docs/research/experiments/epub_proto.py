"""Prototype: EPUB -> sections/blocks using zipfile + lxml (already a dependency via trafilatura)."""
import posixpath, re, sys, zipfile
from lxml import etree, html
z = zipfile.ZipFile(sys.argv[1])
ns = {"c": "urn:oasis:names:tc:opendocument:xmlns:container", "o": "http://www.idpf.org/2007/opf", "dc": "http://purl.org/dc/elements/1.1/"}
opf_path = etree.fromstring(z.read("META-INF/container.xml")).find(".//c:rootfile", ns).get("full-path")
opf = etree.fromstring(z.read(opf_path)); base = posixpath.dirname(opf_path)
title = (opf.findtext(".//dc:title", namespaces=ns) or "").strip(); author = (opf.findtext(".//dc:creator", namespaces=ns) or "").strip()
items = {i.get("id"): i for i in opf.find("o:manifest", ns)}
SKIP_IDS = re.compile(r"pg-(header|footer)|toc|nav|cover|copyright|license", re.I)
sections, skipped = [], 0
for ref in opf.find("o:spine", ns):
    item = items[ref.get("idref")]
    if ref.get("linear") == "no" or "nav" in (item.get("properties") or ""): continue
    doc = html.fromstring(z.read(posixpath.normpath(posixpath.join(base, item.get("href")))))
    for bad in doc.xpath('//*[@id and (starts-with(@id,"pg-header") or starts-with(@id,"pg-footer"))] | //*[contains(@epub:type,"toc") or contains(@epub:type,"pagebreak")] | //nav | //table', namespaces={"epub": "http://www.idpf.org/2007/ops"}):
        skipped += len(bad.text_content().split()); bad.getparent().remove(bad)
    for el in doc.iter("h1", "h2", "h3", "p", "li", "blockquote"):
        text = re.sub(r"\s+", " ", el.text_content()).strip()
        if not text: continue
        if el.tag in ("h1", "h2"): sections.append({"title": text, "blocks": []})
        elif sections: sections[-1]["blocks"].append(("heading" if el.tag == "h3" else "paragraph", text))
        else: sections.append({"title": None, "blocks": [("paragraph", text)]})
words = sum(len(t.split()) for s in sections for _, t in s["blocks"])
print(f"title={title!r} author={author!r} sections={len(sections)} words={words} skipped_words={skipped}")
for s in sections[:16]: print("  ", (s["title"] or "-")[:40], len(s["blocks"]), "blocks", sum(len(t.split()) for _, t in s["blocks"]), "w")
