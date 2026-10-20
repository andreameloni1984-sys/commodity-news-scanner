"""Research controls recovered from September 2026 Gagarin study.

These utilities are diagnostics and validation controls, not predictive signals.
PAPER ONLY: they never create or authorize an entry.
"""
from __future__ import annotations

from datetime import datetime, timezone
import math
import statistics
from typing import Any


DEFAULT_MAX_DATA_AGE_SECONDS = 360.0


def _finite_positive(value: Any) -> bool:
    try:
        return math.isfinite(float(value)) and float(value) > 0
    except (TypeError, ValueError):
        return False


def _epoch(value: Any) -> float | None:
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)):
            result = float(value)
        else:
            text = str(value).strip()
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            result = dt.timestamp()
        return result if math.isfinite(result) else None
    except (TypeError, ValueError, OverflowError):
        return None


def validate_market_snapshot(state: Any, now: datetime | None = None) -> dict:
    """Fail closed on malformed OHLC/timestamps; do not infer a direction.

    An absent optional order-flow feed is reported as unavailable, not as a
    bearish/bullish observation. Existing data-engine status remains authoritative
    for provider freshness and market-session handling.
    """
    now = now or datetime.now(timezone.utc)
    blockers: list[str] = []
    warnings: list[str] = []
    candles = list(getattr(state, "candles", []) or [])
    closes = list(getattr(state, "closes", []) or [])

    if bool(getattr(state, "data_ok", False)):
        if not candles or not closes:
            blockers.append("RESEARCH_OHLC_MISSING")
        if len(candles) != len(closes):
            blockers.append("RESEARCH_OHLC_LENGTH_MISMATCH")

    previous_ts = None
    valid_candles = 0
    for index, candle in enumerate(candles):
        if not isinstance(candle, dict):
            blockers.append("RESEARCH_CANDLE_NOT_OBJECT")
            continue
        ts = _epoch(candle.get("timestamp"))
        if ts is None:
            blockers.append("RESEARCH_TIMESTAMP_INVALID")
        elif previous_ts is not None and ts <= previous_ts:
            blockers.append("RESEARCH_TIMESTAMP_NOT_MONOTONIC")
        if ts is not None:
            previous_ts = ts
            if ts > now.timestamp() + 90:
                blockers.append("RESEARCH_TIMESTAMP_IN_FUTURE")

        values = [candle.get(k) for k in ("open", "high", "low", "close")]
        if not all(_finite_positive(v) for v in values):
            blockers.append("RESEARCH_OHLC_INVALID")
            continue
        op, high, low, close = map(float, values)
        if high < max(op, low, close) or low > min(op, high, close):
            blockers.append("RESEARCH_OHLC_GEOMETRY_INVALID")
            continue
        if index < len(closes) and _finite_positive(closes[index]):
            if not math.isclose(close, float(closes[index]), rel_tol=1e-6, abs_tol=1e-8):
                blockers.append("RESEARCH_CLOSE_SERIES_MISMATCH")
        valid_candles += 1

    age = getattr(state, "data_age_seconds", None)
    try:
        if age is not None and (not math.isfinite(float(age)) or float(age) < 0):
            blockers.append("RESEARCH_DATA_AGE_INVALID")
    except (TypeError, ValueError):
        blockers.append("RESEARCH_DATA_AGE_INVALID")

    metadata = getattr(state, "metadata", {}) or {}
    if isinstance(metadata, dict):
        # Explicit point-in-time guard: only enforce when all timestamps exist.
        timing = metadata.get("feature_timing")
        if isinstance(timing, dict):
            event_time = _epoch(timing.get("event_time"))
            available_at = _epoch(timing.get("available_at"))
            decision_time = _epoch(timing.get("decision_time"))
            if any(x is None for x in (event_time, available_at, decision_time)):
                blockers.append("POINT_IN_TIME_TIMESTAMP_INVALID")
            elif available_at > decision_time or event_time > decision_time:
                blockers.append("LOOKAHEAD_FEATURE_REJECTED")
        flow = metadata.get("order_flow")
        if not isinstance(flow, dict) or not flow:
            warnings.append("ORDER_FLOW_UNAVAILABLE_NOT_DIRECTIONAL")
        else:
            if not flow.get("source") or _epoch(flow.get("timestamp")) is None:
                warnings.append("ORDER_FLOW_UNVERIFIED_NOT_DIRECTIONAL")
            if str(flow.get("direction", "")).upper() not in {"LONG", "SHORT", "NEUTRAL", "NONE", ""}:
                warnings.append("ORDER_FLOW_DIRECTION_INVALID_IGNORED")

    unique_blockers = sorted(set(blockers))
    unique_warnings = sorted(set(warnings))
    return {
        "status": "BLOCKED" if unique_blockers else "PASS",
        "paper_only": True,
        "direction_created": False,
        "candles_checked": len(candles),
        "valid_candles": valid_candles,
        "blockers": unique_blockers,
        "warnings": unique_warnings,
    }


def cost_adjusted_edge(gross_r: float, spread_r: float = 0.0,
                       slippage_r: float = 0.0, fees_r: float = 0.0) -> dict:
    """Return net R after explicit execution costs; no costs are guessed."""
    values = (gross_r, spread_r, slippage_r, fees_r)
    if not all(math.isfinite(float(x)) for x in values):
        raise ValueError("Tutti i valori devono essere numeri finiti")
    if min(spread_r, slippage_r, fees_r) < 0:
        raise ValueError("Spread, slippage e commissioni non possono essere negativi")
    total_cost = float(spread_r) + float(slippage_r) + float(fees_r)
    return {
        "gross_r": float(gross_r),
        "estimated_cost_r": total_cost,
        "net_r": float(gross_r) - total_cost,
        "edge_positive_after_costs": float(gross_r) - total_cost > 0,
        "paper_only": True,
    }


def expected_shortfall(returns: list[float], confidence: float = 0.95) -> dict:
    """Historical CVaR/expected shortfall of returns; lower tail is adverse."""
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence deve essere tra 0 e 1")
    values = [float(x) for x in returns if math.isfinite(float(x))]
    if not values:
        return {"status": "INSUFFICIENT_SAMPLE", "n": 0, "cvar": None, "paper_only": True}
    ordered = sorted(values)
    tail_n = max(1, math.ceil((1.0 - confidence) * len(ordered)))
    tail = ordered[:tail_n]
    return {
        "status": "OBSERVATION",
        "n": len(values),
        "confidence": confidence,
        "var": tail[-1],
        "cvar": statistics.mean(tail),
        "tail_n": tail_n,
        "paper_only": True,
    }


def brier_score(probabilities: list[float], outcomes: list[int]) -> dict:
    """Calibration metric; probabilities are 0..1 and outcomes are 0/1."""
    if len(probabilities) != len(outcomes):
        raise ValueError("Probabilità e outcome devono avere la stessa lunghezza")
    if not probabilities:
        return {"status": "INSUFFICIENT_SAMPLE", "n": 0, "brier": None, "paper_only": True}
    pairs = [(float(p), int(y)) for p, y in zip(probabilities, outcomes)]
    if any(not math.isfinite(p) or p < 0 or p > 1 or y not in (0, 1) for p, y in pairs):
        raise ValueError("Probabilità deve essere 0..1 e outcome 0/1")
    score = statistics.mean((p - y) ** 2 for p, y in pairs)
    return {"status": "OBSERVATION", "n": len(pairs), "brier": score, "paper_only": True}


def utility_weighted_score(outcomes: list[float], utilities: list[float]) -> dict:
    """Summarize realized utility; utility weights must be specified by caller."""
    if len(outcomes) != len(utilities):
        raise ValueError("Outcome e utilità devono avere la stessa lunghezza")
    if not outcomes:
        return {"status": "INSUFFICIENT_SAMPLE", "n": 0, "score": None, "paper_only": True}
    pairs = [(float(x), float(u)) for x, u in zip(outcomes, utilities)]
    if any(not math.isfinite(x) or not math.isfinite(u) or u < 0 for x, u in pairs):
        raise ValueError("Valori finiti richiesti; le utilità non possono essere negative")
    weight_sum = sum(u for _, u in pairs)
    if weight_sum <= 0:
        return {"status": "INVALID_UTILITY_WEIGHTS", "n": len(pairs), "score": None, "paper_only": True}
    return {
        "status": "OBSERVATION",
        "n": len(pairs),
        "score": sum(x * u for x, u in pairs) / weight_sum,
        "paper_only": True,
    }


def attach_research_controls(state: Any) -> Any:
    """Attach research diagnostics and enforce only hard data-integrity blockers."""
    report = validate_market_snapshot(state)
    metadata = getattr(state, "metadata", None)
    if not isinstance(metadata, dict):
        metadata = {}
        state.metadata = metadata
    metadata["research_integrity"] = report
    metadata["research_controls"] = {
        "mode": "PAPER_RESEARCH",
        "paper_only": True,
        "point_in_time_guard": True,
        "order_flow_provider_audit": "UNAVAILABLE" if "ORDER_FLOW_UNAVAILABLE_NOT_DIRECTIONAL" in report["warnings"] else "UNVERIFIED",
        "cost_adjusted_edge": "REQUIRES_SPREAD_SLIPPAGE_FEES",
        "risk_tail_metric": "CVaR_AVAILABLE",
        "probability_calibration": "BRIER_AVAILABLE",
        "strategy_promotion": "DISABLED",
    }
    if report["blockers"]:
        state.data_ok = False
        state.live = False
        state.metadata["research_integrity_blocked"] = True
    else:
        state.metadata["research_integrity_blocked"] = False
    return state
