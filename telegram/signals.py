"""SOYUZ GAGARIN — Signal Channel formatter.

Signal-only presentation layer. It never places orders and never invents
market data. Scores are explicitly confluence scores, not calibrated
probabilities.

Formato aggiornato in stile canali segnalatori professionali
(entry/SL/TP multipli, rischio, motivo, timestamp).
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
    """Recognize canonical Gagarin PAPER_ENTRY, with legacy PAPER_SIGNAL fallback."""
    metadata = getattr(state, "metadata", {}) or {}
    canonical = (
        isinstance(metadata, dict)
        and str(metadata.get("gagarin_action", "")).upper() in {"PAPER_ENTRY", "PAPER_SIGNAL"}
    )
    legacy = str(getattr(state, "final_decision", "")).upper() == "ENTRY"
    return (
        (canonical or legacy)
        and _direction(state) in {"LONG", "SHORT"}
        and bool(getattr(state, "data_ok", False))
        and bool(getattr(state, "live", False))
        and bool(getattr(state, "trigger_confirmed", False))
        and getattr(state, "entry", None) is not None
        and getattr(state, "stop", None) is not None
        and getattr(state, "tp1", None) is not None
    )


def _rule_label(state) -> str:
    metadata = getattr(state, "metadata", {}) or {}
    rule = metadata.get("rule") or metadata.get("paper_rule", {}).get("reason") if isinstance(metadata.get("paper_rule"), dict) else None
    if rule:
        return str(rule)
    return "GAGARIN CONFLUENCE"


def _opportunity_score(state) -> float:
    """Simple ranking score for prioritization."""
    try:
        p = float(getattr(state, "probability", 0) or 0)
        q = float(getattr(state, "quality", 0) or 0)
        c = float(getattr(state, "confidence", 0) or 0)
        return (p * 0.4) + (q * 0.35) + (c * 0.25)
    except Exception:
        return 0.0


def format_signal(state) -> str:
    direction = _direction(state)
    icon = "🟢" if direction == "LONG" else "🔴"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    metadata = getattr(state, "metadata", {}) or {}
    risk_pct = metadata.get("risk_pct") or 0.01
    score = _opportunity_score(state)

    lines = [
        f"{icon} **OPPORTUNITÀ** — {str(state.commodity).upper()} {direction}",
        "━━━━━━━━━━━━━━━━━━━━",
        "🧪 PAPER ONLY • NESSUN ORDINE AUTOMATICO",
        f"🕒 {now}",
        "",
        f"📌 DIREZIONE: {direction}",
        f"💰 ENTRY: {_fmt(state.entry)}",
        f"🛑 SL: {_fmt(state.stop)}",
        f"🎯 TP1: {_fmt(state.tp1)}",
        f"🎯 TP2: {_fmt(state.tp2)}",
        f"🎯 TP3: {_fmt(state.tp3)}",
        "",
        f"📐 RR: TP1 {_fmt(getattr(state, 'rr1', None), 2)} | TP2 {_fmt(getattr(state, 'rr2', None), 2)} | TP3 {_fmt(getattr(state, 'rr3', None), 2)}",
        f"📊 Score: {score:.1f}/100",
        f"⭐ Quality: {_fmt(getattr(state, 'quality', None), 1)}/100",
        f"🛡 Confidence: {_fmt(getattr(state, 'confidence', None), 1)}/100",
        f"📏 ATR: {_fmt(getattr(state, 'atr', None), 5)}",
        f"⚠️ RISK: {float(risk_pct)*100:.1f}% max",
        "",
        f"🌐 Regime: {getattr(state, 'regime', 'UNKNOWN')}",
        f"🏗 Structure: {getattr(state, 'structure', 'UNKNOWN')}",
        f"🎯 Setup: {getattr(state, 'setup', 'NONE')}",
        f"⚡ Trigger: {getattr(state, 'trigger', 'NONE')}",
        f"📜 Motivo: {_rule_label(state)}",
        f"🧠 Analisi: {((getattr(state, 'metadata', {}) or {}).get('analyst_reasoning') or {}).get('conclusion', 'Analisi strutturata non disponibile.')[:300]}",
        f"🔎 Conferme: {', '.join(((getattr(state, 'metadata', {}) or {}).get('analyst_reasoning') or {}).get('evidence', [])[:4]) or 'N/D'}",
        f"⚠️ Contrasti: {', '.join(((getattr(state, 'metadata', {}) or {}).get('analyst_reasoning') or {}).get('conflicts', [])[:3]) or 'Nessun conflitto rilevato'}",
        f"⏱ {_age_label(state)}",
        "",
        "⚠️ Segnale informativo PAPER. Verifica contesto e rischio prima di qualsiasi decisione. Nessun ordine inviato.",
    ]
    return "\n".join(lines)


def format_watch(state) -> str:
    """Pre-alert for setups close to threshold but not fully confirmed."""
    direction = _direction(state)
    score = _opportunity_score(state)
    blockers = list(getattr(state, "blockers", []) or [])
    reason = ", ".join(str(x) for x in blockers[:3]) or "Vicino alla soglia"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return (
        f"🟡 **WATCH** — {str(state.commodity).upper()} {direction}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🕒 {now}\n"
        f"📊 Score: {score:.0f}/100\n"
        f"Direzione: {direction}\n"
        f"Motivo: {reason}\n"
        f"🧠 Analisi: {((getattr(state, 'metadata', {}) or {}).get('analyst_reasoning') or {}).get('conclusion', 'In attesa di evidenze.')[:240]}\n"
        f"⚠️ Contrasti: {', '.join(((getattr(state, 'metadata', {}) or {}).get('analyst_reasoning') or {}).get('conflicts', [])[:2]) or 'N/D'}\n"
        f"Regime: {getattr(state, 'regime', 'UNKNOWN')} | Trigger: {getattr(state, 'trigger', 'NONE')}\n"
        f"⏱ {_age_label(state)}\n\n"
        f"⚠️ Setup interessante ma non ancora confermato. Monitorare."
    )


def format_watch_board(results: Iterable[object], min_score: float = 45.0) -> str:
    """Board of near-threshold setups."""
    results = list(results or [])
    candidates = [
        s for s in results
        if not _is_signal(s)
        and _direction(s) in {"LONG", "SHORT"}
        and _opportunity_score(s) >= min_score
    ]
    candidates.sort(key=_opportunity_score, reverse=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "🟡 **SOYUZ GAGARIN — WATCH**",
        "━━━━━━━━━━━━━━━━━━━━",
        f"🕒 {now}",
        "Setup vicini alla soglia (non ancora segnali operativi)",
        "",
    ]

    if not candidates:
        lines.append("Nessun setup vicino alla soglia.")
        return "\n".join(lines)

    for i, state in enumerate(candidates[:3], 1):
        score = _opportunity_score(state)
        direction = _direction(state)
        lines.append(
            f"{i}. {state.commodity} {direction} — score {score:.0f}\n"
            f"   {_rule_label(state)}"
        )

    lines += ["", "⚠️ Solo monitoraggio. Non è un segnale di entrata."]
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
    signals.sort(key=_opportunity_score, reverse=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "🚀 **SOYUZ GAGARIN — TOP OPPORTUNITÀ**",
        "━━━━━━━━━━━━━━━━━━━━",
        "🧪 PAPER ONLY • NESSUN ORDINE AUTOMATICO",
        f"🕒 {now}",
        "",
    ]

    if not signals:
        lines += [
            "🟡 NESSUN SEGNALE OPERATIVO — NESSUNA OPPORTUNITÀ OPERATIVA",
            "",
            "Gagarin mantiene WAIT finché i dati e la confluence",
            "non sono sufficienti. Nessun segnale viene inventato.",
        ]
        return "\n".join(lines)

    for i, state in enumerate(signals[:3], 1):
        direction = _direction(state)
        icon = "🟢" if direction == "LONG" else "🔴"
        score = _opportunity_score(state)
        lines.append(
            f"{i}. {icon} **{state.commodity} {direction}** (score {score:.0f})\n"
            f"   Entry {_fmt(state.entry)} | SL {_fmt(state.stop)} | TP1 {_fmt(state.tp1)}\n"
            f"   RR {_fmt(getattr(state, 'rr1', None), 2)} | {_rule_label(state)}"
        )

    lines += [
        "",
        "Solo le opportunità più forti. Score = combinazione di confluence, quality e confidence.",
        "PAPER ONLY — verifica sempre prima di decidere.",
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
        "Il canale pubblica segnali e contesto, non ordini.\n"
        "🧪 PAPER ONLY: nessuna esecuzione automatica.\n\n"
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
