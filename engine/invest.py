# ============================================================
# INVEST ENGINE — Analisi azionario / ETF
# PAPER ONLY. Trading 212 demo opzionale.
# ============================================================

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, List

from engine.invest_universe import enabled_instruments, InvestInstrument

# Simple paper analysis using public price sources if available.
# Full Gagarin-style scoring can be added later.

@dataclass
class InvestSignal:
    name: str
    ticker: str
    symbol: str
    direction: str          # LONG / SHORT / NONE
    score: float
    price: Optional[float]
    reason: str
    paper_only: bool = True

def analyze_invest_universe() -> List[InvestSignal]:
    """
    Analisi semplice del paniere Invest.
    Usa dati pubblici se disponibili, altrimenti restituisce segnali neutri.
    """
    signals = []
    instruments = enabled_instruments()

    for inst in instruments:
        # Placeholder: in produzione collegare al data engine esistente
        # o a provider pubblici (Yahoo, Stooq, etc.)
        signals.append(
            InvestSignal(
                name=inst.name,
                ticker=inst.ticker,
                symbol=inst.symbol,
                direction="NONE",
                score=0.0,
                price=None,
                reason="Analisi base attiva. Collega provider dati per segnali reali.",
            )
        )

    return signals

def format_invest_report(signals: List[InvestSignal]) -> str:
    lines = [
        "📈 SEZIONE INVEST — PAPER ONLY",
        "━" * 22,
        "🧪 Solo analisi e segnali demo.",
        "Nessun ordine reale.",
        "",
    ]
    if not signals:
        lines.append("Nessuno strumento nel paniere.")
        return "\n".join(lines)

    for s in signals:
        price_str = f"{s.price:.2f}" if s.price is not None else "N/D"
        lines.append(
            f"• {s.name} ({s.ticker}) | {s.direction} | "
            f"Score {s.score:.1f} | Prezzo {price_str}"
        )
        if s.reason:
            lines.append(f"  {s.reason}")

    lines.append("")
    lines.append("Per attivare ordini demo Trading 212 imposta T212_API_KEY e T212_API_SECRET.")
    lines.append("Endpoint demo: https://demo.trading212.com/api/v0")
    return "\n".join(lines)

# ============================================================
# TRADING 212 DEMO (opzionale)
# ============================================================

def trading212_demo_available() -> bool:
    key = os.getenv("T212_API_KEY", "").strip()
    secret = os.getenv("T212_API_SECRET", "").strip()
    return bool(key and secret)

def get_trading212_demo_status() -> str:
    if trading212_demo_available():
        return "✅ Trading 212 Demo API configurata (chiavi presenti)."
    return "⚪ Trading 212 Demo API non configurata. Imposta T212_API_KEY e T212_API_SECRET."
