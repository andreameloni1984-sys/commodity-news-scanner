"""Contesto da Sputnik (notizie di Trump e mosse dei miliardari) per i segnali CFD.

Fase 1: solo informazione. Il segnale tecnico non cambia; si aggiungono due righe
al messaggio e si registra se Trump era a favore, contro o neutro (per misurarlo poi).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

import requests

log = logging.getLogger(__name__)

DEFAULT_URL = "https://raw.githubusercontent.com/andreameloni1984-sys/trump-trucker/main/sputnik_context.json"

# Strumenti di Sputnik → strumenti del bot CFD (fattore +1 stessa direzione, -1 opposta)
INSTRUMENT_MAP = {
    "GOLD": {"oro": 1},
    "WTI": {"wti": 1},
    "BRENT": {"wti": 1},
    "NASDAQ100": {"nasdaq": 1, "sp500": 1},
    "USD": {"eurusd": -1},
}

# Temi delle operazioni dei miliardari → strumenti CFD collegati
MONEY_THEMES = {
    "oro": {"METALS"},
    "wti": {"ENERGY"},
    "nasdaq": {"AI_TECH"},
    "sp500": {"AI_TECH", "FINANCE", "PHARMA", "DEFENSE", "AUTO"},
    "eurusd": set(),
}

THEME_LABELS = {"METALS": "metalli/miniere", "ENERGY": "energia", "AI_TECH": "tecnologia/AI",
                "FINANCE": "finanza", "PHARMA": "farmaceutico", "DEFENSE": "difesa", "AUTO": "auto"}


def fetch(url: str | None = None) -> dict | None:
    url = url or os.getenv("SPUTNIK_CONTEXT_URL", DEFAULT_URL)
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, dict) else None
    except (requests.RequestException, ValueError) as exc:
        log.warning("Contesto Sputnik non disponibile: %s", type(exc).__name__)
        return None


def _time(value: str) -> datetime | None:
    try:
        t = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def _art(direction: str) -> str:
    return "lo SHORT" if direction == "SHORT" else "il LONG"


def trump_view(key: str, direction: str, ctx: dict | None, now: datetime) -> tuple[str, str]:
    """Restituisce (riga del messaggio, verdetto: favore/contro/misto/neutro/n.d.)."""
    if ctx is None:
        return "🇺🇸 Trump: contesto Sputnik non disponibile", "n.d."
    want = 1 if direction == "LONG" else -1
    votes: list[tuple[int, dict, str]] = []
    for item in ctx.get("trump") or []:
        t = _time(item.get("published", ""))
        if t is None or now - t > timedelta(hours=24):
            continue
        for b in item.get("bias") or []:
            factor = INSTRUMENT_MAP.get(str(b.get("instrument", "")).upper(), {}).get(key)
            if not factor:
                continue
            sign = 1 if "LONG" in str(b.get("bias", "")).upper() else -1
            votes.append((sign * factor, item, str(b.get("reason") or "")))
    if not votes:
        return "🇺🇸 Trump (24h): nessuna notizia che tocchi questo strumento", "neutro"
    pro = [v for v in votes if v[0] == want]
    con = [v for v in votes if v[0] != want]
    _, item, reason = (con or pro)[0] if con else pro[0]
    title = item.get("title", "")[:110]
    if pro and con:
        return f"🇺🇸 Trump (24h): segnali misti — es. «{title}»", "misto"
    if con:
        return f"🇺🇸 Trump (24h): ⚠️ CONTRO {_art(direction)} — «{title}» ({reason}). Valuta di saltare o dimezzare.", "contro"
    return f"🇺🇸 Trump (24h): ✅ a favore {"dello SHORT" if direction == "SHORT" else "del LONG"} — «{title}» ({reason})", "favore"


def money_view(key: str, direction: str, ctx: dict | None) -> tuple[str, str]:
    if ctx is None:
        return "💰 Miliardari: contesto Sputnik non disponibile", "n.d."
    themes = MONEY_THEMES.get(key, set())
    if not themes:
        return "💰 Miliardari: nessun collegamento diretto con questo strumento", "neutro"
    trades, holders = [], []
    for m in ctx.get("money") or []:
        hit = themes & set(m.get("themes") or [])
        if not hit:
            continue
        if m.get("kind") == "TRADE":
            sign = 1 if m.get("action") == "ACQUISTATO" else -1
            trades.append((sign, m, hit))
        else:
            holders.append((m, hit))
    want = 1 if direction == "LONG" else -1
    if trades:
        sign, m, hit = trades[0]
        verb = "ha comprato" if sign > 0 else "ha venduto"
        verdict = "favore" if sign == want else "contro"
        mark = "✅ coerente" if verdict == "favore" else "⚠️ in senso opposto"
        return (f"💰 Miliardari: {m['who']} {verb} {m.get('issuer') or m.get('security', '')} "
                f"({m.get('filed', '')}) · {mark}", verdict)
    if holders:
        names = list(dict.fromkeys(h[0]["who"].split(" · ")[0] for h in holders[:3]))
        labels = ", ".join(sorted({THEME_LABELS.get(t, t) for h in holders for t in h[1]}))
        verb = "ha" if len(names) == 1 else "hanno"
        return f"💰 Miliardari: {', '.join(names)} {verb} posizioni su {labels} (13F, dati trimestrali)", "neutro"
    return "💰 Miliardari: nessuna mossa recente collegata", "neutro"


def annotate(key: str, direction: str, ctx: dict | None, now: datetime) -> dict:
    t_line, t_verdict = trump_view(key, direction, ctx, now)
    m_line, m_verdict = money_view(key, direction, ctx)
    return {"trump": t_verdict, "money": m_verdict, "lines": [t_line, m_line]}
