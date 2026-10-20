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
from .commodity_trade_plan import build_commodity_bracket
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

        entry_value = getattr(state, "entry", None)
        stop_value = getattr(state, "stop", None)
        tp1_value = getattr(state, "tp1", None)
        tp2_value = getattr(state, "tp2", None)
        tp3_value = getattr(state, "tp3", None)
        rr1_value = getattr(state, "rr1", None)
        rr2_value = getattr(state, "rr2", None)
        rr3_value = getattr(state, "rr3", None)
        bracket_generated = False
        stop_atr = _float(getattr(state, "stop_atr", 0.0))

        # Apply the studied structural/ATR bracket only when the source has no
        # bracket at all. Never silently replace partially supplied levels.
        no_existing_bracket = all(value is None for value in (
            stop_value, tp1_value, tp2_value, tp3_value,
        ))
        if no_existing_bracket and entry_value is None and price > 0:
            entry_value = price
        if no_existing_bracket and entry_value is not None and price > 0 and atr > 0:
            bracket = build_commodity_bracket(
                side=side,
                entry=entry_value,
                atr=atr,
                highs=getattr(state, "highs", None),
                lows=getattr(state, "lows", None),
            )
            if bracket.get("ok"):
                entry_value = bracket["entry"]
                stop_value, tp1_value, tp2_value, tp3_value = (
                    bracket["stop"], bracket["tp1"], bracket["tp2"], bracket["tp3"]
                )
                rr1_value, rr2_value, rr3_value = bracket["rr1"], bracket["rr2"], bracket["rr3"]
                stop_atr = bracket["stop_distance_atr"]
                bracket_generated = True
                reasons_for_bracket = list(getattr(state, "blockers", []) or [])
                reasons_for_bracket.append("SL_TP_GENERATED_FROM_ATR_AND_STRUCTURE")
            else:
                reasons_for_bracket = list(getattr(state, "blockers", []) or [])
                reasons_for_bracket.append(str(bracket.get("reason", "BRACKET_GENERATION_FAILED")))
        else:
            reasons_for_bracket = list(getattr(state, "blockers", []) or [])

        if not bracket_generated and stop_atr <= 0 and price > 0 and atr > 0 and stop_value is not None:
            stop_atr = abs(price - _float(stop_value)) / atr

        rr_values = (
            _float(rr1_value),
            _float(rr2_value),
            _float(rr3_value),
        )
        rr3 = rr_values[2]
        rr = max(rr_values)

        reasons = reasons_for_bracket

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
        freshness_ok = bool(explicit_gates.get(
            "freshness_ok",
            getattr(state, "live", False) and bool(meta.get("fresh_live", False)),
        ))
        freshness_ok = freshness_ok and _freshness_ok(state, True, freshness_limit)
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
            entry=entry_value,
            stop=stop_value,
            tp1=tp1_value,
            tp2=tp2_value,
            tp3=tp3_value,
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
            bid=_optional_float(getattr(state, "bid", None)),
            ask=_optional_float(getattr(state, "ask", None)),
            regime=str(getattr(state, "regime", "UNKNOWN")),
            session=str(_metadata(state).get("session", "UNKNOWN")),
        )

        decision = engine.evaluate(market, candidate)

        # Keep the canonical bracket on the source state as well as the
        # decision object. Telegram, feedback and the paper journal consume
        # this same state; otherwise a bracket generated here would be invisible
        # to those downstream consumers.
        if entry_value is not None:
            state.entry = entry_value
        if stop_value is not None:
            state.stop = stop_value
        if tp1_value is not None:
            state.tp1 = tp1_value
        if tp2_value is not None:
            state.tp2 = tp2_value
        if tp3_value is not None:
            state.tp3 = tp3_value
        if rr1_value is not None:
            state.rr1 = rr1_value
        if rr2_value is not None:
            state.rr2 = rr2_value
        if rr3_value is not None:
            state.rr3 = rr3_value
        if stop_atr > 0:
            state.stop_atr = stop_atr

        decisions.append(decision)

    return decisions
