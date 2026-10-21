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






def ema16_32_pullback_diagnostic(closes: list[float]) -> dict:
    """Measure EMA16/EMA32 alignment and proximity; diagnostic, not a signal.

    Requires at least 32 valid closes. No entry or direction is authorized here.
    Pullback proximity is reported relative to the latest close as a percentage.
    """
    try:
        values = [float(x) for x in (closes or [])]
    except (TypeError, ValueError):
        values = []
    if len(values) < 32 or any(not math.isfinite(x) or x <= 0 for x in values):
        return {"status": "INSUFFICIENT_DATA", "paper_only": True,
                "direction_created": False, "ema16": None, "ema32": None}

    def ema(series: list[float], period: int) -> float:
        current = statistics.mean(series[:period])
        alpha = 2.0 / (period + 1.0)
        for value in series[period:]:
            current = alpha * value + (1.0 - alpha) * current
        return current

    e16, e32, latest = ema(values, 16), ema(values, 32), values[-1]
    direction = "LONG_BIAS" if e16 > e32 else "SHORT_BIAS" if e16 < e32 else "NEUTRAL"
    distance_pct = abs(latest - e16) / latest * 100.0
    return {
        "status": "OBSERVATION", "paper_only": True, "direction_created": False,
        "ema16": e16, "ema32": e32, "latest_close": latest,
        "alignment": direction, "distance_from_ema16_pct": distance_pct,
        "near_ema16_within_0_25pct": distance_pct <= 0.25,
        "observations": len(values),
    }


def multi_timeframe_role_diagnostic(series_by_role: dict[str, list[float]]) -> dict:
    """Describe HTF regime / MTF setup / LTF trigger independently.

    Diagnostic only: it does not synthesize a trade direction or modify Gagarin
    state. Caller must supply chronological close series for the named roles.
    """
    role_names = ("regime_htf", "setup_mtf", "trigger_ltf")
    result = {"status": "OBSERVATION", "paper_only": True,
              "direction_created": False, "roles": {}}
    for role in role_names:
        raw = series_by_role.get(role) if isinstance(series_by_role, dict) else None
        try:
            values = [float(x) for x in (raw or [])]
        except (TypeError, ValueError):
            values = []
        if len(values) < 2 or any(not math.isfinite(x) or x <= 0 for x in values):
            result["roles"][role] = {"status": "INSUFFICIENT_DATA", "direction": "NONE"}
            result["status"] = "INCOMPLETE"
            continue
        delta = values[-1] - values[0]
        direction = "LONG" if delta > 0 else "SHORT" if delta < 0 else "NEUTRAL"
        result["roles"][role] = {
            "status": "OBSERVATION", "direction": direction,
            "change_pct": (values[-1] / values[0] - 1.0) * 100.0,
            "observations": len(values),
        }
    return result


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


def anti_edge_validation(candidate_returns: list[float], benchmark_returns: list[float],
                         candidate_costs: list[float] | None = None,
                         benchmark_costs: list[float] | None = None,
                         out_of_sample: list[bool] | None = None,
                         min_sample: int = 30) -> dict:
    """Compare net candidate and baseline returns only on explicitly OOS rows.

    This is a rejection/diagnostic gate, never an automatic strategy promotion.
    Costs are per observation in the same units as returns.
    """
    n = len(candidate_returns)
    if len(benchmark_returns) != n:
        raise ValueError("Candidate e benchmark devono avere la stessa lunghezza")
    candidate_costs = candidate_costs or [0.0] * n
    benchmark_costs = benchmark_costs or [0.0] * n
    out_of_sample = out_of_sample or [True] * n
    if not (len(candidate_costs) == len(benchmark_costs) == len(out_of_sample) == n):
        raise ValueError("Tutte le serie devono avere la stessa lunghezza")
    rows = []
    for i in range(n):
        c, b, cc, bc = map(float, (candidate_returns[i], benchmark_returns[i],
                                   candidate_costs[i], benchmark_costs[i]))
        if not all(math.isfinite(x) for x in (c, b, cc, bc)) or cc < 0 or bc < 0:
            raise ValueError("Rendimenti/costi non validi")
        if out_of_sample[i]:
            rows.append((c - cc, b - bc))
    if len(rows) < min_sample:
        return {"status": "INSUFFICIENT_OOS_SAMPLE", "n_oos": len(rows),
                "need": min_sample, "promoted": False, "paper_only": True}
    candidate = [x[0] for x in rows]
    benchmark = [x[1] for x in rows]
    differences = [c - b for c, b in rows]
    mean_candidate = statistics.mean(candidate)
    mean_benchmark = statistics.mean(benchmark)
    mean_difference = statistics.mean(differences)
    return {
        "status": "OOS_EDGE_NOT_DEMONSTRATED" if mean_difference <= 0 else "OOS_EDGE_CANDIDATE",
        "n_oos": len(rows),
        "candidate_net_mean": mean_candidate,
        "benchmark_net_mean": mean_benchmark,
        "net_mean_difference": mean_difference,
        "candidate_positive_mean": mean_candidate > 0,
        "promoted": False,
        "paper_only": True,
        "note": "La media OOS positiva non basta da sola per promuovere una strategia.",
    }


def deflated_sharpe_probability(returns: list[float], trials: int = 1,
                                annualization: float = 1.0) -> dict:
    """Approximate Deflated Sharpe probability using sample moments.

    Returns are periodic simple returns. This statistic is a research diagnostic;
    serial dependence and non-stationarity still require separate treatment.
    """
    from statistics import NormalDist
    values = [float(x) for x in returns]
    if trials < 1 or annualization <= 0:
        raise ValueError("trials deve essere >=1 e annualization >0")
    if len(values) < 30 or not all(math.isfinite(x) for x in values):
        return {"status": "INSUFFICIENT_SAMPLE", "n": len(values),
                "dsr_probability": None, "paper_only": True}
    mean = statistics.mean(values)
    sd = statistics.stdev(values)
    if sd <= 0:
        return {"status": "DEGENERATE_RETURNS", "n": len(values),
                "dsr_probability": None, "paper_only": True}
    sr_periodic = mean / sd
    sr = sr_periodic * math.sqrt(annualization)
    centered = [x - mean for x in values]
    m2 = statistics.mean(x*x for x in centered)
    if m2 <= 0:
        return {"status": "DEGENERATE_RETURNS", "n": len(values),
                "dsr_probability": None, "paper_only": True}
    skew = statistics.mean(x**3 for x in centered) / (m2 ** 1.5)
    kurtosis = statistics.mean(x**4 for x in centered) / (m2 ** 2)  # non-excess
    if trials == 1:
        benchmark_sr = 0.0
    else:
        normal = NormalDist()
        euler_gamma = 0.5772156649015329
        z1 = normal.inv_cdf(1.0 - 1.0 / trials)
        z2 = normal.inv_cdf(1.0 - 1.0 / (trials * math.e))
        benchmark_sr = math.sqrt(1.0 / (len(values) - 1)) * (
            (1.0 - euler_gamma) * z1 + euler_gamma * z2
        )
    variance_term = 1.0 - skew * sr_periodic + ((kurtosis - 1.0) / 4.0) * sr_periodic**2
    if variance_term <= 0:
        return {"status": "INVALID_MOMENT_ADJUSTMENT", "n": len(values),
                "dsr_probability": None, "paper_only": True}
    z = (sr_periodic - benchmark_sr) * math.sqrt(len(values) - 1) / math.sqrt(variance_term)
    probability = NormalDist().cdf(z)
    return {
        "status": "OBSERVATION",
        "n": len(values),
        "trials": trials,
        "sharpe_periodic": sr_periodic,
        "expected_max_sharpe_null": benchmark_sr,
        "dsr_probability": probability,
        "paper_only": True,
        "note": "Approssimazione; non corregge automaticamente autocorrelazione o cambi di regime.",
    }


def combinatorial_pbo(returns_by_strategy: dict[str, list[float]], n_splits: int = 6) -> dict:
    """CSCV-style Probability of Backtest Overfitting diagnostic.

    Splits the chronological sample into equal contiguous blocks, enumerates
    half-block in-sample combinations, selects the best in-sample strategy and
    checks whether its out-of-sample rank is below the median.
    """
    from itertools import combinations
    names = list(returns_by_strategy)
    if len(names) < 2 or n_splits < 4 or n_splits % 2:
        raise ValueError("Servono almeno 2 strategie e un numero pari di split >=4")
    lengths = {len(returns_by_strategy[name]) for name in names}
    if len(lengths) != 1:
        raise ValueError("Tutte le strategie devono avere lo stesso numero di osservazioni")
    n = lengths.pop()
    if n < n_splits * 2:
        return {"status": "INSUFFICIENT_SAMPLE", "n": n, "pbo": None,
                "promoted": False, "paper_only": True}
    arrays = {}
    for name in names:
        values = [float(x) for x in returns_by_strategy[name]]
        if not all(math.isfinite(x) for x in values):
            raise ValueError("I rendimenti devono essere finiti")
        arrays[name] = values
    block_size = n // n_splits
    usable = block_size * n_splits
    blocks = [list(range(i * block_size, (i + 1) * block_size)) for i in range(n_splits)]
    half = n_splits // 2
    evaluated = 0
    overfit = 0
    lambdas = []
    for selected in combinations(range(n_splits), half):
        ins = set(selected)
        is_idx = [i for b in range(n_splits) if b in ins for i in blocks[b]]
        oos_idx = [i for b in range(n_splits) if b not in ins for i in blocks[b]]
        is_means = {name: statistics.mean(arrays[name][i] for i in is_idx) for name in names}
        best = max(names, key=lambda name: is_means[name])
        oos_means = {name: statistics.mean(arrays[name][i] for i in oos_idx) for name in names}
        # Average rank for ties; rank 1 is worst and rank K is best.
        value = oos_means[best]
        less = sum(v < value for v in oos_means.values())
        equal = sum(v == value for v in oos_means.values())
        rank = less + (equal + 1) / 2.0
        omega = min(1.0 - 1e-12, max(1e-12, rank / (len(names) + 1.0)))
        lam = math.log(omega / (1.0 - omega))
        lambdas.append(lam)
        overfit += int(lam < 0)
        evaluated += 1
    return {
        "status": "OBSERVATION",
        "n": n,
        "strategies": len(names),
        "splits": n_splits,
        "combinations_evaluated": evaluated,
        "pbo": overfit / evaluated if evaluated else None,
        "median_logit_rank": statistics.median(lambdas) if lambdas else None,
        "promoted": False,
        "paper_only": True,
        "note": "CSCV diagnostico; la scelta di strategie e split può influenzare il risultato.",
    }
