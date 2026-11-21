"""Indicatori tecnici in puro Python (nessuna dipendenza da numpy/pandas)."""
from __future__ import annotations


def sma(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def ema_series(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    k = 2 / (period + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def rsi(values: list[float], period: int = 14) -> float | None:
    """RSI di Wilder."""
    if len(values) <= period:
        return None
    gains = losses = 0.0
    for i in range(1, period + 1):
        d = values[i] - values[i - 1]
        gains += max(d, 0)
        losses += max(-d, 0)
    avg_g, avg_l = gains / period, losses / period
    for i in range(period + 1, len(values)):
        d = values[i] - values[i - 1]
        avg_g = (avg_g * (period - 1) + max(d, 0)) / period
        avg_l = (avg_l * (period - 1) + max(-d, 0)) / period
    if avg_l == 0:
        return 100.0
    return 100 - 100 / (1 + avg_g / avg_l)


def macd(values: list[float], fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[float, float, float] | None:
    if len(values) < slow + signal:
        return None
    fast_e, slow_e = ema_series(values, fast), ema_series(values, slow)
    line = [f - s for f, s in zip(fast_e, slow_e)]
    sig = ema_series(line, signal)
    return line[-1], sig[-1], line[-1] - sig[-1]


def atr(high: list[float], low: list[float], close: list[float], period: int = 14) -> float | None:
    if len(close) <= period:
        return None
    trs = [
        max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
        for i in range(1, len(close))
    ]
    value = sum(trs[:period]) / period
    for tr in trs[period:]:
        value = (value * (period - 1) + tr) / period
    return value


def pct_return(values: list[float], lookback: int) -> float | None:
    if len(values) <= lookback or values[-lookback - 1] == 0:
        return None
    return values[-1] / values[-lookback - 1] - 1


def donchian(high: list[float], low: list[float], period: int) -> tuple[float, float] | None:
    """Massimo/minimo delle `period` barre precedenti (esclusa l'ultima)."""
    if len(high) <= period:
        return None
    return max(high[-period - 1:-1]), min(low[-period - 1:-1])


def realized_vol(values: list[float], period: int = 20) -> float | None:
    """Volatilità annualizzata dei rendimenti giornalieri."""
    if len(values) <= period:
        return None
    rets = [values[i] / values[i - 1] - 1 for i in range(len(values) - period, len(values))]
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    return (var ** 0.5) * (252 ** 0.5)
