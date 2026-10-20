"""SOYUZ GAGARIN — EXECUTION ECONOMICS.

Pure, deterministic formulas for execution quality and risk economics.
No market data is fabricated: missing or inconsistent inputs return None.

This module is observational. It does not decide ENTRY and never places orders.
"""

from __future__ import annotations

from typing import Any


def _num(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None


def spread(bid: Any, ask: Any) -> float | None:
    b, a = _num(bid), _num(ask)
    if b is None or a is None or b <= 0 or a <= 0 or a < b:
        return None
    return a - b


def spread_bps(bid: Any, ask: Any) -> float | None:
    b, a = _num(bid), _num(ask)
    s = spread(b, a)
    if b is None or a is None or s is None:
        return None
    mid = (a + b) / 2.0
    return round((s / mid) * 10_000.0, 6) if mid > 0 else None


def executable_price(side: str, bid: Any, ask: Any) -> float | None:
    """Return the observable quote used to enter a market order."""
    s = str(side or "").upper()
    b, a = _num(bid), _num(ask)
    if b is None or a is None or b <= 0 or a <= 0 or a < b:
        return None
    if s == "LONG":
        return a
    if s == "SHORT":
        return b
    return None


def risk_distance(entry: Any, stop: Any) -> float | None:
    e, s = _num(entry), _num(stop)
    if e is None or s is None or e <= 0 or s <= 0:
        return None
    distance = abs(e - s)
    return distance if distance > 0 else None


def reward_distance(side: str, entry: Any, target: Any) -> float | None:
    e, t = _num(entry), _num(target)
    if e is None or t is None or e <= 0 or t <= 0:
        return None
    s = str(side or "").upper()
    reward = t - e if s == "LONG" else e - t if s == "SHORT" else None
    return reward if reward is not None and reward > 0 else None


def rr_from_prices(side: str, entry: Any, stop: Any, target: Any) -> float | None:
    risk = risk_distance(entry, stop)
    reward = reward_distance(side, entry, target)
    if risk is None or reward is None:
        return None
    return round(reward / risk, 6)


def breakeven_win_rate(average_win_r: Any, average_loss_r: Any = 1.0) -> float | None:
    win, loss = _num(average_win_r), _num(average_loss_r)
    if win is None or loss is None or win <= 0 or loss <= 0:
        return None
    return round(loss / (win + loss), 6)


def expectancy_net_r(
    win_probability: Any,
    average_win_r: Any,
    average_loss_r: Any,
    cost_r: Any = 0.0,
) -> float | None:
    p, win, loss, cost = (
        _num(win_probability),
        _num(average_win_r),
        _num(average_loss_r),
        _num(cost_r),
    )
    if p is None or win is None or loss is None or cost is None:
        return None
    if p > 1.0:
        p /= 100.0
    if not 0.0 <= p <= 1.0 or win <= 0 or loss <= 0 or cost < 0:
        return None
    return round(p * win - (1.0 - p) * loss - cost, 6)


def cost_r(cost_price: Any, entry: Any, stop: Any) -> float | None:
    cost, e, s = _num(cost_price), _num(entry), _num(stop)
    risk = risk_distance(e, s)
    if cost is None or risk is None or cost < 0:
        return None
    return round(cost / risk, 6)


def position_size(
    equity: Any,
    risk_fraction: Any,
    entry: Any,
    stop: Any,
    contract_multiplier: Any = 1.0,
) -> float | None:
    """Units/contracts from explicit account and contract economics."""
    eq, frac, mult = _num(equity), _num(risk_fraction), _num(contract_multiplier)
    risk = risk_distance(entry, stop)
    if eq is None or frac is None or mult is None or risk is None:
        return None
    if eq <= 0 or frac <= 0 or frac > 1 or mult <= 0:
        return None
    return round((eq * frac) / (risk * mult), 8)


def basis(futures_price: Any, spot_price: Any) -> float | None:
    f, s = _num(futures_price), _num(spot_price)
    if f is None or s is None or f <= 0 or s <= 0:
        return None
    return round(f - s, 8)


def basis_percent(futures_price: Any, spot_price: Any) -> float | None:
    f, s = _num(futures_price), _num(spot_price)
    if f is None or s is None or f <= 0 or s <= 0:
        return None
    return round(((f - s) / s) * 100.0, 8)


def curve_state(near_price: Any, deferred_price: Any) -> str | None:
    near, deferred = _num(near_price), _num(deferred_price)
    if near is None or deferred is None or near <= 0 or deferred <= 0:
        return None
    if deferred > near:
        return "CONTANGO"
    if deferred < near:
        return "BACKWARDATION"
    return "FLAT"
