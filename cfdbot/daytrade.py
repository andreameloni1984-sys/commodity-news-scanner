"""Segnale del giorno (day trade): una direzione per strumento, chiusura entro sera.

Due appuntamenti (ora di Roma):
  * 10:00 — DAX ed EUR/USD, dopo la prima ora di Francoforte; chiusura alle 17:30
  * 15:00 — Oro, Petrolio WTI, Nasdaq 100, S&P 500, dopo i dati USA delle 14:30
            e prima dell'apertura di Wall Street; chiusura alle 22:00

Tre regole semplici, ognuna vota rialzo (+1) o ribasso (-1):
  1. trend: prezzo sopra/sotto la media esponenziale delle ultime 20 ore
  2. ieri: sopra il massimo (o sopra metà range) / sotto il minimo (o sotto metà range)
  3. oggi: movimento dalla chiusura di ieri (10:00) o dalle 8:00 (15:00)
Direzione = maggioranza. Forza: 3 voti concordi = forte, 2 su 3 = medio.
Il segnale arriva sempre; Trump è solo una nota informativa, mai un blocco.
Stop 1,5 ATR orari, target 3 ATR orari (1:2), uscita forzata a fine giornata.
"""
from __future__ import annotations

import argparse
import logging
import os
from dataclasses import dataclass, field
from datetime import date, datetime, time as dtime, timedelta, timezone
from typing import Callable, Iterable
from zoneinfo import ZoneInfo

from . import indicators as ind
from . import notify, sputnik_context
from .data import Bars, DataError, fetch

log = logging.getLogger("cfdbot.daytrade")
ROME = ZoneInfo("Europe/Rome")

STOP_ATR = 1.5
TARGET_ATR = 3.0


@dataclass(frozen=True)
class DayInstrument:
    key: str
    name: str
    yahoo: str
    t212: str
    spread: float
    decimals: int
    slot: str            # "EU" (10:00) o "US" (15:00)


INSTRUMENTS: tuple[DayInstrument, ...] = (
    DayInstrument("dax", "DAX", "^GDAXI", "Germany 40", 2.0, 1, "EU"),
    DayInstrument("eurusd", "EUR/USD", "EURUSD=X", "EUR/USD", 0.00008, 5, "EU"),
    DayInstrument("oro", "Oro", "GC=F", "Gold", 0.40, 2, "US"),
    DayInstrument("wti", "Petrolio WTI", "CL=F", "Oil (WTI)", 0.03, 2, "US"),
    DayInstrument("nasdaq", "Nasdaq 100", "NQ=F", "US 100", 2.0, 1, "US"),
    DayInstrument("sp500", "S&P 500", "ES=F", "US 500", 0.70, 1, "US"),
)

SLOTS = {
    "EU": {"at": dtime(10, 0), "move_from": None, "exit": dtime(17, 30), "label": "10:00 · sessione europea"},
    "US": {"at": dtime(15, 0), "move_from": dtime(8, 0), "exit": dtime(22, 0), "label": "15:00 · sessione USA"},
}
STRENGTH = {3: ("forte", "🟢"), 2: ("medio", "🟡"), 1: ("debole", "⚪")}


@dataclass
class DaySignal:
    key: str
    direction: str
    votes: list[int]
    strength: str
    entry: float
    stop: float
    target: float
    atr: float
    reasons: list[str] = field(default_factory=list)


def _rome(t: datetime) -> datetime:
    return t.astimezone(ROME)


def evaluate(inst: DayInstrument, bars: Bars, day: date) -> DaySignal | None:
    """Valuta il segnale del giorno con le candele orarie chiuse prima dell'orario del segnale."""
    slot = SLOTS[inst.slot]
    cutoff = datetime.combine(day, slot["at"], ROME)
    idx = [i for i, t in enumerate(bars.time) if t + timedelta(hours=1) <= cutoff]
    if len(idx) < 40:
        return None
    last = idx[-1]
    if _rome(bars.time[last]).date() != day:
        return None  # nessuna candela di oggi (mercato chiuso / festivo)
    closes = bars.close[: last + 1]
    highs, lows = bars.high[: last + 1], bars.low[: last + 1]
    price = closes[-1]

    ema = ind.ema_series(closes, 20)[-1]
    v_trend = 1 if price > ema else -1

    prev_days = sorted({_rome(bars.time[i]).date() for i in idx if _rome(bars.time[i]).date() < day})
    if not prev_days:
        return None
    yday = prev_days[-1]
    y_idx = [i for i in idx if _rome(bars.time[i]).date() == yday]
    y_hi, y_lo, y_close = max(bars.high[i] for i in y_idx), min(bars.low[i] for i in y_idx), bars.close[y_idx[-1]]
    if price > y_hi:
        v_yday, y_txt = 1, "sopra il massimo di ieri"
    elif price < y_lo:
        v_yday, y_txt = -1, "sotto il minimo di ieri"
    else:
        mid = (y_hi + y_lo) / 2
        v_yday = 1 if price >= mid else -1
        y_txt = "nella metà alta del range di ieri" if v_yday > 0 else "nella metà bassa del range di ieri"

    if slot["move_from"] is None:
        ref, ref_txt = y_close, "dalla chiusura di ieri"
    else:
        start = datetime.combine(day, slot["move_from"], ROME)
        today_idx = [i for i in idx if bars.time[i] >= start]
        ref, ref_txt = (bars.open[today_idx[0]], "dalle 8:00") if today_idx else (y_close, "dalla chiusura di ieri")
    move = price / ref - 1 if ref else 0.0
    v_today = 1 if move >= 0 else -1

    votes = [v_trend, v_yday, v_today]
    total = sum(votes)
    direction = "LONG" if total > 0 else "SHORT"
    agree = sum(1 for v in votes if v == (1 if total > 0 else -1))
    strength = STRENGTH[agree][0]
    atr = ind.atr(highs[-30:], lows[-30:], closes[-30:], 14) or 0.0
    if atr <= 0:
        return None
    s = 1 if direction == "LONG" else -1
    reasons = [
        f"trend orario {'rialzista' if v_trend > 0 else 'ribassista'} (prezzo {'sopra' if v_trend > 0 else 'sotto'} la media 20 ore)",
        y_txt,
        f"{move:+.2%} {ref_txt}",
    ]
    return DaySignal(inst.key, direction, votes, strength, price,
                     price - s * STOP_ATR * atr, price + s * TARGET_ATR * atr, atr, reasons)


# ----------------------------------------------------------------------------- backtest

def simulate(inst: DayInstrument, bars: Bars, day: date, sig: DaySignal) -> tuple[float, str] | None:
    """Risultato in R (dopo lo spread) da ingresso all'orario del segnale a uscita a fine giornata."""
    slot = SLOTS[inst.slot]
    start = datetime.combine(day, slot["at"], ROME)
    end = datetime.combine(day, slot["exit"], ROME)
    path = [i for i, t in enumerate(bars.time) if start <= t < end]
    if not path:
        return None
    entry = bars.open[path[0]]
    s = 1 if sig.direction == "LONG" else -1
    risk = STOP_ATR * sig.atr
    stop, target = entry - s * risk, entry + s * TARGET_ATR * sig.atr
    exit_price, how = bars.close[path[-1]], "fine giornata"
    for i in path:
        hit_stop = bars.low[i] <= stop if s > 0 else bars.high[i] >= stop
        hit_tgt = bars.high[i] >= target if s > 0 else bars.low[i] <= target
        if hit_stop:
            exit_price, how = stop, "stop"
            break
        if hit_tgt:
            exit_price, how = target, "target"
            break
    return ((exit_price - entry) * s - inst.spread) / risk, how


def backtest(fetcher: Callable[..., Bars] = fetch) -> dict:
    results: dict[str, list[tuple[str, float]]] = {}
    for inst in INSTRUMENTS:
        try:
            bars = fetcher(inst.yahoo, range_="730d", interval="1h")
        except DataError as exc:
            log.warning("%s: %s", inst.name, exc)
            continue
        days = sorted({_rome(t).date() for t in bars.time})
        rows = []
        for day in days:
            if day.weekday() > 4:
                continue
            sig = evaluate(inst, bars, day)
            if not sig:
                continue
            res = simulate(inst, bars, day, sig)
            if res:
                rows.append((sig.strength, res[0]))
        results[inst.key] = rows
    return results


def summarize(rows: Iterable[tuple[str, float]]) -> str:
    rs = [r for _, r in rows]
    if not rs:
        return "nessuna operazione"
    wins = sum(1 for r in rs if r > 0)
    gross_w = sum(r for r in rs if r > 0)
    gross_l = -sum(r for r in rs if r <= 0)
    pf = gross_w / gross_l if gross_l else float("inf")
    return (f"{len(rs):4d} giorni · vincenti {wins / len(rs):5.1%} · media {sum(rs) / len(rs):+.3f}R · "
            f"totale {sum(rs):+7.1f}R · PF {pf:4.2f}")


# ----------------------------------------------------------------------------- segnale dal vivo

def f(x: float, d: int) -> str:
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_slot(slot: str, signals: list[tuple[DayInstrument, DaySignal, str]]) -> str:
    lines = [f"📅 SEGNALE DEL GIORNO — {SLOTS[slot]['label']}", f"Chiusura entro le {SLOTS[slot]['exit'].strftime('%H:%M')}", ""]
    order = {"forte": 0, "medio": 1, "debole": 2}
    for inst, sig, trump in sorted(signals, key=lambda x: order[x[1].strength]):
        icon = next(i for _, (n, i) in STRENGTH.items() if n == sig.strength)
        arrow = "LONG ↑" if sig.direction == "LONG" else "SHORT ↓"
        d = inst.decimals
        lines += [
            f"{icon} {inst.name} — {arrow} · {sig.strength}  (CFD: {inst.t212})",
            f"   Ingresso {f(sig.entry, d)} · Stop {f(sig.stop, d)} · Target {f(sig.target, d)}",
            "   " + " · ".join(sig.reasons),
        ]
        if trump:
            lines.append(f"   {trump}")
        lines.append("")
    lines.append("🟢 forte = 3 regole d'accordo · 🟡 medio = 2 su 3. Decidi tu su quali entrare.")
    lines.append("Segnale automatico, non è una consulenza. Ordine da inserire a mano su Trading 212.")
    return "\n".join(lines)


def run(now: datetime | None = None, fetcher: Callable[..., Bars] = fetch,
        sender: Callable[[str], bool] = notify.send, st: dict | None = None, dry_run: bool = False,
        context_fetcher: Callable[[], dict | None] | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    local = _rome(now)
    st = st if st is not None else {}
    sent = st.setdefault("day_sent", {})
    if local.weekday() > 4:
        return st
    ctx_loaded, ctx = False, None
    for slot, cfg in SLOTS.items():
        key = f"{local.date().isoformat()}|{slot}"
        start = datetime.combine(local.date(), cfg["at"], ROME)
        if key in sent or not (start <= local < start + timedelta(minutes=55)):
            continue
        signals = []
        for inst in (i for i in INSTRUMENTS if i.slot == slot):
            try:
                bars = fetcher(inst.yahoo, range_="60d", interval="1h")
            except DataError as exc:
                log.warning("%s: %s", inst.name, exc)
                continue
            sig = evaluate(inst, bars, local.date())
            if not sig:
                continue
            if bars.last_price and bars.last_price_time and now - bars.last_price_time < timedelta(minutes=30):
                s = 1 if sig.direction == "LONG" else -1
                sig.entry = bars.last_price
                sig.stop = sig.entry - s * STOP_ATR * sig.atr
                sig.target = sig.entry + s * TARGET_ATR * sig.atr
            if not ctx_loaded:
                ctx = (context_fetcher or sputnik_context.fetch)()
                ctx_loaded = True
            trump_line = sputnik_context.trump_view(inst.key, sig.direction, ctx, now)[0] if ctx else ""
            if "nessuna notizia" in trump_line:
                trump_line = ""
            signals.append((inst, sig, trump_line))
        sent[key] = now.isoformat()
        if not signals:
            log.info("Slot %s: nessun dato (festivo o mercato chiuso)", slot)
            continue
        text = format_slot(slot, signals)
        if dry_run:
            print(text)
        else:
            sender(text)
    # tieni solo gli ultimi 30 giorni
    cutoff = (local.date() - timedelta(days=30)).isoformat()
    st["day_sent"] = {k: v for k, v in sent.items() if k.split("|")[0] >= cutoff}
    return st


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--backtest", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    if args.backtest:
        res = backtest()
        names = {i.key: i.name for i in INSTRUMENTS}
        everything = []
        for key, rows in res.items():
            everything += rows
            print(f"\n{names[key]:<13} tutti    {summarize(rows)}")
            for s in ("forte", "medio", "debole"):
                sub = [r for r in rows if r[0] == s]
                if sub:
                    print(f"{'':13} {s:<8} {summarize(sub)}")
        print(f"\nTOTALE        tutti    {summarize(everything)}")
        print(f"{'':13} forte    {summarize([r for r in everything if r[0] == 'forte'])}")
        print(f"{'':13} f+medio  {summarize([r for r in everything if r[0] in ('forte', 'medio')])}")
        return 0
    from . import state as state_mod
    path = os.getenv("DAY_STATE_PATH", "data/day_state.json")
    dry = args.dry_run or not notify.configured()
    st = state_mod.load(path) if not dry else {}
    st = run(st=st, dry_run=dry)
    if not dry:
        state_mod.save(st, path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
