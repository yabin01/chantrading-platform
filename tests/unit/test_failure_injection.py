from chantrading.adapters.hyperliquid.failure_injection import CASES, FailureCase, FailureScenario, assert_fail_safe


def test_all_critical_failures_block_trading():
    for case in CASES:
        assert case.trading_must_be_blocked
        try:
            assert_fail_safe(case, True)
            assert False
        except AssertionError:
            pass


def test_healthy_case_is_not_in_failure_matrix():
    assert not any(c.scenario == "HEALTHY" for c in CASES)


def test_unknown_order_is_explicitly_fail_safe():
    case = FailureCase(FailureScenario.UNKNOWN_ORDER, "execution result uncertain")
    assert case.trading_must_be_blocked
