from chantrading.chanlun.bi import Bi, BiDirection, BiState
from chantrading.chanlun.segment import (
    SegmentDirection, SegmentEngine, SegmentState
)


def bi(i, direction, start, end):
    return Bi(
        id=f"B{i}",
        start_fractal_id=f"F{i}a",
        end_fractal_id=f"F{i}b",
        start_center_index=i * 2,
        end_center_index=i * 2 + 2,
        start_price=start,
        end_price=end,
        direction=direction,
        state=BiState.BUILDING,
    )


def test_segment_direction_follows_first_bi_and_feature_direction_is_opposite():
    e = SegmentEngine()
    e.update(bi(1, BiDirection.UP, 100, 110))
    s = e.current()
    assert s is not None
    assert s.direction is SegmentDirection.UP
    e.update(bi(2, BiDirection.DOWN, 110, 104))
    assert s.feature_elements[0].direction is BiDirection.DOWN


def test_three_bis_are_not_automatically_a_confirmed_segment():
    e = SegmentEngine()
    e.update(bi(1, BiDirection.UP, 100, 110))
    e.update(bi(2, BiDirection.DOWN, 110, 104))
    events = e.update(bi(3, BiDirection.UP, 104, 112))
    assert not any(x.type == "SEGMENT_CONFIRMED" for x in events)
    assert e.current().state is SegmentState.EXTENDING


def test_type_one_confirms_on_target_feature_fractal_without_gap():
    e = SegmentEngine()
    prices = [
        (1, BiDirection.UP, 100, 110),
        (2, BiDirection.DOWN, 110, 104),
        (3, BiDirection.UP, 104, 112),
        (4, BiDirection.DOWN, 112, 106),
        (5, BiDirection.UP, 106, 120),
        (6, BiDirection.DOWN, 120, 105),
        (7, BiDirection.UP, 105, 113),
    ]
    events = []
    for row in prices:
        events.extend(e.update(bi(*row)))
    assert any(x.type == "SEGMENT_CONFIRMED" for x in events)
    assert e.confirmed_segments()[0].break_type.value == "TYPE_1"


def test_type_two_enters_pending_and_does_not_confirm_on_gap_alone():
    e = SegmentEngine()
    prices = [
        (1, BiDirection.UP, 100, 110),
        (2, BiDirection.DOWN, 110, 104),
        (3, BiDirection.UP, 104, 112),
        (4, BiDirection.DOWN, 112, 101),
        (5, BiDirection.UP, 101, 114),
        (6, BiDirection.DOWN, 114, 120),
        (7, BiDirection.UP, 120, 125),
    ]
    events = []
    for row in prices:
        events.extend(e.update(bi(*row)))
    assert not any(x.type == "SEGMENT_CONFIRMED" for x in events)
    assert e.current().state in {SegmentState.EXTENDING, SegmentState.TYPE_2_PENDING}


def test_duplicate_bi_is_idempotent():
    e = SegmentEngine()
    b = bi(1, BiDirection.UP, 100, 110)
    assert len(e.update(b)) == 1
    assert e.update(b) == []
