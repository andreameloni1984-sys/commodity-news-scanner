"""Bollettino del giorno e avvisi "zona pericolosa" (versione leggera, solo informativa).

    python -m cfdbot.briefing            # invia ciò che è in programma adesso
    python -m cfdbot.briefing --dry-run  # stampa soltanto

* Bollettino (giorni feriali, dalle 8:30 ora di Roma, una volta al giorno): per oro, petrolio,
  S&P 500 e Nasdaq il trend tecnico e la posizione rispetto ai massimi/minimi a 20 giorni,
  i dati USA importanti di oggi con l'ora italiana, le notizie di Trump delle ultime 24 ore
  (da Sputnik) e le posizioni CFD aperte del bot.
* Zona pericolosa: 30 minuti prima di ogni dato USA ad alto impatto, un avviso con gli
  strumenti coinvolti e la finestra da evitare (15 minuti prima e dopo).

Nessuna direzione combinata e nessuna probabilità: solo i fatti ordinati. La previsione
combinata arriverà quando il pagellino avrà misurato quanto vale ogni fattore.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import datetime, time, timedelta, timezone
from typing import Callable
from zoneinfo import ZoneInfo

import requests

from . import notify, sputnik_context, strategy
from . import state as state_mod
from .data import DataError, completed_daily, fetch
from .instruments import BY_KEY

log = logging.getLogger("cfdbot.briefing")
ROME = ZoneInfo("Europe/Rome")
CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
BRIEF_AT = time(8, 30)
WARN_BEFORE = timedelta(minutes=30)
AVOID = timedelta(minutes=15)
BRIEF_KEYS = ("oro", "wti", "sp500", "nasdaq")

# Quali strumenti muove ciascun tipo di dato
OIL_WORDS = ("crude oil", "oil inventories")
ALL_INDICES_GOLD = ("oro", "sp500", "nasdaq")


def affected(title: str) -> tuple[str, ...]:
    t = title.lower()
    if any(w in t for w in OIL_WORDS):
        return ("wti",)
    return ALL_INDICES_GOLD + ("wti",) if any(w in t for w in ("fomc", "federal funds", "fed chair")) else ALL_INDICES_GOLD


def is_relevant(event: dict) -> bool:
    if event.get("country") != "USD":
        return False
    title = str(event.get("title", "")).lower()
    return event.get("impact") == "High" or any(w in title for w in OIL_WORDS)


def fetch_calendar() -> list[dict]:
    try:
        r = requests.get(CALENDAR_URL, timeout=15, headers={"User-Agent": "Mozilla/5.0 (Gagarin briefing)"})
        r.raise_for_status()
        rows = r.json()
        return rows if isinstance(rows, list) else []
    except (requests.RequestException, ValueError) as exc:
        log.warning("Calendario non disponibile: %s", type(exc).__name__)
        return []


def _when(event: dict) -> datetime | None:
    try:
        return datetime.fromisoformat(str(event.get("date", ""))).astimezone(timezone.utc)
    except ValueError:
        return None


def todays_events(calendar: list[dict], now: datetime) -> list[tuple[datetime, dict]]:
    day = now.astimezone(ROME).date()
    out = []
    for e in calendar:
        t = _when(e)
        if t and is_relevant(e) and t.astimezone(ROME).date() == day:
            out.append((t, e))
    return sorted(out, key=lambda x: x[0])


def _event_line(t: datetime, e: dict) -> str:
    extra = []
    if e.get("forecast"):
        extra.append(f"previsto {e['forecast']}")
    if e.get("previous"):
        extra.append(f"precedente {e['previous']}")
    names = ", ".join(BY_KEY[k].name for k in affected(e["title"]))
    return (f"• {t.astimezone(ROME):%H:%M} {e['title']}" + (f" ({', '.join(extra)})" if extra else "")
            + f" → {names}")


def technical_line(key: str, fetcher: Callable, now: datetime) -> str:
    inst = BY_KEY[key]
    try:
        daily = fetcher(inst.yahoo, range_="2y", interval="1d")
    except DataError:
        return f"• {inst.name}: dati non disponibili"
    bars = completed_daily(daily, now)
    t = strategy.trend(bars)
    label = {1: "🟢 trend rialzista", -1: "🔴 trend ribassista", 0: "⚪ laterale"}[t]
    price = daily.last_price or bars.close[-1]
    hi20, lo20 = max(bars.high[-20:]), min(bars.low[-20:])
    if price >= hi20:
        pos = "sui massimi a 20 giorni"
    elif price <= lo20:
        pos = "sui minimi a 20 giorni"
    elif hi20 > lo20:
        share = (price - lo20) / (hi20 - lo20)
        pos = ("vicino ai minimi a 20 giorni" if share < 0.15 else "vicino ai massimi a 20 giorni" if share > 0.85
               else f"dentro il range di 20 giorni ({share:.0%} sopra il minimo)")
    else:
        pos = ""
    return f"• {inst.name}: {label}, {pos}"


def trump_lines(ctx: dict | None, now: datetime) -> list[str]:
    if not ctx:
        return ["• notizie Sputnik non disponibili"]
    lines = []
    for item in (ctx.get("trump") or [])[:4]:
        biases = [f"{b['instrument']} {'⬆️' if 'LONG' in str(b.get('bias', '')).upper() else '⬇️'}"
                  for b in item.get("bias") or []]
        lines.append(f"• {item.get('title', '')[:120]}" + (f" ({', '.join(biases)})" if biases else ""))
    return lines or ["• nessun post rilevante nelle ultime 24 ore"]


def morning_brief(now: datetime, calendar: list[dict], fetcher: Callable, ctx: dict | None, st: dict) -> str:
    local = now.astimezone(ROME)
    days = ("lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica")
    lines = [f"🗞️ BOLLETTINO GAGARIN — {days[local.weekday()]} {local:%d/%m}", ""]
    lines.append("📈 Quadro tecnico")
    lines += [technical_line(k, fetcher, now) for k in BRIEF_KEYS]
    events = todays_events(calendar, now)
    lines += ["", "📅 Dati USA importanti oggi (ora italiana)"]
    if events:
        lines += [_event_line(t, e) for t, e in events]
        windows = ", ".join(f"{(t - AVOID).astimezone(ROME):%H:%M}–{(t + AVOID).astimezone(ROME):%H:%M}" for t, _ in events)
        lines.append(f"⚠️ Zone pericolose: {windows}. Meglio non aprire CFD sugli strumenti coinvolti.")
    else:
        lines.append("• nessun dato ad alto impatto" + ("" if calendar else " (calendario non disponibile)"))
    lines += ["", "🇺🇸 Trump nelle ultime 24 ore (Sputnik)"] + trump_lines(ctx, now)
    open_pos = st.get("open") or {}
    lines += ["", "📂 Posizioni CFD aperte dal bot: " + (", ".join(
        f"{BY_KEY[k].name} {p['direction']}" for k, p in open_pos.items() if k in BY_KEY) or "nessuna")]
    lines += ["", "ℹ️ Solo informazioni, nessuna previsione combinata: arriverà quando il pagellino avrà misurato "
                  "quanto vale ogni fattore."]
    return "\n".join(lines)


def danger_alert(t: datetime, e: dict, now: datetime) -> str:
    names = ", ".join(BY_KEY[k].name for k in affected(e["title"]))
    minutes = max(1, round((t - now).total_seconds() / 60))
    extra = f" · previsto {e['forecast']}, precedente {e.get('previous') or 'n.d.'}" if e.get("forecast") else ""
    return "\n".join([
        f"⚠️ ZONA PERICOLOSA — tra {minutes} minuti: {e['title']} ({t.astimezone(ROME):%H:%M}){extra}",
        f"Strumenti coinvolti: {names}.",
        f"Evita di aprire CFD dalle {(t - AVOID).astimezone(ROME):%H:%M} alle {(t + AVOID).astimezone(ROME):%H:%M}: "
        "movimenti bruschi e spread più larghi.",
    ])


def run(now: datetime | None = None, fetcher: Callable = fetch, calendar_fetcher: Callable[[], list] = fetch_calendar,
        context_fetcher: Callable[[], dict | None] | None = None, send: Callable[[str], bool] = notify.send,
        st: dict | None = None, cfd_state: dict | None = None, dry_run: bool = False) -> dict:
    now = now or datetime.now(timezone.utc)
    st = st if st is not None else {}
    local = now.astimezone(ROME)
    if local.weekday() > 4:
        return st
    out: list[str] = []
    calendar = calendar_fetcher()
    today = local.date().isoformat()
    if local.time() >= BRIEF_AT and st.get("brief_date") != today:
        ctx = (context_fetcher or sputnik_context.fetch)()
        out.append(morning_brief(now, calendar, fetcher, ctx, cfd_state or {}))
        st["brief_date"] = today
    warned = st.setdefault("warned", {})
    for t, e in todays_events(calendar, now):
        key = f"{t.isoformat()}|{e['title']}"
        if key not in warned and timedelta(0) < t - now <= WARN_BEFORE + timedelta(minutes=10):
            out.append(danger_alert(t, e, now))
            warned[key] = now.isoformat()
    st["warned"] = {k: v for k, v in warned.items() if v >= (now - timedelta(days=3)).isoformat()}
    for text in out:
        if dry_run:
            print("\n" + text)
        elif not send(text):
            log.warning("Invio non riuscito")
    return st


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    path = os.getenv("BRIEF_STATE_PATH", "data/brief_state.json")
    try:
        st = json.loads(open(path, encoding="utf-8").read())
    except (OSError, ValueError):
        st = {}
    cfd_state = state_mod.load()
    dry = args.dry_run or not notify.configured()
    st = run(st=st, cfd_state=cfd_state, dry_run=dry)
    if not dry:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(st, fh)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
