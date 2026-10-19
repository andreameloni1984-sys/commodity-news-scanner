"""Pattern recognition, retracement tracking and exit-warning heuristics.

Transparent OHLC heuristics for advisory Telegram alerts only. Not calibrated
prediction; never opens, modifies, or closes orders.
"""
from __future__ import annotations
from typing import Any


def _floats(values: Any) -> list[float]:
    try:
        result = [float(v) for v in (values or [])]
    except (TypeError, ValueError):
        return []
    return result if all(v > 0 for v in result) else []


def _positive(value: Any) -> float | None:
    try:
        number = float(value)
        return number if number > 0 else None
    except (TypeError, ValueError):
        return None


def analyze_pattern_and_exit(*, direction: str, closes: Any, highs: Any = None,
                             lows: Any = None, entry: Any = None, stop: Any = None,
                             tp1: Any = None, atr: Any = None) -> dict[str, Any]:
    """Classify recent structure, pullback depth, and advisory exit state."""
    direction = str(direction or "").upper()
    close, high, low = _floats(closes), _floats(highs), _floats(lows)
    if direction not in {"LONG", "SHORT"} or len(close) < 5:
        return {"pattern": "DATI INSUFFICIENTI", "bias": "UNKNOWN",
                "exit_action": "HOLD", "retracement_status": "NON VALUTABILE",
                "retracement_atr": None,
                "reason": "Servono almeno 5 chiusure valide e direzione LONG/SHORT.",
                "data_points": len(close)}

    current, prior, older = close[-1], close[-2], close[-3]
    momentum = (current / close[-4] - 1.0) * 100.0
    spread = (max(close[-5:]) - min(close[-5:])) / current * 100.0
    pattern = "MOMENTUM"
    bias = "BULLISH" if momentum > 0 else "BEARISH" if momentum < 0 else "NEUTRAL"
    hs, ls = high[-5:], low[-5:]
    if len(hs) == 5 and len(ls) == 5:
        if hs[-1] > hs[-2] > hs[-3] and ls[-1] > ls[-2] > ls[-3]:
            pattern, bias = "HH/HL — TREND RIALZISTA", "BULLISH"
        elif hs[-1] < hs[-2] < hs[-3] and ls[-1] < ls[-2] < ls[-3]:
            pattern, bias = "LH/LL — TREND RIBASSISTA", "BEARISH"
        if current > max(hs[:-1]):
            pattern, bias = "BREAKOUT RIALZISTA", "BULLISH"
        elif current < min(ls[:-1]):
            pattern, bias = "BREAKOUT RIBASSISTA", "BEARISH"
    if current < prior and prior > older and momentum < 0:
        pattern, bias = "POSSIBILE INVERSIONE RIBASSISTA", "BEARISH"
    elif current > prior and prior < older and momentum > 0:
        pattern, bias = "POSSIBILE INVERSIONE RIALZISTA", "BULLISH"
    elif spread < 0.15:
        pattern = "COMPRESSIONE / POSSIBILE BREAKOUT"

    entry_v, stop_v, tp_v, atr_v = (_positive(v) for v in (entry, stop, tp1, atr))
    # Measure pullback from the recent favorable extreme, using only completed
    # prior closes in the supplied sample. It is a diagnostic, not a forecast.
    prior_closes = close[-5:-1]
    if atr_v is None:
        retracement_atr = None
        retracement_status = "NON VALUTABILE — ATR ASSENTE"
    else:
        if direction == "LONG":
            favorable_extreme = max(prior_closes)
            pullback = max(0.0, favorable_extreme - current)
        else:
            favorable_extreme = min(prior_closes)
            pullback = max(0.0, current - favorable_extreme)
        retracement_atr = pullback / atr_v
        if retracement_atr <= 0.5:
            retracement_status = "NESSUN RITRACCIAMENTO SIGNIFICATIVO"
        elif retracement_atr <= 1.0:
            retracement_status = "RITRACCIAMENTO NORMALE"
        elif retracement_atr <= 1.5:
            retracement_status = "RITRACCIAMENTO PROFONDO — RIVALUTARE"
        else:
            retracement_status = "RITRACCIAMENTO MOLTO AMPIO — RISCHIO INVALIDAZIONE"

    adverse = (direction == "LONG" and bias == "BEARISH") or (direction == "SHORT" and bias == "BULLISH")
    invalidated = (direction == "LONG" and stop_v is not None and current <= stop_v) or (direction == "SHORT" and stop_v is not None and current >= stop_v)
    target_reached = (direction == "LONG" and tp_v is not None and current >= tp_v) or (direction == "SHORT" and tp_v is not None and current <= tp_v)
    action, reason = "HOLD", "Nessun criterio di uscita rilevato."
    if invalidated:
        action, reason = "EXIT_WARNING", "Prezzo al livello di stop o oltre: setup da considerare invalidato e da verificare."
    elif target_reached:
        action, reason = "TAKE_PROFIT_WATCH", "TP1 raggiunto/superato: valutare presa profitto e protezione del residuo."
    elif retracement_atr is not None and retracement_atr > 1.5:
        action, reason = "EXIT_WARNING", "Ritracciamento superiore a 1,5 ATR: rischio elevato di deterioramento."
    elif adverse and atr_v is not None and entry_v is not None and abs(current - entry_v) >= 0.75 * atr_v:
        action, reason = "EXIT_WARNING", "Struttura contraria e movimento avverso >= 0,75 ATR."
    elif retracement_atr is not None and retracement_atr > 1.0:
        action, reason = "TIGHTEN_STOP", "Ritracciamento profondo: rivalutare la struttura e proteggere il rischio."
    elif adverse:
        action, reason = "TIGHTEN_STOP", "Schema recente contrario: proteggere il rischio e rivalutare."
    return {"pattern": pattern, "bias": bias, "momentum_pct": round(momentum, 4),
            "retracement_status": retracement_status,
            "retracement_atr": round(retracement_atr, 3) if retracement_atr is not None else None,
            "exit_action": action, "reason": reason, "data_points": len(close),
            "current_close": current}
