"""The structure-eval scorer must be trustworthy before its numbers go in the README."""

from app.structure.models import Block, ParsedDocument, Section, Stats
from structure_eval.cases import all_cases
from structure_eval.score import score_document


def _document(case, paragraphs, title=None, author=None, junk=()):
    blocks = [Block(kind="heading", text=h) for h in case.truth.headings]
    blocks += [Block(kind="paragraph", text=p) for p in [*paragraphs, *junk]]
    stats = Stats(characters=0, words=0, sentences=0, speakers=[], estimated_minutes=0)
    return ParsedDocument(title=title, author=author, format="prose", sections=[Section(blocks=blocks)], stats=stats)


def test_cases_are_deterministic_and_complete():
    first, second = all_cases(), all_cases()
    assert [c.name for c in first] == [c.name for c in second]
    assert all(c.payload == d.payload for c, d in zip(first, second))
    assert all(len(c.truth.paragraphs) == 52 and c.truth.headings for c in first)


def test_perfect_document_scores_full_marks():
    case = all_cases()[0]
    truth = case.truth
    score = score_document(case, _document(case, truth.paragraphs, truth.title, truth.author))
    assert (score.paragraphs_exact, score.headings_found, score.headings_extra) == (52, len(truth.headings), 0)
    assert (score.junk_spoken, score.words_lost, score.title_ok, score.author_ok) == (0, 0, True, True)


def test_merged_paragraphs_junk_and_deletions_are_penalised():
    case = next(c for c in all_cases() if c.name == "gutenberg_style")
    paragraphs = case.truth.paragraphs
    merged = [paragraphs[0] + " " + paragraphs[1], *paragraphs[3:]]  # two glued, one deleted
    score = score_document(case, _document(case, merged, junk=["I. The Harbour", "Project Gutenberg"]))
    assert score.paragraphs_exact == 49
    assert score.junk_spoken == 2
    assert score.words_lost > 0
