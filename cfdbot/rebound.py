"""Strategia "rimbalzo indici" (in osservazione): compra i piccoli cali di S&P 500 e Nasdaq.

Regole (dal laboratorio sulle strategie, 20 anni, costi CFD inclusi):
* solo S&P 500 e Nasdaq 100, solo se la chiusura è sopra la media a 200 giorni;
* ingresso LONG se l'indice chiude nel 20% più basso della giornata (IBS < 0,2)
  oppure dopo 3 chiusure in calo di fila;
* uscita quando chiude sopra la media a 5 giorni o nel 20% più alto della giornata (IBS > 0,8),
  con stop di sicurezza a 2 ATR e al massimo 5 giorni di borsa.

Nel test: rapporto rendimento/rischio 0,64 (0,29 nel 2006-2016, 0,93 nel 2016-2026), circa 28
operazioni l'anno per indice, 67% vincenti, quasi nessuna correlazione con i segnali di Gagarin.
Le posizioni sono tenute a parte (st["rebound"]) e il pagellino le misura separatamente.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from . import indicators as ind
from .data import Bars, completed_daily
from .instruments import Instrument

KEYS = ("sp500", "nasdaq")
IBS_IN, IBS_OUT = 0.2, 0.8
DOWN_DAYS = 3
STOP_ATR = 2.0
MAX_DAYS = 5
MAX_PRICE_AGE = timedelta(hours=3)
MAX_CHASE_ATR = 1.0
FOOTER = ("🔬 IN OSSERVAZIONE: strategia nuova, il pagellino la misura a parte prima di usarla con soldi veri.\n"
          "Segnale automatico, non è una consulenza finanziaria. Ordine da inserire a mano su Trading 212.")


def ibs(bars: Bars, i: int = -1) -> float:
    rng = bars.high[i] - bars.low[i]
    return (bars.close[i] - bars.low[i]) / rng if rng > 0 else 0.5


def entry_setup(bars: Bars) -> tuple[list[str], float] | None:
    """Motivi dell'ingresso e ATR, oppure None."""
    c = bars.close
    if len(c) < 210:
        return None
    sma200, atr = ind.sma(c, 200), ind.atr(bars.high, bars.low, c)
    if sma200 is None or not atr or c[-1] <= sma200:
        return None
    reasons = []
    v = ibs(bars)
    if v < IBS_IN:
        reasons.append(f"chiusura vicino al minimo della giornata (IBS {v:.2f})")
    if all(c[-1 - k] < c[-2 - k] for k in range(DOWN_DAYS)):
        reasons.append(f"{DOWN_DAYS} chiusure in calo di fila")
    if not reasons:
        return None
    return ["Indice sopra la media a 200 giorni"] + reasons, atr


def exit_reason(bars: Bars) -> str | None:
    sma5 = ind.sma(bars.close, 5)
    if sma5 is not None and bars.close[-1] > sma5:
        return "rimbalzo"
    if ibs(bars) > IBS_OUT:
        return "rimbalzo"
    return None


def _fresh(daily: Bars, now: datetime) -> float | None:
    if daily.last_price is None or daily.last_price_time is None or now - daily.last_price_time > MAX_PRICE_AGE:
        return None
    return daily.last_price


def process(inst: Instrument, daily: Bars, hourly: Bars | None, now: datetime, rb: dict,
            sizing, emit) -> None:
    """Segue la posizione rimbalzo dello strumento e cerca nuovi ingressi. rb = st["rebound"]."""
    from . import messages

    bars = completed_daily(daily, now)
    if not len(bars):
        return
    bar_id = bars.time[-1].strftime("%Y-%m-%d")
    new_bar = rb["last_eval"].get(inst.key) != bar_id
    pos = rb["open"].get(inst.key)
    price = _fresh(daily, now)

    if pos:
        exit_px = reason = None
        if hourly:
            start = datetime.fromisoformat(pos["opened_at"]) - timedelta(hours=1)
            if any(t >= start and lo <= pos["stop"] for t, lo in zip(hourly.time, hourly.low)):
                exit_px, reason = pos["stop"], "stop"
        if reason is None and new_bar:
            days = sum(1 for t in bars.time if t.date() > datetime.fromisoformat(pos["opened_at"]).date())
            signal = exit_reason(bars)
            if signal or days >= MAX_DAYS:
                pos["exit_pending"] = signal or "tempo"
        if reason is None and pos.get("exit_pending") and price is not None:
            exit_px, reason = price, pos["exit_pending"]
        if reason:
            r = (exit_px - pos["entry"]) / (pos["entry"] - pos["stop"])
            done = {**pos, "exit": exit_px, "exit_reason": reason, "r": round(r, 2), "closed_at": now.isoformat()}
            done.pop("exit_pending", None)
            rb["open"].pop(inst.key)
            rb["closed"].append(done)
            emit(messages.rebound_closed(inst, done, rb["closed"]))
        rb["last_eval"][inst.key] = bar_id
        return

    if not new_bar:
        return
    setup = entry_setup(bars)
    if not setup:
        rb["last_eval"][inst.key] = bar_id
        return
    if price is None:
        return   # mercato chiuso: riprova alla riapertura
    rb["last_eval"][inst.key] = bar_id
    reasons, atr = setup
    if price - bars.close[-1] > MAX_CHASE_ATR * atr:
        return   # è già rimbalzato: niente ingresso
    stop = price - STOP_ATR * atr
    pos = {
        "key": inst.key, "direction": "LONG", "kind": "rimbalzo", "entry": round(price, inst.decimals),
        "stop": round(stop, inst.decimals), "stop_dist": round(price - stop, inst.decimals), "atr": atr,
        "reasons": reasons, "opened_at": now.isoformat(), **sizing(price, stop),
    }
    rb["open"][inst.key] = pos
    emit(messages.rebound_signal(inst, pos))
