"""Aggressive PAPER desk for SOYUZ GAGARIN.

Ranks opportunities more permissively than the standard governor but never
places real orders and never fabricates market prices. A directional pick is
not represented as an approved entry unless the governor says so.
"""
from __future__ import annotations

from typing import Iterable, Any

from engine.prediction_ranker import rank_predictions


def format_aggressive_desk(states: Iterable[Any]) -> str:
    ranked = rank_predictions(states)
    lines = [
        "🚀 GAGARIN — REPARTO AGGRESSIVE",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "🧪 SIMULAZIONE PAPER ONLY",
        "Mandato: trovare la migliore opportunità LONG o SHORT del mercato.",
        "Il reparto classifica anche candidati non ancora autorizzati all'ingresso.",
        "",
    ]
    if not ranked:
        lines.extend([
            "ESITO: DATI INSUFFICIENTI",
            "Non invento prezzo, direzione o livelli operativi.",
            "Controllare provider, prezzo e ATR.",
        ])
        return "\n".join(lines)

    for index, item in enumerate(ranked[:3], 1):
        approved = (
            item["trigger_confirmed"]
            and item["live"]
            and item["final_decision"] in {"PAPER_ENTRY", "PAPER_SIGNAL", "ENTRY"}
            and item["entry"] is not None
            and item["stop"] is not None
            and item["tp1"] is not None
        )
        lines.extend([
            f"{'🎯 SCELTA PRINCIPALE' if index == 1 else f'Alternativa {index}'}: {item['commodity']} — {item['direction']}",
            f"Score comparativo: {item['score']:.1f}/100 | movimento stimato: {item['expected_move_pct']:.2f}%",
            f"Prezzo attuale: {item['price']:.6g}",
            f"ENTRY: {item['entry']:.6g}" if item["entry"] is not None else "ENTRY: N/D",
            f"STOP LOSS: {item['stop']:.6g}" if item["stop"] is not None else "STOP LOSS: N/D",
            f"TP1: {item['tp1']:.6g}" if item["tp1"] is not None else "TP1: N/D",
            f"TP2: {item['tp2']:.6g}" if item["tp2"] is not None else "TP2: N/D",
            f"TP3: {item['tp3']:.6g}" if item["tp3"] is not None else "TP3: N/D",
            f"Qualità {item['quality']:.0f} | Confidence {item['confidence']:.0f} | Trigger {'CONFERMATO' if item['trigger_confirmed'] else 'DA CONFERMARE'}",
            f"Dati: {item['data_status']} | {'LIVE' if item['live'] else 'NON LIVE'}",
            "STATO: SEGNALE PAPER AUTORIZZATO" if approved else "STATO: CANDIDATO AGGRESSIVO — non ancora autorizzato dal governor",
            "Motivi: " + (", ".join(item["reasons"]) if item["reasons"] else "evidenza limitata"),
            "",
        ])

    lines.extend([
        "REGOLA DI SICUREZZA",
        "Il profilo aggressivo abbassa la soglia di selezione, non disattiva i controlli su dati, trigger, stop o rischio.",
        "Nessun ordine reale: EXECUTION DISABLED / PAPER ONLY.",
        "Score e movimento atteso sono stime euristiche, non probabilità calibrate né garanzie.",
    ])
    return "\n".join(lines)
