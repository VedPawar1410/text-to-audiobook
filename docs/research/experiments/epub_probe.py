"""Structure-only probe of an EPUB: spine, nav, tag counts, furniture signals. Stdlib only."""
import re, sys, zipfile, posixpath
from collections import Counter
z = zipfile.ZipFile(sys.argv[1])
names = z.namelist()
container = z.read("META-INF/container.xml").decode()
opf_path = re.search(r'full-path="([^"]+)"', container)[1]
opf = z.read(opf_path).decode("utf-8", "replace")
base = posixpath.dirname(opf_path)
print("generator:", re.findall(r'name="(?:generator|calibre:[a-z_]+)" content="([^"]*)"', opf)[:2], "| version:", re.search(r'<package[^>]*version="([^"]+)"', opf)[1])
print("drm (encryption.xml):", "META-INF/encryption.xml" in names)
manifest = dict(re.findall(r'<item\b[^>]*?id="([^"]+)"[^>]*?href="([^"]+)"', opf))
manifest.update({i: h for h, i in re.findall(r'<item\b[^>]*?href="([^"]+)"[^>]*?id="([^"]+)"', opf)})
spine = re.findall(r'<itemref\b[^>]*idref="([^"]+)"', opf)
print("spine items:", len(spine), "| page-list:", any(b"page-list" in z.read(n) for n in names if n.endswith((".xhtml",".html",".ncx"))))
navpoints = []
for n in names:
    if n.endswith(".ncx"):
        navpoints = re.findall(r"<text>([^<]*)</text>", z.read(n).decode("utf-8","replace"))
print("toc entries:", len(navpoints), "| first 12:", [t[:40] for t in navpoints[:12]])
tags = Counter(); classes = Counter(); short_num = 0; words = 0; repeated = Counter()
for idref in spine:
    html = z.read(posixpath.normpath(posixpath.join(base, manifest[idref]))).decode("utf-8", "replace")
    tags.update(re.findall(r"<(h[1-6]|p|div|span|li|table|img|a|br)\b", html))
    classes.update(re.findall(r'<p\b[^>]*class="([^"]+)"', html))
    for p in re.findall(r"<p\b[^>]*>(.*?)</p>", html, re.S):
        t = re.sub(r"<[^>]+>", "", p).strip(); words += len(t.split())
        if re.fullmatch(r"\d{1,4}", t): short_num += 1
        if 0 < len(t) < 60: repeated[re.sub(r"\d+", "#", t.lower())] += 1
print("tags:", dict(tags.most_common(10)))
print("p classes:", classes.most_common(6))
print("words:", words, "| <p> that are only a number (page numbers):", short_num)
print("short lines repeated >=5x (running headers?):", [(k[:40], c) for k, c in repeated.most_common(8) if c >= 5])
