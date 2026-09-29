from chantrading.chanlun import Candle, FractalEngine, FractalType


def c(ts, o, h, l, cl, v=1):
    return Candle(ts, o, h, l, cl, v)


def test_top_fractal_confirmation():
    e = FractalEngine()
    assert e.update(c(1, 10, 10, 8, 9)) == []
    assert e.update(c(2, 9, 12, 9, 11)) == []
    events = e.update(c(3, 11, 11, 7, 8))
    assert [x.type for x in events] == ["FRACTAL_CONFIRMED"]
    f = events[0].fractal
    assert f.type is FractalType.TOP
    assert f.center_index == 1
    assert f.confirm_index == 2


def test_bottom_fractal_confirmation():
    e = FractalEngine()
    e.update(c(1, 10, 12, 9, 11))
    e.update(c(2, 11, 11, 6, 7))
    events = e.update(c(3, 7, 10, 7, 9))
    assert events[0].fractal.type is FractalType.BOTTOM


def test_inclusion_direction_and_source_ids():
    e = FractalEngine()
    e.update(c(1, 10, 12, 8, 11), raw_index=100)
    e.update(c(2, 11, 11, 9, 10), raw_index=101)
    p = e.inclusion.processed
    assert len(p) == 1
    assert p[0].source_raw_ids == [100, 101]


def test_confirmed_fractal_is_invalidated_when_right_bar_changes():
    e = FractalEngine()
    e.update(c(1, 10, 10, 8, 9))
    e.update(c(2, 9, 12, 9, 11))
    assert e.update(c(3, 11, 11, 7, 8))[0].type == "FRACTAL_CONFIRMED"

    # The fourth raw candle is included into the right processed candle and
    # changes the three-candle window, so the prior confirmation is invalid.
    events = e.update(c(4, 8, 13, 7, 12))
    assert any(x.type == "FRACTAL_INVALIDATED" for x in events)
