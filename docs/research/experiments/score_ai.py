"""Score structure methods against per-case truth. Methods: narrate (current parser), R (rules only),
C (rules + AI on candidate lines), A (AI labels every line). Prints one row per case x method."""
import json, re, statistics, sys
from app.structure import parse_text
S = sys.argv[1]
PAGE = re.compile(r"^<<page \d+>>$")
norm = lambda t: re.sub(r"\s+", " ", re.sub(r"[*_]|^#+\s*|^-\s+", "", t.strip())).strip()

def truth_for(case, lines):
    """Return per-line truth labels (1-based): X/T/A/H/P/B/blank, built from what we know of each source."""
    lab = {}
    nb = lambda i: lines[i - 1].strip()
    N = len(lines)
    if case == "pdf":
        heads = {"THE ADVENTURES OF SHERLOCK HOLMES", "A SCANDAL IN BOHEMIA", "THE RED-HEADED LEAGUE", "A CASE OF IDENTITY"}
        page = 0
        for i in range(1, N + 1):
            s = nb(i)
            if PAGE.match(s): page += 1; lab[i] = "page"; continue
            if not s: lab[i] = "blank"; continue
            prev = [j for j in range(i - 1, 0, -1) if nb(j)][:1]; nxt = [j for j in range(i + 1, N + 1) if nb(j)][:1]
            top = prev and PAGE.match(nb(prev[0])); bottom = (not nxt) or PAGE.match(nb(nxt[0]))
            if page == 1: lab[i] = "T" if "ADVENTURES" in s else "A"
            elif page == 2: lab[i] = "X"
            elif top and s in heads: lab[i] = "X"
            elif bottom and s.isdigit(): lab[i] = "X"
            elif re.fullmatch(r"[IVX]+\. [A-Z][A-Z ',-]+", s) or re.fullmatch(r"[IVX]+\.", s): lab[i] = "H"
            elif lines[i - 1].startswith("    "): lab[i] = "P"
            else: lab[i] = "B"
        return lab
    blank_groups = True
    if case == "gutenberg_head":
        start = next(i for i in range(1, N + 1) if nb(i) == "I. A SCANDAL IN BOHEMIA")
        for i in range(1, start):
            lab[i] = "blank" if not nb(i) else ("T" if nb(i) == "The Adventures of Sherlock Holmes" else "A" if nb(i).startswith("by Arthur") else "X")
        first = start
    elif case == "wiki":
        refs = next(i for i in range(1, N + 1) if nb(i) == "## References")
        lab[1] = "T"
        for i in range(refs, N + 1): lab[i] = "blank" if not nb(i) else "X"
        first = 2; N_end = refs
    elif case == "avengers":
        lab[1] = "T"; first = 2
    end = N_end if case == "wiki" else N + 1
    prev_blank = True
    for i in range(first, end):
        s = nb(i)
        if not s: lab[i] = "blank"; prev_blank = True; continue
        if case == "avengers" and s.startswith("TITLECARD"): lab[i] = "ignore"
        elif case == "avengers" and s in {"Act One:", "Act Two:", "Act Three", "Post-Credits Scene:"}: lab[i] = "H"
        elif case == "gutenberg_head" and (re.fullmatch(r"[IVX]+\. [A-Z][A-Z ’',-]+", s) or re.fullmatch(r"[IVX]+\.", s)): lab[i] = "H"
        elif case == "wiki" and s.startswith("#"): lab[i] = "H"
        elif case == "avengers" or prev_blank or s.startswith("- "): lab[i] = "P"
        else: lab[i] = "B"
        prev_blank = False
    return lab

def build(lines, labels, para_rule):
    """Walk lines with labels -> (headings, paragraphs, spoken line numbers)."""
    heads, paras, spoken, cur = [], [], set(), None
    nonblank = [l for l in lines if l.strip() and not PAGE.match(l.strip())]
    median = statistics.median(len(l.strip()) for l in nonblank)
    hard_wrapped = sum(1 for a, b in zip(lines, lines[1:]) if a.strip() and b.strip()) > 0.6 * len(nonblank)
    prev_text = None
    for i, raw in enumerate(lines, 1):
        s = raw.strip(); lab = labels.get(i)
        if PAGE.match(s): continue
        if not s:
            prev = next((j for j in range(i - 1, 0, -1) if lines[j - 1].strip()), None)
            nxt = next((j for j in range(i + 1, len(lines) + 1) if lines[j - 1].strip()), None)
            edge = lambda j: j is not None and (PAGE.match(lines[j - 1].strip()) or labels.get(j) == "X")
            if not (edge(prev) or edge(nxt)): cur = None
            continue
        if lab in ("X", "T", "A"): continue
        spoken.add(i)
        if lab in ("H1", "H2"): heads.append(norm(s)); cur = None; prev_text = None; continue
        new = cur is None or lab == "P"
        if para_rule and not new and lab != "B":
            indented = raw.startswith("  ")
            short_end = prev_text and re.search(r"[.!?\"'”’)]$", prev_text) and len(prev_text) < 0.75 * median
            new = indented or (hard_wrapped and bool(short_end))
        if new: cur = []; paras.append(cur)
        cur.append(s); prev_text = s
    return heads, [norm(" ".join(p)) for p in paras], spoken

def rules_labels(lines):
    """Deterministic labels: Gutenberg licence markers; markdown headings."""
    lab, skip = {}, False
    for i, l in enumerate(lines, 1):
        s = l.strip()
        if s.startswith("*** START OF THE PROJECT GUTENBERG"):
            for j in range(1, i + 1): lab[j] = "X"
        if s.startswith("*** END OF THE PROJECT GUTENBERG"): skip = True
        if skip: lab[i] = "X"
        elif re.match(r"^#{1,6}\s", s): lab[i] = "H1" if s.startswith("##") else "T"
    return lab

def ai_labels(case, strategy, provider):
    try: r = json.load(open(f"{S}/ai/{case}.{strategy}.{provider}.json"))
    except FileNotFoundError: return None, None
    labels = {int(k): v for k, v in r["labels"].items()}
    if not labels:  # re-parse "n|LABEL" style answers
        for row in r["raw_head"].split("\n"):
            m = re.match(r"^\s*(\d+)(?:\s*-\s*(\d+))?\s*[|\s]\s*([A-Z]\d?)\b", row)
            if m:
                for n in range(int(m[1]), int(m[2] or m[1]) + 1): labels[n] = m[3]
    labels = {k: ("H1" if v == "H1" else "H2" if v == "H2" else v) for k, v in labels.items() if v != "K"}
    return labels, r

def score(case, lines, truth, heads, paras, spoken):
    t_heads = [norm(lines[i - 1]) for i, v in truth.items() if v == "H"]
    t_paras, cur = [], None
    for i in range(1, len(lines) + 1):
        v = truth.get(i)
        if v == "P": cur = [lines[i - 1].strip()]; t_paras.append(cur)
        elif v == "B" and cur is not None: cur.append(lines[i - 1].strip())
        elif v == "H": cur = None
    t_paras = [norm(" ".join(p)) for p in t_paras]
    para_set = set(paras)
    exact = sum(p in para_set for p in t_paras)
    found = sum(h in heads or any(h == norm(x) for x in heads) for h in t_heads)
    if spoken is None:  # current parser: no line map, so junk = X lines (>=12 chars) found verbatim in spoken text
        blob = " ".join(paras + heads)
        junk = sum(1 for i, v in truth.items() if v in ("X",) and len(lines[i - 1].strip()) >= 12 and norm(lines[i - 1]) in blob)
        junk_s = f"~{junk}"; lost = "?"
    else:
        junk_s = str(sum(1 for i in spoken if truth.get(i) in ("X", "T", "A")))
        lost = sum(1 for i, v in truth.items() if v in ("P", "B", "H") and i not in spoken)
    return f"paras exact {exact:4}/{len(t_paras):<4} ({100*exact/max(1,len(t_paras)):5.1f}%)  headings {found}/{len(t_heads)} (+{max(0,len(heads)-found)} extra)  junk lines spoken {junk_s:>5}  real lines lost {lost}"

for case in ["avengers", "wiki", "gutenberg_head", "pdf"]:
    lines = open(f"{S}/ai/{case}.lines").read().split("\n")
    truth = truth_for(case, lines)
    if case == "pdf":
        from app.ingest.pdf import text_from_pdf
        text, title, author = text_from_pdf(open(f"{S}/pdf_holmes/book.pdf", "rb").read())
    else:
        text = "\n".join(l for l in lines)
    doc = parse_text(text)
    blocks = [b for s in doc.sections for b in s.blocks]
    nh = [norm(b.text) for b in blocks if b.kind == "heading"]
    np_ = [norm(b.text) for b in blocks if b.kind not in ("heading", "scene_break")]
    print(f"\n### {case}")
    print(f"  {'narrate (today)':24}", score(case, lines, truth, nh, np_, None))
    rl = rules_labels(lines)
    import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from rules2 import rules2
    r2 = rules2(lines)
    print(f"  {'R2 better rules':24}", score(case, lines, truth, *build(lines, r2, True)))
    print(f"  {'R rules only':24}", score(case, lines, truth, *build(lines, rl, True)))
    for strategy in ("C", "A"):
        for provider in ("gemini", "groq"):
            labels, r = ai_labels(case, strategy, provider)
            if labels is None: continue
            merged = {**labels, **rl} if strategy == "C" else labels
            if strategy == "C":
                m2 = {**r2, **{k: v for k, v in labels.items() if k not in r2}}
                print(f"  {'R2 + C ' + provider:24}", score(case, lines, truth, *build(lines, m2, True)))
            tok = sum(u["in"] for u in r["usage"]), sum(u["out"] for u in r["usage"])
            name = f"{strategy} {provider} ({tok[0]}/{tok[1]} tok)"
            print(f"  {name:24}", score(case, lines, truth, *build(lines, merged, strategy == "C")))
