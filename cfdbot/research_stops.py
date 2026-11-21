"""Ricerca: stop/target e conferma con candele giapponesi sul segnale swing (10 anni).

    python -m cfdbot.research_stops

Varianti (stesse regole di ingresso e stessi costi del backtest ufficiale):
  base       stop 1,5 ATR · target 3 ATR (metodo attuale)
  strutt     stop oltre l'ultimo minimo/massimo delle 5 candele + 0,2 ATR · target 2× lo stop
  pattern    come base, ma entra solo con engulfing o martello/shooting star coerenti
  chiusura   come base, ma entra solo se la candela chiude nel terzo favorevole del suo range
  livelli    come base, ma target sul massimo/minimo delle 60 candele precedenti (se almeno 1R)
"""
from __future__ import annotations

from . import strategy
from .backtest import OVERNIGHT, Trade, summary
from .data import Bars, fetch
from .instruments import INSTRUMENTS, Instrument

VARIANTS = ("base", "strutt", "pattern", "chiusura", "livelli")


def candle_ok(b: Bars, i: int, direction: str, mode: str) -> bool:
    o, h, l, c = b.open[i], b.high[i], b.low[i], b.close[i]
    rng = h - l
    if rng <= 0:
        return False
    if mode == "chiusura":
        pos = (c - l) / rng
        return pos >= 2 / 3 if direction == "LONG" else pos <= 1 / 3
    po, pc = b.open[i - 1], b.close[i - 1]
    body = abs(c - o)
    upper, lower = h - max(o, c), min(o, c) - l
    if direction == "LONG":
        engulf = pc < po and c > o and c >= po and o <= pc
        hammer = lower >= 2 * body and upper <= body and (c - l) / rng >= 0.6
        return engulf or hammer
    engulf = pc > po and c < o and c <= po and o >= pc
    star = upper >= 2 * body and lower <= body and (h - c) / rng >= 0.6
    return engulf or star


def run(inst: Instrument, bars: Bars, variant: str) -> list[Trade]:
    trades: list[Trade] = []
    i, n = strategy.MIN_BARS - 1, len(bars)
    while i < n - 1:
        setup = strategy.evaluate(bars.upto(i + 1))
        if not setup or (variant in ("pattern", "chiusura") and not candle_ok(bars, i, setup.direction, variant)):
            i += 1
            continue
        s = 1 if setup.direction == "LONG" else -1
        entry = bars.open[i + 1]
        atr = setup.atr
        stop, target = strategy.levels(setup.direction, entry, atr)
        if variant == "strutt":
            if s > 0:
                stop = min(bars.low[i - 4:i + 1]) - 0.2 * atr
            else:
                stop = max(bars.high[i - 4:i + 1]) + 0.2 * atr
            dist = min(max(abs(entry - stop), 0.5 * atr), 3.0 * atr)
            stop = entry - s * dist
            target = entry + s * 2 * dist
        elif variant == "livelli":
            risk = abs(entry - stop)
            level = max(bars.high[i - 60:i - 20]) if s > 0 else min(bars.low[i - 60:i - 20])
            if (level - entry) * s >= risk:
                target = level
        risk = abs(entry - stop)
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
            break
        days = j - i
        cost = inst.spread + OVERNIGHT * entry * max(days - 1, 0)
        r = ((exit_price - entry) * s - cost) / risk
        trades.append(Trade(inst.key, setup.direction, setup.kind, bars.time[i + 1].strftime("%Y-%m-%d"), r, days, how))
        i = j
    return trades


def main() -> int:
    data = {inst.key: fetch(inst.yahoo, range_="10y") for inst in INSTRUMENTS}
    print(f"{'variante':<9} {'risultato complessivo':<95} | 1a metà / 2a metà")
    for v in VARIANTS:
        allt = []
        for inst in INSTRUMENTS:
            allt += run(inst, data[inst.key], v)
        allt.sort(key=lambda t: t.entry_time)
        cut = "2021-11-01"
        a = [t for t in allt if t.entry_time < cut]
        b = [t for t in allt if t.entry_time >= cut]
        print(f"{v:<9} {summary(allt):<95} | {sum(t.r for t in a):+6.1f}R / {sum(t.r for t in b):+6.1f}R")
        for inst in INSTRUMENTS:
            sub = [t for t in allt if t.key == inst.key]
            print(f"   {inst.name:<12} {summary(sub)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
