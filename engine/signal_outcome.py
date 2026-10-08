"""SOYUZ — engine/signal_outcome.py

Registro di quello che succede dopo un segnale. Paper.
Misura movimento, MFE, MAE, durata, ATR, sessione, costi.
Non cerca lo stop o il take profit che avrebbe vinto:
riporta la distribuzione, non un valore tarato.
"""

from __future__ import annotations


def _path(highs, lows, closes, start, end):
    return highs[start:end], lows[start:end], closes[start:end]


def measure_outcome(
    *,
    direction: str,
    entry: float,
    highs: list[float],
    lows: list[float],
    closes: list[float],
    atr: float,
    session: str = "UNKNOWN",
    setup: str = "UNSPECIFIED",
    weekly_bias: str = "UNKNOWN",
    news_note: str = "",
    spread: float = 0.0,
    slippage: float = 0.0,
    commission: float = 0.0,
) -> dict:
    if direction not in {"LONG", "SHORT"} or entry <= 0 or atr <= 0:
        return {"status": "INVALID", "paper_only": True}
    if not highs or len(highs) != len(lows) or len(lows) != len(closes):
        return {"status": "PATH_MISMATCH", "paper_only": True}

    sign = 1 if direction == "LONG" else -1
    fill = entry + sign * (spread / 2 + slippage)
    favorable = []
    adverse = []
    for h, l in zip(highs, lows):
        if direction == "LONG":
            favorable.append(h - fill)
            adverse.append(fill - l)
        else:
            favorable.append(fill - l)
            adverse.append(h - fill)
    mfe = max(favorable)
    mae = max(adverse)
    # durata: prima barra in cui il favorevole raggiunge 1 ATR, se avviene
    duration = next((i + 1 for i, x in enumerate(favorable) if x >= atr), None)
    last = closes[-1]
    move = sign * (last - fill)
    cost = spread + slippage + commission
    net = move - cost
    false_breakout = mfe < atr and mae >= atr
    return {
        "status": "OK",
        "paper_only": True,
        "direction": direction,
        "setup": setup,
        "session": session,
        "weekly_bias": weekly_bias,
        "news_note": news_note,
        "entry": entry,
        "fill": fill,
        "atr": atr,
        "bars": len(closes),
        "move": move,
        "move_atr": move / atr,
        "mfe": mfe,
        "mfe_atr": mfe / atr,
        "mae": mae,
        "mae_atr": mae / atr,
        "duration_bars_to_1atr": duration,
        "false_breakout": false_breakout,
        "spread": spread,
        "slippage": slippage,
        "commission": commission,
        "cost": cost,
        "net": net,
        "rr_realized": (mfe / mae) if mae > 0 else None,
        "note": "SL e TP non sono ottimizzati. mfe_atr e mae_atr sono la distribuzione da cui, dopo il paper, si legge un livello.",
    }
