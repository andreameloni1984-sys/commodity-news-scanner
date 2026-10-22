"""Transparent, causal forecast ensemble for Gagarin (PAPER research only).

Combines trend/momentum, volatility regime, range breakout and reversal risk.
Scores are heuristic rankings, NOT calibrated probabilities. All calculations
use only the supplied candles; no external model or future data is accessed.
"""
from __future__ import annotations
from statistics import mean


def _clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, float(x)))


def forecast_ensemble(candles):
    rows = []
    for c in candles or []:
        try:
            o, h, l, close = (float(c[k]) for k in ("open", "high", "low", "close"))
            # Reject malformed OHLC bars: high/low must contain both open and close.
            if (min(o, h, l, close) <= 0 or h < l
                    or h < max(o, close) or l > min(o, close)):
                continue
            rows.append((o, h, l, close))
        except (KeyError, TypeError, ValueError):
            continue
    result = {
        "version": "causal-ensemble-1.0", "status": "INSUFFICIENT_DATA",
        "direction": "NONE", "score": 0.0, "regime": "UNKNOWN",
        "continuation_score": 0.0, "reversal_risk": 0.0,
        "features": {}, "caveat": "Heuristic score, not calibrated probability; PAPER only.",
    }
    if len(rows) < 35:
        return result
    closes = [r[3] for r in rows]
    trs = []
    for i, r in enumerate(rows):
        trs.append(max(r[1]-r[2], abs(r[1]-closes[i-1]) if i else 0,
                       abs(r[2]-closes[i-1]) if i else 0))
    atr_fast = mean(trs[-8:])
    atr_slow = mean(trs[-32:])
    if atr_fast <= 0 or atr_slow <= 0:
        return result
    vol_ratio = atr_fast / atr_slow
    returns = [(closes[i]/closes[i-1]-1) for i in range(1, len(closes)) if closes[i-1] > 0]
    mom4 = closes[-1]/closes[-5]-1
    mom12 = closes[-1]/closes[-13]-1
    mom32 = closes[-1]/closes[-33]-1
    prior = closes[-25:-1]
    upper, lower = max(prior), min(prior)
    price = closes[-1]
    breakout = "LONG" if price > upper else "SHORT" if price < lower else "NONE"
    # Normalize momentum by recent ATR as a percentage of price.
    atr_pct = atr_fast / price
    momentum = (0.45 * mom4 + 0.35 * mom12 + 0.20 * mom32) / max(atr_pct, 1e-9)
    direction = "LONG" if momentum > 0.15 else "SHORT" if momentum < -0.15 else "NONE"
    if breakout != "NONE" and (direction == "NONE" or breakout == direction):
        direction = breakout
    trend_strength = _clamp(abs(momentum) * 18)
    compression = _clamp((1-vol_ratio) * 100) if vol_ratio < 1 else 0
    expansion = _clamp((vol_ratio-1) * 70) if vol_ratio > 1 else 0
    vol_values = returns[-32:]
    mean_abs = mean(abs(x) for x in vol_values) if vol_values else 0
    shock = abs(returns[-1]) / max(mean_abs, 1e-9) if returns else 0
    reversal = _clamp(max(0, shock-1.5)*22 + max(0, vol_ratio-1.4)*25)
    breakout_score = 75.0 if breakout != "NONE" else 0.0
    score = _clamp(0.55*trend_strength + 0.25*max(compression, expansion) + 0.20*breakout_score)
    if direction == "NONE":
        score *= 0.65
    regime = "HIGH_VOLATILITY" if vol_ratio >= 1.5 or shock >= 3 else (
        "VOLATILITY_COMPRESSION" if vol_ratio <= 0.75 else (
        "TREND" if trend_strength >= 45 else "RANGE_OR_TRANSITION"))
    result.update({
        "status": "CALCULATED", "direction": direction, "score": round(score, 2),
        "regime": regime, "continuation_score": round(_clamp(trend_strength*(1-reversal/150)), 2),
        "reversal_risk": round(reversal, 2),
        "features": {
            "momentum_4bar_pct": round(mom4*100, 5),
            "momentum_12bar_pct": round(mom12*100, 5),
            "momentum_32bar_pct": round(mom32*100, 5),
            "atr_fast_slow_ratio": round(vol_ratio, 4),
            "compression_score": round(compression, 2),
            "expansion_score": round(expansion, 2),
            "breakout": breakout, "trend_strength": round(trend_strength, 2),
            "last_return_shock": round(shock, 3),
        },
    })
    return result
