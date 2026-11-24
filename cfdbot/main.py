"""Ciclo del bot (eseguito ogni ora da GitHub Actions): python -m cfdbot.main [--dry-run]

1. Segue le posizioni aperte: avvisa se è stato toccato stop o take profit, o se sono passati 5 giorni.
2. Su ogni nuova barra giornaliera chiusa cerca nuovi segnali (al massimo una posizione per strumento).
3. Una volta al giorno invia un riepilogo.
"""
from __future__ import annotations

import argparse
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Callable

from . import indicators, messages, notify, rebound, report_card, strategy, vol_alert
from . import sputnik_context
from . import state as state_mod
from .data import Bars, DataError, completed_daily, fetch
from .instruments import BY_KEY, INSTRUMENTS, Instrument

log = logging.getLogger("cfdbot")

MAX_PRICE_AGE = timedelta(hours=3)   # prezzo più vecchio = mercato chiuso, niente nuovi segnali
MAX_CHASE_ATR = 1.0                  # se il prezzo è già scappato di oltre 1 ATR, il segnale si salta
SUMMARY_HOUR_UTC = int(os.getenv("SUMMARY_HOUR_UTC", "6"))

Fetcher = Callable[..., Bars]


def _config() -> tuple[float | None, float]:
    def num(name: str) -> float | None:
        try:
            v = float(os.getenv(name, "").replace(",", "."))
            return v if v > 0 else None
        except ValueError:
            return None
    return num("ACCOUNT_SIZE"), num("RISK_PCT") or 1.0


# EUR/USD escluso di default: nel backtest di 10 anni perde in tutte le varianti di stop/target
# (da -4R a -8R). Si può riattivare con CFD_INSTRUMENTS=oro,wti,sp500,nasdaq,eurusd.
DEFAULT_INSTRUMENTS = ("oro", "wti", "sp500", "nasdaq")


def enabled_instruments() -> list[Instrument]:
    raw = os.getenv("CFD_INSTRUMENTS", "").strip()
    if not raw:
        return [BY_KEY[k] for k in DEFAULT_INSTRUMENTS]
    return [BY_KEY[k.strip()] for k in raw.split(",") if k.strip() in BY_KEY]


def stats(st: dict) -> dict:
    closed = st["closed"]
    n = len(closed)
    return {"n": n, "win": (sum(1 for c in closed if c["r"] > 0) / n) if n else 0.0,
            "total": sum(c["r"] for c in closed)}


def size_position(entry: float, stop: float, eurusd: float | None) -> dict:
    account, risk_pct = _config()
    if not account or not eurusd:
        return {"risk_pct": risk_pct, "risk_eur": None, "units": None, "unit_risk_eur": None}
    risk_eur = account * risk_pct / 100
    per_unit_eur = abs(entry - stop) / eurusd   # tutti gli strumenti sono quotati in USD
    return {"risk_pct": risk_pct, "risk_eur": round(risk_eur, 2), "units": round(risk_eur / per_unit_eur, 4),
            "unit_risk_eur": round(per_unit_eur, 2)}


def manage_open(inst: Instrument, pos: dict, daily: Bars, hourly: Bars | None, now: datetime) -> dict | None:
    """Restituisce la posizione chiusa (con exit/r) oppure None se resta aperta."""
    entry_t = datetime.fromisoformat(pos["opened_at"])
    s = 1 if pos["direction"] == "LONG" else -1
    exit_price = reason = None
    if hourly:
        for t, hi, lo in zip(hourly.time, hourly.high, hourly.low):
            if t < entry_t - timedelta(hours=1):
                continue
            if (lo <= pos["stop"]) if s > 0 else (hi >= pos["stop"]):
                exit_price, reason = pos["stop"], "stop"
                break
            if (hi >= pos["target"]) if s > 0 else (lo <= pos["target"]):
                exit_price, reason = pos["target"], "target"
                break
    if reason is None:
        days = sum(1 for t in completed_daily(daily, now).time if t.date() > entry_t.date())
        if days >= strategy.MAX_DAYS:
            exit_price, reason = daily.last_price, "tempo"
    if reason is None:
        return None
    r = (exit_price - pos["entry"]) * s / abs(pos["entry"] - pos["stop"])
    return {**pos, "exit": exit_price, "exit_reason": reason, "r": round(r, 2), "closed_at": now.isoformat()}


def new_signal(inst: Instrument, daily: Bars, now: datetime, eurusd: float | None) -> tuple[dict | None, str]:
    bars = completed_daily(daily, now)
    setup = strategy.evaluate(bars)
    if not setup:
        return None, "nessun setup"
    price = daily.last_price
    if price is None or daily.last_price_time is None or now - daily.last_price_time > MAX_PRICE_AGE:
        return None, "mercato chiuso"
    s = 1 if setup.direction == "LONG" else -1
    if (price - setup.reference) * s > MAX_CHASE_ATR * setup.atr:
        return None, "prezzo già scappato"
    stop, target = strategy.levels(setup.direction, price, setup.atr)
    if (price - stop) * s <= 0:
        return None, "livelli non validi"
    pos = {
        "key": inst.key, "direction": setup.direction, "kind": setup.kind,
        "entry": round(price, inst.decimals), "stop": round(stop, inst.decimals), "target": round(target, inst.decimals),
        "stop_dist": round(abs(price - stop), inst.decimals), "target_dist": round(abs(target - price), inst.decimals),
        "atr": setup.atr, "reasons": setup.reasons, "opened_at": now.isoformat(),
        **size_position(price, stop, eurusd),
    }
    return pos, "segnale"


BIG_MOVE_ATR = 2.5   # movimento del giorno oltre 2,5 volte l'ATR: avviso informativo


def check_big_move(inst: Instrument, daily: Bars, now: datetime, st: dict, emit: Callable[[str], None]) -> None:
    """Avvisa una volta al giorno per strumento se il prezzo si muove in modo eccezionale."""
    bars = completed_daily(daily, now)
    price = daily.last_price
    if (len(bars) < 20 or price is None or daily.last_price_time is None
            or now - daily.last_price_time > MAX_PRICE_AGE):
        return
    atr = indicators.atr(bars.high, bars.low, bars.close)
    prev = bars.close[-1]
    if not atr or prev <= 0:
        return
    move = price - prev
    ratio = abs(move) / atr
    today = now.strftime("%Y-%m-%d")
    seen = st.setdefault("big_moves", {})
    if ratio < BIG_MOVE_ATR or seen.get(inst.key) == today:
        return
    seen[inst.key] = today
    pos = st["open"].get(inst.key)
    emit(messages.big_move(inst, move, prev, price, ratio, pos["direction"] if pos else None))


def trend_row(inst: Instrument, daily: Bars, now: datetime) -> str:
    t = strategy.trend(completed_daily(daily, now))
    label = {1: "🟢 rialzista", -1: "🔴 ribassista", 0: "⚪ laterale"}[t]
    return f"{inst.name}: {label} · {messages.f(daily.last_price, inst.decimals)}"


def run(now: datetime | None = None, dry_run: bool = False, fetcher: Fetcher = fetch,
        sender: Callable[[str], bool] = notify.send, st: dict | None = None,
        context_fetcher: Callable[[], dict | None] | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    st = st if st is not None else state_mod.load()
    out: list[str] = []

    def emit(text: str) -> None:
        out.append(text)

    eurusd = None
    try:
        eurusd = fetcher("EURUSD=X", range_="5d", interval="1d").last_price
    except DataError as exc:
        log.warning("Cambio EUR/USD non disponibile: %s", exc)

    rows = []
    dailies: dict[str, Bars] = {}
    sputnik_ctx: dict | None = None   # scaricato solo se serve (quando c'è un nuovo segnale)
    for inst in enabled_instruments():
        try:
            daily = fetcher(inst.yahoo, range_="2y", interval="1d")
        except DataError as exc:
            log.warning("%s: %s", inst.name, exc)
            rows.append(f"{inst.name}: dati non disponibili")
            errors = st.setdefault("errors", {})
            errors["dati mancanti"] = errors.get("dati mancanti", 0) + 1
            continue
        rows.append(trend_row(inst, daily, now))
        check_big_move(inst, daily, now, st, emit)
        dailies[inst.key] = daily

        if inst.key in rebound.KEYS and os.getenv("CFD_REBOUND", "1").strip() != "0":
            rb = st.setdefault("rebound", {})
            for part, empty in (("open", {}), ("closed", []), ("last_eval", {})):
                rb.setdefault(part, empty)
            rb_hourly = None
            if inst.key in rb["open"]:
                try:
                    rb_hourly = fetcher(inst.yahoo, range_="1mo", interval="1h")
                except DataError:
                    rb_hourly = None
            rebound.process(inst, daily, rb_hourly, now, rb,
                            lambda entry, stop: size_position(entry, stop, eurusd), emit)

        pos = st["open"].get(inst.key)
        if pos:
            try:
                hourly = fetcher(inst.yahoo, range_="1mo", interval="1h")
            except DataError:
                hourly = None
            done = manage_open(inst, pos, daily, hourly, now)
            if done:
                st["open"].pop(inst.key)
                st["closed"].append(done)
                emit(messages.closed(inst, done, stats(st)))
                log.info("%s chiusa: %s %+.2fR", inst.name, done["exit_reason"], done["r"])
            continue

        bars = completed_daily(daily, now)
        bar_id = bars.time[-1].strftime("%Y-%m-%d") if len(bars) else ""
        if st["last_eval"].get(inst.key) == bar_id:
            continue
        sig, why = new_signal(inst, daily, now, eurusd)
        log.info("%s: barra %s → %s", inst.name, bar_id, why)
        if why == "mercato chiuso":
            continue  # riprova quando il mercato riapre
        st["last_eval"][inst.key] = bar_id
        if sig:
            if sputnik_ctx is None:
                sputnik_ctx = (context_fetcher or sputnik_context.fetch)() or {}
            sig["sputnik"] = sputnik_context.annotate(inst.key, sig["direction"], sputnik_ctx or None, now)
            st["open"][inst.key] = sig
            emit(messages.new_signal(inst, sig))

    today = now.strftime("%Y-%m-%d")
    if now.hour >= SUMMARY_HOUR_UTC and st.get("last_summary") != today and now.weekday() < 5:
        open_lines = [f"{BY_KEY[k].name} {p['direction']} da {messages.f(p['entry'], BY_KEY[k].decimals)} "
                      f"(stop {messages.f(p['stop'], BY_KEY[k].decimals)}, target {messages.f(p['target'], BY_KEY[k].decimals)})"
                      for k, p in st["open"].items() if k in BY_KEY]
        emit(messages.daily_summary(rows, open_lines, stats(st)))
        st["last_summary"] = today

    if vol_alert.due(st, now) and dailies:
        text = vol_alert.build(dailies, now, fetcher)
        if text:
            emit(text)
        vol_alert.mark_sent(st, now)

    if report_card.due(st, now):
        emit(report_card.build(st, now))
        report_card.mark_sent(st, now)

    queue = st["outbox"] + out
    st["outbox"] = []
    for text in queue:
        if dry_run:
            print("\n" + "=" * 60 + "\n" + text)
        elif not sender(text):
            st["outbox"].append(text)
            errors = st.setdefault("errors", {})
            errors["invii Telegram falliti"] = errors.get("invii Telegram falliti", 0) + 1
    if st["outbox"]:
        log.warning("%d messaggi non inviati, riprovo al prossimo giro", len(st["outbox"]))
    return st


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", help="stampa i messaggi senza inviarli né salvare lo stato")
    args = p.parse_args()
    dry = args.dry_run or not notify.configured()
    if dry and not args.dry_run:
        log.warning("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID non impostati: anteprima senza invio e senza salvare lo stato")
    st = run(dry_run=dry, st=state_mod.load() if not dry else state_mod.empty())
    if not dry:
        state_mod.save(st)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
