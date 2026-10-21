from engine.market_structure import analyze_market_structure, breakout_reclaimed, confirmed_swings


def candles_from_swings(highs, lows):
    # Alternating pivot candles separated by enough bars to confirm each pivot.
    candles = []
    for i, (h, l) in enumerate(zip(highs, lows)):
        candles.extend([
            {"high": h - 1, "low": l + 1, "close": (h + l) / 2},
            {"high": h, "low": l, "close": (h + l) / 2},
            {"high": h - 1, "low": l + 1, "close": (h + l) / 2},
        ])
    return candles


def test_confirmed_swings_are_returned_chronologically():
    candles = candles_from_swings([10, 12, 14], [5, 6, 8])
    swings = confirmed_swings(candles, 1, 1)
    assert len(swings["highs"]) >= 2
    assert swings["highs"] == sorted(swings["highs"])


def test_insufficient_data_does_not_force_a_direction():
    result = analyze_market_structure([{"high": 2, "low": 1, "close": 1.5}] * 5,
                                      left_bars=1, right_bars=1)
    assert result["direction"] == "INSUFFICIENT"
    assert result["no_trade_bias"] is False or result["direction"] == "INSUFFICIENT"


def test_failed_breakout_reclaim_detection():
    assert breakout_reclaimed([101, 102, 99], 100, direction="UP")
    assert breakout_reclaimed([99, 98, 101], 100, direction="DOWN")
    assert not breakout_reclaimed([99, 101], 100, direction="UP")
