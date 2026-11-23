"""Pagellino del bot CFD: risultati dal vivo dei segnali (non del backtest).

Ogni segnale viene seguito fino a target, stop o scadenza (5 giorni) sui livelli
indicati nel messaggio; il risultato è in R (1R = rischio del segnale).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .instruments import BY_KEY

ROME = ZoneInfo("Europe/Rome")
REPORT_WEEKDAY = 5      # sabato
REPORT_HOUR = 9


def _line(rows: list[dict]) -> str:
    if not rows:
        return "nessun segnale chiuso"
    wins = sum(1 for r in rows if r["r"] > 0)
    total = sum(r["r"] for r in rows)
    return f"{len(rows)} chiusi · vincenti {wins}/{len(rows)} ({wins / len(rows):.0%}) · totale {total:+.1f}R · media {total / len(rows):+.2f}R"


def build(st: dict, now: datetime) -> str:
    closed = st.get("closed", [])
    week_ago = now - timedelta(days=7)
    week = [c for c in closed if datetime.fromisoformat(c.get("closed_at", "1970-01-01T00:00:00+00:00")) >= week_ago]
    lines = ["📊 PAGELLINO GAGARIN (bot CFD) — risultati dal vivo", ""]
    lines.append("Ultimi 7 giorni: " + _line(week))
    for c in week[-8:]:
        name = BY_KEY[c["key"]].name if c.get("key") in BY_KEY else c.get("key", "?")
        lines.append(f"• {name} {c['direction']} → {c['exit_reason']} {c['r']:+.2f}R")
    lines += ["", "Da quando è attivo: " + _line(closed)]
    by_inst: dict[str, list[dict]] = {}
    for c in closed:
        by_inst.setdefault(c.get("key", "?"), []).append(c)
    for key, rows in sorted(by_inst.items()):
        name = BY_KEY[key].name if key in BY_KEY else key
        lines.append(f"• {name}: {_line(rows)}")
    verdicts: dict[str, list[dict]] = {}
    for c in closed:
        v = (c.get("sputnik") or {}).get("trump")
        if v:
            verdicts.setdefault(v, []).append(c)
    if verdicts:
        lines += ["", "Con il contesto Trump di Sputnik:"]
        for v in ("favore", "contro", "misto", "neutro", "n.d."):
            if v in verdicts:
                lines.append(f"• Trump {v}: {_line(verdicts[v])}")
    rb = st.get("rebound") or {}
    rb_closed = rb.get("closed") or []
    if rb_closed or rb.get("open"):
        rb_week = [c for c in rb_closed
                   if datetime.fromisoformat(c.get("closed_at", "1970-01-01T00:00:00+00:00")) >= week_ago]
        lines += ["", "🔄 Rimbalzo indici (in osservazione)",
                  "Ultimi 7 giorni: " + _line(rb_week), "Da quando è attivo: " + _line(rb_closed),
                  f"Aperte: {len(rb.get('open') or {})} · atteso dal test: ~67% vincenti"]
    open_now = st.get("open", {})
    lines += ["", f"Posizioni ancora aperte: {len(open_now)}"]
    errors = st.get("errors", {})
    if errors:
        lines.append("Problemi tecnici registrati: " + ", ".join(f"{k} {v}" for k, v in sorted(errors.items())))
    else:
        lines.append("Problemi tecnici registrati: nessuno")
    lines += ["", "Confronto atteso dal backtest (10 anni): ~52% vincenti, +0,07R a segnale. "
              "Servono almeno 30 segnali chiusi per un giudizio affidabile."]
    return "\n".join(lines)


def due(st: dict, now: datetime) -> bool:
    local = now.astimezone(ROME)
    week_id = f"{local.isocalendar().year}-W{local.isocalendar().week:02d}"
    return local.weekday() == REPORT_WEEKDAY and local.hour >= REPORT_HOUR and st.get("last_report_week") != week_id


def mark_sent(st: dict, now: datetime) -> None:
    local = now.astimezone(ROME)
    st["last_report_week"] = f"{local.isocalendar().year}-W{local.isocalendar().week:02d}"
