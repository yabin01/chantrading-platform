"""Unit tests for the strict 1M CenterEngine."""
from chantrading.chanlun.center import Center, CenterEngine, CenterEventType, CenterState
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


def test_center_expansion_requires_disjoint_centers_and_overlapping_peripheral_ranges():
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
    assert CenterEngine.classify_center_expansion(previous, following) == "HIGHER_LEVEL_EXPANSION"


def test_center_expansion_rejects_overlap_of_center_intervals():
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
        zg=108,
        zd=104,
        gg=116,
        dd=102,
        start_index=4,
        end_index=6,
    )
    assert CenterEngine.classify_center_expansion(previous, following) == "NO_HIGHER_LEVEL_EXPANSION"


def test_center_expansion_rejects_disjoint_peripheral_ranges():
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
        zg=90,
        zd=85,
        gg=94,
        dd=80,
        start_index=4,
        end_index=6,
    )
    assert CenterEngine.classify_center_expansion(previous, following) == "NO_HIGHER_LEVEL_EXPANSION"


def test_center_relation_contract_is_finite_and_stable():
    assert CenterEngine.CENTER_RELATIONS == (
        "UP_CONTINUATION",
        "DOWN_CONTINUATION",
        "HIGHER_LEVEL_OVERLAP",
        "UNCLASSIFIED",
    )


def test_center_relation_boundary_is_not_continuation():
    previous = Center(
        id="C1", state=CenterState.CONFIRMED, segment_ids=["S1", "S2", "S3"],
        zg=108, zd=105, gg=110, dd=100, start_index=1, end_index=3,
    )
    following = Center(
        id="C2", state=CenterState.CONFIRMED, segment_ids=["S4", "S5", "S6"],
        zg=115, zd=110, gg=120, dd=110, start_index=4, end_index=6,
    )
    assert CenterEngine.classify_center_pair(previous, following) == "HIGHER_LEVEL_OVERLAP"


def test_center_relation_is_order_sensitive():
    lower = Center(
        id="C1", state=CenterState.CONFIRMED, segment_ids=["S1", "S2", "S3"],
        zg=95, zd=90, gg=99, dd=89, start_index=1, end_index=3,
    )
    higher = Center(
        id="C2", state=CenterState.CONFIRMED, segment_ids=["S4", "S5", "S6"],
        zg=108, zd=105, gg=110, dd=100, start_index=4, end_index=6,
    )
    assert CenterEngine.classify_center_pair(lower, higher) == "UP_CONTINUATION"
    assert CenterEngine.classify_center_pair(higher, lower) == "DOWN_CONTINUATION"


def test_extension_limit_allows_up_to_five_in_strict_recursive_mode():
    for count in range(0, 6):
        assert CenterEngine.classify_extension_count(count) == "WITHIN_EXTENSION_LIMIT"


def test_extension_limit_requires_higher_level_after_five_in_strict_recursive_mode():
    assert CenterEngine.classify_extension_count(6) == "HIGHER_LEVEL_REQUIRED"


def test_same_level_decomposition_does_not_auto_upgrade_at_six():
    assert (
        CenterEngine.classify_extension_count(6, mode="SAME_LEVEL_DECOMPOSITION")
        == "SAME_LEVEL_CONTINUATION"
    )


def test_extension_limit_rejects_negative_count():
    try:
        CenterEngine.classify_extension_count(-1)
    except ValueError:
        pass
    else:
        raise AssertionError("negative extension count must be rejected")


def test_extension_limit_rejects_unknown_mode():
    try:
        CenterEngine.classify_extension_count(6, mode="UNKNOWN")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown extension mode must be rejected")


def test_center_overlap_requires_positive_width():
    assert CenterEngine._overlaps(100, 110, 105, 108)
    assert not CenterEngine._overlaps(100, 110, 110, 120)
    assert not CenterEngine._overlaps(100, 110, 90, 100)


def test_center_expansion_detects_exact_peripheral_touch_as_no_overlap():
    previous = Center(id="C1", state=CenterState.CONFIRMED, segment_ids=["S1"], zg=110, zd=100, gg=112, dd=98, start_index=1, end_index=3)
    following = Center(id="C2", state=CenterState.CONFIRMED, segment_ids=["S4"], zg=95, zd=90, gg=98, dd=88, start_index=4, end_index=6)
    assert CenterEngine.classify_center_expansion(previous, following) == "NO_HIGHER_LEVEL_EXPANSION"


def test_center_expansion_detects_strict_peripheral_overlap():
    previous = Center(id="C1", state=CenterState.CONFIRMED, segment_ids=["S1"], zg=110, zd=100, gg=112, dd=98, start_index=1, end_index=3)
    following = Center(id="C2", state=CenterState.CONFIRMED, segment_ids=["S4"], zg=95, zd=90, gg=100.1, dd=88, start_index=4, end_index=6)
    assert CenterEngine.classify_center_expansion(previous, following) == "HIGHER_LEVEL_EXPANSION"


def test_duplicate_segment_is_idempotent():
    e = CenterEngine()
    s = seg(1, 100, 110)
    assert e.update(s) == []
    assert e.update(s) == []
    assert e.segments == [s]


def test_out_of_order_segment_is_rejected():
    e = CenterEngine()
    e.update(seg(2, 100, 110))
    try:
        e.update(seg(1, 101, 109))
    except ValueError as exc:
        assert "chronological order" in str(exc)
    else:
        raise AssertionError("out-of-order segment must be rejected")


def test_unclassified_pair_when_neither_theorem_two_condition_applies():
    previous = Center(id="C1", state=CenterState.CONFIRMED, segment_ids=["S1"], zg=110, zd=100, gg=112, dd=98, start_index=1, end_index=3)
    following = Center(id="C2", state=CenterState.CONFIRMED, segment_ids=["S4"], zg=105, zd=101, gg=113, dd=99, start_index=4, end_index=6)
    assert CenterEngine.classify_center_pair(previous, following) == "UNCLASSIFIED"
