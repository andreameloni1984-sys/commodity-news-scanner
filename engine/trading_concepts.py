"""SOYUZ GAGARIN — VERIFIED TRADING CONCEPTS
Pure formulas. Missing data returns None. PAPER ONLY.
"""
from __future__ import annotations
from typing import Any

def _num(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def risk_distance(side: str, entry: Any, stop: Any) -> float | None:
    e, s = _num(entry), _num(stop)
    if e is None or s is None: return None
    side = str(side or "").upper()
    if side == "LONG" and s < e: return e - s
    if side == "SHORT" and s > e: return s - e
    return None

def reward_distance(side: str, entry: Any, target: Any) -> float | None:
    e, t = _num(entry), _num(target)
    if e is None or t is None: return None
    side = str(side or "").upper()
    if side == "LONG" and t > e: return t - e
    if side == "SHORT" and t < e: return e - t
    return None

def risk_reward(side: str, entry: Any, stop: Any, target: Any) -> float | None:
    risk, reward = risk_distance(side, entry, stop), reward_distance(side, entry, target)
    if risk is None or reward is None or risk <= 0: return None
    return round(reward / risk, 6)

def stop_distance_atr(side: str, entry: Any, stop: Any, atr: Any) -> float | None:
    risk, a = risk_distance(side, entry, stop), _num(atr)
    if risk is None or a is None or a <= 0: return None
    return round(risk / a, 6)

def break_even_win_rate(average_win_r: Any, average_loss_r: Any, cost_r: Any = 0.0) -> float | None:
    w, l, c = _num(average_win_r), _num(average_loss_r), _num(cost_r)
    if w is None or l is None or c is None or w <= 0 or l <= 0 or c < 0: return None
    return round((l + c) / (w + l), 6)

def net_expectancy(win_probability: Any, average_win_r: Any, average_loss_r: Any, cost_r: Any = 0.0) -> float | None:
    p, w, l, c = _num(win_probability), _num(average_win_r), _num(average_loss_r), _num(cost_r)
    if p is None or w is None or l is None or c is None or not 0 <= p <= 1 or w <= 0 or l <= 0 or c < 0: return None
    return round(p * w - (1.0 - p) * l - c, 6)

def spread_cost_r(spread: Any, stop_distance: Any) -> float | None:
    s, d = _num(spread), _num(stop_distance)
    if s is None or d is None or s < 0 or d <= 0: return None
    return round(s / d, 6)

def position_size_units(capital: Any, risk_fraction: Any, entry: Any, stop: Any, contract_value_per_price_unit: Any) -> float | None:
    cap, frac, e, s, cv = _num(capital), _num(risk_fraction), _num(entry), _num(stop), _num(contract_value_per_price_unit)
    if None in (cap, frac, e, s, cv) or cap <= 0 or not 0 < frac <= 1 or e == s or cv <= 0: return None
    return round((cap * frac) / (abs(e - s) * cv), 8)

def curve_basis_pct(spot: Any, futures: Any) -> float | None:
    s, f = _num(spot), _num(futures)
    if s is None or f is None or s <= 0: return None
    return round((f - s) / s * 100.0, 6)

def curve_state(basis_pct: Any, threshold_pct: Any = 0.10) -> str:
    b, t = _num(basis_pct), _num(threshold_pct)
    if b is None or t is None or t < 0: return "UNAVAILABLE"
    if b > t: return "CONTANGO"
    if b < -t: return "BACKWARDATION"
    return "FLAT"

def fair_value_deviation_pct(price: Any, fair_value: Any) -> float | None:
    p, fv = _num(price), _num(fair_value)
    if p is None or fv is None or fv == 0: return None
    return round((p - fv) / abs(fv) * 100.0, 6)
