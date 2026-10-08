"""SOYUZ GAGARIN — engine/weekly_trend.py

Weekly trend rule (v1.0).

Research basis: Kurth, Eisler, Rej, Bouchaud (2026) — trend-following
Sharpe survives only on large-tick contracts (many commodities) and only
at horizons of weeks, not days. Intraday momentum is dead post-2008.

This module does NOT create entries. It classifies the weekly regime
and writes it into the canonical state so that:
- the scanner can rank commodities by weekly trend
- a future weekly trigger can require this regime
- safety can block entries against the weekly trend

Timeframe: daily bars (Yahoo futures GC=F, CL=F, ...).
Lookback: 20 trading days (~1 month).
"""

from __future__ import annotations

from typing import Optional

from engine.state import SoyuzState


# ============================================================
# PARAMETERS
# ============================================================

LOOKBACK_DAYS = 20          # ~1 month of daily bars
MIN_BARS = 15              # minimum bars to classify
SLOPE_ATR_MIN = 0.5        # |net move| / ATR over lookback
SLOPE_ATR_STRONG = 1.0     # strong weekly trend threshold
ATR_PERIOD = 14            # ATR on daily bars


# ============================================================
# HELPERS
# ============================================================

def _safe_float(value) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _daily_closes(state: SoyuzState) -> list:
    """Prefer explicit daily series; fall back to MTF 1h if present."""
    daily = state.metadata.get("daily_closes")
    if isinstance(daily, list) and len(daily) >= MIN_BARS:
        return daily
    mtf = state.mtf_data or {}
    h1 = mtf.get("1h", [])
    if isinstance(h1, list) and len(h1) >= MIN_BARS * 6:
        # compress 1h bars into pseudo-daily closes (last close per day)
        by_day = {}
        for bar in h1:
            if not isinstance(bar, dict):
                continue
            ts = bar.get("timestamp")
            try:
                ts = float(ts)
            except (TypeError, ValueError):
                continue
            day = int(ts // 86400)
            by_day[day] = _safe_float(bar.get("close"))
        return [v for _, v in sorted(by_day.items()) if v is not None]
    return []


def _atr_daily(closes: list) -> Optional[float]:
    """Simple ATR proxy on daily closes: mean of |close-to-close| moves."""
    if len(closes) < ATR_PERIOD + 1:
        return None
    moves = [abs(closes[i] - closes[i - 1]) for i in range(1, len(closes))]
    window = moves[-ATR_PERIOD:]
    if not window:
        return None
    return sum(window) / len(window)


# ============================================================
# MAIN
# ============================================================

def apply_weekly_trend(state: SoyuzState) -> SoyuzState:
    """Classify the weekly trend and store it on the canonical state.

    Writes:
        state.metadata["weekly_trend"] = {
            "direction": "LONG" | "SHORT" | "NONE",
            "slope_atr": float,
            "strength": "STRONG" | "MODERATE" | "NONE",
            "bars": int,
            "status": str,
        }

    Does not touch setup, trigger, risk or safety.
    """
    closes = _daily_closes(state)

    diag = {
        "status": "INSUFFICIENT_DATA",
        "direction": "NONE",
        "slope_atr": None,
        "strength": "NONE",
        "bars": len(closes),
        "lookback_days": LOOKBACK_DAYS,
        "slope_atr_min": SLOPE_ATR_MIN,
        "slope_atr_strong": SLOPE_ATR_STRONG,
    }
    state.metadata["weekly_trend"] = diag

    if len(closes) < MIN_BARS:
        return state

    atr = _atr_daily(closes)
    if atr is None or atr <= 0:
        diag["status"] = "ATR_UNAVAILABLE"
        return state

    lookback = min(LOOKBACK_DAYS, len(closes))
    recent = closes[-lookback:]
    net = recent[-1] - recent[0]
    slope_atr = net / atr

    diag["slope_atr"] = round(slope_atr, 3)
    diag["bars"] = len(closes)

    if abs(slope_atr) < SLOPE_ATR_MIN:
        diag["status"] = "NO_TREND"
        diag["direction"] = "NONE"
        diag["strength"] = "NONE"
        return state

    direction = "LONG" if slope_atr > 0 else "SHORT"
    strength = "STRONG" if abs(slope_atr) >= SLOPE_ATR_STRONG else "MODERATE"

    diag["status"] = "CALCULATED"
    diag["direction"] = direction
    diag["strength"] = strength
    return state


def weekly_trend_blocks_entry(state: SoyuzState) -> Optional[str]:
    """Return a blocker string if the weekly trend opposes the setup.

    Used by safety as an optional gate. Fail-open when weekly data
    is missing: a missing weekly trend must not block entries.
    """
    wt = state.metadata.get("weekly_trend") or {}
    direction = wt.get("direction")
    if direction not in {"LONG", "SHORT"}:
        return None
    if state.setup_direction not in {"LONG", "SHORT"}:
        return None
    if direction != state.setup_direction:
        return "WEEKLY_TREND_MISMATCH"
    return None
