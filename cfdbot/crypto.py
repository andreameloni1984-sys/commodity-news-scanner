"""Segnali cripto (in osservazione) per la sezione Cripto di Trading 212: Bitcoin ed Ethereum.

Stesse regole di Gagarin sui grafici giornalieri, ma:
* solo LONG: nella sezione Cripto si comprano cripto vere, non si può vendere allo scoperto;
* nessuna leva: si indica quanti euro comprare, calcolati sul rischio (ACCOUNT_SIZE × RISK_PCT)
  diviso la distanza dello stop in percentuale, al massimo il 95% del conto (regola Trading 212);
* il mercato non chiude mai: si controlla anche nel weekend, la durata massima è 5 giorni di calendario.

I Termini Crypto di Trading 212 vietano il trading algoritmico: il bot manda solo messaggi,
gli ordini li inserisce l'utente. Se lo stop non si può impostare sulla piattaforma, il messaggio
"STOP TOCCATO" dice di vendere a mano.

Test 10 anni (solo LONG, costi 0,3% andata e ritorno): Bitcoin 106 operazioni, 57% vincenti, +22R;
Ethereum 80 operazioni, 57% vincenti, +19R. Più forte negli anni 2016-2021 che dopo.
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


def entry_signal(coin: Coin, daily: Bars, now: datetime) -> tuple[dict | None, str]:
    bars = completed_daily(daily, now)
    setup = strategy.evaluate(bars)
    if not setup:
        return None, "nessun setup"
    if setup.direction != "LONG":
        return None, "segnale SHORT (non usabile nella sezione Cripto)"
    price = daily.last_price
    if price is None or daily.last_price_time is None or now - daily.last_price_time > MAX_PRICE_AGE:
        return None, "prezzo non aggiornato"
    if price - setup.reference > MAX_CHASE_ATR * setup.atr:
        return None, "prezzo già scappato"
    stop, target = strategy.levels("LONG", price, setup.atr)
    pos = {"key": coin.key, "direction": "LONG", "kind": setup.kind, "entry": round(price, coin.decimals),
           "stop": round(stop, coin.decimals), "target": round(target, coin.decimals),
           "stop_dist": round(price - stop, coin.decimals), "target_dist": round(target - price, coin.decimals),
           "atr": setup.atr, "reasons": setup.reasons, "opened_at": now.isoformat()}
    t1 = strategy.swing_target(bars, "LONG", price, setup.atr)
    if t1 is not None and t1 < target:
        pos.update({"target1": round(t1, coin.decimals), "target1_dist": round(t1 - price, coin.decimals)})
    return pos, "segnale"


def manage(pos: dict, hourly: Bars | None, daily: Bars, now: datetime) -> dict | None:
    """Posizione chiusa (stop, target o tempo) oppure None. Segna pos['tp1_hit_at'] al primo tocco del TP1."""
    opened = datetime.fromisoformat(pos["opened_at"])
    exit_price = reason = None
    tp1 = None
    if hourly:
        for t, hi, lo in zip(hourly.time, hourly.high, hourly.low):
            if t < opened - timedelta(hours=1):
                continue
            if lo <= pos["stop"]:
                exit_price, reason, tp1 = pos["stop"], "stop", tp1 or "stop"
                break
            if pos.get("target1") and tp1 is None and hi >= pos["target1"]:
                tp1 = "target1"
                pos.setdefault("tp1_hit_at", t.isoformat())
            if hi >= pos["target"]:
                exit_price, reason = pos["target"], "target"
                break
    if reason is None and now - opened >= timedelta(days=MAX_DAYS) and daily.last_price:
        exit_price, reason = daily.last_price, "tempo"
    if reason is None:
        return None
    risk = pos["entry"] - pos["stop"]
    r = (exit_price - pos["entry"]) / risk
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
            sig.update(size(sig["entry"], sig["stop"], eurusd, account, risk_pct))
            cr["open"][coin.key] = sig
            emit(messages.crypto_signal(coin, sig))
