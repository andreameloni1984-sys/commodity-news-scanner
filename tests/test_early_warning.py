from datetime import datetime, timezone
import os
import time

from engine.early_warning import compute_market_early_warning, classify_catalyst_timing


def test_market_early_warning_requires_timestamped_data():
    result = compute_market_early_warning([100, 99, 98], [], 1.0)
    assert result["stage"] == "INSUFFICIENT_DATA"
    assert result["execution_authorized"] is False


def test_market_early_warning_detects_directional_acceleration_without_authorizing_trade():
    now = 1_800_000_000.0
    timestamps = [now + i * 60 for i in range(91)]
    closes = []
    for i in range(91):
        if i < 60:
            closes.append(100.0 + 0.002 * i)
        else:
            closes.append(100.12 - 0.035 * (i - 60))
    result = compute_market_early_warning(closes, timestamps, atr=0.5, now=timestamps[-1])
    assert result["direction"] == "SHORT"
    assert result["stage"] in {"EARLY_WARNING", "LATE_MOVE", "WATCH"}
    assert result["execution_authorized"] is False
    assert result["method"] == "HEURISTIC_NOT_CALIBRATED"


def test_catalyst_timing_requires_real_publication_timestamp():
    now = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)
    missing = classify_catalyst_timing({"title": "Oil supply news"}, now)
    fresh = classify_catalyst_timing({
        "published": "Thu, 22 Oct 2026 11:50:00 GMT"
    }, now)
    stale = classify_catalyst_timing({
        "published": "Thu, 22 Oct 2026 06:00:00 GMT"
    }, now)
    assert missing["timing"] == "TIME_UNVERIFIED"
    assert fresh["timing"] == "FRESH_CATALYST"
    assert stale["timing"] == "STALE_CATALYST"
    assert all(x["execution_authorized"] is False for x in (missing, fresh, stale))


def test_catalyst_timing_exposes_future_clock_skew_for_audit():
    now = datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc)
    tolerated = classify_catalyst_timing(
        {"published": "2026-10-23T12:02:00Z"}, now
    )
    invalid = classify_catalyst_timing(
        {"published": "2026-10-23T12:07:00Z"}, now
    )

    assert tolerated["timing"] == "FRESH_CATALYST"
    assert tolerated["age_minutes"] == 0.0
    assert tolerated["future_skew_minutes"] == 2.0
    assert "futuro di 2.0 min" in tolerated["reason"]
    assert invalid["timing"] == "FUTURE_TIMESTAMP_INVALID"
    assert invalid["future_skew_minutes"] == 7.0
    assert invalid["execution_authorized"] is False
    assert tolerated["execution_authorized"] is False


def test_catalyst_timing_treats_naive_now_as_utc_not_host_local_timezone():
    previous_tz = os.environ.get("TZ")
    try:
        # Simulate a non-UTC host: the naive reference time must still mean UTC.
        os.environ["TZ"] = "Etc/GMT+8"
        time.tzset()
        result = classify_catalyst_timing(
            {"published": "2026-10-22T11:50:00Z"},
            datetime(2026, 10, 22, 12, 0),
        )
        assert result["timing"] == "FRESH_CATALYST"
        assert result["age_minutes"] == 10.0
        assert result["execution_authorized"] is False
    finally:
        if previous_tz is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = previous_tz
        time.tzset()


def test_market_early_warning_rejects_stale_latest_timestamp():
    now = 1_800_000_000.0
    timestamps = [now - 9000 + i * 60 for i in range(91)]
    closes = [100.0 + i * 0.02 for i in range(91)]
    result = compute_market_early_warning(closes, timestamps, atr=0.5, now=now)
    assert result["stage"] == "INSUFFICIENT_DATA"
    assert result["direction"] == "NONE"
    assert result["latest_timestamp_age_seconds"] == 3600.0
    assert "troppo vecchio" in result["reasons"][0]
    assert result["execution_authorized"] is False


def test_market_early_warning_rejects_future_latest_timestamp():
    now = 1_800_000_000.0
    timestamps = [now + 300 + i * 60 for i in range(91)]
    closes = [100.0 + i * 0.02 for i in range(91)]
    result = compute_market_early_warning(closes, timestamps, atr=0.5, now=now)
    assert result["stage"] == "INSUFFICIENT_DATA"
    assert result["direction"] == "NONE"
    assert "nel futuro" in result["reasons"][0]
    assert result["execution_authorized"] is False


def test_lead_time_backtest_needs_valid_history():
    from engine.early_warning import backtest_market_early_warning_lead_time
    result = backtest_market_early_warning_lead_time([])
    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["execution_authorized"] is False



def test_market_early_warning_rejects_mismatched_price_timestamp_lengths():
    now = 1_800_000_000.0
    timestamps = [now - (90 - i) * 60 for i in range(91)]
    closes = [100.0 + i * 0.01 for i in range(91)]

    missing_timestamp = compute_market_early_warning(
        closes, timestamps[:-1], atr=0.5, now=now
    )
    missing_price = compute_market_early_warning(
        closes[:-1], timestamps, atr=0.5, now=now
    )

    for result in (missing_timestamp, missing_price):
        assert result["stage"] == "INSUFFICIENT_DATA"
        assert result["direction"] == "NONE"
        assert result["score"] == 0
        assert "non coincide" in result["reasons"][0]
        assert result["execution_authorized"] is False


def test_reversal_is_not_mislabeled_as_directional_acceleration():
    now = 1_800_000_000.0
    timestamps = [now - (90 - i) * 60 for i in range(91)]
    closes = []
    for i in range(91):
        if i <= 30:
            closes.append(103.0)
        elif i <= 60:
            closes.append(103.0 - (3.0 * (i - 30) / 30.0))
        else:
            closes.append(100.0 + (1.0 * (i - 60) / 30.0))
    result = compute_market_early_warning(closes, timestamps, atr=0.5, now=now)
    preceding_30m = (closes[-31] / closes[-61] - 1.0) * 100.0
    latest_30m = (closes[-1] / closes[-31] - 1.0) * 100.0
    assert result["direction"] == "LONG"
    assert "accelerazione recente coerente con la direzione" not in result["reasons"]
    # The reported metric is a signed change in return, not the change in
    # absolute return magnitude; this makes reversal direction explicit.
    assert result["acceleration_pct_points"] == round(latest_30m - preceding_30m, 4)
    assert result["acceleration_pct_points"] > 0
    assert result["execution_authorized"] is False

def test_lead_time_backtest_measures_favorable_move_without_authorizing_trade():
    from engine.early_warning import backtest_market_early_warning_lead_time

    # Quiet drift, then a faster same-direction leg. The controlled OHLC path
    # should produce early-warning samples and a measurable future excursion.
    start = 1_800_000_000.0 - 179 * 60
    candles = []
    price = 100.0
    for i in range(180):
        if i == 0:
            price = 100.0
        elif i < 90:
            price += 0.002
        elif i < 150:
            price += 0.02
        else:
            price += 0.06
        candles.append({
            "timestamp": start + i * 60,
            "high": price + 0.05,
            "low": price - 0.05,
            "close": price,
        })

    result = backtest_market_early_warning_lead_time(candles, max_bars=96, horizon_bars=12)

    assert result["status"] == "OK"
    assert result["sample_count"] > 0
    assert result["favorable_first"] > 0
    assert result["favorable_0_25atr_first"] + result["adverse_0_25atr_first"] + result["same_bar_0_25atr_ambiguous"] + result["neither_reached_0_25atr"] == result["sample_count"]
    assert result["median_warning_to_favorable_0_25atr_seconds"] is not None
    assert all(
        sample["warning_to_favorable_0_25atr_seconds"] is None
        or sample["warning_to_favorable_0_25atr_seconds"] <= sample["lead_seconds"]
        for sample in result["samples"]
    )
    assert 0 <= result["warnings_after_prior_0_5atr_30m_move"] <= result["sample_count"]
    assert result["warnings_after_prior_0_5atr_30m_move_pct"] == round(
        100.0 * result["warnings_after_prior_0_5atr_30m_move"] / result["sample_count"], 1
    )
    assert 0 <= result["warnings_after_prior_opposite_0_5atr_move"] <= result["sample_count"]
    classes = result["prior_move_timing_class_counts"]
    assert sum(classes.values()) == result["sample_count"]
    for label, count in classes.items():
        assert result["prior_move_timing_class_pct"][label] == round(
            100.0 * count / result["sample_count"], 1
        )
    assert set(classes) == {
        "LOW_PRIOR_MOVE_PROXY", "LATE_CONTINUATION_PROXY",
        "REVERSAL_CONTEXT_PROXY", "INTERMEDIATE_PRIOR_MOVE", "UNCLASSIFIED",
    }

    # Outcome statistics must partition the exact samples in each decision-time
    # class and direction; empty groups must remain explicit and safe.
    outcomes_by_class = result["outcomes_by_prior_move_class"]
    outcomes_by_class_direction = result["outcomes_by_prior_move_class_and_direction"]
    assert set(outcomes_by_class) == set(classes)
    assert set(outcomes_by_class_direction) == set(classes)
    for label, summary in outcomes_by_class.items():
        grouped = [
            row for row in result["samples"]
            if row["prior_move_timing_class"] == label
        ]
        assert summary["sample_count"] == len(grouped) == classes[label]
        assert (
            summary["favorable_first"] + summary["adverse_first"]
            + summary["same_bar_ambiguous"] + summary["neither_reached_0_5atr"]
            == summary["sample_count"]
        )
        assert summary["favorable_first"] == sum(
            1 for row in grouped if row["lead_seconds"] is not None and (
                row["first_adverse_seconds"] is None
                or row["lead_seconds"] < row["first_adverse_seconds"]
            )
        )
        assert set(outcomes_by_class_direction[label]) == {"LONG", "SHORT"}
        directional_total = 0
        for direction, direction_summary in outcomes_by_class_direction[label].items():
            directional_group = [
                row for row in grouped if row["direction"] == direction
            ]
            directional_total += direction_summary["sample_count"]
            assert direction_summary["sample_count"] == len(directional_group)
            assert (
                direction_summary["favorable_first"] + direction_summary["adverse_first"]
                + direction_summary["same_bar_ambiguous"]
                + direction_summary["neither_reached_0_5atr"]
                == direction_summary["sample_count"]
            )
            if not directional_group:
                assert direction_summary["median_warning_to_favorable_0_5atr_seconds"] is None
                assert direction_summary["median_warning_to_adverse_0_5atr_seconds"] is None
                assert direction_summary["favorable_first_pct_resolved"] is None
        assert directional_total == summary["sample_count"]

    for sample in result["samples"]:
        prior_return = sample["pre_warning_30m_return_pct"]
        assert prior_return is not None and prior_return > -100.0
        prior_base = sample["entry_price"] / (1.0 + prior_return / 100.0)
        signed_move = (
            (sample["entry_price"] - prior_base) / sample["atr_at_warning"]
            * (1.0 if sample["direction"] == "LONG" else -1.0)
        )
        assert abs(sample["pre_warning_30m_directional_move_atr"] - signed_move) < 0.00011
        assert sample["move_already_underway"] == (signed_move >= 0.5)
        assert sample["prior_move_against_warning"] == (signed_move <= -0.5)
        assert abs(
            sample["pre_warning_30m_move_atr"] - abs(signed_move)
        ) < 0.00011
    assert result["median_seconds_to_favorable_0_5atr"] is not None
    assert result["median_warning_to_favorable_seconds"] == result["median_seconds_to_favorable_0_5atr"]
    assert result["median_warning_to_adverse_seconds"] == result["median_seconds_to_adverse_0_5atr"]
    assert all(
        sample["warning_to_favorable_seconds"] == sample["lead_seconds"]
        and sample["warning_to_adverse_seconds"] == sample["first_adverse_seconds"]
        for sample in result["samples"]
    )
    assert result["adverse_first_pct"] == round(
        100.0 * result["adverse_first"] / result["sample_count"], 1
    )
    resolved = result["favorable_first"] + result["adverse_first"]
    assert result["resolved_first_count"] == resolved
    assert resolved > 0
    assert result["favorable_first_pct_resolved"] == round(
        100.0 * result["favorable_first"] / resolved, 1
    )
    assert result["adverse_first_pct_resolved"] == round(
        100.0 * result["adverse_first"] / resolved, 1
    )
    assert round(
        result["favorable_first_pct_resolved"] + result["adverse_first_pct_resolved"], 1
    ) == 100.0
    adverse_times = [
        sample["first_adverse_seconds"]
        for sample in result["samples"]
        if sample["first_adverse_seconds"] is not None
    ]
    from statistics import median
    assert result["median_seconds_to_adverse_0_5atr"] == (
        median(adverse_times) if adverse_times else None
    )
    assert result["execution_authorized"] is False
    assert result["method"] == "ROLLING_WALK_FORWARD_NOT_CALIBRATED"
    assert all(sample["lead_seconds"] is not None for sample in result["samples"])


def test_lead_time_backtest_rejects_conflicting_duplicate_ohlc_timestamps():
    from engine.early_warning import backtest_market_early_warning_lead_time

    start = 1_800_000_000.0 - 39 * 60
    candles = []
    for i in range(40):
        close = 100.0 + i * 0.01
        candles.append({
            "timestamp": start + i * 60,
            "high": close + 0.05,
            "low": close - 0.05,
            "close": close,
        })
    conflicting = dict(candles[10])
    conflicting["high"] += 0.25
    candles.append(conflicting)

    result = backtest_market_early_warning_lead_time(candles)

    assert result["status"] == "INVALID_DATA"
    assert result["sample_count"] == 0
    assert "timestamp duplicati" in result["reason"]
    assert result["execution_authorized"] is False


def test_lead_time_backtest_rejects_invalid_parameters_without_raising():
    from engine.early_warning import backtest_market_early_warning_lead_time

    invalid_options = [
        {"max_bars": 0},
        {"max_bars": 1},
        {"max_bars": 29},
        {"max_bars": -1},
        {"max_bars": "not-a-number"},
        {"max_bars": float("nan")},
        {"horizon_bars": 2},
        {"horizon_bars": 13},
        {"horizon_bars": "not-a-number"},
        {"horizon_bars": float("inf")},
        {"horizon_bars": True},
    ]
    for options in invalid_options:
        result = backtest_market_early_warning_lead_time([], **options)
        assert result["status"] == "INVALID_PARAMETERS"
        assert result["sample_count"] == 0
        assert result["execution_authorized"] is False

def test_lead_time_backtest_warning_metadata_is_invariant_to_future_price_changes():
    from engine.early_warning import backtest_market_early_warning_lead_time

    start = 1_800_000_000.0 - 179 * 60
    candles = []
    price = 100.0
    for i in range(180):
        if i == 0:
            price = 100.0
        elif i < 90:
            price += 0.002
        elif i < 150:
            price += 0.02
        else:
            price += 0.06
        candles.append({
            "timestamp": start + i * 60,
            "high": price + 0.05,
            "low": price - 0.05,
            "close": price,
        })

    cutoff_index = 130
    cutoff_timestamp = candles[cutoff_index]["timestamp"]
    changed_future = [dict(candle) for candle in candles]
    # Change only candles strictly after the cutoff. Warning decisions up to
    # that time must not depend on these future outcomes.
    for i in range(cutoff_index + 1, len(changed_future)):
        for field in ("high", "low", "close"):
            changed_future[i][field] -= 2.0

    baseline = backtest_market_early_warning_lead_time(
        candles, max_bars=96, horizon_bars=12
    )
    altered = backtest_market_early_warning_lead_time(
        changed_future, max_bars=96, horizon_bars=12
    )

    assert baseline["status"] == altered["status"] == "OK"
    baseline_prefix = {
        row["warning_timestamp"]: row
        for row in baseline["samples"]
        if row["warning_timestamp"] <= cutoff_timestamp
    }
    altered_prefix = {
        row["warning_timestamp"]: row
        for row in altered["samples"]
        if row["warning_timestamp"] <= cutoff_timestamp
    }
    assert baseline_prefix
    assert baseline_prefix.keys() == altered_prefix.keys()
    for timestamp, row in baseline_prefix.items():
        other = altered_prefix[timestamp]
        assert row["direction"] == other["direction"]
        assert row["score"] == other["score"]
        assert row["entry_price"] == other["entry_price"]
        assert row["atr_at_warning"] == other["atr_at_warning"]
        # All warning-time diagnostics, including the lateness class, must be
        # invariant when only candles after the cutoff are changed.
        for field in (
            "pre_warning_30m_return_pct",
            "pre_warning_30m_move_atr",
            "pre_warning_30m_directional_move_atr",
            "move_already_underway",
            "prior_move_against_warning",
            "prior_move_timing_class",
        ):
            assert row[field] == other[field]
    assert baseline["execution_authorized"] is False
    assert altered["execution_authorized"] is False

def test_lead_time_backtest_rejects_malformed_candle_instead_of_skipping_it():
    from engine.early_warning import backtest_market_early_warning_lead_time

    start = 1_800_000_000.0 - 39 * 60
    candles = []
    for i in range(40):
        close = 100.0 + i * 0.01
        candles.append({
            "timestamp": start + i * 60,
            "high": close + 0.05,
            "low": close - 0.05,
            "close": close,
        })
    candles[20] = {**candles[20], "close": float("nan")}

    result = backtest_market_early_warning_lead_time(candles)

    assert result["status"] == "INVALID_DATA"
    assert result["sample_count"] == 0
    assert "OHLC o timestamp non valido" in result["reason"]
    assert result["execution_authorized"] is False


def test_market_early_warning_rejects_conflicting_duplicate_timestamps():
    now = 1_800_000_000.0
    timestamps = [now - (19 - i) * 60 for i in range(20)]
    closes = [100.0 + i * 0.02 for i in range(20)]
    timestamps.append(timestamps[10])
    closes.append(closes[10] + 0.5)

    result = compute_market_early_warning(closes, timestamps, atr=0.5, now=now)

    assert result["stage"] == "INVALID_DATA"
    assert result["direction"] == "NONE"
    assert result["score"] == 0
    assert "timestamp duplicati" in result["reasons"][0]
    assert result["execution_authorized"] is False

def test_market_early_warning_rejects_recent_timestamp_gap():
    now = 1_800_000_000.0
    timestamps = [now - (90 - i) * 60 for i in range(91)]
    # A ten-minute hole immediately before the latest quote makes the latest
    # 30m/60m return timing ambiguous, even though the final timestamp is fresh.
    timestamps = [stamp - 540 if i < 90 else stamp for i, stamp in enumerate(timestamps)]
    closes = [100.0 + i * 0.001 for i in range(90)] + [101.0]

    result = compute_market_early_warning(closes, timestamps, atr=0.5, now=now)

    assert result["stage"] == "INSUFFICIENT_DATA"
    assert result["direction"] == "NONE"
    assert result["score"] == 0
    assert "gap nei timestamp nell'ultima ora" in result["reasons"][0]
    assert result["execution_authorized"] is False


def test_market_early_warning_suppresses_volatility_bonus_across_older_gap():
    now = 1_800_000_000.0
    timestamps = [now - (39 - i) * 900 for i in range(40)]
    # Insert a one-hour gap ending 75 minutes before the latest candle. It is
    # outside the momentum freshness guard but inside the volatility sample.
    timestamps = [stamp - 2700 if i <= 33 else stamp for i, stamp in enumerate(timestamps)]
    closes = [
        100.0 + i * 0.01 + (0.6 if i >= 34 else 0.0)
        for i in range(40)
    ]

    result = compute_market_early_warning(closes, timestamps, atr=0.5, now=now)

    assert result["direction"] == "LONG"
    assert "volatilità/jump non valutati: cadenza timestamp irregolare" in result["reasons"]
    assert "espansione della volatilità intraday" not in result["reasons"]
    assert "candela anomala/jump rispetto al baseline" not in result["reasons"]
    assert result["execution_authorized"] is False

def test_market_early_warning_rejects_malformed_observations_instead_of_skipping_them():
    now = 1_800_000_000.0
    timestamps = [now - (19 - i) * 60 for i in range(20)]
    closes = [100.0 + i * 0.02 for i in range(20)]

    malformed_inputs = []
    bad_close = list(closes)
    bad_close[8] = float("nan")
    malformed_inputs.append((bad_close, timestamps))
    bad_timestamp = list(timestamps)
    bad_timestamp[8] = float("inf")
    malformed_inputs.append((closes, bad_timestamp))
    non_positive_close = list(closes)
    non_positive_close[8] = 0.0
    malformed_inputs.append((non_positive_close, timestamps))

    for prices, stamps in malformed_inputs:
        result = compute_market_early_warning(prices, stamps, atr=0.5, now=now)
        assert result["stage"] == "INVALID_DATA"
        assert result["direction"] == "NONE"
        assert result["score"] == 0
        assert "warning rifiutato" in result["reasons"][0]
        assert result["execution_authorized"] is False

def test_market_early_warning_rejects_invalid_explicit_time_parameters():
    now = 1_800_000_000.0
    timestamps = [now - (19 - i) * 60 for i in range(20)]
    closes = [100.0 + i * 0.02 for i in range(20)]

    invalid_now_values = (float("nan"), float("inf"), "not-a-timestamp", True)
    for invalid_now in invalid_now_values:
        result = compute_market_early_warning(
            closes, timestamps, atr=0.5, now=invalid_now
        )
        assert result["stage"] == "INVALID_PARAMETERS"
        assert result["direction"] == "NONE"
        assert result["score"] == 0
        assert result["execution_authorized"] is False

    invalid_age_limits = (float("nan"), float("inf"), -1, "not-a-number", True)
    for invalid_age in invalid_age_limits:
        result = compute_market_early_warning(
            closes, timestamps, atr=0.5, now=now,
            max_latest_age_seconds=invalid_age,
        )
        assert result["stage"] == "INVALID_PARAMETERS"
        assert result["direction"] == "NONE"
        assert result["score"] == 0
        assert result["execution_authorized"] is False




def test_lead_time_backtest_rejects_large_time_gaps_in_evaluation_window():
    from engine.early_warning import backtest_market_early_warning_lead_time

    start = 1_800_000_000.0 - 59 * 60
    candles = []
    for i in range(60):
        close = 100.0 + i * 0.02
        # Insert a 15-minute hole; bar-count horizons are no longer comparable
        # to the other one-minute samples, even though all OHLC values are valid.
        timestamp = start + i * 60 + (900 if i >= 35 else 0)
        candles.append({
            "timestamp": timestamp,
            "high": close + 0.05,
            "low": close - 0.05,
            "close": close,
        })

    result = backtest_market_early_warning_lead_time(candles, max_bars=96, horizon_bars=12)

    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["sample_count"] == 0
    assert "gap temporale" in result["reason"]
    assert result["execution_authorized"] is False
    assert result["method"] == "ROLLING_WALK_FORWARD_NOT_CALIBRATED"

def test_four_hour_context_is_unavailable_across_historical_timestamp_gap():
    now = 1_800_000_000.0
    # Five-minute observations span just over four hours. A 20-minute hole
    # sits two hours back, outside the latest-hour hard stop but inside the
    # 4h context window; short-horizon momentum should remain measurable.
    timestamps = []
    closes = []
    for i in range(49):
        stamp = now - 4 * 3600 + i * 300
        if i <= 24:
            stamp -= 900
        timestamps.append(stamp)
        closes.append(100.0 + i * 0.02)

    result = compute_market_early_warning(closes, timestamps, atr=0.5, now=now)

    assert result["returns_pct"]["30m"] is not None
    assert result["returns_pct"]["60m"] is not None
    assert result["returns_pct"]["4h"] is None
    assert "contesto 4h allineato" not in result["reasons"]
    assert result["execution_authorized"] is False


def test_market_early_warning_does_not_treat_three_hours_as_four_hour_context():
    now = 1_800_000_000.0
    # The available series is fresh and regular, but starts only three hours
    # before now. The old 4h lookup tolerance could accept this first quote
    # (exactly one hour from the target) and mislabel a 3h return as 4h.
    timestamps = [now - minute * 60 for minute in range(180, -1, -1)]
    closes = [100.0 + index * 0.01 for index in range(len(timestamps))]

    result = compute_market_early_warning(
        closes, timestamps, atr=0.5, now=now
    )

    assert result["returns_pct"]["30m"] is not None
    assert result["returns_pct"]["60m"] is not None
    assert result["returns_pct"]["4h"] is None
    assert "contesto 4h allineato" not in result["reasons"]
    assert result["execution_authorized"] is False

def test_market_early_warning_rejects_boolean_prices_and_timestamps():
    now = 1_800_000_000.0
    timestamps = [now - (19 - i) * 60 for i in range(20)]
    closes = [100.0 + i * 0.02 for i in range(20)]

    bad_prices = list(closes)
    bad_prices[8] = True
    bad_timestamps = list(timestamps)
    bad_timestamps[8] = True

    for prices, stamps in ((bad_prices, timestamps), (closes, bad_timestamps)):
        result = compute_market_early_warning(prices, stamps, atr=0.5, now=now)
        assert result["stage"] == "INVALID_DATA"
        assert result["direction"] == "NONE"
        assert result["score"] == 0
        assert "non valido" in result["reasons"][0]
        assert result["execution_authorized"] is False


def test_lead_time_backtest_rejects_boolean_ohlc_and_timestamps():
    from engine.early_warning import backtest_market_early_warning_lead_time

    start = 1_800_000_000.0 - 39 * 60
    candles = []
    for i in range(40):
        close = 100.0 + i * 0.01
        candles.append({
            "timestamp": start + i * 60,
            "high": close + 0.05,
            "low": close - 0.05,
            "close": close,
        })

    malformed = []
    bad_high = [dict(row) for row in candles]
    bad_high[10]["high"] = True
    malformed.append(bad_high)
    bad_timestamp = [dict(row) for row in candles]
    bad_timestamp[10]["timestamp"] = True
    malformed.append(bad_timestamp)

    for rows in malformed:
        result = backtest_market_early_warning_lead_time(rows)
        assert result["status"] == "INVALID_DATA"
        assert result["sample_count"] == 0
        assert "OHLC o timestamp non valido" in result["reason"]
        assert result["execution_authorized"] is False
