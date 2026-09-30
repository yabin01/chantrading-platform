"""Unit tests for the strict 1M CenterEngine."""
from chantrading.chanlun.center import CenterEngine, CenterEventType, CenterState
from chantrading.chanlun.segment import Segment, SegmentDirection, SegmentState


def seg(i, low, high):
    return Segment(
        id=f"S{i}",
        direction=SegmentDirection.UP if i % 2 else SegmentDirection.DOWN,
        state=SegmentState.CONFIRMED,
        start_bi_id=f"B{i}a",
        current_end_bi_id=f"B{i}b",
        confirmed_end_bi_id=f"B{i}b",
        start_index=i * 10,
        end_index=i * 10 + 9,
        high=high,
        low=low,
    )


def test_three_segments_with_common_overlap_confirm_center():
    e = CenterEngine()
    events = []
    for s in [seg(1, 100, 110), seg(2, 103, 112), seg(3, 105, 108)]:
        events.extend(e.update(s))

    assert any(x.type is CenterEventType.CENTER_CONFIRMED for x in events)
    c = e.current()
    assert c is not None
    assert c.state is CenterState.CONFIRMED
    assert c.zd == 105
    assert c.zg == 108
    assert c.segment_ids == ["S1", "S2", "S3"]


def test_overlapping_followup_segment_extends_center():
    e = CenterEngine()
    for s in [seg(1, 100, 110), seg(2, 103, 112), seg(3, 105, 108)]:
        e.update(s)

    events = e.update(seg(4, 106, 111))
    c = e.current()

    assert c is not None
    assert c.state is CenterState.EXTENDING
    assert c.extension_count == 1
    assert c.zd == 105
    assert c.zg == 108
    assert any(x.type is CenterEventType.CENTER_EXTENDED for x in events)


def test_non_overlapping_followup_terminates_current_center():
    e = CenterEngine()
    for s in [seg(1, 100, 110), seg(2, 103, 112), seg(3, 105, 108)]:
        e.update(s)

    events = e.update(seg(4, 109, 115))

    assert any(x.type is CenterEventType.CENTER_TERMINATED for x in events)
    assert e.current() is None
    assert e.confirmed_centers()[0].terminated_by_segment_id == "S4"


def test_requires_confirmed_segments():
    e = CenterEngine()
    s = seg(1, 100, 110)
    s.state = SegmentState.EXTENDING
    try:
        e.update(s)
    except ValueError as exc:
        assert "confirmed segments" in str(exc)
    else:
        raise AssertionError("unconfirmed segment must be rejected")


def test_replay_is_deterministic():
    segments = [seg(1, 100, 110), seg(2, 103, 112), seg(3, 105, 108), seg(4, 106, 111)]
    a = CenterEngine()
    b = CenterEngine()
    for s in segments:
        a.update(s)
        b.update(s)
    assert a.snapshot() == b.snapshot()


def test_extension_keeps_original_center_interval_fixed():
    e = CenterEngine()
    for s in [seg(1, 100, 110), seg(2, 103, 112), seg(3, 105, 108)]:
        e.update(s)

    e.update(seg(4, 106, 111))
    c = e.current()
    assert c is not None
    assert (c.zd, c.zg) == (105, 108)
    assert c.gg == 112
    assert c.dd == 100


def test_new_center_must_not_overlap_terminated_center():
    e = CenterEngine()
    for s in [seg(1, 100, 110), seg(2, 103, 112), seg(3, 105, 108)]:
        e.update(s)

    # Terminate above the original center.
    e.update(seg(4, 109, 115))
    e.update(seg(5, 110, 118))
    e.update(seg(6, 112, 120))

    assert e.current() is not None
    assert e.current().id == "CENTER_S6"
    assert e.current().segment_ids == ["S4", "S5", "S6"]
    assert e.current().zd == 112
    assert e.current().zg == 115
    assert e.centers[0].terminated_by_segment_id == "S4"


def test_center_pair_theorem_two_classifies_up_and_down_continuation():
    previous = Center(
        id="C1",
        state=CenterState.CONFIRMED,
        segment_ids=["S1", "S2", "S3"],
        zg=108,
        zd=105,
        gg=110,
        dd=100,
        start_index=1,
        end_index=3,
    )
    following = Center(
        id="C2",
        state=CenterState.CONFIRMED,
        segment_ids=["S4", "S5", "S6"],
        zg=120,
        zd=115,
        gg=125,
        dd=111,
        start_index=4,
        end_index=6,
    )
    assert CenterEngine.classify_center_pair(previous, following) == "UP_CONTINUATION"
    assert CenterEngine.classify_center_pair(following, previous) == "DOWN_CONTINUATION"


def test_center_pair_theorem_two_detects_higher_level_overlap():
    previous = Center(
        id="C1",
        state=CenterState.CONFIRMED,
        segment_ids=["S1", "S2", "S3"],
        zg=110,
        zd=100,
        gg=112,
        dd=98,
        start_index=1,
        end_index=3,
    )
    following = Center(
        id="C2",
        state=CenterState.CONFIRMED,
        segment_ids=["S4", "S5", "S6"],
        zg=95,
        zd=90,
        gg=99,
        dd=89,
        start_index=4,
        end_index=6,
    )
    assert CenterEngine.classify_center_pair(previous, following) == "HIGHER_LEVEL_OVERLAP"
