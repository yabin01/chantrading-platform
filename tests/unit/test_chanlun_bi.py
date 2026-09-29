from chantrading.chanlun.bi import BiDirection, BiEngine, BiState
from chantrading.chanlun.models import Fractal, FractalStatus, FractalType


def f(fid, typ, center, top, bottom):
    return Fractal(
        id=fid,
        type=typ,
        center_index=center,
        confirm_index=center + 1,
        top=top,
        bottom=bottom,
        source_processed_ids=(center - 1, center, center + 1),
        status=FractalStatus.CONFIRMED,
    )


def test_bottom_to_top_forms_up_bi_only_with_one_intermediate_processed_candle():
    e = BiEngine()
    assert e.update(f("B0", FractalType.BOTTOM, 1, 10, 8))[0].type == "BI_ANCHOR_SET"
    assert e.update(f("T1", FractalType.TOP, 3, 14, 10))[0].type == "BI_CONFIRMED"
    bi = e.confirmed_bis()[0]
    assert bi.direction is BiDirection.UP
    assert bi.processed_candles_between == 1


def test_top_and_bottom_sharing_a_processed_candle_do_not_form_bi():
    e = BiEngine()
    e.update(f("T0", FractalType.TOP, 1, 14, 10))
    events = e.update(f("B1", FractalType.BOTTOM, 2, 12, 8))
    assert events[0].type == "FRACTAL_REJECTED_NO_INTERMEDIATE_CANDLE"
    assert e.confirmed_bis() == []


def test_same_type_keeps_more_extreme_top():
    e = BiEngine()
    e.update(f("T0", FractalType.TOP, 1, 14, 10))
    events = e.update(f("T1", FractalType.TOP, 3, 16, 11))
    assert events[0].type == "FRACTAL_SUPERSEDED"
    assert e.state == (0, 0)
    assert e.confirmed_bis() == []


def test_same_type_weaker_top_is_ignored():
    e = BiEngine()
    e.update(f("T0", FractalType.TOP, 1, 14, 10))
    events = e.update(f("T1", FractalType.TOP, 3, 13, 9))
    assert events[0].type == "FRACTAL_IGNORED_SAME_TYPE"
    assert e._anchor.id == "T0"


def test_top_to_bottom_forms_down_bi():
    e = BiEngine()
    e.update(f("T0", FractalType.TOP, 1, 15, 11))
    events = e.update(f("B1", FractalType.BOTTOM, 3, 10, 7))
    assert events[0].type == "BI_CONFIRMED"
    bi = e.confirmed_bis()[0]
    assert bi.direction is BiDirection.DOWN
    assert bi.start_price == 15
    assert bi.end_price == 7


def test_endpoint_revision_after_more_extreme_same_type():
    e = BiEngine()
    e.update(f("B0", FractalType.BOTTOM, 1, 10, 8))
    e.update(f("T1", FractalType.TOP, 3, 14, 10))
    events = e.update(f("T2", FractalType.TOP, 5, 16, 11))
    assert events[0].type == "BI_ENDPOINT_REVISED"
    assert e.confirmed_bis()[0].end_fractal_id == "T2"
    assert e.confirmed_bis()[0].end_price == 16
    assert e.confirmed_bis()[0].state is BiState.EXTENDING


def test_invalid_order_does_not_form_bi():
    e = BiEngine()
    e.update(f("B0", FractalType.BOTTOM, 1, 10, 8))
    events = e.update(f("T1", FractalType.TOP, 3, 7, 9))
    assert events[0].type == "FRACTAL_REJECTED_PRICE_ORDER"
    assert e.confirmed_bis() == []


def test_non_confirmed_fractal_is_ignored():
    e = BiEngine()
    x = f("T0", FractalType.TOP, 1, 15, 11)
    x.status = FractalStatus.CANDIDATE
    assert e.update(x) == []
