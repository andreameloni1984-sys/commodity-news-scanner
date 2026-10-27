"""
GAGARIN feedback and forward-outcome tracker.

Records each distinct approved paper signal once, then scores its subsequent
OHLC path. Ambiguous same-bar stop/target touches are resolved conservatively
as STOP. Scores are observational and never change trading decisions.
"""
from __future__ import annotations

import csv
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

FEEDBACK_FILE = Path("gagarin_feedback.csv")
FIELDS = [
    "signal_id", "timestamp_utc", "entry_bar_timestamp", "last_checked_timestamp",
    "commodity", "symbol", "direction", "action", "timeframe",
    "probability", "quality", "confidence", "entry", "stop", "tp1", "tp2", "tp3",
    "rr1", "rr2", "rr3", "stop_atr", "regime", "structure", "setup", "trigger",
    "data_source", "data_status", "outcome", "r_multiple", "mfe_r", "mae_r", "bars_held",
]


def _value(state, name, default=""):
    value = getattr(state, name, default)
    return default if value is None else value


def _number(value):
    try:
        number = float(value)
        return number if number == number and abs(number) != float("inf") else None
    except (TypeError, ValueError):
        return None


def _timestamp(value):
    if value in (None, ""):
        return None
    try:
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip()
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            # Outcome scoring must not invent a timezone for a naive timestamp.
            # Reject it so ambiguous bars cannot shift into the forward-outcome window.
            if parsed.tzinfo is None:
                return None
            return parsed.astimezone(timezone.utc).timestamp()
        except ValueError:
            return float(text)
    except (TypeError, ValueError, OverflowError):
        return None


def _candles(state):
    raw = list(getattr(state, "candles", []) or [])
    parsed = []
    for candle in raw:
        if not isinstance(candle, dict):
            continue
        ts = _timestamp(candle.get("timestamp", candle.get("time")))
        high = _number(candle.get("high", candle.get("h")))
        low = _number(candle.get("low", candle.get("l")))
        if ts is not None and high is not None and low is not None and high >= low:
            parsed.append((ts, high, low))
    if parsed:
        # Providers may resend/update a candle with the same timestamp.
        # Keep the last valid observation for that timestamp so a duplicate
        # bar cannot be counted twice in forward-outcome scoring.
        deduplicated = {}
        for ts, high, low in parsed:
            deduplicated[ts] = (ts, high, low)
        return [deduplicated[ts] for ts in sorted(deduplicated)]
    # Some data providers expose parallel OHLC/timestamp arrays instead.
    timestamps = list(getattr(state, "timestamps", []) or [])
    highs = list(getattr(state, "highs", []) or [])
    lows = list(getattr(state, "lows", []) or [])
    for ts, high, low in zip(timestamps, highs, lows):
        ts, high, low = _timestamp(ts), _number(high), _number(low)
        if ts is not None and high is not None and low is not None and high >= low:
            parsed.append((ts, high, low))
    deduplicated = {}
    for ts, high, low in parsed:
        deduplicated[ts] = (ts, high, low)
    return [deduplicated[ts] for ts in sorted(deduplicated)]


def _signal_record(state, now=None):
    now = now or datetime.now(timezone.utc)
    metadata = _value(state, "metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    candles = _candles(state)
    bar_ts = candles[-1][0] if candles else now.timestamp()
    values = {
        "commodity": _value(state, "commodity"),
        "symbol": str(_value(state, "symbol")).upper(),
        "direction": str(_value(state, "setup_direction")).upper(),
        "action": str(metadata.get("gagarin_action", _value(state, "final_decision", "WATCH"))).upper(),
        "entry": _value(state, "entry"),
        "stop": _value(state, "stop"),
        "tp1": _value(state, "tp1"),
        "tp2": _value(state, "tp2"),
        "tp3": _value(state, "tp3"),
        "timeframe": str(_value(state, "timeframe")).strip().lower(),
        "bar_ts": bar_ts,
    }
    # Timeframe is part of forecast identity: identical levels on the same
    # candle can represent distinct 5m and 15m hypotheses and must not collide.
    key = "|".join(str(values[k]) for k in ("symbol", "direction", "timeframe", "entry", "stop", "tp1", "tp2", "tp3", "bar_ts"))
    signal_id = hashlib.sha256(key.encode("utf-8")).hexdigest()[:20]
    return {
        "signal_id": signal_id,
        "timestamp_utc": now.isoformat(),
        "entry_bar_timestamp": bar_ts,
        "last_checked_timestamp": bar_ts,
        "commodity": values["commodity"],
        "symbol": values["symbol"],
        "direction": values["direction"],
        "action": values["action"],
        "timeframe": values["timeframe"],
        "probability": _value(state, "probability"),
        "quality": _value(state, "quality"),
        "confidence": _value(state, "confidence"),
        "entry": values["entry"],
        "stop": values["stop"],
        "tp1": values["tp1"],
        "tp2": values["tp2"],
        "tp3": values["tp3"],
        "rr1": _value(state, "rr1"),
        "rr2": _value(state, "rr2"),
        "rr3": _value(state, "rr3"),
        "stop_atr": _value(state, "stop_atr"),
        "regime": _value(state, "regime"),
        "structure": _value(state, "structure_direction"),
        "setup": _value(state, "setup"),
        "trigger": _value(state, "trigger"),
        "data_source": _value(state, "data_source"),
        "data_status": metadata.get("data_status", ""),
        "outcome": "OPEN",
        "r_multiple": "",
        "mfe_r": "",
        "mae_r": "",
        "bars_held": 0,
    }


def append_signal(state, path=FEEDBACK_FILE):
    record = _signal_record(state)
    rows = load_feedback(path)
    if any(row.get("signal_id") == record["signal_id"] for row in rows):
        return False
    rows.append(record)
    _write_rows(rows, path)
    return True


def record_entries(results, path=FEEDBACK_FILE):
    """Record canonical paper entries once; no duplicate row every scan."""
    count = 0
    rows = load_feedback(path)
    seen = {row.get("signal_id") for row in rows}
    for state in results:
        metadata = getattr(state, "metadata", {}) or {}
        canonical = isinstance(metadata, dict) and str(metadata.get("gagarin_action", "")).upper() in {"PAPER_ENTRY", "PAPER_SIGNAL"}
        legacy = str(getattr(state, "final_decision", "")).upper() == "ENTRY"
        if not (canonical or legacy):
            continue
        record = _signal_record(state)
        if record["signal_id"] in seen:
            continue
        rows.append(record)
        seen.add(record["signal_id"])
        count += 1
    if count:
        _write_rows(rows, path)
    return count

def record_forecasts(results, path=FEEDBACK_FILE):
    """
    Record live, directional forecasts with a valid bracket, including setups
    that are not entry-authorized yet. These are labelled by action so forecast
    quality is not confused with the performance of approved paper entries.
    """
    count = 0
    changed = False
    rows = load_feedback(path)
    by_id = {row.get("signal_id"): row for row in rows if row.get("signal_id")}
    seen = set(by_id)
    for state in results:
        side = str(getattr(state, "setup_direction", "") or "").upper()
        if side not in {"LONG", "SHORT"}:
            continue
        if not bool(getattr(state, "data_ok", False)) or not bool(getattr(state, "live", False)):
            continue
        record = _signal_record(state)
        values = [_number(record.get(k)) for k in ("entry", "stop", "tp1", "tp2", "tp3")]
        if any(value is None or value <= 0 for value in values):
            continue
        entry, stop, tp1, tp2, tp3 = values
        geometry_ok = (stop < entry < tp1 < tp2 < tp3) if side == "LONG" else (tp3 < tp2 < tp1 < entry < stop)
        if not geometry_ok:
            continue
        existing = by_id.get(record["signal_id"])
        if existing is not None:
            # If the same setup advances from WATCH to approved ENTRY in the
            # same candle, preserve one sample and upgrade its action label.
            if record["action"] in {"PAPER_ENTRY", "PAPER_SIGNAL"} and existing.get("action") not in {"PAPER_ENTRY", "PAPER_SIGNAL"}:
                existing["action"] = record["action"]
                changed = True
            continue
        rows.append(record)
        by_id[record["signal_id"]] = record
        seen.add(record["signal_id"])
        count += 1
    if count or changed:
        _write_rows(rows, path)
    return count


def update_open_outcomes(results, path=FEEDBACK_FILE):
    """
    Update open signals from candles strictly after their entry bar.
    First barrier touched closes the paper signal. If SL and a TP are touched
    in the same candle, count SL first because intrabar order is unknowable.
    """
    rows = load_feedback(path)
    if not rows:
        return 0
    # Prefer exact symbol + timeframe matching. A symbol-only map silently
    # overwrites candles when multiple timeframe states for one instrument are
    # passed in the same scan, which can mis-score historical forecasts.
    states_by_key = {}
    states_by_symbol = {}
    for state_item in results:
        symbol = str(getattr(state_item, "symbol", "") or "").upper()
        timeframe = str(getattr(state_item, "timeframe", "") or "").lower()
        if not symbol:
            continue
        states_by_key[(symbol, timeframe)] = state_item
        states_by_symbol.setdefault(symbol, []).append(state_item)
    changed = 0
    for row in rows:
        if row.get("outcome", "OPEN") != "OPEN":
            continue
        symbol = str(row.get("symbol", "") or "").upper()
        timeframe = str(row.get("timeframe", "") or "").lower()
        state = states_by_key.get((symbol, timeframe))
        if state is None:
            # Safe compatibility fallback only when exactly one state exists
            # for the symbol; never guess between competing timeframes.
            candidates = states_by_symbol.get(symbol, [])
            if len(candidates) == 1:
                state = candidates[0]
        if state is None:
            continue
        side = str(row.get("direction", "")).upper()
        entry, stop = _number(row.get("entry")), _number(row.get("stop"))
        targets = [_number(row.get(f"tp{i}")) for i in (1, 2, 3)]
        if side not in {"LONG", "SHORT"} or entry is None or stop is None or any(t is None for t in targets):
            continue
        risk = entry - stop if side == "LONG" else stop - entry
        if risk <= 0:
            continue
        start_ts = _timestamp(row.get("entry_bar_timestamp")) or _timestamp(row.get("timestamp_utc"))
        candles = [c for c in _candles(state) if start_ts is not None and c[0] > start_ts]
        if not candles:
            continue
        mfe, mae = 0.0, 0.0
        last_ts = start_ts
        bars = 0
        for ts, high, low in candles:
            last_ts = ts
            bars += 1
            if side == "LONG":
                mfe = max(mfe, (high - entry) / risk)
                mae = min(mae, (low - entry) / risk)
                stop_hit = low <= stop
                hit_targets = [i for i, target in enumerate(targets) if high >= target]
            else:
                mfe = max(mfe, (entry - low) / risk)
                mae = min(mae, (entry - high) / risk)
                stop_hit = high >= stop
                hit_targets = [i for i, target in enumerate(targets) if low <= target]
            if stop_hit:
                row.update(outcome="STOP", r_multiple=-1.0)
                break
            if hit_targets:
                idx = max(hit_targets)
                reward = (targets[idx] - entry) if side == "LONG" else (entry - targets[idx])
                row.update(outcome=f"TP{idx + 1}", r_multiple=round(reward / risk, 6))
                break
        row["mfe_r"] = round(mfe, 6)
        row["mae_r"] = round(mae, 6)
        row["bars_held"] = bars
        row["last_checked_timestamp"] = last_ts
        changed += 1
    if changed:
        _write_rows(rows, path)
    return changed


def _durable_store_enabled(path):
    return Path(path) == FEEDBACK_FILE and bool(os.getenv("DATABASE_URL", "").strip())

def storage_backend():
    """Describe feedback persistence without exposing credentials."""
    if not os.getenv("DATABASE_URL", "").strip():
        return "LOCAL_CSV_NO_DATABASE_URL"
    rows = _load_durable_rows()
    return "POSTGRES" if rows is not None else "LOCAL_CSV_DATABASE_UNAVAILABLE"


def _load_durable_rows():
    try:
        from state_store import ensure_schema, load_state
        if not ensure_schema():
            return None
        rows = load_state("gagarin_feedback_rows")
        return rows if isinstance(rows, list) else []
    except Exception:
        return None


def _save_durable_rows(rows):
    try:
        from state_store import ensure_schema, save_state
        if not ensure_schema():
            return False
        return bool(save_state("gagarin_feedback_rows", rows))
    except Exception:
        return False


def _write_rows(rows, path):
    path = Path(path)
    if _durable_store_enabled(path) and _save_durable_rows(rows):
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_feedback(path=FEEDBACK_FILE):
    path = Path(path)
    if _durable_store_enabled(path):
        rows = _load_durable_rows()
        if rows is not None:
            return rows
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def _calibration_metrics(rows):
    """Descriptive probability calibration on closed outcomes; not a guarantee of future accuracy."""
    samples = []
    for row in rows:
        if (row.get("outcome", "OPEN") or "OPEN") == "OPEN":
            continue
        probability = _number(row.get("probability"))
        realized_r = _number(row.get("r_multiple"))
        if probability is None or not 0.0 <= probability <= 100.0 or realized_r is None:
            continue
        samples.append((probability / 100.0, 1.0 if realized_r > 0 else 0.0))

    if not samples:
        return {"samples": 0, "brier_score": None, "bins": []}

    brier = sum((p - outcome) ** 2 for p, outcome in samples) / len(samples)
    buckets = {}
    for probability, outcome in samples:
        lower = min(90, int(probability * 10) * 10)
        bucket = buckets.setdefault(lower, {"count": 0, "probability_sum": 0.0, "wins": 0})
        bucket["count"] += 1
        bucket["probability_sum"] += probability
        bucket["wins"] += int(outcome > 0.0)
    bins = []
    for lower, bucket in sorted(buckets.items()):
        count = bucket["count"]
        bins.append({
            "range_pct": f"{lower}-{lower + 10}",
            "count": count,
            "mean_predicted_pct": round(100.0 * bucket["probability_sum"] / count, 2),
            "observed_win_rate_pct": round(100.0 * bucket["wins"] / count, 2),
        })
    return {"samples": len(samples), "brier_score": round(brier, 6), "bins": bins}


def summarize(path=FEEDBACK_FILE):
    rows = load_feedback(path)
    outcomes = {}
    realized_r = []
    groups = {}
    by_regime = {}
    by_setup = {}
    by_action = {}
    for row in rows:
        outcome = row.get("outcome", "OPEN") or "OPEN"
        outcomes[outcome] = outcomes.get(outcome, 0) + 1
        value = _number(row.get("r_multiple"))
        if outcome == "OPEN" or value is None:
            continue
        realized_r.append(value)
        key = (str(row.get("symbol", "")), str(row.get("direction", "")))
        group = groups.setdefault(key, {"closed": 0, "wins": 0, "realized_r": 0.0})
        group["closed"] += 1
        group["wins"] += int(value > 0)
        group["realized_r"] += value
        for target, label in ((by_regime, "regime"), (by_setup, "setup"), (by_action, "action")):
            name = str(row.get(label, "") or "UNKNOWN")
            item = target.setdefault(name, {"closed": 0, "wins": 0, "realized_r": 0.0})
            item["closed"] += 1
            item["wins"] += int(value > 0)
            item["realized_r"] += value

    def finish_groups(source):
        result = {}
        for name, item in source.items():
            count = item["closed"]
            result[name] = {
                "closed": count,
                "win_rate_pct": round(100.0 * item["wins"] / count, 2) if count else None,
                "average_r": round(item["realized_r"] / count, 4) if count else None,
                "realized_r": round(item["realized_r"], 4),
            }
        return result

    closed = len(realized_r)
    wins = sum(value > 0 for value in realized_r)
    by_symbol_direction = finish_groups({
        f"{symbol} {direction}": group for (symbol, direction), group in groups.items()
    })
    # The drawdown is calculated in the recorded outcome order. It is a diagnostic,
    # not a portfolio equity curve, because concurrent exposure is not modelled here.
    equity = peak = max_drawdown = 0.0
    for value in realized_r:
        equity += value
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
    return {
        "total": len(rows),
        "open": outcomes.get("OPEN", 0),
        "closed": closed,
        "outcomes": outcomes,
        "win_rate_pct": round(100.0 * wins / closed, 2) if closed else None,
        "average_r": round(sum(realized_r) / closed, 4) if closed else None,
        "realized_r": round(sum(realized_r), 4) if closed else 0.0,
        "max_drawdown_r_sequential": round(max_drawdown, 4),
        "by_symbol_direction": by_symbol_direction,
        "by_regime": finish_groups(by_regime),
        "by_setup": finish_groups(by_setup),
        "by_action": finish_groups(by_action),
        "probability_calibration": _calibration_metrics(rows),
    }

def format_summary(summary):
    win_rate = "N/D" if summary.get("win_rate_pct") is None else f"{summary['win_rate_pct']:.1f}%"
    avg_r = "N/D" if summary.get("average_r") is None else f"{summary['average_r']:.2f}R"
    text = (
        f"signals={summary['total']} open={summary['open']} closed={summary['closed']} "
        f"win_rate={win_rate} avg_R={avg_r} total_R={summary.get('realized_r', 0.0)} "
        f"outcomes={summary['outcomes']}"
    )
    groups = summary.get("by_symbol_direction", {})
    if groups:
        best = sorted(groups.items(), key=lambda item: (item[1]["average_r"], item[1]["closed"]), reverse=True)[:3]
        text += " | per_asset=" + "; ".join(
            f"{name}: n={stats['closed']} win={stats['win_rate_pct']:.1f}% avg={stats['average_r']:.2f}R"
            for name, stats in best
        )
    return text
