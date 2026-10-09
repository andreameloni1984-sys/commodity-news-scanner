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

        meta = _metadata(state)
        explicit_gates = meta.get("operational_gates", {})
        if not isinstance(explicit_gates, dict):
            explicit_gates = {}

        # Derive missing operational gates from canonical evidence.
        # Explicit producer gates override these derived values.
        candle_count = int(meta.get("candle_count", 0) or 0)
        data_quality_ok = bool(explicit_gates.get(
            "data_quality_ok",
            getattr(state, "data_ok", False) and candle_count >= 30,
        ))
        freshness_gate = bool(explicit_gates.get(
            "freshness_ok",
            getattr(state, "live", False) and bool(meta.get("fresh_live", False)),
        ))
        # An explicit producer gate is not allowed to override an absent,
        # future-dated, or stale timestamp.
        freshness_ok = freshness_gate and _freshness_ok(
            state, configured=True, max_age_seconds=freshness_limit
        )
        contract_ok = bool(explicit_gates.get(
            "contract_ok",
            symbol in engine.config.allowed_assets and bool(meta.get("resolved_symbol")),
        ))
        liquidity_ok = bool(explicit_gates.get(
            "liquidity_ok",
            getattr(state, "data_ok", False),
        ))
        volatility_ok = bool(explicit_gates.get(
            "volatility_ok",
            stop_atr > 0 and stop_atr <= engine.config.max_stop_atr,
        ))
        opportunity_type = str(getattr(state, "opportunity_type", "NONE") or "NONE").upper()
        regime = getattr(state, "regime", "UNKNOWN")
        regime_allowed = (
            regime in {"TREND_UP", "TREND_DOWN"}
            if opportunity_type == "TREND_CONTINUATION"
            else regime in {"RANGE", "MIXED", "TREND_UP", "TREND_DOWN", "UNKNOWN"}
        )
        regime_ok = bool(explicit_gates.get("regime_ok", regime_allowed))
        session_ok = bool(explicit_gates.get(
            "session_ok",
            getattr(state, "live", False),
        ))
        # Curve evidence is not yet a mandatory producer in the canonical state.
        curve_ok = bool(explicit_gates.get("curve_ok", True))

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
            opportunity_type=str(getattr(state, "opportunity_type", "NONE") or "NONE").upper(),
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
            data_quality_ok=data_quality_ok,
            freshness_ok=freshness_ok,
            contract_ok=contract_ok,
            liquidity_ok=liquidity_ok,
            volatility_ok=volatility_ok,
            regime_ok=regime_ok,
            session_ok=session_ok,
            curve_ok=curve_ok,
        )

        market = MarketSnapshot(
            symbol=symbol,
            timestamp=str(getattr(state, "analysis_timestamp", "") or ""),
            price=price,
            atr=atr,
            regime=str(getattr(state, "regime", "UNKNOWN")),
            session=str(_metadata(state).get("session", "UNKNOWN")),
        )

        decisions.append(engine.evaluate(market, candidate))

    return decisions
