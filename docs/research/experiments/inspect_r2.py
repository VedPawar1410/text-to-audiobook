import sys
import os; exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "score_ai.py")).read().split("for case in [")[0])
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from rules2 import rules2
lines = open(f"{S}/ai/pdf.lines").read().split("\n"); truth = truth_for("pdf", lines)
heads, paras, spoken = build(lines, rules2(lines), True)
t_paras, cur = [], None
for i in range(1, len(lines) + 1):
    v = truth.get(i)
    if v == "P": cur = [lines[i-1].strip()]; t_paras.append(cur)
    elif v == "B" and cur is not None: cur.append(lines[i-1].strip())
    elif v == "H": cur = None
t = [norm(" ".join(p)) for p in t_paras]; ps = set(paras)
miss = [p for p in t if p not in ps]
print(len(miss), "missed; produced", len(paras), "paragraphs vs", len(t))
for m in miss[:3]:
    near = [p for p in paras if p[:25] == m[:25]]
    print("  TRUTH:", m[-70:]); print("  OURS :", (near[0][-70:] if near else "(no paragraph starts like this)"))
