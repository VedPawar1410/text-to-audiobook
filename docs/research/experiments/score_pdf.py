"""Score Narrate's current PDF path against truth.json: what leaks, what structure survives."""
import json, re, sys
from app.ingest.pdf import text_from_pdf
from app.structure import parse_text
d = sys.argv[1]
truth = json.load(open(d + "/truth.json"))
text, title, author = text_from_pdf(open(d + "/book.pdf", "rb").read())
doc = parse_text(text, title=title, author=author)
blocks = [b for s in doc.sections for b in s.blocks]
spoken = " ".join(b.text for b in blocks)
headers = {f["text"] for f in truth["furniture"] if f["label"] == "running_header"}
leaked_headers = sum(spoken.count(h) for h in headers)
n_headers = sum(1 for f in truth["furniture"] if f["label"] == "running_header")
leaked_nums = len(re.findall(r"(?<![\w.])\d{1,3}(?![\w.])", spoken))  # bare numbers mid-text
contents = [l["text"].split("  ")[0].strip() for l in truth["lines"] if l["label"] == "contents"][1:]
print(f"title={doc.title!r} author={doc.author!r}  words={doc.stats.words}  sections={len(doc.sections)}: {[s.title for s in doc.sections][:8]}")
print(f"running headers spoken: {leaked_headers} of {n_headers} | bare numbers in spoken text: {leaked_nums}")
print(f"contents page spoken: {'CONTENTS' in spoken}, contents lines in text: {sum(c in spoken for c in contents)} of {len(contents)}")
paras = [b for b in blocks if b.kind == "paragraph"]
print(f"paragraph blocks: {len(paras)} (truth {truth['paragraphs']}); longest {max(len(b.text.split()) for b in paras)} words; chapters as headings: {sum(b.kind=='heading' for b in blocks)} (truth {len(truth['chapters'])})")
for h in list(headers)[:3]:
    i = spoken.find(h); print("   leak example:", repr(spoken[max(0,i-50):i+len(h)+30]))
