import pysbd

# pysbd knows English abbreviations ("Dr.", "p.m.", "e.g."), so it won't split there.
_segmenter = pysbd.Segmenter(language="en", clean=False)


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _segmenter.segment(text) if s.strip()]
