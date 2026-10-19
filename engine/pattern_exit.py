"""Pattern, continuation, retracement and reversal heuristics for Gagarin.

Transparent OHLC heuristics for advisory alerts only; not a calibrated forecast.
Never opens, modifies, or closes orders.
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


def analyze_pattern_and_exit(
    *,
    direction: str,
    closes: Any,
    highs: Any = None,
    lows: Any = None,
    entry: Any = None,
    stop: Any = None,
    tp1: Any = None,
    atr: Any = None,
    current_price: Any = None,
) -> dict[str, Any]:
    """Analyze closed candles, but use a valid live quote for exit thresholds."""
    direction = str(direction or "").upper()
    close, high, low = _floats(closes), _floats(highs), _floats(lows)
    if direction not in {"LONG", "SHORT"} or len(close) < 5:
        return {
            "pattern": "DATI INSUFFICIENTI",
            "bias": "UNKNOWN",
            "exit_action": "HOLD",
            "retracement_status": "NON VALUTABILE",
            "retracement_atr": None,
            "reversal_status": "NON VALUTABILE",
            "reversal_score": 0,
            "reason": "Servono almeno 5 chiusure valide e direzione LONG/SHORT.",
            "data_points": len(close),
        }

    current_close = close[-1]
    momentum = (current_close / close[-4] - 1.0) * 100.0
    prev_momentum = (close[-2] / close[-5] - 1.0) * 100.0
    # Keep candle-pattern recognition based on closed OHLC data. A live quote
    # may update exit/retracement checks without pretending a candle has closed.
    reference_price = _positive(current_price)
    if reference_price is None:
        reference_price = current_close

    pattern = "MOMENTUM"
    bias = "BULLISH" if momentum > 0 else "BEARISH" if momentum < 0 else "NEUTRAL"
    hs, ls = high[-5:], low[-5:]
    lower_highs = higher_highs = lower_lows = higher_lows = False
    if len(hs) == 5 and len(ls) == 5:
        lower_highs = hs[-1] < hs[-2] < hs[-3]
        higher_highs = hs[-1] > hs[-2] > hs[-3]
        lower_lows = ls[-1] < ls[-2] < ls[-3]
        higher_lows = ls[-1] > ls[-2] > ls[-3]
        if higher_highs and higher_lows:
            pattern, bias = "HH/HL — TREND RIALZISTA", "BULLISH"
        elif lower_highs and lower_lows:
            pattern, bias = "LH/LL — TREND RIBASSISTA", "BEARISH"
        if current_close > max(hs[:-1]):
            pattern, bias = "BREAKOUT RIALZISTA", "BULLISH"
        elif current_close < min(ls[:-1]):
            pattern, bias = "BREAKOUT RIBASSISTA", "BEARISH"

    stop_v, tp_v, atr_v = (_positive(v) for v in (stop, tp1, atr))
    prior_closes = close[-5:-1]
    if atr_v is None:
        retracement_atr = None
        retracement_status = "NON VALUTABILE — ATR ASSENTE"
    else:
        if direction == "LONG":
            favorable_extreme = max(prior_closes)
            pullback = max(0.0, favorable_extreme - reference_price)
        else:
            favorable_extreme = min(prior_closes)
            pullback = max(0.0, reference_price - favorable_extreme)
        retracement_atr = pullback / atr_v
        if retracement_atr <= 0.5:
            retracement_status = "NESSUN RITRACCIAMENTO SIGNIFICATIVO"
        elif retracement_atr <= 1.0:
            retracement_status = "RITRACCIAMENTO NORMALE"
        elif retracement_atr <= 1.5:
            retracement_status = "RITRACCIAMENTO PROFONDO — RIVALUTARE"
        else:
            retracement_status = "RITRACCIAMENTO MOLTO AMPIO — RISCHIO INVALIDAZIONE"

    # Reversal scoring remains based on closed candles, not a transient quote.
    reversal_score = 0
    if direction == "LONG":
        reversal_score += int(momentum < 0)
        reversal_score += int(prev_momentum > 0 and momentum < prev_momentum)
        reversal_score += int(lower_highs)
        reversal_score += int(lower_lows)
        reversal_score += int(len(ls) == 5 and current_close < min(ls[:-1]))
        adverse = bias == "BEARISH"
    else:
        reversal_score += int(momentum > 0)
        reversal_score += int(prev_momentum < 0 and momentum > prev_momentum)
        reversal_score += int(higher_highs)
        reversal_score += int(higher_lows)
        reversal_score += int(len(hs) == 5 and current_close > max(hs[:-1]))
        adverse = bias == "BULLISH"

    if reversal_score >= 3:
        reversal_status = "POSSIBILE INVERSIONE — EVIDENZE MULTIPLE"
        pattern = "POSSIBILE INVERSIONE " + ("RIBASSISTA" if direction == "LONG" else "RIALZISTA")
    elif reversal_score == 2:
        reversal_status = "RISCHIO INVERSIONE IN AUMENTO"
    elif reversal_score == 1:
        reversal_status = "SEGNALI CONTRARI INIZIALI"
    else:
        reversal_status = "NESSUNA INVERSIONE RILEVATA"

    invalidated = (
        direction == "LONG" and stop_v is not None and reference_price <= stop_v
    ) or (
        direction == "SHORT" and stop_v is not None and reference_price >= stop_v
    )
    target_reached = (
        direction == "LONG" and tp_v is not None and reference_price >= tp_v
    ) or (
        direction == "SHORT" and tp_v is not None and reference_price <= tp_v
    )
    action = "HOLD"
    reason = "Struttura non invalidata; mantenimento da rivalutare a ogni nuova quotazione."
    if invalidated:
        action, reason = "EXIT_WARNING", (
            "Quotazione corrente al livello di stop o oltre: setup potenzialmente "
            "invalidato; verificare subito. L'esecuzione può differire dal livello."
        )
    elif target_reached:
        action, reason = "TAKE_PROFIT_WATCH", (
            "Quotazione corrente a TP1 o oltre: valutare presa profitto e protezione "
            "del residuo; il prezzo di esecuzione non è garantito."
        )
    elif reversal_score >= 3:
        action, reason = "EXIT_WARNING", (
            "Più segnali contrari concordanti su candele chiuse: possibile inversione, "
            "rivalutare/invalidare il setup."
        )
    elif retracement_atr is not None and retracement_atr > 1.5:
        action, reason = "EXIT_WARNING", (
            "Ritracciamento superiore a 1,5 ATR rispetto alla quotazione di riferimento: "
            "rischio elevato di deterioramento."
        )
    elif reversal_score == 2 or (retracement_atr is not None and retracement_atr > 1.0):
        action, reason = "TIGHTEN_STOP", (
            "Rischio di inversione o ritracciamento profondo: rivalutare e proteggere il rischio."
        )
    elif adverse:
        action, reason = "TIGHTEN_STOP", "Schema recente contrario: proteggere il rischio e rivalutare."

    return {
        "pattern": pattern,
        "bias": bias,
        "momentum_pct": round(momentum, 4),
        "previous_momentum_pct": round(prev_momentum, 4),
        "retracement_status": retracement_status,
        "retracement_atr": round(retracement_atr, 3) if retracement_atr is not None else None,
        "reversal_status": reversal_status,
        "reversal_score": reversal_score,
        "exit_action": action,
        "reason": reason,
        "data_points": len(close),
        "current_close": current_close,
        "reference_price": reference_price,
        "reference_price_source": "live_quote" if _positive(current_price) is not None else "last_closed_candle",
    }
