"""SOYUZ GAGARIN — engine/weekly_trend.py

Weekly trend filter for commodity entries.

Research (Kurth, Eisler, Rej, Bouchaud 2026; CTA literature):
- momentum on small-tick contracts (indices, FX) died after 2008
- momentum on large-tick contracts (many commodities) survives, but
  only at weekly horizons, not intraday
- the 5-minute trigger engine stays as the execution trigger;
  this module decides the SIDE and whether a side is allowed

Rule (frozen, no parameters fitted on the same data):
- compute the net move over the last N weekly bars (default 8)
- LONG allowed only if net move > +MIN_MOVE_ATR * ATR(weekly)
- SHORT allowed only if net move < -MIN_MOVE_ATR * ATR(weekly)
- otherwise the side is blocked with WEEKLY_TREND_BLOCK

This is a filter, not a signal. It does not create entries.
It does not touch the intraday pipeline.
"""

from __future__ import annotations

from engine.state import SoyuzState


# ============================================================
# FROZEN PARAMETERS
# ============================================================

LOOKBACK_WEEKS = 8          # net move window on weekly bars
MIN_MOVE_ATR = 0.5         # minimum net move in weekly ATR
MIN_BARS = 6               # minimum weekly bars required
ATR_PERIOD = 14            # weekly ATR period


# ============================================================
# HELPERS
# ============================================================


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _weekly_bars(state: SoyuzState) -> list:
    """Build weekly OHLC bars from the M5 series.

    Each bar: dict with open/high/low/close/timestamp (epoch, UTC).
    Weeks are Monday 00:00 UTC anchored.
    """
    closes = state.closes or []
    highs = state.highs or []
    lows = state.lows or []
    timestamps = state.timestamps or []

    if not (len(closes) == len(highs) == len(lows) == len(timestamps)):
        return []

    bars = []
    for ts, o_src, h, l, c in zip(timestamps, closes, highs, lows, closes):
        t = _safe_float(ts)
        if t is None:
            continue
        # Monday 00:00 UTC anchor
        week_start = t - ((t + 3 * 86400) % (7 * 86400))
        o = _safe_float(o_src)
        hh = _safe_float(h)
        ll = _safe_float(l)
        cc = _safe_float(c)
        if None in (o, hh, ll, cc) or min(o, hh, ll, cc) <= 0:
            continue
        if hh < ll or hh < max(o, cc) or ll > min(o, cc):
            continue
        if bars and bars[-1]["week_start"] == week_start:
            b = bars[-1]
            b["high"] = max(b["high"], hh)
            b["low"] = min(b["low"], ll)
            b["close"] = cc
            b["timestamp"] = t
        else:
            bars.append({
                "week_start": week_start,
                "open": o,
                "high": hh,
                "low": ll,
                "close": cc,
                "timestamp": t,
            })
    return bars


def _weekly_atr(bars: list, period: int = ATR_PERIOD) -> float | None:
    """Wilder ATR on weekly bars."""
    if len(bars) < period + 1:
        return None
    trs = []
    for i in range(1, len(bars)):
        prev_close = bars[i - 1]["close"]
        tr = max(
            bars[i]["high"] - bars[i]["low"],
            abs(bars[i]["high"] - prev_close),
            abs(bars[i]["low"] - prev_close),
        )
        trs.append(tr)
    if len(trs) < period:
        return None
    atr = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr = (atr * (period - 1) + tr) / period
    return atr


def _net_move_atr(bars: list, atr: float) -> tuple[float | None, str]:
    if atr is None or atr <= 0 or len(bars) < 2:
        return None, "NONE"
    window = bars[-LOOKBACK_WEEKS:] if len(bars) >= LOOKBACK_WEEKS else bars
    if len(window) < MIN_BARS:
        return None, "NONE"
    net = window[-1]["close"] - window[0]["open"]
    norm = net / atr
    if norm > MIN_MOVE_ATR:
        return norm, "LONG"
    if norm < -MIN_MOVE_ATR:
        return norm, "SHORT"
    return norm, "NONE"


# ============================================================
# MAIN
# ============================================================


def apply_weekly_trend(state: SoyuzState) -> SoyuzState:
    """Attach weekly trend evidence to the canonical state.

    Sets:
      state.metadata["weekly_trend"] = {
        "status": CALCULATED | INSUFFICIENT_DATA | NO_DATA,
        "net_move_atr": float | None,
        "direction": LONG | SHORT | NONE,
        "lookback_weeks": int,
        "atr": float | None,
        "bars": int,
      }

    Does NOT modify setup, trigger, risk, safety or final_decision.
    The side filter is applied by safety (gate 21) so the journal
    records the blocker explicitly.
    """
    meta = getattr(state, "metadata", None)
    if not isinstance(meta, dict):
        meta = {}
        state.metadata = meta

    bars = _weekly_bars(state)
    atr = _weekly_atr(bars)
    norm, direction = _net_move_atr(bars, atr)

    if not bars:
        status = "NO_DATA"
    elif len(bars) < MIN_BARS or atr is None:
        status = "INSUFFICIENT_DATA"
    else:
        status = "CALCULATED"

    meta["weekly_trend"] = {
        "status": status,
        "net_move_atr": round(norm, 4) if norm is not None else None,
        "direction": direction,
        "lookback_weeks": LOOKBACK_WEEKS,
        "min_move_atr": MIN_MOVE_ATR,
        "atr": round(atr, 6) if atr is not None else None,
        "bars": len(bars),
    }
    return state


def weekly_side_allowed(state: SoyuzState, side: str) -> bool:
    """True if the weekly trend permits this side.

    Fail-closed: insufficient data blocks the side.
    """
    meta = getattr(state, "metadata", {}) or {}
    wt = meta.get("weekly_trend", {})
    if not isinstance(wt, dict):
        return False
    if wt.get("status") != "CALCULATED":
        return False
    direction = wt.get("direction", "NONE")
    return direction == side
