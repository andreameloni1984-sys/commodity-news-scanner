"""
SOYUZ GAGARIN — FEEDBACK ENGINE v1.0

Signal learning loop:
SIGNAL -> TRACK -> OUTCOME -> STATISTICS -> FEEDBACK

Questo modulo è esclusivamente osservazionale.
NON modifica soglie Gagarin e NON autorizza operazioni.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path


FEEDBACK_FILE = Path("gagarin_feedback.csv")


FIELDS = [
    "timestamp_utc",
    "commodity",
    "symbol",
    "direction",
    "probability",
    "quality",
    "confidence",
    "entry",
    "stop",
    "tp1",
    "tp2",
    "tp3",
    "rr1",
    "rr2",
    "rr3",
    "stop_atr",
    "regime",
    "structure",
    "setup",
    "trigger",
    "data_source",
    "data_status",
    "outcome",
    "r_multiple",
]


def _value(state, name, default=""):
    """Legge un attributo dallo state senza generare errori."""
    value = getattr(state, name, default)
    return default if value is None else value


def build_signal_record(state, timestamp=None):
    """
    Crea uno snapshot completo del segnale al momento dell'ENTRY.
    """

    if timestamp is None:
        timestamp = datetime.now(timezone.utc)

    metadata = _value(state, "metadata", {})

    if not isinstance(metadata, dict):
        metadata = {}

    return {
        "timestamp_utc": timestamp.isoformat(),

        "commodity": _value(state, "commodity"),
        "symbol": _value(state, "symbol"),
        "direction": _value(state, "setup_direction"),

        "probability": _value(state, "probability"),
        "quality": _value(state, "quality"),
        "confidence": _value(state, "confidence"),

        "entry": _value(state, "entry"),
        "stop": _value(state, "stop"),

        "tp1": _value(state, "tp1"),
        "tp2": _value(state, "tp2"),
        "tp3": _value(state, "tp3"),

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

        # Il segnale appena registrato è ancora aperto.
        "outcome": "OPEN",

        # Verrà valorizzato quando il segnale sarà chiuso.
        "r_multiple": "",
    }


def append_signal(state, path=FEEDBACK_FILE):
    """
    Aggiunge un singolo segnale al registro.
    """

    record = build_signal_record(state)

    exists = path.exists()

    with path.open(
        "a",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=FIELDS,
        )

        if not exists:
            writer.writeheader()

        writer.writerow(record)

    return record


def record_entries(results, path=FEEDBACK_FILE):
    """
    Registra solamente gli stati che hanno superato
    tutti i gate e sono diventati ENTRY.
    """

    existing = load_feedback(path)
    fingerprints = {
        (row.get("symbol"), row.get("direction"), row.get("setup"),
         row.get("entry"), row.get("stop"), row.get("tp1"), row.get("tp2"), row.get("tp3"))
        for row in existing
    }
    count = 0

    for state in results:
        if getattr(state, "final_decision", "") != "ENTRY":
            continue
        record = build_signal_record(state)
        fingerprint = (record["symbol"], record["direction"], record["setup"],
                       str(record["entry"]), str(record["stop"]), str(record["tp1"]),
                       str(record["tp2"]), str(record["tp3"]))
        if fingerprint in fingerprints:
            continue
        # Write the prebuilt snapshot so the fingerprint and saved values match.
        exists = Path(path).exists()
        with Path(path).open("a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=FIELDS)
            if not exists:
                writer.writeheader()
            writer.writerow(record)
        fingerprints.add(fingerprint)
        count += 1

    return count


def load_feedback(path=FEEDBACK_FILE):
    """
    Carica tutti i segnali registrati.
    """

    if not path.exists():
        return []

    with path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:

        return list(
            csv.DictReader(file)
        )


def summarize(path=FEEDBACK_FILE):
    """
    Produce un riepilogo degli outcome.
    """

    rows = load_feedback(path)

    outcomes = {}

    for row in rows:

        outcome = (
            row.get("outcome", "OPEN")
            or "OPEN"
        )

        outcomes[outcome] = (
            outcomes.get(outcome, 0) + 1
        )

    return {
        "total": len(rows),

        "open": outcomes.get(
            "OPEN",
            0,
        ),

        "closed": (
            len(rows)
            - outcomes.get("OPEN", 0)
        ),

        "outcomes": outcomes,
    }


def format_summary(summary):
    """
    Formato compatto per log/Telegram.
    """

    return (
        f"signals={summary['total']} "
        f"open={summary['open']} "
        f"closed={summary['closed']} "
        f"outcomes={summary['outcomes']}"
    )

def _parse_timestamp(value):
    """Parse ISO timestamps, normalizing naive timestamps to UTC."""
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _hit_outcome(row, candles):
    """Resolve the first stop/target hit conservatively from later OHLC candles.

    If stop and target are both touched in one candle, stop wins because
    OHLC data cannot establish intrabar ordering.
    """
    direction = str(row.get("direction", "")).upper()
    try:
        entry, stop = float(row["entry"]), float(row["stop"])
        targets = [(f"TP{i}", float(row[f"tp{i}"]), i)
                   for i in (1, 2, 3) if row.get(f"tp{i}") not in ("", None)]
    except (KeyError, TypeError, ValueError):
        return None
    if direction not in {"LONG", "SHORT"} or entry == stop or not targets:
        return None
    risk = abs(entry - stop)
    opened = _parse_timestamp(row.get("timestamp_utc"))
    if opened is None:
        return None
    for candle in candles:
        stamp = _parse_timestamp(candle.get("timestamp", candle.get("datetime")))
        if stamp is None or stamp <= opened:
            continue
        try:
            high, low = float(candle["high"]), float(candle["low"])
        except (KeyError, TypeError, ValueError):
            continue
        stop_hit = low <= stop if direction == "LONG" else high >= stop
        hit_targets = [item for item in targets
                       if (high >= item[1] if direction == "LONG" else low <= item[1])]
        if stop_hit:
            return {"outcome": "STOP", "r_multiple": -1.0, "closed_at": stamp.isoformat()}
        if hit_targets:
            name, target_price, _ = max(hit_targets, key=lambda item: item[2])
            reward = target_price - entry if direction == "LONG" else entry - target_price
            return {"outcome": name, "r_multiple": round(reward / risk, 4),
                    "closed_at": stamp.isoformat()}
    return None


def evaluate_open_signals(candles_by_symbol, path=FEEDBACK_FILE):
    """Resolve OPEN rows against later chronological OHLC candles.

    candles_by_symbol maps symbols to candle mappings with timestamp/datetime,
    high, and low. Updates the CSV; it never submits orders or changes decisions.
    """
    rows = load_feedback(path)
    if not rows:
        return 0
    changed = 0
    for row in rows:
        if (row.get("outcome") or "OPEN") != "OPEN":
            continue
        result = _hit_outcome(row, candles_by_symbol.get(row.get("symbol"), []))
        if result is None:
            continue
        row["outcome"] = result["outcome"]
        row["r_multiple"] = result["r_multiple"]
        row["closed_at_utc"] = result["closed_at"]
        changed += 1
    if changed:
        fields = list(FIELDS)
        if any("closed_at_utc" in row for row in rows):
            fields.append("closed_at_utc")
        with Path(path).open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
    return changed
