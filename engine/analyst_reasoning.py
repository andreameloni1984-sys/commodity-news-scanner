"""GAGARIN analyst layer.

Produces an auditable, human-readable market thesis from the canonical state.
It does not create setups, alter scores, bypass the Governor, or authorize trades.
"""
from __future__ import annotations

from typing import Any


def _side(value: Any) -> str:
    value = str(value or "NONE").strip().upper()
    return value if value in {"LONG", "SHORT"} else "NONE"


def _number(value: Any):
    try:
        result = float(value)
        return result if result == result and abs(result) != float("inf") else None
    except (TypeError, ValueError):
        return None


def build_reasoning(state: object, decision: object | None = None) -> dict[str, Any]:
    """Explain the best-supported thesis, opposing evidence and decision."""
    meta = getattr(state, "metadata", {}) or {}
    if not isinstance(meta, dict):
        meta = {}

    symbol = str(getattr(state, "symbol", "") or getattr(state, "commodity", "strumento"))
    setup_side = _side(getattr(state, "setup_direction", "NONE"))
    structure_side = _side(getattr(state, "structure_direction", "NONE"))
    mtf_side = _side(getattr(state, "mtf_direction", "NONE"))
    trigger_side = _side(getattr(state, "trigger_direction", "NONE"))
    regime = str(getattr(state, "regime", "UNKNOWN") or "UNKNOWN").upper()
    opportunity = str(getattr(state, "opportunity_type", "NONE") or "NONE").upper()
    trigger = str(getattr(state, "trigger", "NONE") or "NONE").upper()
    news = meta.get("sputnik_intelligence", {})
    news_events = news.get("events", []) if isinstance(news, dict) else []

    evidence: list[str] = []
    conflicts: list[str] = []
    missing: list[str] = []
    aligned = 0
    opposed = 0

    if bool(getattr(state, "data_ok", False)):
        evidence.append("qualità dati dichiarata valida")
    else:
        missing.append("qualità dei dati non valida")

    if bool(getattr(state, "live", False)):
        evidence.append("feed in modalità live")
    else:
        missing.append("quotazione live non confermata")

    if regime in {"TREND_UP", "TREND_DOWN"}:
        trend_side = "LONG" if regime == "TREND_UP" else "SHORT"
        evidence.append(f"regime {regime}")
        if setup_side != "NONE":
            if trend_side == setup_side:
                aligned += 1
            else:
                opposed += 1
                conflicts.append(f"regime {regime} contrario al setup {setup_side}")
    elif regime == "RANGE":
        evidence.append("mercato in range: preferire estremi/reversal, evitare inseguimento")
    elif regime == "HIGH_VOLATILITY":
        conflicts.append("volatilità elevata: rischio di falsi breakout e stop più ampi")
    else:
        missing.append("regime non classificato con sufficiente chiarezza")

    if structure_side != "NONE":
        evidence.append(f"struttura {structure_side}")
        if setup_side != "NONE":
            if structure_side == setup_side:
                aligned += 1
            else:
                opposed += 1
                conflicts.append(f"struttura {structure_side} in conflitto con setup {setup_side}")
    else:
        missing.append("direzione della struttura non definita")

    if mtf_side != "NONE":
        mtf_alignment = _number(getattr(state, "mtf_alignment", 0)) or 0.0
        evidence.append(f"multi-timeframe {mtf_side} (allineamento {mtf_alignment:.0f}/100)")
        if setup_side != "NONE":
            if mtf_side == setup_side:
                aligned += 1
            else:
                opposed += 1
                conflicts.append(f"multi-timeframe {mtf_side} contrario al setup {setup_side}")
    else:
        missing.append("conferma multi-timeframe assente")

    if setup_side != "NONE":
        evidence.append(f"setup individuato {setup_side} ({opportunity})")
    else:
        missing.append("nessun setup direzionale valido")

    if bool(getattr(state, "trigger_confirmed", False)) and trigger_side == setup_side and setup_side != "NONE":
        evidence.append(f"trigger confermato: {trigger}")
        aligned += 1
    else:
        missing.append("trigger d'ingresso non confermato")

    news_biases = []
    for event in news_events[:8]:
        impacts = event.get("impact", {}) or {}
        for asset, impact in impacts.items():
            if impact not in {"RIALZISTA", "RIBASSISTA"}:
                continue
            direction = "LONG" if impact == "RIALZISTA" else "SHORT"
            news_biases.append((str(asset), direction, str(event.get("title") or "")[:160]))
    matching_news = [item for item in news_biases if item[1] == setup_side]
    opposing_news = [item for item in news_biases if item[1] != setup_side and setup_side != "NONE"]
    if matching_news:
        evidence.append("notizie pubbliche con impatto coerente: " + ", ".join(sorted({x[0] for x in matching_news})))
        aligned += 1
    if opposing_news:
        conflicts.append("notizie pubbliche con impatto opposto: " + ", ".join(sorted({x[0] for x in opposing_news})))
        opposed += 1
    if not news_events:
        missing.append("nessun evento pubblico rilevante disponibile")

    price = _number(getattr(state, "price", None))
    atr = _number(getattr(state, "atr", None))
    entry = _number(getattr(state, "entry", None))
    stop = _number(getattr(state, "stop", None))
    tp1 = _number(getattr(state, "tp1", None))
    rr1 = _number(getattr(state, "rr1", None))
    if price is None or atr is None or atr <= 0:
        missing.append("prezzo o ATR non disponibili per validare la geometria")
    if entry is None or stop is None or tp1 is None:
        missing.append("bracket operativo completo (entry/SL/TP1) non disponibile")
    elif setup_side == "LONG" and not (stop < entry < tp1):
        conflicts.append("geometria LONG di entry/SL/TP1 incoerente")
        opposed += 1
    elif setup_side == "SHORT" and not (tp1 < entry < stop):
        conflicts.append("geometria SHORT di entry/SL/TP1 incoerente")
        opposed += 1
    elif rr1 is not None:
        evidence.append(f"rischio/rendimento TP1 = {rr1:.2f}R")

    action = str(getattr(decision, "action", "") or meta.get("gagarin_action", "WAIT")).upper()
    governor_reason = str(getattr(decision, "reason", "") or meta.get("gagarin_reason", ""))
    if action in {"PAPER_ENTRY", "PAPER_SIGNAL"}:
        verdict = "PAPER_SIGNAL"
        conclusion = "Le evidenze tecniche principali sono coerenti e il Governor ha autorizzato un segnale paper."
    elif setup_side in {"LONG", "SHORT"}:
        verdict = "WATCH_" + setup_side
        conclusion = f"Esiste una tesi {setup_side}, ma non è ancora un ingresso autorizzato. Attendere il completamento dei controlli mancanti."
    else:
        verdict = "NO_DIRECTION"
        conclusion = "Non emerge una direzione sufficientemente supportata: meglio non forzare un'operazione."

    if opposed:
        conclusion += " Sono presenti elementi contrari da non ignorare."
    if governor_reason:
        conclusion += " Governor: " + governor_reason[:220]

    bull_case = (
        f"Scenario LONG: struttura e regime si riallineano al rialzo, il prezzo conferma il trigger e le notizie non contraddicono la tesi."
    )
    bear_case = (
        f"Scenario SHORT: struttura e regime si riallineano al ribasso, il prezzo conferma il trigger e le notizie non contraddicono la tesi."
    )
    if setup_side == "LONG":
        bull_case = "Tesi principale LONG: il setup rialzista può proseguire se struttura, multi-timeframe e trigger restano allineati."
        bear_case = "Scenario alternativo: perdita della struttura/supporto, notizia contraria o mancato follow-through invalidano il LONG."
    elif setup_side == "SHORT":
        bear_case = "Tesi principale SHORT: il setup ribassista può proseguire se struttura, multi-timeframe e trigger restano allineati."
        bull_case = "Scenario alternativo: recupero della struttura/resistenza, notizia contraria o mancato follow-through invalidano lo SHORT."

    return {
        "version": "ANALYST_LAYER_1",
        "symbol": symbol,
        "verdict": verdict,
        "direction": setup_side,
        "alignment_count": aligned,
        "conflict_count": opposed,
        "evidence": evidence[:10],
        "conflicts": conflicts[:8],
        "missing": missing[:8],
        "bull_case": bull_case,
        "bear_case": bear_case,
        "conclusion": conclusion,
        "governor_action": action,
        "governor_reason": governor_reason,
        "news_status": news.get("status", "UNAVAILABLE") if isinstance(news, dict) else "UNAVAILABLE",
    }
