"""
SOYUZ GAGARIN — REAL ADAPTER v1.0

Collega i dati REALI prodotti da commodity_bot.py
ai tre motori SOYUZ.

MODALITÀ SHADOW:
- non esegue ordini
- non invia Telegram
- non modifica commodity_bot.py
- non bypassa Gagarin
- confronta la decisione SOYUZ con l'autorità operativa esistente
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from soyuz_adapter import SoyuzAdapter
from soyuz_motors import SoyuzDecision


# ============================================================
# GENERIC HELPERS
# ============================================================

def _num(value: Any, default: float = 0.0) -> float:
    try:
        n = float(value)
        if n != n:
            return default
        return n
    except (TypeError, ValueError):
        return default


def _bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.strip().lower() in {
            "1",
            "true",
            "yes",
            "y",
            "ok",
            "confirmed",
            "authorized",
            "ready",
        }

    return bool(value)


def _first(data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return default


def _nested(data: Dict[str, Any], *paths: str, default: Any = None) -> Any:
    """
    Cerca valori anche dentro strutture annidate.

    Esempio:
        _nested(a, "risk.mode", "risk_mode")
    """

    for path in paths:
        current: Any = data

        try:
            for part in path.split("."):
                if not isinstance(current, dict):
                    current = None
                    break

                current = current.get(part)

            if current is not None:
                return current

        except Exception:
            continue

    return default


def _direction(value: Any) -> str:
    value = str(value or "WAIT").upper().strip()

    if value in {"BUY", "LONG", "CALL"}:
        return "LONG"

    if value in {"SELL", "SHORT", "PUT"}:
        return "SHORT"

    return "WAIT"


def _reasons(*values: Any) -> List[str]:
    result: List[str] = []

    for value in values:

        if value is None:
            continue

        if isinstance(value, str):
            items = [value]

        elif isinstance(value, (list, tuple, set)):
            items = value

        else:
            items = [value]

        for item in items:
            text = str(item).strip()

            if text and text not in result:
                result.append(text)

    return result[:30]


# ============================================================
# MTF
# ============================================================

def _extract_mtf_score(analysis: Dict[str, Any]) -> float:
    """
    Estrae il punteggio MTF dai campi reali del bot.

    Priorità:
    1. mtf_score
    2. timeframes score
    3. singoli timeframe
    """

    direct = _nested(
        analysis,
        "mtf_score",
        "mtf",
        "timeframe_score",
        default=None,
    )

    if direct is not None:
        return max(0.0, min(100.0, _num(direct)))

    timeframes = analysis.get("timeframes")

    if not isinstance(timeframes, dict):
        return 0.0

    values = []

    for tf in ("4H", "1H", "15m"):
        item = timeframes.get(tf)

        if isinstance(item, dict):

            score = _first(
                item,
                "score",
                "alignment_score",
                "strength",
                default=None,
            )

            if score is not None:
                values.append(_num(score))

    if not values:
        return 0.0

    return max(0.0, min(100.0, sum(values) / len(values)))


# ============================================================
# STRUCTURE
# ============================================================

def _structural_ok(
    analysis: Dict[str, Any],
    direction: str,
) -> bool:

    explicit = _first(
        analysis,
        "gagarin_structure_ok",
        "structure_ok",
        default=None,
    )

    if explicit is not None:
        return _bool(explicit)

    timeframes = analysis.get("timeframes")

    if not isinstance(timeframes, dict):
        return False

    aligned = 0

    for tf in ("4H", "1H", "15m"):

        item = timeframes.get(tf)

        if not isinstance(item, dict):
            continue

        tf_direction = _direction(
            _first(
                item,
                "direction",
                "bias",
                "signal",
                "trend",
                default="WAIT",
            )
        )

        if tf_direction == direction:
            aligned += 1

    return aligned >= 2


# ============================================================
# TRIGGER
# ============================================================

def _trigger_confirmed(analysis: Dict[str, Any]) -> bool:

    explicit = _first(
        analysis,
        "gagarin_trigger_ok",
        "trigger_ok",
        default=None,
    )

    if explicit is not None:
        return _bool(explicit)

    prediction = analysis.get("prediction_authority_v531")

    if isinstance(prediction, dict):

        value = _first(
            prediction,
            "trigger_confirmed",
            "confirmed",
            default=None,
        )

        if value is not None:
            return _bool(value)

    trigger = analysis.get("entry_trigger")

    if isinstance(trigger, dict):

        return _bool(
            _first(
                trigger,
                "confirmed",
                "trigger_confirmed",
                default=False,
            )
        )

    return False


# ============================================================
# RISK
# ============================================================

def _risk_ok(analysis: Dict[str, Any]) -> bool:

    explicit = _first(
        analysis,
        "gagarin_risk_ok",
        "risk_ok",
        default=None,
    )

    if explicit is not None:
        return _bool(explicit)

    risk_mode = str(
        _nested(
            analysis,
            "risk.mode",
            "risk_mode",
            default="NORMAL",
        )
        or "NORMAL"
    ).upper()

    if risk_mode in {
        "SHOCK",
        "ALERT",
        "EXTREME",
        "BLOCK",
    }:
        return False

    policy = analysis.get("entry_policy")

    if isinstance(policy, dict):

        blocked = _first(
            policy,
            "risk_blocked",
            "safety_blocked",
            default=False,
        )

        if _bool(blocked):
            return False

        rr1 = _num(
            _first(
                policy,
                "rr_tp1",
                "rr1",
                default=analysis.get("rr_tp1", 0),
            )
        )

        rr2 = _num(
            _first(
                policy,
                "rr_tp2",
                "rr2",
                default=analysis.get("rr_tp2", 0),
            )
        )

        if rr1 > 0 and rr2 > 0:
            return rr1 >= 1.5 and rr2 >= 2.0

    return True


# ============================================================
# SAFETY
# ============================================================

def _safety_ok(analysis: Dict[str, Any]) -> bool:

    explicit = _first(
        analysis,
        "gagarin_safety_ok",
        "safety_ok",
        default=None,
    )

    if explicit is not None:
        return _bool(explicit)

    risk_mode = str(
        _nested(
            analysis,
            "risk.mode",
            "risk_mode",
            default="NORMAL",
        )
        or "NORMAL"
    ).upper()

    if risk_mode in {
        "SHOCK",
        "ALERT",
        "EXTREME",
    }:
        return False

    reversal = str(
        _nested(
            analysis,
            "reversal.stage",
            "reversal_stage",
            default="NONE",
        )
        or "NONE"
    ).upper()

    if reversal == "CONFIRMED":
        return False

    blockers = _first(
        analysis,
        "gagarin_blockers",
        "safety_blockers",
        default=[],
    )

    if blockers:
        return False

    return True


# ============================================================
# MACRO MOTOR
# ============================================================

def build_real_macro_data(
    analysis: Dict[str, Any],
) -> Dict[str, Any]:

    return {
        "regime": _first(
            analysis,
            "market_regime",
            "regime",
            "market_regime_state",
            default="UNKNOWN",
        ),

        "inflation_bias": _num(
            _first(
                analysis,
                "inflation_bias",
                "inflation_impact",
                default=0,
            )
        ),

        "rates_bias": _num(
            _first(
                analysis,
                "rates_bias",
                "interest_rates_bias",
                "fed_bias",
                default=0,
            )
        ),

        "dollar_bias": _num(
            _first(
                analysis,
                "dollar_bias",
                "usd_bias",
                "dxy_bias",
                default=0,
            )
        ),

        "energy_bias": _num(
            _first(
                analysis,
                "energy_bias",
                "energy_impact",
                default=0,
            )
        ),

        "geopolitical_bias": _num(
            _first(
                analysis,
                "geopolitical_bias",
                "geopolitical_impact",
                "political_bias",
                "political_impact",
                default=0,
            )
        ),

        "fundamentals_bias": _num(
            _first(
                analysis,
                "fundamentals_bias",
                "fundamental_bias",
                "commodity_fundamental_bias",
                default=0,
            )
        ),

        "confidence": _num(
            _first(
                analysis,
                "macro_confidence",
                "fundamental_confidence",
                "confidence",
                default=0,
            )
        ),

        "reasons": _reasons(
            _first(analysis, "macro_reasons"),
            _first(analysis, "fundamental_reasons"),
            _first(analysis, "political_reasons"),
            _first(analysis, "geopolitical_reasons"),
        ),
    }


# ============================================================
# INTELLIGENCE MOTOR
# ============================================================

def build_real_intelligence_data(
    analysis: Dict[str, Any],
) -> Dict[str, Any]:

    direction = _direction(
        _first(
            analysis,
            "setup_direction",
            "model_signal",
            "final_direction",
            "direction",
            "bias",
            default="WAIT",
        )
    )

    mtf_score = _extract_mtf_score(analysis)

    correlation_score = _num(
        _first(
            analysis,
            "correlation_score",
            "cross_commodity_score",
            "cross_sectional_score",
            default=0,
        )
    )

    news_score = _num(
        _first(
            analysis,
            "news_score",
            "news_impact_score",
            "market_intelligence_score",
            default=0,
        )
    )

    futures_score = _num(
        _first(
            analysis,
            "futures_score",
            "futures_structure_score",
            default=0,
        )
    )

    anomaly_score = _num(
        _first(
            analysis,
            "anomaly_score",
            "anomaly",
            "volatility_score",
            default=0,
        )
    )

    return {
        "direction": direction,
        "mtf_score": mtf_score,
        "correlation_score": max(
            0.0,
            min(100.0, correlation_score),
        ),
        "news_score": max(
            0.0,
            min(100.0, news_score),
        ),
        "futures_score": max(
            0.0,
            min(100.0, futures_score),
        ),
        "anomaly_score": max(
            0.0,
            min(100.0, anomaly_score),
        ),
        "reasons": _reasons(
            _first(analysis, "intelligence_reasons"),
            _first(analysis, "market_intelligence_reasons"),
            _first(analysis, "news_reasons"),
            _first(analysis, "futures_reasons"),
        ),
    }


# ============================================================
# GAGARIN MOTOR
# ============================================================

def build_real_gagarin_data(
    analysis: Dict[str, Any],
) -> Dict[str, Any]:

    direction = _direction(
        _first(
            analysis,
            "setup_direction",
            "model_signal",
            "final_direction",
            "direction",
            default="WAIT",
        )
    )

    regime = str(
        _first(
            analysis,
            "market_regime",
            "regime",
            default="UNKNOWN",
        )
        or "UNKNOWN"
    ).upper()

    regime_ok = _first(
        analysis,
        "gagarin_regime_ok",
        "regime_ok",
        default=None,
    )

    if regime_ok is None:
        regime_ok = (
            direction in {"LONG", "SHORT"}
            and regime not in {
                "UNKNOWN",
                "SHOCK",
                "BLOCK",
            }
        )

    structure_ok = _structural_ok(
        analysis,
        direction,
    )

    setup_status = str(
        _first(
            analysis,
            "setup_status",
            default="",
        )
        or ""
    ).upper()

    setup_ok = _first(
        analysis,
        "gagarin_setup_ok",
        "setup_ok",
        default=None,
    )

    if setup_ok is None:
        setup_ok = (
            direction in {"LONG", "SHORT"}
            and setup_status not in {
                "NO_SETUP",
                "NO_DIRECTION",
            }
        )

    trigger_ok = _trigger_confirmed(
        analysis
    )

    risk_ok = _risk_ok(
        analysis
    )

    safety_ok = _safety_ok(
        analysis
    )

    return {
        "regime_ok": _bool(regime_ok),
        "structure_ok": bool(structure_ok),
        "setup_ok": _bool(setup_ok),
        "trigger_ok": bool(trigger_ok),
        "risk_ok": bool(risk_ok),
        "safety_ok": bool(safety_ok),
        "reasons": _reasons(
            _first(analysis, "gagarin_blockers"),
            _first(analysis, "gagarin_reasons"),
            _first(analysis, "entry_policy_blockers"),
        ),
    }


# ============================================================
# REAL ADAPTER
# ============================================================

class SoyuzRealAdapter:

    def __init__(
        self,
        adapter: Optional[SoyuzAdapter] = None,
    ) -> None:

        self.adapter = adapter or SoyuzAdapter()

    def evaluate(
        self,
        commodity: str,
        analysis: Dict[str, Any],
    ) -> Dict[str, Any]:

        macro_data = build_real_macro_data(
            analysis
        )

        intelligence_data = build_real_intelligence_data(
            analysis
        )

        gagarin_data = build_real_gagarin_data(
            analysis
        )

        decision: SoyuzDecision = (
            self.adapter.fusion.evaluate(
                commodity=commodity,
                macro_data=macro_data,
                intelligence_data=intelligence_data,
                gagarin_data=gagarin_data,
            )
        )

        actual_operational_allowed = _bool(
            _first(
                analysis,
                "operational_entry_allowed",
                default=False,
            )
        )

        entry_policy = analysis.get(
            "entry_policy"
        )

        actual_entry_status = ""

        if isinstance(entry_policy, dict):
            actual_entry_status = str(
                entry_policy.get(
                    "entry_status",
                    "",
                )
            )

        return {
            "commodity": commodity,

            "soyuz": {
                "state": decision.state,
                "direction": decision.direction,
                "macro_bias": decision.macro_bias,
                "intelligence_score": decision.intelligence_score,
                "gagarin_authorized": decision.gagarin_authorized,
                "reasons": decision.reasons,
                "metadata": decision.metadata,
            },

            "existing_bot": {
                "operational_entry_allowed":
                    actual_operational_allowed,

                "entry_status":
                    actual_entry_status,

                "setup_direction":
                    _direction(
                        _first(
                            analysis,
                            "setup_direction",
                            "model_signal",
                            default="WAIT",
                        )
                    ),

                "entry_probability":
                    _num(
                        analysis.get(
                            "entry_probability",
                            0,
                        )
                    ),

                "quality":
                    _num(
                        analysis.get(
                            "quality",
                            0,
                        )
                    ),

                "confidence":
                    _num(
                        analysis.get(
                            "confidence",
                            0,
                        )
                    ),
            },

            "shadow": {
                "same_direction":
                    decision.direction ==
                    _direction(
                        _first(
                            analysis,
                            "setup_direction",
                            "model_signal",
                            default="WAIT",
                        )
                    ),

                "soyuz_authorized":
                    decision.gagarin_authorized,

                "existing_bot_authorized":
                    actual_operational_allowed,

                "agreement":
                    decision.gagarin_authorized ==
                    actual_operational_allowed,
            },
        }


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================

def evaluate_real_soyuz(
    commodity: str,
    analysis: Dict[str, Any],
) -> Dict[str, Any]:

    adapter = SoyuzRealAdapter()

    return adapter.evaluate(
        commodity=commodity,
        analysis=analysis,
    )


# ============================================================
# SHADOW REPORT
# ============================================================

def shadow_summary(
    result: Dict[str, Any],
) -> str:

    soyuz = result.get(
        "soyuz",
        {},
    )

    existing = result.get(
        "existing_bot",
        {},
    )

    shadow = result.get(
        "shadow",
        {},
    )

    return (
        f"SOYUZ SHADOW | "
        f"{result.get('commodity', '?')} | "
        f"{soyuz.get('direction', 'WAIT')} | "
        f"SOYUZ={soyuz.get('state', 'NO_SETUP')} | "
        f"EXISTING="
        f"{'AUTHORIZED' if existing.get('operational_entry_allowed') else 'BLOCKED'} | "
        f"AGREEMENT="
        f"{'YES' if shadow.get('agreement') else 'NO'}"
    )