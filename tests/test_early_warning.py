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
    cadence = result["cadence_diagnostics"]
    assert cadence["evaluated_bar_count"] == 108
    assert cadence["evaluated_interval_count"] == 107
    assert cadence["typical_interval_seconds"] == 60.0
    assert cadence["max_observed_interval_seconds"] == 60.0
    assert cadence["max_allowed_interval_seconds"] == 300.0
    assert cadence["gap_count"] == 0
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

    paired_summaries = [
        result["non_overlapping_outcomes"],
        *outcomes_by_class.values(),
        *(
            subgroup
            for by_direction in outcomes_by_class_direction.values()
            for subgroup in by_direction.values()
        ),
    ]
    for group_summary in paired_summaries:
        for threshold in ("0_25atr", "0_5atr"):
            paired_count = group_summary[f"paired_threshold_order_sample_count_{threshold}"]
            assert group_summary[
                f"paired_threshold_order_sample_count_{threshold}_sufficient_for_interpretation"
            ] is (paired_count >= 20)

    # Full-sample outcomes may reuse the same future candles when opposite
    # directions warn close together. The secondary diagnostic must not.
    non_overlapping = [
        row for row in result["samples"]
        if row["non_overlapping_outcome_sample"]
    ]
    non_overlapping_indices = [row["warning_bar_index"] for row in non_overlapping]
    assert result["non_overlapping_sample_count"] == len(non_overlapping)
    assert result["overlapping_future_window_samples_excluded"] == (
        result["sample_count"] - len(non_overlapping)
    )
    assert all(
        right - left >= 12
        for left, right in zip(non_overlapping_indices, non_overlapping_indices[1:])
    )
    non_overlapping_summary = result["non_overlapping_outcomes"]
    assert non_overlapping_summary["sample_count"] == len(non_overlapping)
    assert (
        non_overlapping_summary["favorable_first"]
        + non_overlapping_summary["adverse_first"]
        + non_overlapping_summary["same_bar_ambiguous"]
        + non_overlapping_summary["neither_reached_0_5atr"]
        == len(non_overlapping)
    )

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
    cadence = result["cadence_diagnostics"]
    assert cadence["evaluated_bar_count"] == 60
    assert cadence["evaluated_interval_count"] == 59
    assert cadence["typical_interval_seconds"] == 60.0
    assert cadence["max_observed_interval_seconds"] == 960.0
    assert cadence["max_allowed_interval_seconds"] == 300.0
    assert cadence["gap_count"] == 1
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



def test_non_overlapping_outcome_selection_excludes_cross_direction_overlap():
    from engine.early_warning import _select_non_overlapping_outcome_samples

    # The warning at bar 25 has a future window overlapping bar 20's window;
    # the warning at bar 32 is the first allowed next window, irrespective of
    # direction, and bar 44 is also non-overlapping with bar 32.
    samples = [
        {"warning_bar_index": 20, "direction": "LONG"},
        {"warning_bar_index": 25, "direction": "SHORT"},
        {"warning_bar_index": 32, "direction": "SHORT"},
        {"warning_bar_index": 44, "direction": "LONG"},
    ]

    selected = _select_non_overlapping_outcome_samples(samples, horizon_bars=12)

    assert [row["warning_bar_index"] for row in selected] == [20, 32, 44]


def test_temporal_holdout_keeps_future_outcomes_on_their_own_side_of_split(monkeypatch):
    import engine.early_warning as early_warning

    def always_warn(closes, timestamps, atr=None, now=None, **kwargs):
        return {
            "stage": "EARLY_WARNING",
            "direction": "LONG",
            "score": 75,
            "returns_pct": {"30m": 0.1},
        }

    monkeypatch.setattr(early_warning, "compute_market_early_warning", always_warn)
    start = 1_800_000_000.0 - 119 * 60
    candles = []
    for i in range(120):
        close = 100.0 + i * 0.02
        candles.append({
            "timestamp": start + i * 60,
            "high": close + 0.05,
            "low": close - 0.05,
            "close": close,
        })

    result = early_warning.backtest_market_early_warning_lead_time(
        candles, max_bars=96, horizon_bars=12
    )

    assert result["status"] == "OK"
    validation = result["temporal_validation"]
    assert validation["status"] == "OK"
    assert validation["minimum_sample_count_for_interpretation"] == 20
    assert validation["recommended_min_max_bars_for_20_non_overlapping_holdout_samples"] == 81 * 12
    assert validation["holdout_sample_count_sufficient_for_interpretation"] == (
        validation["holdout_non_overlapping_sample_count"] >= 20
    )
    split_index = validation["split_start_bar_index"]
    assert split_index is not None
    assert (
        validation["development_sample_count"]
        + validation["holdout_sample_count"]
        + validation["split_boundary_excluded_sample_count"]
        == result["sample_count"]
    )

    for sample in result["samples"]:
        index = sample["warning_bar_index"]
        partition = sample["temporal_validation_partition"]
        if partition == "DEVELOPMENT":
            assert index + 12 < split_index
        elif partition == "HOLDOUT":
            assert index >= split_index
        elif partition == "SPLIT_BOUNDARY_EXCLUDED":
            assert index < split_index
            assert index + 12 >= split_index
        else:
            raise AssertionError(f"unexpected partition for a valid split: {partition}")

    for key in ("development", "holdout"):
        summary = validation[key]
        assert summary["minimum_sample_count_for_descriptive_interpretation"] == 20
        assert summary["sample_count_sufficient_for_interpretation"] == (
            summary["sample_count"] >= 20
        )
        assert (
            summary["favorable_first"]
            + summary["adverse_first"]
            + summary["same_bar_ambiguous"]
            + summary["neither_reached_0_5atr"]
            == summary["sample_count"]
        )
        assert (
            summary["favorable_0_25atr_first"]
            + summary["adverse_0_25atr_first"]
            + summary["same_bar_0_25atr_ambiguous"]
            + summary["neither_reached_0_25atr"]
            == summary["sample_count"]
        )
        for metric, count_key in (
            ("favorable_0_25atr_first_pct", "favorable_0_25atr_first"),
            ("adverse_0_25atr_first_pct", "adverse_0_25atr_first"),
            ("same_bar_0_25atr_ambiguous_pct", "same_bar_0_25atr_ambiguous"),
            ("neither_reached_0_25atr_pct", "neither_reached_0_25atr"),
        ):
            expected = (
                round(100.0 * summary[count_key] / summary["sample_count"], 1)
                if summary["sample_count"] else None
            )
            assert summary[metric] == expected
        assert summary["median_warning_to_favorable_0_25atr_seconds"] is None or (
            summary["median_warning_to_favorable_0_25atr_seconds"] >= 0
        )
        assert summary["median_warning_to_adverse_0_25atr_seconds"] is None or (
            summary["median_warning_to_adverse_0_25atr_seconds"] >= 0
        )
    assert validation["holdout_sample_count_sufficient_for_interpretation"] is False

    # Holdout timing diagnostics must include only the de-overlapped holdout
    # samples, and LONG/SHORT subgroups must reconcile to that exact count.
    by_class_and_direction = validation["holdout_by_prior_move_class_and_direction"]
    nested_count = sum(
        subgroup["sample_count"]
        for by_direction in by_class_and_direction.values()
        for subgroup in by_direction.values()
    )
    assert nested_count == validation["holdout_non_overlapping_sample_count"]
    for by_direction in by_class_and_direction.values():
        for summary in by_direction.values():
            assert summary["minimum_sample_count_for_descriptive_interpretation"] == 20
            assert summary["sample_count_sufficient_for_interpretation"] == (
                summary["sample_count"] >= 20
            )
            assert (
                summary["favorable_first"]
                + summary["adverse_first"]
                + summary["same_bar_ambiguous"]
                + summary["neither_reached_0_5atr"]
                == summary["sample_count"]
            )
            assert (
                summary["favorable_0_25atr_first"]
                + summary["adverse_0_25atr_first"]
                + summary["same_bar_0_25atr_ambiguous"]
                + summary["neither_reached_0_25atr"]
                == summary["sample_count"]
            )
            for metric, count_key in (
                ("favorable_0_25atr_first_pct", "favorable_0_25atr_first"),
                ("adverse_0_25atr_first_pct", "adverse_0_25atr_first"),
                ("same_bar_0_25atr_ambiguous_pct", "same_bar_0_25atr_ambiguous"),
                ("neither_reached_0_25atr_pct", "neither_reached_0_25atr"),
            ):
                expected = (
                    round(100.0 * summary[count_key] / summary["sample_count"], 1)
                    if summary["sample_count"] else None
                )
                assert summary[metric] == expected
            assert summary["median_warning_to_favorable_0_25atr_seconds"] is None or (
                summary["median_warning_to_favorable_0_25atr_seconds"] >= 0
            )
            assert summary["median_warning_to_adverse_0_25atr_seconds"] is None or (
                summary["median_warning_to_adverse_0_25atr_seconds"] >= 0
            )

    # Top-level outcome percentages must expose ambiguous and no-hit cases,
    # not only decisive favorable/adverse outcomes.
    assert result["same_bar_ambiguous_pct"] == round(
        100.0 * result["same_bar_ambiguous"] / result["sample_count"], 1
    )
    assert result["neither_reached_0_5atr_pct"] == round(
        100.0 * result["neither_reached_0_5atr"] / result["sample_count"], 1
    )
    assert result["same_bar_0_25atr_ambiguous_pct"] == round(
        100.0 * result["same_bar_0_25atr_ambiguous"] / result["sample_count"], 1
    )
    assert result["neither_reached_0_25atr_pct"] == round(
        100.0 * result["neither_reached_0_25atr"] / result["sample_count"], 1
    )
    # Paired lead margin is positive when the favorable threshold came first,
    # negative when adverse came first, and null for same-candle/one-sided cases.
    for sample in result["samples"]:
        for margin_key, favorable_key, adverse_key in (
            ("favorable_before_adverse_0_25atr_seconds",
             "warning_to_favorable_0_25atr_seconds", "warning_to_adverse_0_25atr_seconds"),
            ("favorable_before_adverse_0_5atr_seconds", "lead_seconds", "first_adverse_seconds"),
        ):
            favorable_time = sample[favorable_key]
            adverse_time = sample[adverse_key]
            if favorable_time is None or adverse_time is None or favorable_time == adverse_time:
                assert sample[margin_key] is None
            else:
                assert sample[margin_key] == adverse_time - favorable_time

    from statistics import median
    non_overlapping = [row for row in result["samples"] if row["non_overlapping_outcome_sample"]]
    summary = result["non_overlapping_outcomes"]
    for margin_key, count_key in (
        ("favorable_before_adverse_0_25atr_seconds", "paired_threshold_order_sample_count_0_25atr"),
        ("favorable_before_adverse_0_5atr_seconds", "paired_threshold_order_sample_count_0_5atr"),
    ):
        values = [row[margin_key] for row in non_overlapping if row[margin_key] is not None]
        median_key = "median_" + margin_key
        assert summary[count_key] == len(values)
        assert summary[median_key] == (median(values) if values else None)

    # A large outcome group must not make its much smaller paired-margin
    # subset appear statistically sufficient. Check every public stratification.
    paired_summaries = [
        result["non_overlapping_outcomes"],
        validation["development"],
        validation["holdout"],
        *result["outcomes_by_prior_move_class"].values(),
        *(
            subgroup
            for by_direction in result["outcomes_by_prior_move_class_and_direction"].values()
            for subgroup in by_direction.values()
        ),
        *(
            subgroup
            for by_direction in validation["holdout_by_prior_move_class_and_direction"].values()
            for subgroup in by_direction.values()
        ),
        *validation["holdout_by_direction"].values(),
    ]
    for group_summary in paired_summaries:
        for threshold in ("0_25atr", "0_5atr"):
            paired_count = group_summary[f"paired_threshold_order_sample_count_{threshold}"]
            assert group_summary[
                f"paired_threshold_order_sample_count_{threshold}_sufficient_for_interpretation"
            ] is (paired_count >= 20)
            favorable_count = group_summary[f"paired_favorable_first_count_{threshold}"]
            adverse_count = group_summary[f"paired_adverse_first_count_{threshold}"]
            assert favorable_count + adverse_count == paired_count
            expected_favorable_pct = (
                round(100.0 * favorable_count / paired_count, 1) if paired_count else None
            )
            assert group_summary[f"paired_favorable_first_pct_{threshold}"] == expected_favorable_pct

    # Top-level paired-margin fields must follow the same sufficiency rule even
    # when this short series cannot provide 20 paired observations.
    assert result["minimum_sample_count_for_descriptive_interpretation"] == 20
    for threshold in ("0_25atr", "0_5atr"):
        paired_count = result[f"paired_threshold_order_sample_count_{threshold}"]
        assert result[
            f"paired_threshold_order_sample_count_{threshold}_sufficient_for_interpretation"
        ] is (paired_count >= 20)
        favorable_count = result[f"paired_favorable_first_count_{threshold}"]
        adverse_count = result[f"paired_adverse_first_count_{threshold}"]
        assert favorable_count + adverse_count == paired_count
        expected_favorable_pct = (
            round(100.0 * favorable_count / paired_count, 1) if paired_count else None
        )
        assert result[f"paired_favorable_first_pct_{threshold}"] == expected_favorable_pct

    assert result["execution_authorized"] is False

    # A short evaluation span must not manufacture a development/holdout split.
    short_result = early_warning.backtest_market_early_warning_lead_time(
        candles[-40:], max_bars=30, horizon_bars=12
    )
    assert short_result["status"] == "OK"
    short_validation = short_result["temporal_validation"]
    assert short_validation["status"] == "INSUFFICIENT_DATA"
    assert short_validation["minimum_sample_count_for_interpretation"] == 20
    assert short_validation["recommended_min_max_bars_for_20_non_overlapping_holdout_samples"] == 81 * 12
    assert short_validation["unsplit_sample_count"] == short_result["sample_count"]
    assert short_validation["holdout_sample_count_sufficient_for_interpretation"] is False
    assert sum(
        subgroup["sample_count"]
        for by_direction in short_validation["holdout_by_prior_move_class_and_direction"].values()
        for subgroup in by_direction.values()
    ) == 0
    assert short_result["execution_authorized"] is False



def test_paired_margin_order_metrics_report_share_with_favorable_threshold_first():
    from engine.early_warning import _paired_margin_order_metrics

    assert _paired_margin_order_metrics([60, -120, 30, -30]) == {
        "favorable_first_count": 2,
        "adverse_first_count": 2,
        "favorable_first_pct": 50.0,
    }
    assert _paired_margin_order_metrics([-60, -120]) == {
        "favorable_first_count": 0,
        "adverse_first_count": 2,
        "favorable_first_pct": 0.0,
    }
    assert _paired_margin_order_metrics([]) == {
        "favorable_first_count": 0,
        "adverse_first_count": 0,
        "favorable_first_pct": None,
    }


def test_paired_margin_sufficiency_uses_paired_count_not_total_warning_count(monkeypatch):
    import engine.early_warning as early_warning
    from statistics import median

    def always_warn(closes, timestamps, atr=None, now=None, **kwargs):
        return {
            "stage": "EARLY_WARNING",
            "direction": "LONG",
            "score": 75,
            "returns_pct": {"30m": 0.1},
        }

    monkeypatch.setattr(early_warning, "compute_market_early_warning", always_warn)
    start = 1_800_000_000.0 - 499 * 60
    candles = []
    for i in range(500):
        close = 100.0 + i * 0.02
        candles.append({
            "timestamp": start + i * 60,
            "high": close + 0.02,
            "low": close - 0.02,
            "close": close,
        })

    result = early_warning.backtest_market_early_warning_lead_time(
        candles, max_bars=300, horizon_bars=12
    )

    assert result["status"] == "OK"
    assert result["sample_count"] >= 20
    assert result["minimum_sample_count_for_descriptive_interpretation"] == 20
    for threshold in ("0_25atr", "0_5atr"):
        margin_key = f"favorable_before_adverse_{threshold}_seconds"
        count_key = f"paired_threshold_order_sample_count_{threshold}"
        median_key = f"median_favorable_before_adverse_{threshold}_seconds"
        sufficient_key = f"paired_threshold_order_sample_count_{threshold}_sufficient_for_interpretation"
        values = [
            sample[margin_key]
            for sample in result["samples"]
            if sample[margin_key] is not None
        ]
        assert result[count_key] == len(values)
        assert result[median_key] == (median(values) if values else None)
        assert result[count_key] < 20
        assert result[sufficient_key] is False

    assert result["execution_authorized"] is False


def test_temporal_holdout_direction_summaries_reconcile_with_deoverlapped_samples(monkeypatch):
    import engine.early_warning as early_warning
    from statistics import median

    def alternating_direction_warning(closes, timestamps, atr=None, now=None, **kwargs):
        return {
            "stage": "EARLY_WARNING",
            "direction": "LONG" if (len(closes) // 12) % 2 else "SHORT",
            "score": 75,
            "returns_pct": {"30m": 0.1},
        }

    monkeypatch.setattr(
        early_warning, "compute_market_early_warning", alternating_direction_warning
    )
    start = 1_800_000_000.0 - 299 * 60
    candles = []
    for i in range(300):
        close = 100.0 + i * 0.02
        candles.append({
            "timestamp": start + i * 60,
            "high": close + 0.05,
            "low": close - 0.05,
            "close": close,
        })

    result = early_warning.backtest_market_early_warning_lead_time(
        candles, max_bars=300, horizon_bars=12
    )
    assert result["status"] == "OK"
    validation = result["temporal_validation"]
    assert validation["status"] == "OK"

    holdout_samples = [
        row for row in result["samples"]
        if row["temporal_validation_partition"] == "HOLDOUT"
    ]
    holdout_non_overlapping = early_warning._select_non_overlapping_outcome_samples(
        holdout_samples, horizon_bars=12
    )
    by_direction = validation["holdout_by_direction"]
    assert set(by_direction) == {"LONG", "SHORT"}
    assert sum(summary["sample_count"] for summary in by_direction.values()) == len(
        holdout_non_overlapping
    )
    assert all(by_direction[direction]["sample_count"] > 0 for direction in ("LONG", "SHORT"))

    for direction in ("LONG", "SHORT"):
        selected = [
            row for row in holdout_non_overlapping if row["direction"] == direction
        ]
        summary = by_direction[direction]
        assert summary["sample_count"] == len(selected)
        for threshold in ("0_25atr", "0_5atr"):
            margin_key = f"favorable_before_adverse_{threshold}_seconds"
            count_key = f"paired_threshold_order_sample_count_{threshold}"
            median_key = f"median_favorable_before_adverse_{threshold}_seconds"
            margins = [
                row[margin_key] for row in selected if row[margin_key] is not None
            ]
            assert summary[count_key] == len(margins)
            assert summary[median_key] == (median(margins) if margins else None)
            assert summary[
                f"{count_key}_sufficient_for_interpretation"
            ] is (len(margins) >= 20)

    assert result["execution_authorized"] is False




def test_irregular_baseline_cadence_does_not_claim_volatility_expansion():
    # A gap older than the latest hour does not invalidate the 30m/60m
    # returns, but it does make the wider volatility baseline incomparable.
    # The diagnostic must say "not evaluated" and keep the boolean false.
    now = 1_800_000_000.0
    timestamps = []
    for i in range(91):
        stamp = now - (90 - i) * 300
        if i >= 61:
            stamp += 1500
        timestamps.append(stamp)
    closes = [100.0 + i * 0.03 for i in range(91)]

    result = compute_market_early_warning(
        closes, timestamps, atr=1.0, now=timestamps[-1]
    )

    assert result["stage"] in {"WATCH", "EARLY_WARNING", "LATE_MOVE"}
    assert any(
        "volatilità/jump non valutati: cadenza timestamp irregolare" in reason
        for reason in result["reasons"]
    )
    assert result["volatility_expansion"] is False
    assert result["execution_authorized"] is False


def test_extremely_large_integer_market_data_fails_closed_without_overflow():
    # float(very_large_int) raises OverflowError; public APIs must classify the
    # input as invalid data rather than crashing the warning/backtest pipeline.
    huge = 10 ** 10000
    warning = compute_market_early_warning(
        [huge], [1_800_000_000.0], now=1_800_000_000.0
    )
    assert warning["stage"] == "INVALID_DATA"
    assert warning["direction"] == "NONE"
    assert warning["execution_authorized"] is False

    from engine.early_warning import backtest_market_early_warning_lead_time

    backtest = backtest_market_early_warning_lead_time(
        [{
            "timestamp": 1_800_000_000.0,
            "high": huge,
            "low": 100.0,
            "close": 100.0,
        }],
        max_bars=30,
        horizon_bars=3,
    )
    assert backtest["status"] == "INVALID_DATA"
    assert backtest["sample_count"] == 0
    assert backtest["execution_authorized"] is False


def test_backtest_rejects_millisecond_timestamps_instead_of_inflating_lead_times():
    start_seconds = 1_800_000_000
    candles = []
    for i in range(40):
        close = 100.0 + i * 0.01
        candles.append({
            "timestamp": (start_seconds + i * 60) * 1000,
            "high": close + 0.05,
            "low": close - 0.05,
            "close": close,
        })

    from engine.early_warning import backtest_market_early_warning_lead_time

    result = backtest_market_early_warning_lead_time(
        candles, max_bars=30, horizon_bars=3
    )

    assert result["status"] == "INVALID_DATA"
    assert result["sample_count"] == 0
    assert "timestamp" in result["reason"]
    assert "millisecondi" in result["reason"]
    assert result["execution_authorized"] is False


def test_market_early_warning_rejects_millisecond_timestamps_explicitly():
    now_seconds = 1_800_000_000
    timestamps_ms = [(now_seconds - (19 - i) * 60) * 1000 for i in range(20)]
    closes = [100.0 + i * 0.02 for i in range(20)]

    result = compute_market_early_warning(
        closes, timestamps_ms, atr=0.5, now=now_seconds
    )

    assert result["stage"] == "INVALID_DATA"
    assert result["direction"] == "NONE"
    assert result["score"] == 0
    assert "millisecondi" in result["reasons"][0]
    assert result["execution_authorized"] is False


def test_market_early_warning_rejects_millisecond_reference_clock():
    now_seconds = 1_800_000_000
    timestamps = [now_seconds - (19 - i) * 60 for i in range(20)]
    closes = [100.0 + i * 0.02 for i in range(20)]

    result = compute_market_early_warning(
        closes, timestamps, atr=0.5, now=now_seconds * 1000
    )

    assert result["stage"] == "INVALID_PARAMETERS"
    assert result["direction"] == "NONE"
    assert result["score"] == 0
    assert "now" in result["reasons"][0]
    assert "millisecondi" in result["reasons"][0]
    assert result["execution_authorized"] is False

