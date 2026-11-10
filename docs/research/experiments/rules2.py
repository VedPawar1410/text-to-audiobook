"""R2: a generic deterministic labeller prototype (no AI). Returns {line_no: label}."""
import re
from collections import Counter
PAGE = re.compile(r"^<<page \d+>>$")
CHAPTERISH = re.compile(r"^(?:chapter|part|book|act|scene|prologue|epilogue|interlude|post-credits)\b.{0,50}$|^[IVXLC]+\.(?:\s+\S.{0,60})?$|^\d{1,3}\.\s+[A-Z].{0,60}$", re.I)
BACK_MATTER = re.compile(r"^#{1,3}\s*(references|sources|notes|external links|see also|further reading|bibliography|citations)\s*$", re.I)
TOC_ENTRY = re.compile(r"^.{3,80}?(?:\s{2,}|\.{3,}\s*)\d{1,4}$")

def rules2(lines):
    lab, N = {}, len(lines)
    s = [l.strip() for l in lines]
    # 1. Gutenberg licence markers
    for i, t in enumerate(s):
        if t.startswith("*** START OF THE PROJECT GUTENBERG"):
            for j in range(i + 1): lab[j + 1] = "X"
        if t.startswith("*** END OF THE PROJECT GUTENBERG"):
            for j in range(i, N): lab[j + 1] = "X"
    # 2. page furniture: short edge lines that repeat on >= 3 pages, and bare numbers at edges
    pages = [i for i, t in enumerate(s) if PAGE.match(t)]
    if len(pages) >= 3:
        edges = []
        for k, p in enumerate(pages):
            end = pages[k + 1] if k + 1 < len(pages) else N
            body = [i for i in range(p + 1, end) if s[i]]
            edges += body[:2] + body[-2:]
        key = lambda i: re.sub(r"\d+", "#", s[i].lower())
        counts = Counter(key(i) for i in set(edges) if len(s[i]) <= 70)
        for i in set(edges):
            if s[i].isdigit() or (len(s[i]) <= 70 and counts[key(i)] >= 3):
                lab[i + 1] = "X"
    # 3. contents: a "Contents" line and the dense run of short lines after it; or >= 3 "title .... 12" lines
    for i, t in enumerate(s):
        if re.fullmatch(r"(table of )?contents", t, re.I):
            lab[i + 1] = "X"; j = i + 1
            while j < N and not s[j]: j += 1
            while j < N and s[j] and len(s[j]) <= 70: lab[j + 1] = "X"; j += 1
    run = []
    for i, t in enumerate(s + [""]):
        if t and TOC_ENTRY.match(t): run.append(i); continue
        if len(run) >= 3:
            for j in run: lab[j + 1] = "X"
        run = []
    # 4. markdown back matter (web pages): references etc. up to the next heading of the same level
    for i, t in enumerate(s):
        if BACK_MATTER.match(t):
            level = len(t) - len(t.lstrip("#")); j = i
            while j < N and not (j > i and s[j].startswith("#") and len(s[j]) - len(s[j].lstrip("#")) <= level):
                lab[j + 1] = "X"; j += 1
    # 5. headings: markdown; or a short line that stands alone (blank/page edge around it) or ends with ":"
    def isolated(i):
        before = i == 0 or not s[i - 1] or PAGE.match(s[i - 1])
        after = i + 1 >= N or not s[i + 1]
        return before and after
    for i, t in enumerate(s):
        if (i + 1) in lab or not t or PAGE.match(t): continue
        if re.match(r"^#{1,6}\s", t):
            lab[i + 1] = "T" if re.match(r"^#\s", t) and i < 3 else ("H1" if t.startswith("## ") else "H2"); continue
        words = len(t.split())
        if words > 8 or len(t) > 70: continue
        starts_para = i == 0 or not s[i - 1]
        if CHAPTERISH.match(t) and (isolated(i) or starts_para):
            lab[i + 1] = "H2" if re.fullmatch(r"[IVXLC]+\.|act .*|post-credits.*", t, re.I) else "H1"
        elif isolated(i) and not re.search(r"[.,;!?\"'”’)…]$", t) and (t.isupper() or t.endswith(":") or t.istitle()):
            lab[i + 1] = "H1" if t.isupper() else "H2"
        elif starts_para and t.endswith(":") and words <= 4:
            lab[i + 1] = "H2"
    # title: first nonblank line if short and the doc has no markdown title yet
    first = next(i for i, t in enumerate(s) if t and (i + 1) not in lab and not PAGE.match(t)) if any(s) else None
    if first is not None and len(s[first]) <= 80 and not first in () and "T" not in lab.values() and isolated(first):
        lab[first + 1] = "T"
    return lab
