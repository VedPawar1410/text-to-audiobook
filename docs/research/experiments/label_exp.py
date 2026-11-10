"""AI line-labelling experiment. Usage: label_exp.py <scratch> <case> <strategy A|C> <provider gemini|groq>

A: every line is sent ("n|text", capped at 100 chars); the model lists only lines that START something.
C: rules decide paragraphs; the model sees only candidate lines (short / page-edge / numeric / caps).
Writes <scratch>/ai/<case>.<strategy>.<provider>.json with labels, tokens and latency.
"""
import json, re, sys, time
import httpx
from google import genai
from google.genai import types
from app.config import settings

S, case, strategy, provider = sys.argv[1:5]
lines = open(f"{S}/ai/{case}.lines").read().split("\n")
PAGE = re.compile(r"^<<page \d+>>$")

RULES = """You prepare text that will be read aloud as an audiobook. Input lines are "number|text".
"<<page N>>" lines are page breaks added by the PDF extractor.
Labels:
  H1 = chapter, part or story title    H2 = sub-heading inside a chapter (e.g. "I.", "Act One:")
  T  = the book/article title (once)   A  = the author's name or byline (once)
  X  = must NOT be read aloud: running headers/footers, page numbers, contents or index pages,
       licence/legal boilerplate, reference lists, citations, navigation links, social-media junk"""
FULL = RULES + """
  P  = first line of a new paragraph (also list items and one-line dialogue)
Output ONLY lines that start something, one per line: "number LABEL", or "first-last LABEL" for a run of
consecutive lines with the same label (use runs for X). Unlisted lines continue the paragraph above.
Blank lines need no label. No other text."""
CAND = RULES + """
  K  = ordinary text, keep as is
You see only some lines of the document (the ambiguous ones), in order, with their real line numbers.
Output ONLY the lines that are not K, one per line: "number LABEL" or "first-last LABEL". No other text."""

def is_candidate(i):
    s = lines[i].strip()
    if not s or PAGE.match(s): return False
    near_page_edge = any(PAGE.match(lines[j].strip()) for j in range(max(0, i - 2), min(len(lines), i + 3)))
    short = len(s) <= 60 and len(s.split()) <= 8 and not s.endswith((",", ";"))
    return near_page_edge or s.isdigit() or short or s.startswith("#") or (s.isupper() and len(s) <= 80)

if strategy == "A":
    shown = [i for i in range(len(lines)) if lines[i].strip()]
    system = FULL
else:
    shown = [i for i in range(len(lines)) if is_candidate(i)]
    system = CAND
payload = "\n".join(f"{i + 1}|{lines[i][:100]}" for i in shown)

def call_gemini(text):
    client = genai.Client(api_key=settings.gemini_api_key)
    t = time.time()
    r = client.models.generate_content(model="gemini-3.5-flash-lite", contents=text,
        config=types.GenerateContentConfig(system_instruction=system, temperature=0, max_output_tokens=20000))
    u = r.usage_metadata
    return r.text or "", {"in": u.prompt_token_count, "out": u.candidates_token_count, "think": u.thoughts_token_count or 0, "s": round(time.time() - t, 1)}

def call_groq(text):
    t = time.time()
    r = httpx.post("https://api.groq.com/openai/v1/chat/completions", timeout=120,
        headers={"Authorization": f"Bearer {settings.groq_api_key}"},
        json={"model": "openai/gpt-oss-120b", "temperature": 0, "reasoning_effort": "low", "max_completion_tokens": 8000,
              "messages": [{"role": "system", "content": system}, {"role": "user", "content": text}]})
    if r.status_code != 200: raise SystemExit(f"groq {r.status_code}: {r.text[:300]}")
    j = r.json(); u = j["usage"]
    return j["choices"][0]["message"]["content"] or "", {"in": u["prompt_tokens"], "out": u["completion_tokens"],
        "think": (u.get("completion_tokens_details") or {}).get("reasoning_tokens", 0), "s": round(time.time() - t, 1),
        "tpm_left": r.headers.get("x-ratelimit-remaining-tokens"), "rpd_left": r.headers.get("x-ratelimit-remaining-requests")}

# Groq's free tier allows 8k tokens/minute, so big inputs go in chunks of ~4.5k tokens (~18k chars), a minute apart
chunks, cur = [], []
limit = 18000 if provider == "groq" else 10**9
for row in payload.split("\n"):
    if cur and sum(len(r) + 1 for r in cur) + len(row) > limit: chunks.append(cur); cur = []
    cur.append(row)
if cur: chunks.append(cur)
out, usage = [], []
for k, chunk in enumerate(chunks):
    if k: time.sleep(62)
    text, u = (call_gemini if provider == "gemini" else call_groq)("\n".join(chunk))
    out.append(text); usage.append(u)
labels = {}
for row in "\n".join(out).split("\n"):
    m = re.match(r"^\s*(\d+)(?:\s*-\s*(\d+))?\s+([A-Z]\d?)\b", row)
    if m:
        a, b = int(m[1]), int(m[2] or m[1])
        for n in range(a, b + 1): labels[n] = m[3]
res = {"case": case, "strategy": strategy, "provider": provider, "lines": len(lines), "shown": len(shown),
       "requests": len(chunks), "usage": usage, "labels": labels, "raw_head": "\n".join(out)[:1500]}
json.dump(res, open(f"{S}/ai/{case}.{strategy}.{provider}.json", "w"))
tot = {k: sum(u[k] for u in usage) for k in ("in", "out", "think", "s")}
print(f"{case:15} {strategy} {provider:6} lines={len(lines)} shown={len(shown)} requests={len(chunks)} tokens in={tot['in']} out={tot['out']} think={tot['think']} time={tot['s']}s labels={len(labels)}", usage[-1].get("tpm_left", ""), usage[-1].get("rpd_left", ""))
