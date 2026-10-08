"""SOYUZ — engine/paper_journal.py

Applica le misure di signal_outcome alla regola a 20 giorni.
Solo chiusure: high e low non ci sono, quindi MFE e MAE sono
sottostimati. Non tarare stop o take profit su questo file.
"""

from __future__ import annotations

import statistics

from engine.signal_outcome import measure_outcome
from engine.weekly_trend import LOOKBACK, SLOPE_MIN, weekly_trend

HOLD_CAP = 20
ROUND_TRIP_BPS = 8


def _atr(closes: list[float], end: int, period: int = 14) -> float:
    moves = [abs(closes[j] - closes[j - 1]) for j in range(end - period + 1, end + 1)]
    return sum(moves) / len(moves)


def journal(closes: list[float], dates: list[str] | None = None) -> dict:
    trades = []
    i = LOOKBACK
    while i < len(closes) - 1:
        signal = weekly_trend(closes[: i + 1])
        if signal.get("direction") != "LONG" or signal.get("slope_atr", 0) < SLOPE_MIN:
            i += 1
            continue
        entry = closes[i]
        atr = signal["atr"]
        end = i + 1
        while end < len(closes) and end - i <= HOLD_CAP:
            later = weekly_trend(closes[: end + 1])
            end += 1
            if later.get("direction") != "LONG":
                break
        path = closes[i + 1 : end]
        if not path:
            i += 1
            continue
        cost = entry * ROUND_TRIP_BPS / 10000
        outcome = measure_outcome(
            direction="LONG",
            entry=entry,
            highs=path,
            lows=path,
            closes=path,
            atr=atr,
            session="DAILY_CLOSE",
            setup="weekly_20",
            weekly_bias="FAVOREVOLE",
            spread=cost,
        )
        outcome["date"] = dates[i] if dates else None
        trades.append(outcome)
        i = end
    if not trades:
        return {"status": "NO_TRADES", "paper_only": True, "trades": []}

    def med(key):
        vals = [t[key] for t in trades if isinstance(t.get(key), (int, float))]
        return statistics.median(vals) if vals else None

    return {
        "status": "OK",
        "paper_only": True,
        "rule": "weekly_20",
        "n": len(trades),
        "move_atr_median": med("move_atr"),
        "mfe_atr_median": med("mfe_atr"),
        "mae_atr_median": med("mae_atr"),
        "bars_median": med("bars"),
        "false_breakout_rate": sum(1 for t in trades if t.get("false_breakout")) / len(trades),
        "net_median": med("net"),
        "net_mean": statistics.mean(t["net"] for t in trades),
        "trades": trades,
        "note": "Close-only. Non usare mfe/mae per scegliere lo stop.",
    }
