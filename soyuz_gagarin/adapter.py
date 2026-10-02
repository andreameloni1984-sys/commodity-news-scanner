"""Adapter tra il motore commodity esistente e il SOYUZ GAGARIN v1."""

from __future__ import annotations

from typing import Iterable

from .engine import GagarinEngine
from .models import Candidate, MarketSnapshot


def evaluate_states(states: Iterable[object]):
    """Applica il nuovo Risk Governor agli stati già prodotti dal motore commodity."""
    engine = GagarinEngine()
    decisions = []

    for state in states:
        symbol = str(getattr(state, "symbol", "")).strip().upper()
        price = float(getattr(state, "price", 0.0) or 0.0)
        atr = float(getattr(state, "atr", 0.0) or 0.0)
        side = str(getattr(state, "setup_direction", "WAIT") or "WAIT").upper()

        stop_atr = float(getattr(state, "stop_atr", 0.0) or 0.0)
        if stop_atr <= 0 and price > 0 and atr > 0:
            stop = getattr(state, "stop", None)
            if stop is not None:
                stop_atr = abs(price - float(stop)) / atr

        rr = max(
            float(getattr(state, "rr3", 0.0) or 0.0),
            float(getattr(state, "rr2", 0.0) or 0.0),
            float(getattr(state, "rr1", 0.0) or 0.0),
        )

        blocked = str(getattr(state, "final_decision", "WAIT")) != "ENTRY"
        candidate = Candidate(
            symbol=symbol,
            side=side,
            probability=float(getattr(state, "probability", 0.0) or 0.0),
            quality=float(getattr(state, "quality", 0.0) or 0.0),
            confidence=float(getattr(state, "confidence", 0.0) or 0.0),
            rr=rr,
            stop_distance_atr=stop_atr,
            reasons=list(getattr(state, "blockers", []) or []),
            blocked=blocked,
            block_reason="LEGACY_ENGINE_WAIT" if blocked else None,
        )

        market = MarketSnapshot(
            symbol=symbol,
            timestamp=str(getattr(state, "analysis_timestamp", "") or ""),
            price=price,
            atr=atr,
            regime=str(getattr(state, "regime", "UNKNOWN")),
        )
        decisions.append(engine.evaluate(market, candidate))

    return decisions
