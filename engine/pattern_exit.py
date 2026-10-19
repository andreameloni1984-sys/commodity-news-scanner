"""Pattern recognition and exit-warning heuristics for Gagarin Telegram alerts.

Uses supplied OHLC data and current setup levels. Transparent heuristic only;
it is not a calibrated prediction and never places orders.
"""
from __future__ import annotations
from typing import Any


def _floats(values: Any) -> list[float]:
    try:
        result = [float(v) for v in (values or [])]
    except (TypeError, ValueError):
        return []
    return result if all(v > 0 for v in result) else []


def analyze_pattern_and_exit(*, direction: str, closes: Any, highs: Any = None,
                             lows: Any = None, entry: Any = None, stop: Any = None,
                             tp1: Any = None, atr: Any = None) -> dict[str, Any]:
    """Classify recent OHLC structure and return advisory exit action."""
    direction = str(direction or "").upper()
    close, high, low = _floats(closes), _floats(highs), _floats(lows)
    if direction not in {"LONG", "SHORT"} or len(close) < 5:
        return {"pattern": "DATI INSUFFICIENTI", "bias": "UNKNOWN",
                "exit_action": "HOLD",
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

    def pos(value: Any) -> float | None:
        try:
            number = float(value)
            return number if number > 0 else None
        except (TypeError, ValueError):
            return None
    entry_v, stop_v, tp_v, atr_v = (pos(v) for v in (entry, stop, tp1, atr))
    adverse = (direction == "LONG" and bias == "BEARISH") or (direction == "SHORT" and bias == "BULLISH")
    invalidated = (direction == "LONG" and stop_v is not None and current <= stop_v) or (direction == "SHORT" and stop_v is not None and current >= stop_v)
    target_reached = (direction == "LONG" and tp_v is not None and current >= tp_v) or (direction == "SHORT" and tp_v is not None and current <= tp_v)
    action, reason = "HOLD", "Nessun criterio di uscita rilevato."
    if invalidated:
        action, reason = "EXIT_WARNING", "Prezzo al livello di stop o oltre: verificare subito il setup."
    elif target_reached:
        action, reason = "TAKE_PROFIT_WATCH", "TP1 raggiunto/superato: valutare presa profitto e protezione del residuo."
    elif adverse and atr_v is not None and entry_v is not None and abs(current - entry_v) >= 0.75 * atr_v:
        action, reason = "EXIT_WARNING", "Struttura contraria e movimento avverso >= 0,75 ATR."
    elif adverse:
        action, reason = "TIGHTEN_STOP", "Schema recente contrario: proteggere il rischio e rivalutare."
    return {"pattern": pattern, "bias": bias, "momentum_pct": round(momentum, 4),
            "exit_action": action, "reason": reason, "data_points": len(close),
            "current_close": current}
