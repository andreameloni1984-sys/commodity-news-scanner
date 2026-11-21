"""Strumenti seguiti dal bot."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Instrument:
    key: str
    name: str
    yahoo: str          # simbolo dati (Yahoo Finance)
    t212: str           # nome indicativo del CFD su Trading 212
    spread: float       # spread tipico stimato, in punti di prezzo (per backtest e avvisi)
    decimals: int


INSTRUMENTS: tuple[Instrument, ...] = (
    Instrument("oro", "Oro", "GC=F", "Gold", 0.40, 2),
    Instrument("wti", "Petrolio WTI", "CL=F", "Oil (WTI)", 0.03, 2),
    Instrument("sp500", "S&P 500", "^GSPC", "US 500", 0.70, 1),
    Instrument("nasdaq", "Nasdaq 100", "^NDX", "US 100", 2.00, 1),
    Instrument("eurusd", "EUR/USD", "EURUSD=X", "EUR/USD", 0.00008, 5),
)

BY_KEY = {i.key: i for i in INSTRUMENTS}
