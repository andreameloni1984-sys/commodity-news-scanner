"""Deterministic, no-lookahead market-structure features for Gagarin.

Input candles are chronological mappings with high/low/close numeric fields.
A pivot is only available after right_bars candles have closed; this avoids
using future candles as if they were known in real time. This module describes
structure; it does not independently authorize trades.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence


def _num(candle: Mapping[str, Any], key: str) -> float | None:
    try:
        value = float(candle[key])
    except (KeyError, TypeError, ValueError):
        return None
    return value if value == value and abs(value) != float("inf") else None


def confirmed_swings(candles: Sequence[Mapping[str, Any]], left_bars: int = 2,
                     right_bars: int = 2) -> dict[str, list[tuple[int, float]]]:
    """Return confirmed (index, price) swing highs/lows, chronological."""
    if left_bars < 1 or right_bars < 1:
        raise ValueError("left_bars and right_bars must be >= 1")
    highs: list[tuple[int, float]] = []
    lows: list[tuple[int, float]] = []
    for i in range(left_bars, len(candles) - right_bars):
        high = _num(candles[i], "high")
        low = _num(candles[i], "low")
        neighborhood = candles[i-left_bars:i] + candles[i+1:i+right_bars+1]
        nh = [_num(c, "high") for c in neighborhood]
        nl = [_num(c, "low") for c in neighborhood]
        if high is not None and all(v is not None for v in nh) and high > max(nh):
            highs.append((i, high))
        if low is not None and all(v is not None for v in nl) and low < min(nl):
            lows.append((i, low))
    return {"highs": highs, "lows": lows}


def analyze_market_structure(candles: Sequence[Mapping[str, Any]], *,
                             left_bars: int = 2, right_bars: int = 2,
                             min_swings: int = 2) -> dict[str, Any]:
    """Classify structure as BULLISH, BEARISH, RANGE, TRANSITION or INSUFFICIENT.

    Direction is based on the last two confirmed swing highs AND lows. A
    one-sided break is treated as TRANSITION, not a confirmed reversal.
    """
    swings = confirmed_swings(candles, left_bars, right_bars)
    highs, lows = swings["highs"], swings["lows"]
    result: dict[str, Any] = {
        "direction": "INSUFFICIENT",
        "confidence": "LOW",
        "swing_highs": highs[-2:],
        "swing_lows": lows[-2:],
        "last_close": _num(candles[-1], "close") if candles else None,
        "reasons": [],\n        "no_trade_bias": True,
    }
    if len(highs) < min_swings or len(lows) < min_swings:
        result["reasons"].append("Non ci sono abbastanza swing confermati.")
        return result

    hh = highs[-1][1] > highs[-2][1]
    lh = highs[-1][1] < highs[-2][1]
    hl = lows[-1][1] > lows[-2][1]
    ll = lows[-1][1] < lows[-2][1]
    if hh and hl:
        result.update(direction="BULLISH", confidence="MEDIUM")
        result["reasons"].append("Ultimi massimi e minimi confermati crescenti (HH + HL).")
    elif lh and ll:
        result.update(direction="BEARISH", confidence="MEDIUM")
        result["reasons"].append("Ultimi massimi e minimi confermati decrescenti (LH + LL).")
    elif (hh and ll) or (lh and hl):
        result.update(direction="TRANSITION", confidence="LOW")
        result["reasons"].append("Massimi e minimi discordanti: possibile transizione.")
    else:
        result.update(direction="RANGE", confidence="LOW")
        result["reasons"].append("Sequenza non direzionale: possibile mercato laterale.")

    last_close = result["last_close"]
    last_high = highs[-1][1]
    last_low = lows[-1][1]
    if last_close is not None and last_close > last_high:
        result["breakout"] = "ABOVE_LAST_SWING_HIGH"
    elif last_close is not None and last_close < last_low:
        result["breakout"] = "BELOW_LAST_SWING_LOW"
    else:
        result["breakout"] = "NONE"
    if result["breakout"] != "NONE":
        result["reasons"].append(
            "Prezzo oltre l'ultimo swing: richiede conferma; non equivale da solo a un ingresso."
        )
    result["no_trade_bias"] = result["direction"] in {"RANGE", "TRANSITION", "INSUFFICIENT"}
    return result


def breakout_reclaimed(previous_closes: Sequence[float], level: float, *,
                       direction: str) -> bool:
    """Flag a potential failed breakout when price closes back through a level.

    previous_closes should contain the latest two or more CLOSED candle closes.
    direction='UP' means a breakout above resistance; 'DOWN' below support.
    """
    if len(previous_closes) < 2:
        return False
    a, b = float(previous_closes[-2]), float(previous_closes[-1])
    level = float(level)
    if direction.upper() == "UP":
        return a > level and b <= level
    if direction.upper() == "DOWN":
        return a < level and b >= level
    raise ValueError("direction must be 'UP' or 'DOWN'")
