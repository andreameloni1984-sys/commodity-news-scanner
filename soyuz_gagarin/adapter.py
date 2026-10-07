"""Adapter dal motore commodity esistente al SOYUZ GAGARIN.

Il vecchio motore resta una sorgente di evidenza nello stato canonico.
IMPORTANTE: final_decision del legacy engine NON viene usato come veto.
Gagarin ricostruisce i cancelli operativi dai campi dello stato e prende
la decisione finale in modo indipendente.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from .engine import GagarinEngine
from .models import Candidate, MarketSnapshot


def _float(value, default=0.0) -> float:
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return float(default)


def _optional_float(value):
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _metadata(state) -> dict:
    value = getattr(state, "metadata", {}) or {}
    return value if isinstance(value, dict) else {}


def _freshness_ok(state, configured: bool, max_age_seconds: int) -> bool:
    """Never trust a stale timestamp just because a producer said LIVE/fresh."""
    if not configured:
        return False
    raw = str(getattr(state, "analysis_timestamp", "") or "").strip()
    if not raw:
        return False
    try:
        timestamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - timestamp.astimezone(timezone.utc)).total_seconds()
    except (TypeError, ValueError):
        return False
    return 0 <= age <= max_age_seconds


def _gate(state, name: str, fallback: bool) -> bool:
    """Read an explicit gate; missing evidence fails closed."""
    meta = _metadata(state)
    gates = meta.get("operational_gates", {})
    if isinstance(gates, dict) and name in gates:
        return bool(gates[name])
    return fallback


def evaluate_states(states: Iterable[object]):
    engine = GagarinEngine()
    freshness_limit = engine.config.blocked_if_stale_seconds
    decisions = []

    for state in states:
        symbol = str(getattr(state, "symbol", "")).strip().upper()
        price = _float(getattr(state, "price", 0.0))
        atr = _float(getattr(state, "atr", 0.0))

        side = str(
            getattr(state, "setup_direction", "NONE") or "NONE"
        ).upper()

        stop_atr = _float(getattr(state, "stop_atr", 0.0))
        if stop_atr <= 0 and price > 0 and atr > 0:
            stop = getattr(state, "stop", None)
            if stop is not None:
                stop_atr = abs(price - _float(stop)) / atr

        rr_values = (
            _float(getattr(state, "rr1", 0.0)),
            _float(getattr(state, "rr2", 0.0)),
            _float(getattr(state, "rr3", 0.0)),
        )
        rr3 = rr_values[2]
        rr = max(rr_values)

        reasons = list(getattr(state, "blockers", []) or [])

        candidate = Candidate(
            symbol=symbol,
            side=side,
            probability=_float(getattr(state, "probability", 0.0)),
            quality=_float(getattr(state, "quality", 0.0)),
            confidence=_float(getattr(state, "confidence", 0.0)),
            rr=rr,
            stop_distance_atr=stop_atr,
            reasons=reasons,
            blocked=False,
            block_reason=None,
            data_ok=bool(getattr(state, "data_ok", False)),
            live=bool(getattr(state, "live", False)),
            trigger_confirmed=bool(getattr(state, "trigger_confirmed", False)),
            structure_direction=str(
                getattr(state, "structure_direction", "NONE") or "NONE"
            ).upper(),
            mtf_direction=str(
                getattr(state, "mtf_direction", "NONE") or "NONE"
            ).upper(),
            entry=getattr(state, "entry", None),
            stop=getattr(state, "stop", None),
            tp1=getattr(state, "tp1", None),
            tp2=getattr(state, "tp2", None),
            tp3=getattr(state, "tp3", None),
            rr1=rr_values[0],
            rr2=rr_values[1],
            rr3=rr3,
            paper_only=_gate(state, "paper_only", True),
            data_quality_ok=_gate(state, "data_quality_ok", False),
            freshness_ok=_freshness_ok(state, _gate(state, "freshness_ok", False), freshness_limit),
            contract_ok=_gate(state, "contract_ok", False),
            liquidity_ok=_gate(state, "liquidity_ok", False),
            volatility_ok=_gate(state, "volatility_ok", False),
            regime_ok=_gate(state, "regime_ok", False),
            session_ok=_gate(state, "session_ok", False),
            curve_ok=_gate(state, "curve_ok", False),
        )

        market = MarketSnapshot(
            symbol=symbol,
            timestamp=str(getattr(state, "analysis_timestamp", "") or ""),
            price=price,
            atr=atr,
            bid=_optional_float(getattr(state, "bid", None)),
            ask=_optional_float(getattr(state, "ask", None)),
            regime=str(getattr(state, "regime", "UNKNOWN")),
            session=str(_metadata(state).get("session", "UNKNOWN")),
        )

        decisions.append(engine.evaluate(market, candidate))

    return decisions
