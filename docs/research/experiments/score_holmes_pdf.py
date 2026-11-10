"""Real-prose check: the 60-page Holmes PDF through the real import path, against truth.json."""
import json, re, sys
from app.ingest.pdf import text_from_pdf
from app.structure import parse_text
d = sys.argv[1]
truth = json.load(open(d + "/truth.json"))
text, title, author = text_from_pdf(open(d + "/book.pdf", "rb").read())
doc = parse_text(text, title=title, author=author)
norm = lambda t: re.sub(r"\s+", " ", t.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')).strip()
paras, cur = [], None
for l in truth["lines"]:
    if l["label"] == "body_start": cur = [l["text"].strip()]; paras.append(cur)
    elif l["label"] == "body" and cur is not None: cur.append(l["text"].strip())
    elif l["label"] in ("chapter", "subheading"): cur = None
paras = [norm(" ".join(p)) for p in paras]
blocks = [b for s in doc.sections for b in s.blocks]
body = {norm(b.text) for b in blocks if b.kind != "heading"}
heads = [b.text for b in blocks if b.kind == "heading"]
spoken = " ".join(norm(b.text) for b in blocks if b.kind != "heading")
headers = {f["text"] for f in truth["furniture"] if f["label"] == "running_header"}
print(f"title={doc.title!r} author={doc.author!r}")
print(f"paragraphs exact: {sum(p in body for p in paras)}/{len(paras)}; paragraph blocks: {sum(b.kind=='paragraph' for b in blocks)}")
print(f"headings: {heads}")
numbers = re.findall(r"(?<![\w.,])[0-9]{1,3}(?![\w.,])", spoken)
print(f"running headers spoken: {sum(spoken.count(norm(h)) for h in headers)}; bare numbers: {len(numbers)}")
want = re.findall(r"[a-z']+", " ".join(paras).lower()); got = re.findall(r"[a-z']+", spoken.lower())
from collections import Counter; print("words lost:", sum((Counter(want) - Counter(got)).values()), "of", len(want))
