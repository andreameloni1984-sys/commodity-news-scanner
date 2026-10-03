"""SOYUZ GAGARIN — Signal Channel formatter.

Signal-only presentation layer. It never places orders and never invents
market data. Scores are explicitly confluence scores, not calibrated
probabilities.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable


def _fmt(value, digits=5):
    if value is None:
        return "N/D"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "N/D"


def _age_label(state) -> str:
    age = getattr(state, "data_age_seconds", None)
    if age is None:
        return "FRESHNESS N/D"
    try:
        return f"dati {float(age):.0f}s"
    except (TypeError, ValueError):
        return "FRESHNESS N/D"


def _direction(state) -> str:
    direction = str(getattr(state, "setup_direction", "") or "").upper()
    return direction if direction in {"LONG", "SHORT"} else "WAIT"


def _is_signal(state) -> bool:
    return (
        str(getattr(state, "final_decision", "")).upper() == "ENTRY"
        and _direction(state) in {"LONG", "SHORT"}
        and bool(getattr(state, "data_ok", False))
        and bool(getattr(state, "live", False))
        and bool(getattr(state, "trigger_confirmed", False))
        and getattr(state, "entry", None) is not None
        and getattr(state, "stop", None) is not None
        and getattr(state, "tp1", None) is not None
    )


def format_signal(state) -> str:
    direction = _direction(state)
    icon = "🟢" if direction == "LONG" else "🔴"

    lines = [
        f"{icon} SOYUZ SIGNAL — {str(state.commodity).upper()}",
        "━━━━━━━━━━━━━━━━━━━━",
        "🧪 PAPER ONLY • NO AUTO-ORDER",
        "",
        f"📌 {direction}",
        f"💰 Entry: {_fmt(state.entry)}",
        f"🛑 SL: {_fmt(state.stop)}",
        f"🎯 TP1: {_fmt(state.tp1)}",
        f"🎯 TP2: {_fmt(state.tp2)}",
        f"🎯 TP3: {_fmt(state.tp3)}",
        "",
        f"📐 RR: TP1 {_fmt(getattr(state, 'rr1', None), 2)} | "
        f"TP2 {_fmt(getattr(state, 'rr2', None), 2)} | "
        f"TP3 {_fmt(getattr(state, 'rr3', None), 2)}",
        f"📊 Confluence: {_fmt(getattr(state, 'probability', None), 1)} / 100",
        f"⭐ Quality: {_fmt(getattr(state, 'quality', None), 1)} / 100",
        f"🛡 Confidence: {_fmt(getattr(state, 'confidence', None), 1)} / 100",
        f"📏 ATR: {_fmt(getattr(state, 'atr', None), 5)}",
        "",
        f"🌐 Regime: {getattr(state, 'regime', 'UNKNOWN')}",
        f"🏗 Structure: {getattr(state, 'structure', 'UNKNOWN')}",
        f"🎯 Setup: {getattr(state, 'setup', 'NONE')}",
        f"⚡ Trigger: {getattr(state, 'trigger', 'NONE')}",
        f"⏱ {_age_label(state)}",
        "",
        "⚠️ Segnale informativo: rischio e contesto vanno verificati prima di qualsiasi decisione.",
    ]
    return "\n".join(lines)


def format_wait(state) -> str:
    blockers = list(getattr(state, "blockers", []) or [])
    reason = ", ".join(str(x) for x in blockers[:5]) or "GATE_NOT_CONFIRMED"
    return (
        f"🟡 WAIT — {str(state.commodity).upper()}\n"
        f"Direzione: {_direction(state)}\n"
        f"Motivo: {reason}\n"
        f"Regime: {getattr(state, 'regime', 'UNKNOWN')} | "
        f"Trigger: {getattr(state, 'trigger', 'NONE')}\n"
        f"⏱ {_age_label(state)}"
    )


def format_signal_board(results: Iterable[object]) -> str:
    results = list(results or [])
    signals = [s for s in results if _is_signal(s)]

    lines = [
        "🚀 SOYUZ GAGARIN — SIGNAL BOARD",
        "━━━━━━━━━━━━━━━━━━━━",
        "🧪 PAPER ONLY • NESSUN ORDINE AUTOMATICO",
        "",
    ]

    if not signals:
        lines += [
            "🟡 NESSUN SEGNALE OPERATIVO",
            "",
            "Gagarin mantiene WAIT finché i dati e la confluence",
            "non sono sufficienti. Nessun segnale viene inventato.",
        ]
        return "\n".join(lines)

    for i, state in enumerate(signals[:5], 1):
        direction = _direction(state)
        icon = "🟢" if direction == "LONG" else "🔴"
        lines.append(
            f"{i}. {icon} {state.commodity} {direction} | "
            f"Entry {_fmt(state.entry)} | "
            f"SL {_fmt(state.stop)} | "
            f"TP1 {_fmt(state.tp1)} | "
            f"RR {_fmt(getattr(state, 'rr1', None), 2)}"
        )

    lines += [
        "",
        "Nota: Confluence/Quality/Confidence sono score del motore,",
        "non probabilità statisticamente calibrate.",
    ]
    return "\n".join(lines)


def format_top(results: Iterable[object], limit: int = 5) -> str:
    results = list(results or [])
    lines = [
        "📊 SOYUZ GAGARIN — TOP SETUP",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
    ]
    for i, state in enumerate(results[:limit], 1):
        direction = _direction(state)
        lines.append(
            f"{i}. {state.commodity} | {direction} | "
            f"C {_fmt(getattr(state, 'probability', 0), 1)} | "
            f"Q {_fmt(getattr(state, 'quality', 0), 1)} | "
            f"{getattr(state, 'final_decision', 'WAIT')}"
        )
    if not results:
        lines.append("Nessun dato disponibile.")
    return "\n".join(lines)


def format_channel_guide() -> str:
    return (
        "📚 SOYUZ GAGARIN — GUIDA\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Il canale pubblica segnali e contesto, non ordini.\n\n"
        "🟢 SIGNAL — setup che supera i controlli disponibili.\n"
        "🟡 WAIT — setup interessante ma non ancora confermato.\n"
        "🔴 BLOCKED — dati o condizioni operative insufficienti.\n\n"
        "Ogni segnale mostra Entry, SL, TP1/2/3, RR, ATR, regime, "
        "structure, setup e trigger.\n\n"
        "I punteggi sono score di confluence: non sono probabilità "
        "statisticamente calibrate e non costituiscono garanzia di risultato.\n\n"
        "Gestione del rischio e decisione finale restano sempre a carico dell'utente."
    )


def format_risk_guide() -> str:
    return (
        "🛡 SOYUZ — RISK GUIDE\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "• Il segnale non è un ordine.\n"
        "• Lo SL definisce il punto di invalidazione del setup.\n"
        "• RR viene mostrato per TP1/TP2/TP3 quando disponibile.\n"
        "• Se i dati sono stale, incoerenti o incompleti → WAIT.\n"
        "• Nessun edge statistico viene dichiarato senza validazione.\n"
        "• PAPER ONLY: nessuna esecuzione automatica."
    )
