"""Backtest della strategia su storico giornaliero: python -m cfdbot.backtest [anni]

Ipotesi prudenti: ingresso all'apertura del giorno dopo il segnale, se nella stessa
barra vengono toccati stop e target si assume lo stop, costi = spread stimato +
finanziamento overnight ~0,02% del nozionale per notte.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass

from . import strategy
from .data import Bars, fetch
from .instruments import INSTRUMENTS, Instrument

OVERNIGHT = 0.0002


@dataclass
class Trade:
    key: str
    direction: str
    kind: str
    entry_time: str
    r: float
    days: int
    exit: str


def run(inst: Instrument, bars: Bars) -> list[Trade]:
    trades: list[Trade] = []
    i = strategy.MIN_BARS - 1
    n = len(bars)
    while i < n - 1:
        setup = strategy.evaluate(bars.upto(i + 1))
        if not setup:
            i += 1
            continue
        entry = bars.open[i + 1]
        stop, target = strategy.levels(setup.direction, entry, setup.atr)
        risk = abs(entry - stop)
        s = 1 if setup.direction == "LONG" else -1
        exit_price, how, j = None, "tempo", i + 1
        while j < n:
            hit_stop = bars.low[j] <= stop if s > 0 else bars.high[j] >= stop
            hit_tgt = bars.high[j] >= target if s > 0 else bars.low[j] <= target
            if hit_stop:
                exit_price, how = stop, "stop"
                break
            if hit_tgt:
                exit_price, how = target, "target"
                break
            if j - i >= strategy.MAX_DAYS:
                exit_price = bars.close[j]
                break
            j += 1
        if exit_price is None:
            break  # operazione ancora aperta a fine storico
        days = j - i
        cost = inst.spread + OVERNIGHT * entry * max(days - 1, 0)
        r = ((exit_price - entry) * s - cost) / risk
        trades.append(Trade(inst.key, setup.direction, setup.kind, bars.time[i + 1].strftime("%Y-%m-%d"), r, days, how))
        i = j  # niente nuove operazioni sullo stesso strumento finché questa è aperta
    return trades


def summary(trades: list[Trade]) -> str:
    if not trades:
        return "nessuna operazione"
    wins = [t for t in trades if t.r > 0]
    total = sum(t.r for t in trades)
    gross_win = sum(t.r for t in wins)
    gross_loss = -sum(t.r for t in trades if t.r <= 0)
    pf = gross_win / gross_loss if gross_loss else float("inf")
    eq = peak = dd = 0.0
    for t in trades:
        eq += t.r
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    return (f"{len(trades):4d} op · vincenti {len(wins) / len(trades):5.1%} · media {total / len(trades):+.2f}R · "
            f"totale {total:+6.1f}R · profit factor {pf:4.2f} · max drawdown {dd:4.1f}R")


def main() -> int:
    years = sys.argv[1] if len(sys.argv) > 1 else "10"
    all_trades: list[Trade] = []
    for inst in INSTRUMENTS:
        bars = fetch(inst.yahoo, range_=f"{years}y")
        trades = run(inst, bars)
        all_trades += trades
        print(f"{inst.name:<12} {summary(trades)}")
        for kind in ("breakout", "pullback"):
            for d in ("LONG", "SHORT"):
                sub = [t for t in trades if t.kind == kind and t.direction == d]
                if sub:
                    print(f"   {kind:<8} {d:<5} {summary(sub)}")
    all_trades.sort(key=lambda t: t.entry_time)
    half = len(all_trades) // 2
    print(f"\nTOTALE       {summary(all_trades)}")
    if half:
        print(f"1a metà      {summary(all_trades[:half])}  (dal {all_trades[0].entry_time})")
        print(f"2a metà      {summary(all_trades[half:])}  (dal {all_trades[half].entry_time})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
