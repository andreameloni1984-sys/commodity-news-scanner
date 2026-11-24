"""Bollettino del giorno e avvisi "zona pericolosa" (versione leggera, solo informativa).

    python -m cfdbot.briefing            # invia ciò che è in programma adesso
    python -m cfdbot.briefing --dry-run  # stampa soltanto

* Bollettino (giorni feriali, dalle 8:30 ora di Roma, una volta al giorno): per oro, petrolio,
  S&P 500 e Nasdaq il trend tecnico e la posizione rispetto ai massimi/minimi a 20 giorni,
  i dati USA importanti di oggi con l'ora italiana, le notizie di Trump delle ultime 24 ore
  (da Sputnik) e le posizioni CFD aperte del bot.
* Zona pericolosa: 30 minuti prima di ogni dato USA ad alto impatto, un avviso con gli
  strumenti coinvolti e la finestra da evitare (15 minuti prima e dopo).
* Avviso leggero 🟡: 15 minuti prima dei dati USA di importanza media (PMI, fiducia, case…).

Nessuna direzione combinata e nessuna probabilità: solo i fatti ordinati. La previsione
combinata arriverà quando il pagellino avrà misurato quanto vale ogni fattore.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
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
WARN_MEDIUM = timedelta(minutes=15)
AVOID_MEDIUM = timedelta(minutes=5)
BRIEF_KEYS = ("oro", "wti", "sp500", "nasdaq")

# Quali strumenti muove ciascun tipo di dato
OIL_WORDS = ("crude oil", "oil inventories")
ALL_INDICES_GOLD = ("oro", "sp500", "nasdaq")


def affected(title: str) -> tuple[str, ...]:
    t = title.lower()
    if any(w in t for w in OIL_WORDS):
        return ("wti",)
    return ALL_INDICES_GOLD + ("wti",) if any(w in t for w in ("fomc", "federal funds", "fed chair")) else ALL_INDICES_GOLD


def is_major(event: dict) -> bool:
    """Dati che aprono una zona pericolosa: alto impatto, più le scorte di petrolio."""
    title = str(event.get("title", "")).lower()
    return event.get("impact") == "High" or any(w in title for w in OIL_WORDS)


def is_relevant(event: dict) -> bool:
    if event.get("country") != "USD":
        return False
    if is_major(event):
        return True
    # Importanza media (PMI, fiducia, case, ordini): avviso leggero. I discorsi no: troppo vaghi.
    return event.get("impact") == "Medium" and "speaks" not in str(event.get("title", "")).lower()


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
    mark = "🔴" if is_major(e) else "🟡"
    level = "" if is_major(e) else " [importanza media]"
    return (f"• {mark} {t.astimezone(ROME):%H:%M} {e['title']}{level}" + (f" ({', '.join(extra)})" if extra else "")
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


EMPTY_POST = re.compile(r"^(quote post|repost|post|video|photo)( from .*)?$", re.I)
# Parole che collegano un post agli strumenti seguiti (oltre alle indicazioni di Sputnik)
TOPIC_WORDS = {
    "wti": ("oil", "crude", "gasoline", "opec", "drill", "petroleum", "energy prices"),
    "oro": ("gold",),
    "sp500": ("stock market", "stock markets", "stocks", "the market", "dow", "s&p", "trillion dollars", "wall street"),
    "nasdaq": ("nasdaq", "tech stocks"),
}
MAX_TRUMP_CHARS = 220


def short_text(text: str, limit: int = MAX_TRUMP_CHARS) -> str:
    """Testo fino all'ultima frase completa (o all'ultima parola intera) entro il limite."""
    text = " ".join(text.split())
    clipped = len(text) > limit or (len(text) >= 190 and text[-1] not in ".!?\"”")
    if not clipped:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    if end >= 60:
        return cut[:end + 1]
    return cut.rsplit(" ", 1)[0].rstrip(",;:") + "…"


def post_instruments(item: dict) -> dict[str, str]:
    """Strumenti CFD toccati dal post → freccia di Sputnik ("⬆️"/"⬇️") o "" se solo per argomento."""
    found: dict[str, str] = {}
    for b in item.get("bias") or []:
        up = "LONG" in str(b.get("bias", "")).upper()
        for key, factor in sputnik_context.INSTRUMENT_MAP.get(str(b.get("instrument", "")).upper(), {}).items():
            found[key] = "⬆️" if up == (factor > 0) else "⬇️"
    text = str(item.get("title", "")).lower()
    for key, words in TOPIC_WORDS.items():
        if key not in found and any(re.search(rf"\b{re.escape(w)}\b", text) for w in words):
            found[key] = ""
    return found


def trump_lines(ctx: dict | None, now: datetime) -> list[str]:
    if not ctx:
        return ["• notizie Sputnik non disponibili"]
    posts = []
    for item in ctx.get("trump") or []:
        title = str(item.get("title", "")).strip()
        if not title or EMPTY_POST.match(title):
            continue
        try:
            published = datetime.fromisoformat(str(item.get("published")))
            if now - published > timedelta(hours=24):
                continue
        except ValueError:
            pass
        posts.append((post_instruments(item), item))
    posts.sort(key=lambda p: not p[0])   # prima i post che toccano i nostri strumenti
    lines = []
    for keys, item in posts[:4]:
        tags = ", ".join(f"{BY_KEY[k].name} {arrow}".strip() for k, arrow in keys.items() if k in BY_KEY)
        lines.append(f"• {short_text(item['title'])}" + (f"\n   → {tags}" if tags else ""))
    return lines or ["• nessun post rilevante nelle ultime 24 ore"]


def macro_lines(fetcher: Callable, calendar: list[dict], now: datetime) -> list[str]:
    """Dollaro, rendimento del decennale USA e riunioni OPEC+ della settimana (solo informazione)."""
    lines = []
    try:
        dxy = fetcher("DX-Y.NYB", range_="1mo", interval="1d")
        last, week = dxy.last_price or dxy.close[-1], dxy.close[-6]
        chg = (last / week - 1) * 100
        note = (" → pressione sull'oro" if chg >= 1 else " → sostegno all'oro" if chg <= -1 else "")
        lines.append(f"• Dollaro (indice DXY): {last:.1f}, {chg:+.1f}% in una settimana{note}".replace(".", ","))
    except (DataError, IndexError, TypeError):
        lines.append("• Dollaro: dato non disponibile")
    try:
        tnx = fetcher("^TNX", range_="1mo", interval="1d")
        last, week = tnx.last_price or tnx.close[-1], tnx.close[-6]
        bp = (last - week) * 100
        note = (" → pressione su oro e Nasdaq" if bp >= 15 else " → sostegno a oro e Nasdaq" if bp <= -15 else "")
        lines.append(f"• Rendimento titoli di Stato USA a 10 anni: {last:.2f}%, {bp:+.0f} punti base in una settimana{note}"
                     .replace(".", ","))
    except (DataError, IndexError, TypeError):
        lines.append("• Tassi USA: dato non disponibile")
    for e in calendar:
        if "opec" in str(e.get("title", "")).lower():
            t = _when(e)
            if t and timedelta(0) <= t - now <= timedelta(days=7):
                days = ("lun", "mar", "mer", "gio", "ven", "sab", "dom")
                lines.append(f"• 🛢️ {e['title']}: {days[t.astimezone(ROME).weekday()]} {t.astimezone(ROME):%d/%m %H:%M} "
                             "→ possibile scossone sul petrolio")
    return lines


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
        windows = ", ".join(f"{(t - AVOID).astimezone(ROME):%H:%M}–{(t + AVOID).astimezone(ROME):%H:%M}"
                            for t, e in events if is_major(e))
        if windows:
            lines.append(f"⚠️ Zone pericolose: {windows}. Meglio non aprire CFD sugli strumenti coinvolti.")
        if any(not is_major(e) for _, e in events):
            lines.append("🟡 Dati di importanza media: possibili scatti per qualche minuto, ti avviso 15 minuti prima.")
    else:
        lines.append("• nessun dato ad alto impatto" + ("" if calendar else " (calendario non disponibile)"))
    lines += ["", "💵 Dollaro, tassi e petrolio (variabili che muovono oro e indici)"] + macro_lines(fetcher, calendar, now)
    lines += ["", "🇺🇸 Trump nelle ultime 24 ore (Sputnik)"] + trump_lines(ctx, now)
    open_pos = st.get("open") or {}
    lines += ["", "📂 Posizioni CFD aperte dal bot: " + (", ".join(
        f"{BY_KEY[k].name} {p['direction']}" for k, p in open_pos.items() if k in BY_KEY) or "nessuna")]
    lines += ["", "ℹ️ Solo informazioni, nessuna previsione combinata: arriverà quando il pagellino avrà misurato "
                  "quanto vale ogni fattore."]
    return "\n".join(lines)


def _titles(es: list[dict]) -> str:
    parts = []
    for e in es:
        extra = f" (previsto {e['forecast']}, precedente {e.get('previous') or 'n.d.'})" if e.get("forecast") else ""
        parts.append(f"{e['title']}{extra}")
    return " · ".join(parts)


def _names(es: list[dict]) -> str:
    keys = []
    for e in es:
        keys += [k for k in affected(e["title"]) if k not in keys]
    return ", ".join(BY_KEY[k].name for k in keys)


def danger_alert(t: datetime, es, now: datetime) -> str:
    es = es if isinstance(es, list) else [es]
    minutes = max(1, round((t - now).total_seconds() / 60))
    return "\n".join([
        f"⚠️ ZONA PERICOLOSA — tra {minutes} minuti ({t.astimezone(ROME):%H:%M}): {_titles(es)}",
        f"Strumenti coinvolti: {_names(es)}.",
        f"Evita di aprire CFD dalle {(t - AVOID).astimezone(ROME):%H:%M} alle {(t + AVOID).astimezone(ROME):%H:%M}: "
        "movimenti bruschi e spread più larghi.",
    ])


def medium_alert(t: datetime, es, now: datetime) -> str:
    es = es if isinstance(es, list) else [es]
    minutes = max(1, round((t - now).total_seconds() / 60))
    return "\n".join([
        f"🟡 ATTENZIONE — tra {minutes} minuti ({t.astimezone(ROME):%H:%M}): {_titles(es)}",
        f"Dati di importanza media: possibili scatti su {_names(es)} "
        f"dalle {(t - AVOID_MEDIUM).astimezone(ROME):%H:%M} alle {(t + AVOID_MEDIUM).astimezone(ROME):%H:%M}.",
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
    groups: dict[tuple[datetime, bool], list[dict]] = {}
    for t, e in todays_events(calendar, now):
        key = f"{t.isoformat()}|{e['title']}"
        lead = WARN_BEFORE if is_major(e) else WARN_MEDIUM
        if key not in warned and timedelta(0) < t - now <= lead + timedelta(minutes=10):
            groups.setdefault((t, is_major(e)), []).append(e)
            warned[key] = now.isoformat()
    for (t, major), es in sorted(groups.items(), key=lambda g: (g[0][0], not g[0][1])):
        out.append(danger_alert(t, es, now) if major else medium_alert(t, es, now))
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
