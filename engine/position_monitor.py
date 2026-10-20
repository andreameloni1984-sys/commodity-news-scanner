"""Persistent advisory monitor for manually registered Gagarin positions.

Uses Gagarin provider quotes and OHLC candles, not a broker execution API.
Alerts only when a meaningful exit/risk state changes. PAPER/ADVISORY ONLY.
"""
from __future__ import annotations

import json
import math
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from engine.pattern_exit import analyze_pattern_and_exit

_POSITION_FILE = Path(os.getenv("GAGARIN_POSITION_FILE", "data/gagarin_tracked_positions.json"))
_LOCK = threading.RLock()
_MAX_QUOTE_AGE = max(1.0, float(os.getenv("LIVE_MAX_AGE_SECONDS", "60")))


def _positive(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number > 0 else None


def _read() -> dict[str, dict]:
    try:
        raw = json.loads(_POSITION_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _write(positions: dict[str, dict]) -> None:
    _POSITION_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp = _POSITION_FILE.with_suffix(_POSITION_FILE.suffix + ".tmp")
    temp.write_text(json.dumps(positions, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(_POSITION_FILE)


def register_position(
    *, symbol: str, commodity: str, direction: str, entry: Any,
    stop: Any, tp1: Any, tp2: Any = None, tp3: Any = None,
) -> tuple[bool, str]:
    """Register a user-entered position for alert-only monitoring."""
    symbol = str(symbol or "").strip().upper()
    commodity = str(commodity or "").strip()
    direction = str(direction or "").strip().upper()
    entry_v, stop_v, tp1_v = (_positive(x) for x in (entry, stop, tp1))
    tp2_v, tp3_v = _positive(tp2), _positive(tp3)
    if not symbol or not commodity or direction not in {"LONG", "SHORT"}:
        return False, "Uso: /monitora ORO LONG 2700 2680 2740 [TP2] [TP3]"
    if any(v is None for v in (entry_v, stop_v, tp1_v)):
        return False, "Entry, stop e TP1 devono essere prezzi positivi e validi."
    if tp2 is not None and tp2_v is None or tp3 is not None and tp3_v is None:
        return False, "TP2/TP3, se indicati, devono essere prezzi positivi."
    if tp3_v is not None and tp2_v is None:
        return False, "Per registrare TP3 devi indicare anche TP2."
    if direction == "LONG":
        valid = stop_v < entry_v < tp1_v
        valid = valid and (tp2_v is None or tp1_v < tp2_v)
        valid = valid and (tp3_v is None or tp2_v is not None and tp2_v < tp3_v)
    else:
        valid = tp1_v < entry_v < stop_v
        valid = valid and (tp2_v is None or tp2_v < tp1_v)
        valid = valid and (tp3_v is None or tp2_v is not None and tp3_v < tp2_v)
    if not valid:
        return False, "Livelli incoerenti con la direzione LONG/SHORT; controlla entry, stop e target."
    with _LOCK:
        positions = _read()
        positions[symbol] = {
            "symbol": symbol, "commodity": commodity, "direction": direction,
            "entry": entry_v, "stop": stop_v, "tp1": tp1_v, "tp2": tp2_v, "tp3": tp3_v,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_alert_action": None,
        }
        _write(positions)
    return True, (
        f"MONITOR ATTIVO — {commodity} {direction}\n"
        f"Entry {entry_v:g} | SL {stop_v:g} | TP1 {tp1_v:g}"
        + (f" | TP2 {tp2_v:g}" if tp2_v is not None else "")
        + (f" | TP3 {tp3_v:g}" if tp3_v is not None else "")
        + "\nControllo ogni 15 minuti. Quotazioni Gagarin/provider, non Trading 212; "
          "solo avvisi, nessuna modifica o chiusura automatica."
    )


def remove_position(symbol: str) -> tuple[bool, str]:
    symbol = str(symbol or "").strip().upper()
    with _LOCK:
        positions = _read()
        if symbol not in positions:
            return False, f"Nessuna posizione monitorata per {symbol or 'simbolo vuoto'}."
        removed = positions.pop(symbol)
        _write(positions)
    return True, f"Monitor disattivato: {removed.get('commodity', symbol)} ({symbol})."


def list_positions() -> list[dict]:
    with _LOCK:
        return list(_read().values())


def _match_state(position: dict, states: Iterable[Any]) -> Any:
    symbol = str(position.get("symbol") or "").upper()
    commodity = str(position.get("commodity") or "").casefold()
    for state in states:
        if str(getattr(state, "symbol", "") or "").upper() == symbol:
            return state
    for state in states:
        if str(getattr(state, "commodity", "") or "").casefold() == commodity:
            return state
    return None


def evaluate_positions(states: Iterable[Any]) -> list[str]:
    """Evaluate positions and emit messages only on meaningful state transitions."""
    states = list(states or [])
    messages: list[str] = []
    with _LOCK:
        positions = _read()
        changed = False
        for symbol, position in positions.items():
            state = _match_state(position, states)
            if state is None or not bool(getattr(state, "live", False)):
                continue
            price = _positive(getattr(state, "price", None))
            age = getattr(state, "data_age_seconds", None)
            try:
                age = float(age)
            except (TypeError, ValueError):
                continue
            if price is None or not math.isfinite(age) or age < 0 or age > _MAX_QUOTE_AGE:
                continue
            result = analyze_pattern_and_exit(
                direction=position["direction"],
                opens=getattr(state, "opens", []),
                closes=getattr(state, "closes", []),
                highs=getattr(state, "highs", []),
                lows=getattr(state, "lows", []),
                entry=position["entry"], stop=position["stop"], tp1=position["tp1"],
                atr=getattr(state, "atr", None), current_price=price,
            )
            action = str(result.get("exit_action") or "HOLD")
            if action == "HOLD":
                if position.get("last_alert_action") is not None:
                    position["last_alert_action"] = None
                    changed = True
                continue
            if action == position.get("last_alert_action"):
                continue
            labels = {
                "EXIT_WARNING": "🔴 RISCHIO / POSSIBILE INVALIDAZIONE",
                "TIGHTEN_STOP": "🟠 ATTENZIONE / PROTEGGERE IL RISCHIO",
                "TAKE_PROFIT_WATCH": "💰 TP1 RAGGIUNTO — VALUTARE LA PRESA DI PROFITTO",
            }
            label = labels.get(action)
            if label is None:
                continue
            message = [
                f"GAGARIN — MONITOR POSIZIONE: {position['commodity']} {position['direction']}",
                label,
                f"Quotazione provider: {price:g} USD (dato vecchio di {age:.0f}s)",
                f"Entry: {position['entry']:g} | SL: {position['stop']:g} | TP1: {position['tp1']:g}",
                f"Candele: {result.get('candlestick_pattern', 'non valutabile')}",
                f"Struttura: {result.get('pattern', 'non valutabile')}",
                f"Inversione: {result.get('reversal_status', 'non valutabile')}",
                f"Motivo: {result.get('reason', 'rivalutare il setup')}",
                "Solo avviso: non viene inviato, modificato o chiuso alcun ordine. Prezzo provider, non Trading 212.",
            ]
            messages.append("\n".join(message))
            position["last_alert_action"] = action
            position["last_alert_at"] = datetime.now(timezone.utc).isoformat()
            changed = True
        if changed:
            _write(positions)
    return messages
