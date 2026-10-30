from app.render.cache import ClipCache
from tests.fakes import FakeEngine


def test_second_request_comes_from_disk(tmp_path):
    engine = FakeEngine()
    cache = ClipCache(tmp_path, engine)

    first = cache.get("Every timeline ends.", "am_michael", 0.9)
    again = ClipCache(tmp_path, engine).get("Every timeline ends.", "am_michael", 0.9)  # e.g. a later render

    assert len(engine.calls) == 1
    assert [w.text for w in again.words] == [w.text for w in first.words]
    assert abs(len(again.audio) - len(first.audio)) == 0


def test_key_depends_on_everything_that_changes_the_sound(tmp_path):
    cache = ClipCache(tmp_path, FakeEngine())
    key = cache.key("Hello.", "am_michael", 1.0)

    assert cache.key("Hello.", "am_michael", 1.0) == key
    assert cache.key("Hello.", "am_michael", 0.95) != key
    assert cache.key("Hello.", "bm_george", 1.0) != key
    assert cache.key("Hello!", "am_michael", 1.0) != key


def test_no_temporary_files_are_left_behind(tmp_path):
    ClipCache(tmp_path, FakeEngine()).get("Hello.", "am_michael", 1.0)

    assert sorted(p.suffix for p in tmp_path.iterdir()) == [".flac", ".json"]
