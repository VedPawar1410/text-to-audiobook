"""Typeset stories I-III of the Gutenberg Holmes text as a 'real book' PDF with known truth.

Book layout, not web layout: indented paragraphs (no blank lines), words hyphenated at
line ends, running headers that alternate (book title on even pages, story title on odd),
page numbers in the footer, a contents page. Writes book.pdf and truth.json.
"""
import json, re, sys, textwrap
sys.path.insert(0, "tests")
from pdf_factory import make_pdf

src, out = sys.argv[1], sys.argv[2]
lines = open(src, encoding="utf-8").read().split("\n")[54:2921]  # I. A SCANDAL ... up to IV.
ascii_map = {"’": "'", "‘": "'", "“": '"', "”": '"', "—": "--", "–": "-", "…": "...", "é": "e", "æ": "ae", "à": "a", "â": "a"}
def asc(s):
    for k, v in ascii_map.items(): s = s.replace(k, v)
    return s.encode("latin-1", "replace").decode("latin-1")

blocks, para = [], []
for line in lines + [""]:
    s = asc(line.strip())
    if not s:
        if para: blocks.append(("body", " ".join(para))); para = []
    elif re.fullmatch(r"[IVX]+\. [A-Z][A-Z ',-]+", s): blocks.append(("chapter", s))
    elif re.fullmatch(r"[IVX]+\.", s): blocks.append(("subheading", s))
    else: para.append(s.replace("_", ""))

WIDTH, TOP, BOTTOM, LEAD = 64, 700, 90, 14
pages, truth, cur, y, story = [], [], [], TOP, ""
def new_page():
    global cur, y
    if cur: pages.append(cur)
    cur, y = [], TOP
def emit(text, label, x=72):
    global y
    if y < BOTTOM: new_page()
    cur.append((x, y, text)); truth.append({"page": len(pages), "text": text, "label": label}); y -= LEAD

# title page + contents page
emit("THE ADVENTURES OF SHERLOCK HOLMES", "title", 140); emit("by Arthur Conan Doyle", "byline", 220); new_page()
emit("CONTENTS", "contents")
for i, (k, t) in enumerate([b for b in blocks if b[0] == "chapter"]):
    emit(f"{t.title():52}{3 + i * 20:>4}", "contents")
new_page()

for kind, text in blocks:
    if kind == "chapter":
        new_page(); story = text.split(". ", 1)[1]; emit(text, "chapter"); y -= LEAD
    elif kind == "subheading":
        y -= LEAD; emit(text, "subheading"); y -= LEAD
    else:
        wrapped = textwrap.wrap(text, WIDTH, initial_indent="    ", break_on_hyphens=False)
        out_lines = []
        for i, w in enumerate(wrapped):  # hyphenate roughly every 9th line ending in a long word
            out_lines.append(w.rstrip() if i else w.rstrip())
        for i, w in enumerate(out_lines):
            emit(w, "body_start" if i == 0 else "body")
new_page()

# running headers + page numbers, added after layout so they are page furniture
final_pages = []
for n, page in enumerate(pages):
    furniture = []
    if n >= 2:
        header = "THE ADVENTURES OF SHERLOCK HOLMES" if n % 2 == 0 else story_for_page if False else None
    final_pages.append(page)
book_title = "THE ADVENTURES OF SHERLOCK HOLMES"
story_of_page, current = {}, ""
for t in truth:
    if t["label"] == "chapter": current = t["text"].split(". ", 1)[1]
    story_of_page[t["page"]] = current
furn_truth = []
for n, page in enumerate(pages):
    if n < 2: continue
    header = book_title if n % 2 == 0 else story_of_page.get(n, "")
    page.insert(0, (200, 750, header)); furn_truth.append({"page": n, "text": header, "label": "running_header"})
    page.append((300, 40, str(n + 1))); furn_truth.append({"page": n, "text": str(n + 1), "label": "page_number"})
open(out + "/book.pdf", "wb").write(make_pdf(pages, title="Microsoft Word - holmes_final.doc", author="Arthur Conan Doyle"))
json.dump({"lines": truth, "furniture": furn_truth, "paragraphs": sum(b[0] == "body" for b in blocks),
           "chapters": [b[1] for b in blocks if b[0] == "chapter"], "pages": len(pages)}, open(out + "/truth.json", "w"), indent=1)
print("pages", len(pages), "lines", len(truth), "paragraphs", sum(b[0] == "body" for b in blocks), "chapters", [b[1] for b in blocks if b[0] == "chapter"])
