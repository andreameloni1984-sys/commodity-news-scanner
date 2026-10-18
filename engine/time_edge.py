"""Parallel time-of-day research desk for Aggressive 212.

This module is strictly informational: it never changes the normal aggressive
ranking, thresholds, setup decisions, risk, or execution. No orders are placed.
Historical profitability is not claimed unless validated trade-log statistics
are supplied in a future version.
"""
from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo
from typing import Any, Iterable

from engine.prediction_ranker import rank_predictions

ROME = ZoneInfo("Europe/Rome")


def _session_context(now: datetime | None = None) -> dict[str, Any]:
    now = (now or datetime.now(ROME)).astimezone(ROME)
    day = now.date()
    # US/EU daylight-saving transition weeks (Italian local time).
    if day < __import__("datetime").date(2026, 10, 26):
        overlap = (time(15, 0), time(19, 0))
        wall_open = time(15, 30)
    elif day < __import__("datetime").date(2026, 11, 2):
        overlap = (time(14, 0), time(19, 0))
        wall_open = time(14, 30)
    else:
        overlap = (time(14, 0), time(18, 0))
        wall_open = time(15, 30)

    t = now.time().replace(tzinfo=None)
    if time(8, 0) <= t <= time(11, 0):
        active = "SESSIONE EUROPEA 08:00–11:00"
        note = "Finestra da osservare per metalli e petrolio; il vantaggio netto non è dimostrato."
    elif overlap[0] <= t <= overlap[1]:
        if wall_open <= t <= time(18, 0):
            active = "OVERLAP / APERTURA USA"
        else:
            active = "OVERLAP LONDRA–USA"
        note = "Finestra candidata per studiare volatilità e segnali; più movimento non equivale a più profitto."
    elif time(11, 0) < t < overlap[0]:
        active = "FASCIA INTERMEDIA"
        note = "Nessun vantaggio orario confermato: confrontare i risultati netti registrati."
    else:
        active = "FUORI DALLE FINESTRE PRIORITARIE DI STUDIO"
        note = "Il desk normale resta invariato; questa nota non blocca né promuove segnali."
    return {
        "now": now.strftime("%d/%m/%Y %H:%M"),
        "active": active,
        "note": note,
        "overlap": f"{overlap[0].strftime('%H:%M')}–{overlap[1].strftime('%H:%M')}",
        "wall_open": wall_open.strftime("%H:%M"),
    }


def format_time_edge_desk(states: Iterable[Any], now: datetime | None = None) -> str:
    """Render an independent time-window commentary; does not alter desk output."""
    context = _session_context(now)
    ranked = rank_predictions(states)
    lines = [
        "🧠 AGGRESSIVE 212 — CERVELLO PARALLELO TIME EDGE",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "SOLO ANALISI | NON MODIFICA IL DESK AGGRESSIVE 212",
        f"Ora italiana: {context['now']}",
        f"Fascia corrente: {context['active']}",
        f"Overlap di riferimento: {context['overlap']} | apertura USA: {context['wall_open']}",
        context["note"],
        "",
        "CANDIDATI OSSERVATI (stesso universo; soglie e ranking originali intatti):",
    ]
    if not ranked:
        lines.append("Dati insufficienti per un confronto dei candidati.")
    else:
        for i, item in enumerate(ranked[:3], 1):
            name = str(item.get("commodity") or "Strumento")
            direction = str(item.get("direction") or "N/D")
            lines.append(
                f"{i}. {name} — {direction} | score desk {float(item.get('score') or 0):.1f}/100"
            )
            lname = name.lower()
            if any(x in lname for x in ("oro", "gold", "wti", "brent", "petrolio", "oil")):
                lines.append("   Finestra da confrontare: sessione europea e overlap USA.")
            elif any(x in lname for x in ("argento", "silver", "platino", "palladio")):
                lines.append("   Finestra da confrontare: soprattutto overlap USA; verificare sul log.")
            else:
                lines.append("   Finestra migliore: non determinabile senza statistiche per strumento e orario.")
    lines.extend([
        "",
        "STATO DELLA PROVA: SPERIMENTALE.",
        "15:30–18:00 è una candidata per lo studio del movimento, non una fascia dimostrata come più redditizia.",
        "Per dichiarare un vantaggio servono trade chiusi per strumento/fascia, costi reali, expectancy netta, profit factor e drawdown.",
        "Nessuna soglia cambiata. Nessun segnale escluso. PAPER/DEMO ONLY.",
    ])
    return "\n".join(lines)
