"""LUBJANKA conditional trade plan from completed M5 OHLCV bars."""
from __future__ import annotations
import math
import time
from typing import Any

def build_conditional_playbook(candles: Any, interception: dict, *, now_epoch: float | None = None) -> dict:
    now = time.time() if now_epoch is None else float(now_epoch)
    if not isinstance(interception, dict) or interception.get("status") != "INTERCEPTED":
        return {"status": "UNAVAILABLE", "reason": "nessuna intercettazione LUBJANKA valida", "paper_only": True}
    direction = str(interception.get("direction") or "").upper()
    if direction not in {"LONG", "SHORT"}:
        return {"status": "NO_PLAN", "reason": "direzione assente", "paper_only": True}
    if not isinstance(candles, (list, tuple)):
        return {"status": "UNAVAILABLE", "reason": "candele non disponibili", "paper_only": True}
    bars = []
    for bar in candles:
        if not isinstance(bar, dict):
            continue
        try:
            ts = float(bar.get("timestamp"))
            high, low, close = (float(bar[k]) for k in ("high", "low", "close"))
        except (TypeError, ValueError, OverflowError):
            continue
        if all(math.isfinite(v) for v in (ts, high, low, close)) and ts + 300 <= now + 1:
            bars.append({"timestamp": ts, "high": high, "low": low, "close": close})
    if len(bars) < 8:
        return {"status": "UNAVAILABLE", "reason": "meno di 8 candele M5 chiuse", "paper_only": True}
    latest = bars[-1]
    age = now - latest["timestamp"]
    if age < 0 or age > 600:
        return {"status": "UNAVAILABLE", "reason": "ultima candela M5 non fresca", "bar_age_seconds": round(age, 1), "paper_only": True}
    ranges = []
    for previous, current in zip(bars[-15:-1], bars[-14:]):
        ranges.append(max(current["high"] - current["low"], abs(current["high"] - previous["close"]), abs(current["low"] - previous["close"])))
    atr = sum(ranges) / len(ranges) if ranges else 0.0
    if not math.isfinite(atr) or atr <= 0:
        return {"status": "UNAVAILABLE", "reason": "ATR M5 non calcolabile", "paper_only": True}
    if direction == "SHORT":
        entry = latest["low"] - atr * 0.05
        stop = latest["high"] + atr * 0.15
        risk = stop - entry
        tp1, tp2 = entry - 1.5 * risk, entry - 2.5 * risk
        activation = f"candela M5 chiusa sotto {entry:.8g}"
        invalidation = f"superamento di {stop:.8g} prima dell'attivazione"
    else:
        entry = latest["high"] + atr * 0.05
        stop = latest["low"] - atr * 0.15
        risk = entry - stop
        tp1, tp2 = entry + 1.5 * risk, entry + 2.5 * risk
        activation = f"candela M5 chiusa sopra {entry:.8g}"
        invalidation = f"rottura di {stop:.8g} prima dell'attivazione"
    if risk <= 0 or not all(math.isfinite(v) for v in (entry, stop, tp1, tp2)):
        return {"status": "UNAVAILABLE", "reason": "geometria rischio non valida", "paper_only": True}
    return {
        "status": "CONDITIONAL_PLAN", "direction": direction,
        "directional_conflict": bool(interception.get("directional_conflict")),
        "directions_detected": interception.get("directions_detected", [direction]),
        "interceptor": interception.get("primary_interceptor", "LUBJANKA"),
        "timeframe": "M5", "reference_close": latest["close"],
        "entry_trigger": round(entry, 8), "stop_loss": round(stop, 8),
        "take_profit_1": round(tp1, 8), "take_profit_2": round(tp2, 8),
        "risk_distance": round(risk, 8), "rr_tp1": 1.5, "rr_tp2": 2.5,
        "activation": activation, "invalidation": invalidation,
        "bar_age_seconds": round(age, 1), "atr_m5": round(atr, 8),
        "execution_status": "NOT_EXECUTED", "paper_only": True,
        "note": ("CONFLITTO TRA INTERCETTORI: direzione primaria mostrata come ipotesi. " if interception.get("directional_conflict") else "") + "Piano condizionale OHLCV M5; non e un ordine e non sostituisce il Governor."
    }
