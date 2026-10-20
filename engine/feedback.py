"""
GAGARIN feedback and forward-outcome tracker.

Records each distinct approved paper signal once, then scores its subsequent
OHLC path. Ambiguous same-bar stop/target touches are resolved conservatively
as STOP. Scores are observational and never change trading decisions.
"""
from __future__ import annotations

import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path

FEEDBACK_FILE = Path("gagarin_feedback.csv")
FIELDS = [
    "signal_id", "timestamp_utc", "entry_bar_timestamp", "last_checked_timestamp",
    "commodity", "symbol", "direction", "timeframe",
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
            return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
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
        if ts is not None and high is not None and low is not None:
            parsed.append((ts, high, low))
    if parsed:
        return sorted(parsed)
    # Some data providers expose parallel OHLC/timestamp arrays instead.
    timestamps = list(getattr(state, "timestamps", []) or [])
    highs = list(getattr(state, "highs", []) or [])
    lows = list(getattr(state, "lows", []) or [])
    for ts, high, low in zip(timestamps, highs, lows):
        ts, high, low = _timestamp(ts), _number(high), _number(low)
        if ts is not None and high is not None and low is not None:
            parsed.append((ts, high, low))
    return sorted(parsed)


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
        "entry": _value(state, "entry"),
        "stop": _value(state, "stop"),
        "tp1": _value(state, "tp1"),
        "tp2": _value(state, "tp2"),
        "tp3": _value(state, "tp3"),
        "bar_ts": bar_ts,
    }
    key = "|".join(str(values[k]) for k in ("symbol", "direction", "entry", "stop", "tp1", "tp2", "tp3", "bar_ts"))
    signal_id = hashlib.sha256(key.encode("utf-8")).hexdigest()[:20]
    return {
        "signal_id": signal_id,
        "timestamp_utc": now.isoformat(),
        "entry_bar_timestamp": bar_ts,
        "last_checked_timestamp": bar_ts,
        "commodity": values["commodity"],
        "symbol": values["symbol"],
        "direction": values["direction"],
        "timeframe": _value(state, "timeframe"),
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


def update_open_outcomes(results, path=FEEDBACK_FILE):
    """
    Update open signals from candles strictly after their entry bar.
    First barrier touched closes the paper signal. If SL and a TP are touched
    in the same candle, count SL first because intrabar order is unknowable.
    """
    rows = load_feedback(path)
    if not rows:
        return 0
    states = {str(getattr(s, "symbol", "")).upper(): s for s in results}
    changed = 0
    for row in rows:
        if row.get("outcome", "OPEN") != "OPEN":
            continue
        state = states.get(str(row.get("symbol", "")).upper())
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
        start_ts = _timestamp(row.get("entry_bar_timestamp"))
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


def _write_rows(rows, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_feedback(path=FEEDBACK_FILE):
    path = Path(path)
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def summarize(path=FEEDBACK_FILE):
    rows = load_feedback(path)
    outcomes = {}
    realized_r = []
    groups = {}
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
    closed = len(realized_r)
    wins = sum(value > 0 for value in realized_r)
    by_symbol_direction = {}
    for (symbol, direction), group in groups.items():
        count = group["closed"]
        by_symbol_direction[f"{symbol} {direction}"] = {
            "closed": count,
            "win_rate_pct": round(100.0 * group["wins"] / count, 2),
            "average_r": round(group["realized_r"] / count, 4),
            "realized_r": round(group["realized_r"], 4),
        }
    return {
        "total": len(rows),
        "open": outcomes.get("OPEN", 0),
        "closed": closed,
        "outcomes": outcomes,
        "win_rate_pct": round(100.0 * wins / closed, 2) if closed else None,
        "average_r": round(sum(realized_r) / closed, 4) if closed else None,
        "realized_r": round(sum(realized_r), 4) if closed else 0.0,
        "by_symbol_direction": by_symbol_direction,
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
