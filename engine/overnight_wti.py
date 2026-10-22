"""PAPER-ONLY WTI overnight feature research.

Measures overnight price/volatility context. It does not emit LONG/SHORT
signals or alter Gagarin's final decision. Thresholds use only prior ranges.
"""
from __future__ import annotations
from math import log, sqrt
from statistics import mean
from typing import Iterable, Mapping, Sequence


def _num(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result and abs(result) != float("inf") else None


def _percentile(sorted_values: Sequence[float], fraction: float) -> float:
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * fraction
    low = int(position)
    high = min(low + 1, len(sorted_values) - 1)
    weight = position - low
    return sorted_values[low] * (1 - weight) + sorted_values[high] * weight


def summarize_overnight(
    bars: Iterable[Mapping],
    *,
    previous_close: float | None = None,
    us_open: float | None = None,
    historical_ranges_pct: Sequence[float] = (),
    event_flags: Mapping[str, bool] | None = None,
) -> dict:
    """Summarize timestamp-ordered overnight OHLC(V) bars.

    Historical ranges must be available before this overnight session.
    Missing or invalid inputs remain null rather than being guessed.
    """
    parsed = []
    for bar in bars:
        high, low, close = (_num(bar.get(k)) for k in ("high", "low", "close"))
        if high is None or low is None or close is None or high < low or close <= 0:
            continue
        parsed.append({"open": _num(bar.get("open")), "high": high, "low": low,
                       "close": close, "volume": _num(bar.get("volume"))})
    flags = dict(event_flags or {})
    if not parsed:
        return {
            "feature": "WTI_OVERNIGHT_REGIME", "paper_only": True,
            "status": "INSUFFICIENT_DATA", "bar_count": 0,
            "overnight_return_pct": None, "range_pct": None,
            "realized_volatility_pct": None, "gap_to_us_open_pct": None,
            "volume": None, "regime": "UNKNOWN", "directional_bias": "UNTESTED",
            "event_flags": flags,
        }

    first, last = parsed[0], parsed[-1]
    base = _num(previous_close)
    if base is None:
        base = first["open"]
    overnight_return = ((last["close"] / base) - 1) * 100 if base and base > 0 else None
    high = max(row["high"] for row in parsed)
    low = min(row["low"] for row in parsed)
    range_pct = ((high - low) / base) * 100 if base and base > 0 else None
    closes = [row["close"] for row in parsed]
    log_returns = [log(closes[i] / closes[i - 1]) for i in range(1, len(closes))
                   if closes[i] > 0 and closes[i - 1] > 0]
    realized_vol = sqrt(sum(value * value for value in log_returns)) * 100 if log_returns else None
    opening_price = _num(us_open)
    gap = ((opening_price / last["close"]) - 1) * 100 if opening_price and opening_price > 0 else None
    volumes = [row["volume"] for row in parsed if row["volume"] is not None and row["volume"] >= 0]
    history = sorted(v for v in (_num(x) for x in historical_ranges_pct)
                     if v is not None and v >= 0)
    if range_pct is None:
        regime = "UNKNOWN"
    elif len(history) < 20:
        regime = "UNCLASSIFIED_INSUFFICIENT_HISTORY"
    elif range_pct >= _percentile(history, 0.90):
        regime = "SHOCK"
    elif range_pct >= _percentile(history, 0.75):
        regime = "EXPANDED"
    elif range_pct <= _percentile(history, 0.25):
        regime = "QUIET"
    else:
        regime = "NORMAL"

    return {
        "feature": "WTI_OVERNIGHT_REGIME", "paper_only": True,
        "status": "OBSERVATION_ONLY", "bar_count": len(parsed),
        "overnight_return_pct": overnight_return, "range_pct": range_pct,
        "realized_volatility_pct": realized_vol, "gap_to_us_open_pct": gap,
        "volume": sum(volumes) if volumes else None, "regime": regime,
        "directional_bias": "UNTESTED", "event_flags": flags,
        "event_caution": any(bool(v) for v in flags.values()),
        "interpretation": (
            "Overnight direction is descriptive only; do not infer LONG/SHORT "
            "edge until forward returns are validated out-of-sample."
        ),
    }


def evaluate_directional_edge(
    observations: Iterable[Mapping], *, minimum_samples: int = 30,
) -> dict:
    """Compare overnight sign with next-session return; never a live signal."""
    pairs = []
    for row in observations:
        overnight = _num(row.get("overnight_return_pct"))
        forward = _num(row.get("next_session_return_pct"))
        if overnight is not None and forward is not None and overnight != 0 and forward != 0:
            pairs.append((overnight, forward))
    count = len(pairs)
    if not count:
        return {"paper_only": True, "status": "INSUFFICIENT_DATA", "samples": 0,
                "same_direction_rate_pct": None, "mean_next_session_return_pct": None,
                "directional_edge_validated": False}
    hit_rate = sum((overnight > 0) == (forward > 0) for overnight, forward in pairs) / count * 100
    enough = count >= minimum_samples
    return {
        "paper_only": True, "status": "RESEARCH_ONLY" if enough else "INSUFFICIENT_SAMPLE",
        "samples": count, "same_direction_rate_pct": hit_rate,
        "mean_next_session_return_pct": mean(forward for _, forward in pairs),
        "directional_edge_validated": False,
        "promotion_gate": "Require costs, chronological walk-forward/OOS, regime/event "
                          "splits, and stable results before considering any signal change.",
    }



def collect_wti_overnight_sessions(
    *,
    period: str = "60d",
    interval: str = "5m",
    request_get=None,
    now_utc=None,
) -> dict:
    """Fetch public Yahoo continuous WTI futures bars and group ET overnight sessions.

    Session date D is defined explicitly as 18:00 ET on D-1 through 09:00 ET on D.
    Bars are retained with UTC and America/New_York timestamps and volume where
    supplied. This is a research proxy on CL=F, not executable-contract data.
    Network access is only used when this function is explicitly called.
    """
    from datetime import datetime, timezone, timedelta
    from zoneinfo import ZoneInfo

    try:
        import requests
    except ImportError:
        return {"status": "UNAVAILABLE", "source": "Yahoo Finance CL=F",
                "error": "requests package unavailable", "sessions": []}

    getter = request_get or requests.get
    eastern = ZoneInfo("America/New_York")
    url = "https://query1.finance.yahoo.com/v8/finance/chart/CL=F"
    try:
        response = getter(
            url,
            params={"range": period, "interval": interval, "events": "history"},
            headers={"User-Agent": "Mozilla/5.0 Gagarin-WTI-Overnight/1.0"},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        chart = payload.get("chart") or {}
        if chart.get("error"):
            raise ValueError(str(chart["error"]))
        result_list = chart.get("result") or []
        if not result_list:
            raise ValueError("Yahoo returned no chart data")
        result = result_list[0]
        timestamps = result.get("timestamp") or []
        quotes = (result.get("indicators", {}).get("quote") or [{}])
        quote = quotes[0] if quotes else {}
        sessions = {}
        us_sessions = {}
        rejected = 0
        for index, stamp in enumerate(timestamps):
            try:
                stamp = int(stamp)
                o, h, low, close = (
                    _num((quote.get(key) or [])[index])
                    for key in ("open", "high", "low", "close")
                )
                raw_volume = (quote.get("volume") or [])
                volume = _num(raw_volume[index]) if index < len(raw_volume) else None
                if None in (o, h, low, close) or min(o, h, low, close) <= 0:
                    rejected += 1
                    continue
                if h < max(o, close, low) or low > min(o, close) or low > h:
                    rejected += 1
                    continue
                utc_dt = datetime.fromtimestamp(stamp, tz=timezone.utc)
                et_dt = utc_dt.astimezone(eastern)
                minute = et_dt.hour * 60 + et_dt.minute
                # Session D comprises 18:00-23:59 ET on D-1 and 00:00-08:59 ET on D.
                if minute >= 18 * 60:
                    session_date = (et_dt.date() + timedelta(days=1)).isoformat()
                    destination = sessions
                elif minute < 9 * 60:
                    session_date = et_dt.date().isoformat()
                    destination = sessions
                elif 9 * 60 <= minute < 14 * 60 + 30:
                    session_date = et_dt.date().isoformat()
                    destination = us_sessions
                else:
                    continue
                row = {
                    "timestamp": stamp, "timestamp_utc": utc_dt.isoformat(),
                    "timestamp_et": et_dt.isoformat(), "session_date": session_date,
                    "open": o, "high": h, "low": low, "close": close,
                    "volume": volume,
                }
                destination.setdefault(session_date, []).append(row)
            except (IndexError, TypeError, ValueError, OverflowError):
                rejected += 1
                continue

        output = []
        for session_date, bars in sorted(sessions.items()):
            bars.sort(key=lambda row: row["timestamp"])
            # Reject duplicate timestamps deterministically; keep first valid record.
            deduped = []
            seen = set()
            for bar in bars:
                if bar["timestamp"] in seen:
                    continue
                seen.add(bar["timestamp"])
                deduped.append(bar)
            if not deduped:
                continue
            summary = summarize_overnight(deduped)
            regular = sorted(us_sessions.get(session_date, []), key=lambda row: row["timestamp"])
            regular = list({row["timestamp"]: row for row in regular}.values())
            # For 5-minute bars, 09:00-14:29 ET should contain 66 bars.
            regular_first_minute = (
                datetime.fromtimestamp(regular[0]["timestamp"], tz=timezone.utc)
                .astimezone(eastern).hour * 60
                + datetime.fromtimestamp(regular[0]["timestamp"], tz=timezone.utc)
                .astimezone(eastern).minute
            ) if regular else None
            regular_last_et = datetime.fromtimestamp(regular[-1]["timestamp"], tz=timezone.utc).astimezone(eastern) if regular else None
            regular_last_minute = regular_last_et.hour * 60 + regular_last_et.minute if regular_last_et else None
            regular_complete = (
                len(regular) >= 53 and regular_first_minute == 9 * 60
                and regular_last_minute == 14 * 60 + 25
            )
            if regular_complete:
                regular_open = regular[0]["open"]
                regular_close = regular[-1]["close"]
                next_session_return = ((regular_close / regular_open) - 1) * 100 if regular_open > 0 else None
            else:
                next_session_return = None
            overnight_first_et = datetime.fromtimestamp(deduped[0]["timestamp"], tz=timezone.utc).astimezone(eastern)
            overnight_last_et = datetime.fromtimestamp(deduped[-1]["timestamp"], tz=timezone.utc).astimezone(eastern)
            overnight_complete = (
                overnight_first_et.hour * 60 + overnight_first_et.minute == 18 * 60
                and overnight_last_et.hour * 60 + overnight_last_et.minute == 8 * 60 + 55
                and len(deduped) >= 180
            )
            summary.update({
                "session_date": session_date,
                "overnight_coverage_complete": overnight_complete,
                "next_session_return_pct": next_session_return,
                "us_session_coverage_complete": regular_complete,
                "us_session_bar_count": len(regular),
                "us_session_first_bar_utc": regular[0]["timestamp_utc"] if regular else None,
                "us_session_last_bar_utc": regular[-1]["timestamp_utc"] if regular else None,
                "source": "Yahoo Finance continuous futures CL=F",
                "interval": interval,
                "first_bar_utc": deduped[0]["timestamp_utc"],
                "last_bar_utc": deduped[-1]["timestamp_utc"],
                "bars": deduped,
                "volume_coverage": (
                    sum(bar["volume"] is not None for bar in deduped) / len(deduped)
                ),
            })
            output.append(summary)
        current = now_utc or datetime.now(timezone.utc)
        return {
            "status": "OK" if output else "INSUFFICIENT_DATA",
            "paper_only": True,
            "source": "Yahoo Finance continuous futures CL=F",
            "period_requested": period, "interval": interval,
            "timezone": "America/New_York",
            "session_definition": "18:00 ET previous calendar day through 08:59 ET session date",
            "forward_session_definition": "09:00-14:29 ET on the same session date; open-to-close return",
            "retrieved_at_utc": current.astimezone(timezone.utc).isoformat(),
            "rejected_bars": rejected, "sessions": output,
            "limitations": [
                "Incomplete sessions are retained for inspection but the forward return is null unless first/last US bars and minimum coverage are present.",
                "Continuous futures data can include roll effects and is not a specific tradable contract.",
                "Yahoo timestamps/volume availability and history may be incomplete; verify coverage before analysis.",
                "No bid/ask, commission or slippage data are provided by this feed.",
                "This collector does not schedule EIA/OPEC events or produce trading signals.",
            ],
        }
    except Exception as exc:
        return {
            "status": "FETCH_ERROR", "paper_only": True,
            "source": "Yahoo Finance continuous futures CL=F",
            "error": f"{type(exc).__name__}: {str(exc)[:200]}",
            "sessions": [],
        }


def evaluate_cost_adjusted_directional_edge(
    observations: Iterable[Mapping],
    *,
    round_trip_cost_bps: float,
    minimum_samples: int = 30,
) -> dict:
    """Descriptive sign-following test with explicit round-trip cost deduction.

    next_session_return_pct is a percentage return (e.g. 0.4 means +0.4%).
    Cost is in basis points of notional. This is not a strategy backtest because
    it does not model entry prices, fills, stop/target logic, or market impact.
    """
    cost_bps = _num(round_trip_cost_bps)
    if cost_bps is None or cost_bps < 0:
        return {"paper_only": True, "status": "INVALID_COST", "samples": 0,
                "directional_edge_validated": False}
    cost_pct = cost_bps / 100.0
    pairs = []
    for row in observations:
        overnight = _num(row.get("overnight_return_pct"))
        forward = _num(row.get("next_session_return_pct"))
        if overnight is None or forward is None or overnight == 0:
            continue
        # Hypothetical sign-following exposure: long for positive overnight,
        # short for negative overnight. Costs deducted once per round trip.
        gross = forward if overnight > 0 else -forward
        pairs.append((gross, gross - cost_pct))
    count = len(pairs)
    if not count:
        return {"paper_only": True, "status": "INSUFFICIENT_DATA", "samples": 0,
                "gross_mean_pct": None, "net_mean_pct": None,
                "net_positive_rate_pct": None, "directional_edge_validated": False}
    net = [item[1] for item in pairs]
    enough = count >= minimum_samples
    return {
        "paper_only": True, "status": "RESEARCH_ONLY" if enough else "INSUFFICIENT_SAMPLE",
        "samples": count, "round_trip_cost_bps": cost_bps,
        "gross_mean_pct": mean(item[0] for item in pairs),
        "net_mean_pct": mean(net),
        "net_median_pct": sorted(net)[count // 2],
        "net_positive_rate_pct": sum(value > 0 for value in net) / count * 100,
        "directional_edge_validated": False,
        "warning": "Costs are a user-supplied scenario, not measured bid/ask or broker fees.",
    }


def chronological_walk_forward(
    observations: Sequence[Mapping],
    *,
    train_fraction: float = 0.60,
    validation_fraction: float = 0.20,
) -> dict:
    """Partition already chronologically ordered observations without shuffling."""
    n = len(observations)
    if not 0 < train_fraction < 1 or not 0 < validation_fraction < 1:
        return {"paper_only": True, "status": "INVALID_SPLIT"}
    if train_fraction + validation_fraction >= 1:
        return {"paper_only": True, "status": "INVALID_SPLIT"}
    train_end = int(n * train_fraction)
    validation_end = int(n * (train_fraction + validation_fraction))
    if train_end < 1 or validation_end <= train_end or validation_end >= n:
        return {"paper_only": True, "status": "INSUFFICIENT_DATA", "samples": n}
    return {
        "paper_only": True, "status": "PARTITIONED_NOT_EVALUATED", "samples": n,
        "train": list(observations[:train_end]),
        "validation": list(observations[train_end:validation_end]),
        "out_of_sample": list(observations[validation_end:]),
        "warning": "Input must be sorted by session date before splitting; no shuffling or leakage checks are inferred.",
    }



def write_wti_overnight_archive(report: Mapping, path="data/wti_overnight_sessions.json") -> dict:
    """Persist a fetched report as a research artifact; never used by signal logic."""
    import json
    from pathlib import Path
    destination = Path(path)
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(dict(report), indent=2, sort_keys=True) + "\\n", encoding="utf-8")
        return {"paper_only": True, "status": "SAVED", "path": str(destination), "sessions": len(report.get("sessions", []))}
    except (OSError, TypeError, ValueError) as exc:
        return {"paper_only": True, "status": "SAVE_ERROR", "path": str(destination),
                "error": f"{type(exc).__name__}: {str(exc)[:160]}"}
