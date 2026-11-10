import re, sys
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from rules2 import rules2  # rules2.py sits next to this script
from app.structure import parse_text
lines = open(sys.argv[1] + "/dl_gutenberg/holmes_lf.txt", encoding="utf-8").read().split("\n")
s = [l.strip() for l in lines]
stories = [t for t in s if re.fullmatch(r"[IVX]+\. [A-Z][A-Z’' ,-]+", t)]
parts = [i for i, t in enumerate(s) if re.fullmatch(r"[IVX]+\.", t)]
lab = rules2(lines)
h = [s[i - 1] for i, v in sorted(lab.items()) if v in ("H1", "H2")]
x_words = sum(len(s[i - 1].split()) for i, v in lab.items() if v == "X")
start = next(i for i, t in enumerate(s) if t.startswith("*** START")); end = next(i for i, t in enumerate(s) if t.startswith("*** END"))
truth_junk = sum(len(t.split()) for t in s[: start + 1] + s[end:]) + sum(len(t.split()) for t in s[start + 1: start + 30] if t and not t.startswith("The Adventures") and not t.startswith("by "))
lost = [s[i - 1][:40] for i, v in lab.items() if v == "X" and start + 30 < i - 1 < end]
print(f"stories: {sum(t in h for t in stories)}/{len(stories)}  parts (I., II.): {sum(s[i] in h for i in parts)}/{len(parts)} (headings total {len(h)})")
print(f"X words dropped: {x_words} (licence+contents ~{truth_junk}); real lines wrongly dropped: {len(lost)} {lost[:3]}")
extra = [t for t in h if t not in stories and not re.fullmatch(r'[IVX]+\.', t)]
print("extra headings:", len(extra), extra[:10])
doc = parse_text("\n".join(lines))
print("narrate today: sections", len(doc.sections), "headings", sum(b.kind == 'heading' for x in doc.sections for b in x.blocks))
