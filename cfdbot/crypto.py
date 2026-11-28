"""Segnali cripto (in osservazione) su Bitcoin ed Ethereum per Trading 212.

Stesse regole di Gagarin sui grafici giornalieri:
* LONG → sezione Cripto (cripto vere, niente costo per notte);
* SHORT → CFD (nella sezione Cripto non si vende allo scoperto): leva 1:2, stop automatico,
  quantità calcolata come per i CFD di Gagarin;
* LONG senza leva: si indica quanti euro comprare, calcolati sul rischio (ACCOUNT_SIZE × RISK_PCT)
  diviso la distanza dello stop in percentuale, al massimo il 95% del conto (regola Trading 212);
* il mercato non chiude mai: si controlla anche nel weekend, la durata massima è 5 giorni di calendario.

I Termini Crypto di Trading 212 vietano il trading algoritmico: il bot manda solo messaggi,
gli ordini li inserisce l'utente. Se lo stop non si può impostare sulla piattaforma, il messaggio
"STOP TOCCATO" dice di vendere a mano.

Test 10 anni (costi inclusi): LONG Bitcoin 106 operazioni, 57% vincenti, +22R; Ethereum 80, 57%, +19R.
SHORT (CFD) Bitcoin 50 operazioni, 54%, +9R; Ethereum 51, 55%, +10R (debole negli ultimi anni).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable

from . import strategy
from .data import Bars, DataError, completed_daily

log = logging.getLogger("cfdbot.crypto")

MAX_DAYS = 5
MAX_PRICE_AGE = timedelta(hours=3)
MAX_CHASE_ATR = 1.0
MAX_SHARE = 0.95
CFD_LEVERAGE = 2   # ESMA: CFD su cripto con leva massima 1:2


@dataclass(frozen=True)
class Coin:
    key: str
    name: str
    yahoo: str
    t212: str
    decimals: int


COINS: tuple[Coin, ...] = (
    Coin("btc", "Bitcoin", "BTC-USD", "Bitcoin (BTC/USD)", 0),
    Coin("eth", "Ethereum", "ETH-USD", "Ethereum (ETH/USD)", 2),
)


def size(entry: float, stop: float, eurusd: float | None, account: float | None, risk_pct: float) -> dict:
    """Euro da comprare per rischiare risk_pct del conto allo stop (senza leva)."""
    if not account or not eurusd or entry <= stop:
        return {"risk_pct": risk_pct}
    stop_pct = (entry - stop) / entry
    amount = min(account * risk_pct / 100 / stop_pct, account * MAX_SHARE)
    return {"risk_pct": risk_pct, "amount_eur": round(amount, 2), "risk_eur": round(amount * stop_pct, 2),
            "units": round(amount * eurusd / entry, 6), "capped": amount >= account * MAX_SHARE - 0.01}


def size_cfd(entry: float, stop: float, eurusd: float | None, account: float | None, risk_pct: float) -> dict:
    """Quantità CFD per rischiare risk_pct del conto allo stop (posizione SHORT)."""
    if not account or not eurusd or stop <= entry:
        return {"risk_pct": risk_pct}
    risk = account * risk_pct / 100
    units = risk / ((stop - entry) / eurusd)
    notional = units * entry / eurusd
    return {"risk_pct": risk_pct, "risk_eur": round(risk, 2), "units": round(units, 6),
            "notional_eur": round(notional, 2), "margin_eur": round(notional / CFD_LEVERAGE, 2)}


def entry_signal(coin: Coin, daily: Bars, now: datetime) -> tuple[dict | None, str]:
    bars = completed_daily(daily, now)
    setup = strategy.evaluate(bars)
    if not setup:
        return None, "nessun setup"
    price = daily.last_price
    if price is None or daily.last_price_time is None or now - daily.last_price_time > MAX_PRICE_AGE:
        return None, "prezzo non aggiornato"
    s = 1 if setup.direction == "LONG" else -1
    if (price - setup.reference) * s > MAX_CHASE_ATR * setup.atr:
        return None, "prezzo già scappato"
    stop, target = strategy.levels(setup.direction, price, setup.atr)
    pos = {"key": coin.key, "direction": setup.direction, "kind": setup.kind,
           "where": "sezione Cripto" if s > 0 else "CFD", "entry": round(price, coin.decimals),
           "stop": round(stop, coin.decimals), "target": round(target, coin.decimals),
           "stop_dist": round(abs(price - stop), coin.decimals), "target_dist": round(abs(target - price), coin.decimals),
           "atr": setup.atr, "reasons": setup.reasons, "opened_at": now.isoformat()}
    t1 = strategy.swing_target(bars, setup.direction, price, setup.atr)
    if t1 is not None and abs(t1 - price) < abs(target - price):
        pos.update({"target1": round(t1, coin.decimals), "target1_dist": round(abs(t1 - price), coin.decimals)})
    return pos, "segnale"


def manage(pos: dict, hourly: Bars | None, daily: Bars, now: datetime) -> dict | None:
    """Posizione chiusa (stop, target o tempo) oppure None. Segna pos['tp1_hit_at'] al primo tocco del TP1."""
    opened = datetime.fromisoformat(pos["opened_at"])
    s = 1 if pos["direction"] == "LONG" else -1
    exit_price = reason = None
    tp1 = None
    if hourly:
        for t, hi, lo in zip(hourly.time, hourly.high, hourly.low):
            if t < opened - timedelta(hours=1):
                continue
            if (lo <= pos["stop"]) if s > 0 else (hi >= pos["stop"]):
                exit_price, reason, tp1 = pos["stop"], "stop", tp1 or "stop"
                break
            if pos.get("target1") and tp1 is None and ((hi >= pos["target1"]) if s > 0 else (lo <= pos["target1"])):
                tp1 = "target1"
                pos.setdefault("tp1_hit_at", t.isoformat())
            if (hi >= pos["target"]) if s > 0 else (lo <= pos["target"]):
                exit_price, reason = pos["target"], "target"
                break
    if reason is None and now - opened >= timedelta(days=MAX_DAYS) and daily.last_price:
        exit_price, reason = daily.last_price, "tempo"
    if reason is None:
        return None
    risk = abs(pos["entry"] - pos["stop"])
    r = (exit_price - pos["entry"]) * s / risk
    done = {**pos, "exit": exit_price, "exit_reason": reason, "r": round(r, 2), "closed_at": now.isoformat()}
    if pos.get("target1"):
        done["r_tp1"] = round(pos["target1_dist"] / risk if tp1 == "target1" else r, 2)
    return done


def process(now: datetime, fetcher: Callable[..., Bars], st: dict, eurusd: float | None,
            account: float | None, risk_pct: float, emit: Callable[[str], None]) -> None:
    from . import messages

    cr = st.setdefault("crypto", {})
    for part, empty in (("open", {}), ("closed", []), ("last_eval", {})):
        cr.setdefault(part, empty)
    for coin in COINS:
        try:
            daily = fetcher(coin.yahoo, range_="2y", interval="1d")
        except DataError as exc:
            log.warning("%s: %s", coin.name, exc)
            continue
        pos = cr["open"].get(coin.key)
        if pos:
            try:
                hourly = fetcher(coin.yahoo, range_="1mo", interval="1h")
            except DataError:
                hourly = None
            done = manage(pos, hourly, daily, now)
            if pos.get("tp1_hit_at") and not pos.get("tp1_notified"):
                pos["tp1_notified"] = True
                if now - datetime.fromisoformat(pos["tp1_hit_at"]) <= timedelta(hours=3):
                    emit(messages.crypto_target1(coin, pos))
            if done:
                cr["open"].pop(coin.key)
                cr["closed"].append(done)
                emit(messages.crypto_closed(coin, done, cr["closed"]))
            continue
        bars = completed_daily(daily, now)
        if not len(bars):
            continue
        bar_id = bars.time[-1].strftime("%Y-%m-%d")
        if cr["last_eval"].get(coin.key) == bar_id:
            continue
        sig, why = entry_signal(coin, daily, now)
        log.info("%s: barra %s → %s", coin.name, bar_id, why)
        if why == "prezzo non aggiornato":
            continue
        cr["last_eval"][coin.key] = bar_id
        if sig:
            sizer = size if sig["direction"] == "LONG" else size_cfd
            sig.update(sizer(sig["entry"], sig["stop"], eurusd, account, risk_pct))
            cr["open"][coin.key] = sig
            emit(messages.crypto_signal(coin, sig))
