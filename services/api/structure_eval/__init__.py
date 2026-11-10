"""Structure evaluation: how well does import find chapters, paragraphs and junk?

Every case is built from one synthetic book (corpus.py), rendered into a messy real-world
format (cases.py): a web paste, a Gutenberg-style file, a typeset PDF, a web article...
Because we render the mess ourselves, the right answer is known exactly, so each change to
the parser gets an honest before/after score (score.py).

Run from services/api:  uv run --no-sync python -m structure_eval
"""
