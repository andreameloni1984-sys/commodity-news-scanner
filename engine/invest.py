# ============================================================
# INVEST ENGINE — Analisi azionario / ETF
# PAPER ONLY. SPUTNIK bridge + Trading 212 demo opzionale.
# ============================================================

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, List

from engine.invest_universe import enabled_instruments
from engine.sputnik_bridge import sputnik_to_invest_signals

@dataclass
class InvestSignal:
    name: str
    ticker: str
    symbol: str
    direction: str
    score: float
    price: Optional[float]
    reason: str
    paper_only: bool = True
    source: str = "LOCAL"

def analyze_invest_universe() -> List[InvestSignal]:
    """Combina paniere base + segnali SPUTNIK."""
    signals: List[InvestSignal] = []

    # 1. Segnali da SPUTNIK (catalizzatori pubblici)
    sputnik_raw = sputnik_to_invest_signals()
    for item in sputnik_raw:
        signals.append(
            InvestSignal(
                name=item["name"],
                ticker=item["ticker"],
                symbol=item["symbol"],
                direction=item["direction"],
                score=float(item["score"]),
                price=item.get("price"),
                reason=item["reason"],
                source="SPUTNIK",
            )
        )

    # 2. Paniere base (se non già coperto da SPUTNIK)
    covered = {s.symbol for s in signals}
    for inst in enabled_instruments():
        if inst.symbol in covered:
            continue
        signals.append(
            InvestSignal(
                name=inst.name,
                ticker=inst.ticker,
                symbol=inst.symbol,
                direction="NONE",
                score=0.0,
                price=None,
                reason="Nessun catalizzatore SPUTNIK recente.",
                source="LOCAL",
            )
        )

    signals.sort(key=lambda s: (s.source == "SPUTNIK", s.score), reverse=True)
    return signals

def format_invest_report(signals: List[InvestSignal]) -> str:
    lines = [
        "📈 SEZIONE INVEST — PAPER ONLY",
        "━" * 22,
        "🧪 Segnali da SPUTNIK + paniere base.",
        "Nessun ordine reale.",
        "",
    ]
    if not signals:
        lines.append("Nessuno strumento nel paniere.")
        return "\n".join(lines)

    sputnik_count = sum(1 for s in signals if s.source == "SPUTNIK")
    if sputnik_count:
        lines.append(f"🛰 {sputnik_count} segnale/i da SPUTNIK (catalizzatori pubblici).")
        lines.append("")

    for s in signals:
        price_str = f"{s.price:.2f}" if s.price is not None else "N/D"
        tag = "SPUTNIK" if s.source == "SPUTNIK" else "BASE"
        lines.append(
            f"• [{tag}] {s.name} ({s.ticker}) | {s.direction} | "
            f"Score {s.score:.1f} | Prezzo {price_str}"
        )
        if s.reason:
            lines.append(f"  {s.reason}")

    lines.append("")
    lines.append("Per ordini demo Trading 212: imposta T212_API_KEY e T212_API_SECRET.")
    lines.append("Endpoint demo: https://demo.trading212.com/api/v0")
    return "\n".join(lines)

def trading212_demo_available() -> bool:
    key = os.getenv("T212_API_KEY", "").strip()
    secret = os.getenv("T212_API_SECRET", "").strip()
    return bool(key and secret)

def get_trading212_demo_status() -> str:
    if trading212_demo_available():
        return "✅ Trading 212 Demo API configurata (chiavi presenti)."
    return "⚪ Trading 212 Demo API non configurata. Imposta T212_API_KEY e T212_API_SECRET."
