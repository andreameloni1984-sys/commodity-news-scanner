"""Ricerca: un voto 1-10 per i segnali swing distingue davvero le operazioni migliori?

    python -m cfdbot.research_score

Metodo anti-illusione: le regole del voto si stimano SOLO sulla prima metà del periodo
(prima del 2021-11) e si verificano sulla seconda metà, mai vista.
Caratteristiche misurate al momento del segnale (nessun dato futuro):
  forza del trend   = |prezzo - SMA200| / ATR
  momentum          = |rendimento 20 giorni| / volatilità
  volatilità        = ATR% rispetto alla sua mediana di 1 anno
  RSI14 (nella direzione del segnale), tipo (breakout/pullback), strumento.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass

from . import indicators as ind
from . import strategy
from .backtest import OVERNIGHT
from .data import Bars, fetch
from .instruments import BY_KEY, Instrument
from .main import DEFAULT_INSTRUMENTS

CUT = "2021-11-01"


@dataclass
class Row:
    key: str
    date: str
    r: float
    feats: dict


def features(bars: Bars, setup) -> dict:
    c = bars.close
    s = 1 if setup.direction == "LONG" else -1
    sma200 = ind.sma(c, 200) or c[-1]
    trend = s * (c[-1] - sma200) / setup.atr
    r20 = ind.pct_return(c, 20) or 0.0
    vol = ind.realized_vol(c, 20) or 1e-9
    mom = s * r20 / (vol / (252 ** 0.5) * (20 ** 0.5))
    atr_pct = [ind.atr(bars.high[:k], bars.low[:k], c[:k]) / c[k - 1] for k in range(len(c) - 250, len(c), 10)]
    atrp_now = setup.atr / c[-1]
    vol_regime = atrp_now / statistics.median(atr_pct)
    rsi = ind.rsi(c) or 50.0
    rsi_dir = rsi if s > 0 else 100 - rsi
    return {"trend": trend, "mom": mom, "vol": vol_regime, "rsi": rsi_dir, "kind": setup.kind}


def collect(inst: Instrument, bars: Bars) -> list[Row]:
    rows, i, n = [], strategy.MIN_BARS + 260, len(bars)
    while i < n - 1:
        sub = bars.upto(i + 1)
        setup = strategy.evaluate(sub)
        if not setup:
            i += 1
            continue
        s = 1 if setup.direction == "LONG" else -1
        entry = bars.open[i + 1]
        stop, target = strategy.levels(setup.direction, entry, setup.atr)
        risk = abs(entry - stop)
        exit_price, j = None, i + 1
        while j < n:
            if (bars.low[j] <= stop) if s > 0 else (bars.high[j] >= stop):
                exit_price = stop
                break
            if (bars.high[j] >= target) if s > 0 else (bars.low[j] <= target):
                exit_price = target
                break
            if j - i >= strategy.MAX_DAYS:
                exit_price = bars.close[j]
                break
            j += 1
        if exit_price is None:
            break
        cost = inst.spread + OVERNIGHT * entry * max(j - i - 1, 0)
        rows.append(Row(inst.key, bars.time[i + 1].strftime("%Y-%m-%d"),
                        ((exit_price - entry) * s - cost) / risk, features(sub, setup)))
        i = j
    return rows


NUMERIC = ("trend", "mom", "vol", "rsi")


def fit(train: list[Row]) -> dict:
    """Per ogni caratteristica: soglie dei terzili e R medio per terzile (solo dati di stima)."""
    model = {}
    for f in NUMERIC:
        vals = sorted(r.feats[f] for r in train)
        q1, q2 = vals[len(vals) // 3], vals[2 * len(vals) // 3]
        buckets = {0: [], 1: [], 2: []}
        for r in train:
            v = r.feats[f]
            buckets[0 if v <= q1 else 1 if v <= q2 else 2].append(r.r)
        model[f] = {"cuts": (q1, q2), "avg": {b: statistics.mean(x) for b, x in buckets.items() if x}}
    for f, getter in (("kind", lambda r: r.feats["kind"]), ("inst", lambda r: r.key)):
        groups: dict[str, list[float]] = {}
        for r in train:
            groups.setdefault(getter(r), []).append(r.r)
        model[f] = {k: statistics.mean(v) for k, v in groups.items()}
    return model


def raw_score(model: dict, r: Row) -> float:
    total = 0.0
    for f in NUMERIC:
        q1, q2 = model[f]["cuts"]
        v = r.feats[f]
        total += model[f]["avg"].get(0 if v <= q1 else 1 if v <= q2 else 2, 0.0)
    total += model["kind"].get(r.feats["kind"], 0.0)
    total += model["inst"].get(r.key, 0.0)
    return total


def report(name: str, rows: list[Row], model: dict, cuts: tuple[float, float]) -> None:
    lo, hi = cuts
    groups = {"basso": [], "medio": [], "alto": []}
    for r in rows:
        s = raw_score(model, r)
        groups["basso" if s <= lo else "medio" if s <= hi else "alto"].append(r.r)
    print(f"\n{name}: {len(rows)} operazioni")
    for g, rs in groups.items():
        if rs:
            win = sum(1 for x in rs if x > 0) / len(rs)
            print(f"   voto {g:<6} {len(rs):4d} op · vincenti {win:5.1%} · media {statistics.mean(rs):+.3f}R · totale {sum(rs):+6.1f}R")
    xs = [raw_score(model, r) for r in rows]
    ys = [r.r for r in rows]
    if len(rows) > 2:
        print(f"   correlazione voto/risultato: {statistics.correlation(xs, ys):+.3f}")


def main() -> int:
    rows: list[Row] = []
    for key in DEFAULT_INSTRUMENTS:
        inst = BY_KEY[key]
        rows += collect(inst, fetch(inst.yahoo, range_="10y"))
    rows.sort(key=lambda r: r.date)
    train = [r for r in rows if r.date < CUT]
    test = [r for r in rows if r.date >= CUT]
    model = fit(train)
    tr_scores = sorted(raw_score(model, r) for r in train)
    cuts = (tr_scores[len(tr_scores) // 3], tr_scores[2 * len(tr_scores) // 3])
    print("Caratteristiche (R medio per terzile basso/medio/alto, stimato sulla 1a metà):")
    for f in NUMERIC:
        a = model[f]["avg"]
        print(f"   {f:<6} {a.get(0, 0):+.3f} / {a.get(1, 0):+.3f} / {a.get(2, 0):+.3f}")
    print(f"   tipo   {model['kind']}")
    print(f"   strum. { {k: round(v, 3) for k, v in model['inst'].items()} }")
    report("1a metà (stima, ottimistica per costruzione)", train, model, cuts)
    report("2a metà (verifica, mai vista)", test, model, cuts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
