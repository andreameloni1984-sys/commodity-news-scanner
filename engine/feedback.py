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
    "signal_id", "alert_id", "timestamp_utc", "entry_bar_timestamp", "last_checked_timestamp",
    "commodity", "symbol", "direction", "action", "timeframe",
    "probability", "quality", "confidence", "entry", "stop", "tp1", "tp2", "tp3",
    "rr1", "rr2", "rr3", "stop_atr", "regime", "structure", "setup", "trigger",
    "data_source", "data_status", "alert_price", "alert_stage", "human_review", "human_review_at", "outcome", "r_multiple", "mfe_r", "mae_r", "bars_held",
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
        # TP1 is required to define a valid tracked setup; TP2/TP3 are
        # optional. Older rows and valid one-target setups must still resolve.
        raw_targets = [row.get(f"tp{i}") for i in (1, 2, 3)]
        targets = [_number(value) if value not in (None, "") else None for value in raw_targets]
        if side not in {"LONG", "SHORT"} or entry is None or stop is None or targets[0] is None:
            continue
        # A supplied but malformed target is not silently ignored.
        if any(raw not in (None, "") and parsed is None for raw, parsed in zip(raw_targets, targets)):
            continue
        risk = entry - stop if side == "LONG" else stop - entry
        if risk <= 0:
            continue
        active_targets = [(i, target) for i, target in enumerate(targets) if target is not None]
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


def _durable_feedback_enabled(path):
    return Path(path) == FEEDBACK_FILE and bool(__import__("os").getenv("DATABASE_URL", "").strip())


def _load_durable_feedback():
    try:
        from state_store import ensure_schema, load_state
        if not ensure_schema():
            return None
        rows = load_state("gagarin_feedback_rows")
        return rows if isinstance(rows, list) else []
    except Exception:
        return None


def _save_durable_feedback(rows):
    try:
        from state_store import ensure_schema, save_state
        return bool(ensure_schema() and save_state("gagarin_feedback_rows", rows))
    except Exception:
        return False


def storage_backend():
    if not __import__("os").getenv("DATABASE_URL", "").strip():
        return "LOCAL_CSV_NO_DATABASE_URL"
    return "POSTGRES" if _load_durable_feedback() is not None else "LOCAL_CSV_DATABASE_UNAVAILABLE"


def _write_rows(rows, path):
    path = Path(path)
    if _durable_feedback_enabled(path) and _save_durable_feedback(rows):
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_feedback(path=FEEDBACK_FILE):
    path = Path(path)
    if _durable_feedback_enabled(path):
        rows = _load_durable_feedback()
        if rows is not None:
            return rows
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def summarize(path=FEEDBACK_FILE):
    rows = load_feedback(path)
    outcomes = {}
    realized_r = []
    for row in rows:
        outcome = row.get("outcome", "OPEN") or "OPEN"
        outcomes[outcome] = outcomes.get(outcome, 0) + 1
        value = _number(row.get("r_multiple"))
        if outcome != "OPEN" and value is not None:
            realized_r.append(value)
    closed = len(realized_r)
    wins = sum(value > 0 for value in realized_r)
    return {
        "total": len(rows),
        "open": outcomes.get("OPEN", 0),
        "closed": closed,
        "outcomes": outcomes,
        "win_rate_pct": round(100.0 * wins / closed, 2) if closed else None,
        "average_r": round(sum(realized_r) / closed, 4) if closed else None,
        "realized_r": round(sum(realized_r), 4) if closed else 0.0,
    }


def format_summary(summary):
    win_rate = "N/D" if summary.get("win_rate_pct") is None else f"{summary['win_rate_pct']:.1f}%"
    avg_r = "N/D" if summary.get("average_r") is None else f"{summary['average_r']:.2f}R"
    return (
        f"signals={summary['total']} open={summary['open']} closed={summary['closed']} "
        f"win_rate={win_rate} avg_R={avg_r} total_R={summary.get('realized_r', 0.0)} "
        f"outcomes={summary['outcomes']}"
    )


def assign_alert_ids(alerts, now=None):
    """Attach stable short IDs to one outgoing alert batch before formatting."""
    now = now or datetime.now(timezone.utc)
    stamp = now.isoformat()
    for alert in alerts:
        if alert.get("alert_id"):
            continue
        raw = "|".join((
            str(alert.get("symbol") or alert.get("commodity") or ""),
            str(alert.get("direction") or ""),
            str(alert.get("stage") or "DIRECTIONAL"),
            stamp,
        ))
        alert["alert_id"] = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10].upper()
        alert["sent_at_utc"] = stamp
    return alerts


def record_sent_alerts(alerts, path=FEEDBACK_FILE):
    """Persist only alerts confirmed delivered by Telegram; never sends messages."""
    rows = load_feedback(path)
    known = {str(row.get("alert_id") or "") for row in rows}
    added = 0
    for alert in alerts or []:
        alert_id = str(alert.get("alert_id") or "").strip().upper()
        if not alert_id or alert_id in known:
            continue
        analysis = alert.get("pattern_analysis") or {}
        rows.append({
            "signal_id": alert_id,
            "alert_id": alert_id,
            "timestamp_utc": alert.get("sent_at_utc") or datetime.now(timezone.utc).isoformat(),
            "entry_bar_timestamp": "",
            "last_checked_timestamp": "",
            "commodity": alert.get("commodity", ""),
            "symbol": str(alert.get("symbol") or alert.get("commodity") or "").upper(),
            "direction": str(alert.get("direction") or "").upper(),
            "action": str(alert.get("stage") or "DIRECTIONAL").upper(),
            "timeframe": alert.get("timeframe", ""),
            "probability": alert.get("probability", ""),
            "quality": alert.get("quality", ""),
            "confidence": alert.get("confidence", ""),
            "entry": alert.get("entry", ""),
            "stop": alert.get("stop", ""),
            "tp1": alert.get("tp1", ""),
            "tp2": alert.get("tp2", ""),
            "tp3": alert.get("tp3", ""),
            "data_source": alert.get("provider") or alert.get("data_source", ""),
            "data_status": "SENT_ALERT",
            "alert_price": alert.get("price", ""),
            "alert_stage": alert.get("stage", "DIRECTIONAL"),
            "human_review": "",
            "human_review_at": "",
            "outcome": "OPEN",
            "r_multiple": "",
            "mfe_r": "",
            "mae_r": "",
            "bars_held": 0,
        })
        known.add(alert_id)
        added += 1
    if added:
        _write_rows(rows, path)
    return added


def pending_alert_reviews(path=FEEDBACK_FILE, limit=10):
    """Return the newest actually-sent alerts that have not been manually reviewed."""
    rows = load_feedback(path)
    pending = [
        row for row in rows
        if row.get("alert_id") and not str(row.get("human_review") or "").strip()
    ]
    pending.sort(key=lambda row: str(row.get("timestamp_utc") or ""), reverse=True)
    return pending[:max(0, int(limit))]


def review_alert(alert_id, verdict, path=FEEDBACK_FILE, now=None):
    """Attach a manual verdict to one alert ID (or unique ID prefix)."""
    verdict = str(verdict or "").strip().upper().replace("-", "_")
    aliases = {"ESATTO": "ESATTO", "CORRETTO": "ESATTO", "SBAGLIATO": "SBAGLIATO",
               "NON_VALUTABILE": "NON_VALUTABILE", "NONVALUTABILE": "NON_VALUTABILE",
               "N_D": "NON_VALUTABILE"}
    if verdict not in aliases:
        return False, "Valutazione non valida. Usa ESATTO, SBAGLIATO o NON_VALUTABILE."
    key = str(alert_id or "").strip().upper()
    if not key:
        return False, "Manca l'ID alert."
    rows = load_feedback(path)
    matches = [row for row in rows if row.get("alert_id") and str(row["alert_id"]).upper().startswith(key)]
    if len(matches) != 1:
        return False, "ID non trovato o ambiguo. Usa l'ID completo mostrato in /alertsera."
    row = matches[0]
    if str(row.get("human_review") or "").strip():
        return False, f"Alert {row['alert_id']} già valutato: {row['human_review']}."
    row["human_review"] = aliases[verdict]
    row["human_review_at"] = (now or datetime.now(timezone.utc)).isoformat()
    _write_rows(rows, path)
    return True, f"Alert {row['alert_id']} registrato: {row['human_review']}."


def format_alert_review(path=FEEDBACK_FILE, limit=10, day=None):
    """Build a daily review list; callers decide when/where to deliver it."""
    rows = load_feedback(path)
    pending = pending_alert_reviews(path=path, limit=limit)
    day = day or datetime.now(timezone.utc).date().isoformat()
    sent_today = [
        row for row in rows
        if row.get("alert_id") and str(row.get("timestamp_utc", "")).startswith(day)
    ]
    reviewed_today = [
        row for row in sent_today if str(row.get("human_review") or "").strip()
    ]
    lines = [
        "📊 GAGARIN — SONDAGGIO ALERT",
        f"Data UTC: {day}",
        f"Alert registrati oggi: {len(sent_today)} | valutati: {len(reviewed_today)} | da valutare: {len(sent_today) - len(reviewed_today)}",
        "",
    ]
    if not pending:
        lines.append("Nessun alert in attesa di valutazione.")
    else:
        lines.append("Rispondi per ogni alert:")
        for row in pending:
            price = row.get("alert_price") or "N/D"
            lines.append(
                f"ID {row.get('alert_id')} — {row.get('commodity') or row.get('symbol')} "
                f"{row.get('direction') or 'N/D'} | prezzo alert {price} | "
                f"stato {row.get('alert_stage') or row.get('action') or 'N/D'}"
            )
            lines.append(f"/valutaalert {row.get('alert_id')} ESATTO")
            lines.append(f"/valutaalert {row.get('alert_id')} SBAGLIATO")
            lines.append(f"/valutaalert {row.get('alert_id')} NON_VALUTABILE")
    lines.extend(["", "Esito automatico e valutazione manuale sono metriche separate. PAPER ONLY."])
    return "\n".join(lines)
