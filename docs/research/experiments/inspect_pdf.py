import sys, re, collections
sys.argv = [sys.argv[0], sys.argv[1]]
import os; exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "score_ai.py")).read().split("for case in [")[0])
lines = open(f"{S}/ai/pdf.lines").read().split("\n"); truth = truth_for("pdf", lines); rl = rules_labels(lines)
for strategy, provider in [("A", "gemini"), ("C", "gemini"), ("C", "groq")]:
    labels, r = ai_labels("pdf", strategy, provider)
    merged = {**labels, **rl} if strategy == "C" else labels
    heads, paras, spoken = build(lines, merged, strategy == "C")
    junk = [lines[i-1].strip()[:30] for i in sorted(spoken) if truth.get(i) in ("X","T","A")]
    print(f"== {strategy} {provider}: label counts {collections.Counter(labels.values())}")
    print("   junk spoken (sample):", collections.Counter(junk).most_common(5))
    t_heads = {norm(lines[i-1]) for i, v in truth.items() if v == "H"}
    print("   extra headings:", [h[:30] for h in heads if h not in t_heads][:8])
    print("   last labelled line:", max(labels), "of", len(lines))
