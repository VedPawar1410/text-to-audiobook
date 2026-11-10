"""Build the numbered-line inputs for the AI labelling experiment (one .txt per case)."""
import io, sys
from pypdf import PdfReader
S = sys.argv[1]
cases = {}
pages = [p.extract_text(extraction_mode="layout") or "" for p in PdfReader(S + "/pdf_holmes/book.pdf").pages]
pdf_lines = []
for n, page in enumerate(pages, 1):
    pdf_lines.append(f"<<page {n}>>")
    pdf_lines += [l.rstrip() for l in page.split("\n")]
cases["pdf"] = pdf_lines
import os
# The Avengers thread is third-party text and isn't in the repo: point AVENGERS_TXT at your own copy
if os.environ.get("AVENGERS_TXT"):
    cases["avengers"] = open(os.environ["AVENGERS_TXT"], encoding="utf-8").read().split("\n")
cases["gutenberg_head"] = open(S + "/dl_gutenberg/holmes_lf.txt", encoding="utf-8").read().split("\n")[:700]
cases["wiki"] = open(S + "/web/wiki.md", encoding="utf-8").read().split("\n")
for name, lines in cases.items():
    # collapse runs of blank lines (they carry no extra signal) and cap line length
    out, blank = [], False
    for l in lines:
        if not l.strip():
            if blank: continue
            blank = True
        else: blank = False
        out.append(l)
    open(f"{S}/ai/{name}.lines", "w").write("\n".join(out))
    numbered = "\n".join(f"{i}|{l[:100]}" for i, l in enumerate(out, 1))
    full = "\n".join(f"{i}|{l}" for i, l in enumerate(out, 1))
    print(f"{name:15} lines={len(out):5}  chars(numbered,cap100)={len(numbered):7}  ~tokens={len(numbered)//4:6}  full ~tokens={len(full)//4}")
