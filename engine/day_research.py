"""SOYUZ GAGARIN — engine/day_research.py

Note di ricerca sul day trading. Paper only. Non cambia final_decision.
Non promuove regole. Accumula osservazioni e confronta ipotesi.

Fonti studiate:
- Zarattini, Barbon, Aziz: intraday momentum su SPY, 2007-2024,
  ~19.6% annuo al netto dei costi, Sharpe 1.33. Uscite migliori sul VWAP.
- Opening Range Breakout: range dei primi 30 minuti, entrata sulla rottura,
  stop dentro il range, target pari all'altezza del range.
- Studio 2026 su E-mini S&P: 75% successo ORB vs 53% momentum generico.
- Studio 2026 su micro Nasdaq: 14 famiglie di segnali OHLCV, 11 falliscono
  perché il guadagno lordo è sotto il costo di transazione.
- Stop in ATR adattivi: drawdown ridotto 45-65% su 15 futures, 20 anni.
- Stop tecnico oltre la zona di trappola, non al livello esatto.
- Uscite basate sul tempo (trailing, break-even, timeout) battono le uscite
  a prezzo fisso in 11 mesi su 13.
- Limite giornaliero: rischio 1% a operazione, stop al 3% di perdita giornaliera.

Strumenti misurati: SPY, QQQ (ETF liquidi), ES/NQ/MES/MNQ (futures),
EUR/USD, GBP/USD (forex major, overlap Londra-NY).

Non misurati / esclusi dal day: petrolio, oro, gas, cereali — restano
nel motore settimanale. Le candele giapponesi e Fibonacci non sono
segnali: descrivono il prezzo, non lo prevedono.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

OUT = Path("data/day_research.json")

NOTES = {
    "orb": {
        "description": "Opening Range Breakout: range dei primi 30 minuti USA",
        "entry": "rottura del range con volume sopra la media",
        "stop": "lato opposto del range, mai sotto 0.8 ATR",
        "target": "altezza del range, poi uscita sul VWAP",
        "evidence": "studio 2026 E-mini S&P: 75% vs 53% momentum generico",
    },
    "vwap_exit": {
        "description": "Uscita al ritorno sul VWAP, non a prezzo fisso",
        "evidence": "Zarattini et al: uscite VWAP migliori delle uscite a prezzo fisso",
    },
    "costs": {
        "description": "Il costo è il muro: 11 su 14 famiglie di segnali falliscono",
        "evidence": "studio 2026 micro Nasdaq: guadagno lordo sotto il costo del giro",
        "rule": "nessun segnale senza spread e slippage scritti nel conto",
    },
    "atr_stop": {
        "description": "Stop in ATR adattivo, non percentuale fissa",
        "evidence": "drawdown ridotto 45-65% su 15 futures su 20 anni",
    },
    "daily_limit": {
        "description": "Stop al 3% di perdita giornaliera o 3 perdite di fila",
        "evidence": "disciplina, non segnale: protegge dal giorno in serie",
    },
    "instruments": {
        "SPY": "ETF S&P 500, spread 1 centesimo, volume enorme, orario 15:30-22:00 Roma",
        "QQQ": "ETF Nasdaq 100, range di apertura più largo, stesso schema di SPY",
        "ES_NQ": "E-mini S&P e Nasdaq: leva alta, tick fisso, stop in ATR obbligatorio",
        "MES_MNQ": "Micro: stesso sottostante, capitale piccolo, costo giro 0.25$/contratto",
        "EURUSD_GBPUSD": "Forex major: solo overlap Londra-NY 14:00-17:00 Roma, spread pesa di più",
        "excluded_from_day": "WTI, Brent, oro, argento, gas, cereali: restano nel motore settimanale",
    },
    "candles_fibonacci": {
        "description": "Candele giapponesi e Fibonacci: etichette, non segnali",
        "evidence": "studi su engulfing S&P 500: potere predittivo vicino a zero dopo i costi",
    },
}


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build() -> dict:
    return {
        "paper_only": True,
        "promoted": None,
        "updated_at": _now(),
        "notes": NOTES,
        "status": "RESEARCH_NOTES",
        "next_step": "accumulare casi day su paper prima di qualsiasi promozione",
    }


def run() -> dict:
    report = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
