"""Outcome-first market ranking for SOYUZ GAGARIN (PAPER ONLY).

Ranks the strongest current directional forecast across the scanned universe.
Scores are transparent heuristic selection scores, NOT calibrated probabilities.
"""
from __future__ import annotations

from typing import Any, Iterable


def _num(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        return number if number == number else default
    except (TypeError, ValueError):
        return default


def _direction(value: Any) -> str:
    value = str(value or "").strip().upper()
    return value if value in {"LONG", "SHORT"} else "NONE"


def rank_predictions(states: Iterable[Any]) -> list[dict]:
    """Rank all analysable assets by directional evidence and potential move."""
    if isinstance(states, dict):
        states = states.values()
    ranked = []
    for state in states:
        name = str(getattr(state, "commodity", "") or "").strip()
        if not name:
            continue
        metadata = getattr(state, "metadata", {}) or {}
        if not isinstance(metadata, dict):
            metadata = {}
        directions = [
            _direction(getattr(state, "pre_move_direction", "NONE")),
            _direction(getattr(state, "setup_direction", "NONE")),
            _direction(getattr(state, "structure_direction", "NONE")),
            _direction(getattr(state, "mtf_direction", "NONE")),
            _direction(getattr(state, "opportunity_direction", "NONE")),
        ]
        # The most recent confirmed setup takes priority; otherwise use the
        # pre-move model and then structural/MTF context.
        direction = next((d for d in directions[1:2] if d != "NONE"), "NONE")
        if direction == "NONE":
            direction = next((d for d in (directions[0], directions[2], directions[3], directions[4]) if d != "NONE"), "NONE")
        if direction == "NONE":
            # Always produce a directional candidate when the current market
            # series supplies momentum; this is a lower-evidence fallback.
            move24 = _num(getattr(state, "move_24h_pct", 0))
            move4 = _num(getattr(state, "move_4h_pct", 0))
            if move24 != 0:
                direction = "LONG" if move24 > 0 else "SHORT"
            elif move4 != 0:
                direction = "LONG" if move4 > 0 else "SHORT"
            else:
                closes = getattr(state, "closes", []) or []
                try:
                    if len(closes) >= 2 and float(closes[-1]) != float(closes[0]):
                        direction = "LONG" if float(closes[-1]) > float(closes[0]) else "SHORT"
                except (TypeError, ValueError):
                    pass
        if direction == "NONE":
            continue

        live = bool(getattr(state, "live", False))
        data_ok = bool(getattr(state, "data_ok", False))
        price = _num(getattr(state, "price", 0))
        atr = _num(getattr(state, "atr", 0))
        # A directional ranking without a valid price and volatility scale is
        # not comparable; fail closed rather than inventing a candidate.
        if price <= 0 or atr <= 0:
            continue

        pre_move = _num(getattr(state, "pre_move_score", 0))
        opportunity = _num(getattr(state, "opportunity_score", 0))
        continuation = _num(getattr(state, "continuation_score", 0))
        probability = _num(getattr(state, "probability", 0))
        quality = _num(getattr(state, "quality", 0))
        confidence = _num(getattr(state, "confidence", 0))
        expected_move = _num(getattr(state, "expected_move_pct", 0))
        atr_pct = atr / price * 100 if atr > 0 else 0.0
        if expected_move <= 0:
            expected_move = atr_pct * (1.0 + pre_move / 100.0)
        if expected_move <= 0:
            expected_move = abs(_num(getattr(state, "move_24h_pct", 0))) or abs(_num(getattr(state, "move_4h_pct", 0)))

        score = 0.0
        reasons = []
        regime = str(getattr(state, "regime", "") or "").upper()
        structure = str(getattr(state, "structure", "") or "").upper()
        if (direction == "LONG" and regime == "TREND_UP") or (direction == "SHORT" and regime == "TREND_DOWN"):
            score += 15; reasons.append("regime coerente")
        if (direction == "LONG" and "BULL" in structure) or (direction == "SHORT" and "BEAR" in structure):
            score += 12; reasons.append("struttura coerente")
        if _direction(getattr(state, "mtf_direction", "NONE")) == direction:
            score += 10; reasons.append("multi-timeframe coerente")
        if _direction(getattr(state, "setup_direction", "NONE")) == direction:
            score += 12; reasons.append("setup nella direzione")
        if bool(getattr(state, "trigger_confirmed", False)):
            score += 8; reasons.append("trigger confermato")
        score += min(15, pre_move * 0.15)
        if pre_move >= 65:
            reasons.append("pre-movimento elevato")
        score += min(10, opportunity * 0.10)
        score += min(8, continuation * 0.08)
        score += min(5, quality * 0.05)
        score += min(5, confidence * 0.05)
        # Reward expected range only mildly: volatility is opportunity and risk.
        score += min(5, expected_move * 0.8)
        if live and data_ok:
            score += 10; reasons.append("dati live validi")
        elif not data_ok:
            score -= 15; reasons.append("dati non validati")
        if not live:
            score -= 8; reasons.append("prezzi non live")
        # Penalise disagreement between independent directional inputs.
        active = [d for d in directions if d != "NONE"]
        conflicts = sum(1 for d in active if d != direction)
        score -= conflicts * 5
        score = max(0.0, min(100.0, score))

        ranked.append({
            "commodity": name,
            "symbol": str(getattr(state, "symbol", "") or ""),
            "direction": direction,
            "score": round(score, 1),
            "expected_move_pct": round(expected_move, 3),
            "price": price,
            "entry": getattr(state, "entry", None),
            "stop": getattr(state, "stop", None),
            "tp1": getattr(state, "tp1", None),
            "tp2": getattr(state, "tp2", None),
            "tp3": getattr(state, "tp3", None),
            "rr3": getattr(state, "rr3", None),
            "probability_score": round(probability, 1),
            "quality": round(quality, 1),
            "confidence": round(confidence, 1),
            "data_status": str(metadata.get("data_status", "UNKNOWN")),
            "live": live,
            "trigger_confirmed": bool(getattr(state, "trigger_confirmed", False)),
            "final_decision": str(getattr(state, "final_decision", "UNKNOWN")),
            "reasons": reasons,
            "paper_only": True,
        })
    ranked.sort(key=lambda row: (row["score"], row["expected_move_pct"]), reverse=True)
    return ranked


def format_best_prediction(states: Iterable[Any], profile: str = "AGGRESSIVE") -> str:
    ranked = rank_predictions(states)
    heading = "🚀 GAGARIN — MIGLIORE PREVISIONE"
    if not ranked:
        return (
            f"{heading}\n━━━━━━━━━━━━━━━━━━━━\n"
            "Nessuna previsione direzionale calcolabile: mancano prezzi/ATR o una direzione coerente.\n"
            "Il motore non inventa uno strumento né un prezzo. PAPER ONLY."
        )
    best = ranked[0]
    lines = [
        heading, "━━━━━━━━━━━━━━━━━━━━", "🧪 PAPER ONLY",
        f"PROFILO: {profile}",
        f"SCELTA #1: {best['commodity']} ({best['symbol']}) — {best['direction']}",
        f"SCORE PREVISIONE: {best['score']:.1f}/100 (indice comparativo, NON probabilità)",
        f"MOVIMENTO ATTESO DAL MODELLO: circa {best['expected_move_pct']:.2f}%",
        f"PREZZO: {best['price']:.6g}",
        f"ENTRY: {best['entry']:.6g}" if best['entry'] is not None else "ENTRY: non disponibile",
        f"STOP LOSS: {best['stop']:.6g}" if best['stop'] is not None else "STOP LOSS: non disponibile",
        f"TAKE PROFIT 1: {best['tp1']:.6g}" if best['tp1'] is not None else "TAKE PROFIT 1: non disponibile",
        f"TAKE PROFIT 2: {best['tp2']:.6g}" if best['tp2'] is not None else "TAKE PROFIT 2: non disponibile",
        f"TAKE PROFIT 3: {best['tp3']:.6g}" if best['tp3'] is not None else "TAKE PROFIT 3: non disponibile",
        f"QUALITÀ {best['quality']:.0f} | CONFIDENCE {best['confidence']:.0f} | TRIGGER {'SÌ' if best['trigger_confirmed'] else 'NO'}",
        f"DATI: {best['data_status']} | {'LIVE' if best['live'] else 'NON LIVE'}",
        "PERCHÉ: " + (", ".join(best["reasons"]) if best["reasons"] else "segnali deboli"),
    ]
    if not best["trigger_confirmed"] or not best["live"] or best["final_decision"] not in {"PAPER_ENTRY", "PAPER_SIGNAL"}:
        lines.append("STATO: migliore candidata da monitorare; ingresso non confermato dal governor.")
    else:
        lines.append("STATO: segnale PAPER autorizzato dal governor.")
    if len(ranked) > 1:
        lines.append("")
        lines.append("ALTERNATIVE: " + " | ".join(
            f"{x['commodity']} {x['direction']} (score {x['score']:.0f}, atteso {x['expected_move_pct']:.2f}%)"
            for x in ranked[1:4]
        ))
    lines.append("Nota: il movimento atteso è una stima euristica basata sui dati disponibili, non una probabilità calibrata né una garanzia.")
    return "\n".join(lines)
