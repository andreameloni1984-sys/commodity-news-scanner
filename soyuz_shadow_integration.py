"""
SOYUZ GAGARIN — SHADOW INTEGRATION v1.1

Ponte tra commodity_bot.py e i tre motori SOYUZ.

MODALITÀ SHADOW:
- NON modifica results
- NON modifica operational_entry_allowed
- NON modifica signal/action_label
- NON invia Telegram
- NON esegue ordini
- NON sostituisce Gagarin
- NON bypassa i gate esistenti
- produce esclusivamente un confronto diagnostico
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, List, Optional

from soyuz_adapter import SoyuzAdapter, decision_summary


# ============================================================
# GENERIC HELPERS
# ============================================================

def _first(
    data: Dict[str, Any],
    *keys: str,
    default: Any = None,
) -> Any:
    if not isinstance(data, dict):
        return default

    for key in keys:
        if key in data and data[key] is not None:
            return data[key]

    return default


def _dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> List[Any]:
    if value is None:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, tuple):
        return list(value)

    return [value]


def _bool(
    value: Any,
    default: bool = False,
) -> bool:
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return bool(value)

    if isinstance(value, str):
        text = value.strip().lower()

        if text in {
            "1", "true", "yes", "y", "ok",
            "confirmed", "confirm", "authorized",
            "authorised", "ready", "pass", "passed",
            "valid", "safe",
        }:
            return True

        if text in {
            "0", "false", "no", "n", "blocked",
            "block", "failed", "fail", "invalid",
            "unsafe", "wait", "waiting", "none",
        }:
            return False

    return default


def _num(
    value: Any,
    default: float = 0.0,
) -> float:
    try:
        number = float(value)

        if number != number:
            return default

        return number

    except (TypeError, ValueError):
        return default


def _bounded(
    value: Any,
    low: float = 0.0,
    high: float = 100.0,
) -> float:
    return max(
        low,
        min(
            high,
            _num(value, low),
        ),
    )


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default

    text = str(value).strip()
    return text if text else default


def _upper(value: Any, default: str = "") -> str:
    text = _text(value)
    return text.upper() if text else default


def _clean_reasons(
    values: Iterable[Any],
) -> List[str]:
    if isinstance(values, str):
        values = [values]

    result: List[str] = []

    for value in values or []:
        text = _text(value)

        if text and text not in result:
            result.append(text)

    return result[:20]


# ============================================================
# DIRECTION
# ============================================================

def extract_direction(
    analysis: Dict[str, Any],
) -> str:
    value = _first(
        analysis,
        "final_direction",
        "setup_direction",
        "model_signal",
        "signal",
        "bias",
        default="WAIT",
    )

    direction = _upper(value)

    if "LONG" in direction:
        return "LONG"

    if "SHORT" in direction:
        return "SHORT"

    return "WAIT"


# ============================================================
# TIMEFRAME / MTF
# ============================================================

def _extract_timeframe_direction(
    value: Any,
) -> Optional[str]:
    if isinstance(value, str):
        direction = _upper(value)

        if "LONG" in direction:
            return "LONG"

        if "SHORT" in direction:
            return "SHORT"

        return "WAIT"

    if isinstance(value, dict):
        candidate = _first(
            value,
            "direction",
            "signal",
            "bias",
            "trend",
            "side",
            "model_signal",
            "setup_direction",
            default=None,
        )

        if candidate is not None:
            return _extract_timeframe_direction(candidate)

    return None


def extract_mtf_score(
    analysis: Dict[str, Any],
    direction: str,
) -> float:
    explicit = _first(
        analysis,
        "mtf_score",
        "mtf",
        "multi_timeframe_score",
        default=None,
    )

    if explicit is not None:
        return _bounded(explicit)

    timeframes = _first(
        analysis,
        "timeframes",
        "multi_timeframe",
        "multi_timeframes",
        default=None,
    )

    if not isinstance(timeframes, dict):
        return 0.0

    preferred = [
        "4H",
        "1H",
        "15m",
        "5m",
        "1m",
    ]

    directions: List[str] = []

    for key in preferred:
        if key not in timeframes:
            continue

        value = _extract_timeframe_direction(
            timeframes[key]
        )

        if value:
            directions.append(value)

    if not directions or direction not in {"LONG", "SHORT"}:
        return 0.0

    aligned = sum(
        1
        for item in directions
        if item == direction
    )

    usable = len(directions)

    return _bounded(
        aligned / usable * 100.0
    )


# ============================================================
# GAGARIN NESTED DATA
# ============================================================

def extract_gagarin(
    analysis: Dict[str, Any],
) -> Dict[str, Any]:
    value = analysis.get("gagarin")

    if isinstance(value, dict):
        return value

    return {}


def _section(
    gagarin: Dict[str, Any],
    name: str,
) -> Dict[str, Any]:
    value = gagarin.get(name)

    if isinstance(value, dict):
        return value

    return {}


# ============================================================
# REGIME GATE
# ============================================================

def extract_regime_ok(
    analysis: Dict[str, Any],
    gagarin: Dict[str, Any],
) -> bool:
    explicit = _first(
        analysis,
        "gagarin_regime_ok",
        "regime_ok",
        default=None,
    )

    if explicit is not None:
        return _bool(explicit)

    regime_data = _section(
        gagarin,
        "regime",
    )

    explicit_nested = _first(
        regime_data,
        "ok",
        "valid",
        "confirmed",
        "allowed",
        default=None,
    )

    if explicit_nested is not None:
        return _bool(explicit_nested)

    regime = _upper(
        _first(
            regime_data,
            "state",
            "regime",
            "name",
            "label",
            default=None,
        )
    )

    if not regime:
        regime = _upper(
            _first(
                analysis,
                "market_regime",
                "regime",
                "regime_name",
                default="UNKNOWN",
            )
        )

    if regime in {
        "SHOCK",
        "REGIME_SHOCK",
        "CRISIS",
        "PANIC",
    }:
        return False

    if regime in {
        "UNKNOWN",
        "NONE",
        "",
    }:
        return False

    return True


# ============================================================
# STRUCTURE GATE
# ============================================================

def extract_structure_ok(
    analysis: Dict[str, Any],
    gagarin: Dict[str, Any],
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

    structure = _section(
        gagarin,
        "structure",
    )

    explicit_nested = _first(
        structure,
        "ok",
        "valid",
        "confirmed",
        "allowed",
        default=None,
    )

    if explicit_nested is not None:
        return _bool(explicit_nested)

    state = _upper(
        _first(
            structure,
            "state",
            "status",
            "label",
            default="",
        )
    )

    if state in {
        "INVALID",
        "BROKEN",
        "CONFLICT",
        "FAILED",
        "NO_STRUCTURE",
        "SHOCK",
    }:
        return False

    mtf_score = extract_mtf_score(
        analysis,
        direction,
    )

    return (
        direction in {"LONG", "SHORT"}
        and mtf_score >= 80.0
    )


# ============================================================
# SETUP GATE
# ============================================================

def extract_setup_ok(
    analysis: Dict[str, Any],
    gagarin: Dict[str, Any],
    direction: str,
) -> bool:
    explicit = _first(
        analysis,
        "gagarin_setup_ok",
        "setup_ok",
        default=None,
    )

    if explicit is not None:
        return _bool(explicit)

    setup = _section(
        gagarin,
        "setup",
    )

    explicit_nested = _first(
        setup,
        "ok",
        "valid",
        "confirmed",
        "allowed",
        default=None,
    )

    if explicit_nested is not None:
        return _bool(explicit_nested)

    state = _upper(
        _first(
            setup,
            "state",
            "status",
            "label",
            default="",
        )
    )

    if state in {
        "NO_SETUP",
        "NONE",
        "INVALID",
        "FAILED",
        "BLOCKED",
    }:
        return False

    if state in {
        "READY",
        "CONFIRMED",
        "VALID",
        "ACTIVE",
        "SETUP",
    }:
        return direction in {
            "LONG",
            "SHORT",
        }

    return False


# ============================================================
# TRIGGER GATE
# ============================================================

def extract_technical_trigger_ok(analysis: Dict[str, Any]) -> bool:
    """Read only the lower-level technical trigger, excluding prediction authority."""
    trigger_value = analysis.get("entry_trigger")
    if isinstance(trigger_value, dict):
        value = _first(
            trigger_value,
            "confirmed",
            "ok",
            "valid",
            "authorized",
            "trigger_confirmed",
            default=None,
        )
        if value is not None:
            return _bool(value)
        state = _upper(_first(trigger_value, "state", "status", "label", default=""))
        return state in {"CONFIRMED", "READY", "VALID", "ACTIVE", "TRIGGERED"}
    if trigger_value is not None:
        return _bool(trigger_value)
    return False


def extract_prediction_trigger_ok(analysis: Dict[str, Any]) -> Optional[bool]:
    prediction = analysis.get("prediction_authority_v531")
    if not isinstance(prediction, dict):
        return None
    value = _first(prediction, "trigger_confirmed", "confirmed", default=None)
    if value is None:
        return None
    return _bool(value)


def extract_trigger_ok(
    analysis: Dict[str, Any],
    gagarin: Dict[str, Any],
) -> bool:
    # Prediction Authority v5.3.1 is the final trigger authority.
    # A lower-level technical trigger (entry_trigger) must not override a
    # prediction-level FALSE. This is diagnostic only; it never authorizes an entry.
    prediction_value = extract_prediction_trigger_ok(analysis)
    if prediction_value is not None:
        return prediction_value

    explicit = _first(
        analysis,
        "gagarin_trigger_ok",
        "trigger_ok",
        default=None,
    )

    if explicit is not None:
        return _bool(explicit)

    trigger = _section(
        gagarin,
        "trigger",
    )

    if not trigger:
        trigger_value = analysis.get(
            "entry_trigger"
        )

        if isinstance(trigger_value, dict):
            trigger = trigger_value

        elif trigger_value is not None:
            return _bool(
                trigger_value
            )

    explicit_nested = _first(
        trigger,
        "confirmed",
        "ok",
        "valid",
        "authorized",
        "trigger_confirmed",
        default=None,
    )

    if explicit_nested is not None:
        return _bool(explicit_nested)

    state = _upper(
        _first(
            trigger,
            "state",
            "status",
            "label",
            default="",
        )
    )

    if state in {
        "CONFIRMED",
        "READY",
        "VALID",
        "ACTIVE",
        "TRIGGERED",
    }:
        return True

    return False


# ============================================================
# RISK GATE
# ============================================================

def extract_risk_ok(
    analysis: Dict[str, Any],
    gagarin: Dict[str, Any],
) -> bool:
    explicit = _first(
        analysis,
        "gagarin_risk_ok",
        "risk_ok",
        default=None,
    )

    if explicit is not None:
        return _bool(explicit)

    risk = _section(
        gagarin,
        "risk",
    )

    explicit_nested = _first(
        risk,
        "ok",
        "valid",
        "confirmed",
        "allowed",
        default=None,
    )

    if explicit_nested is not None:
        return _bool(explicit_nested)

    state = _upper(
        _first(
            risk,
            "state",
            "status",
            "mode",
            "label",
            default="",
        )
    )

    if state in {
        "BLOCKED",
        "INVALID",
        "FAILED",
        "SHOCK",
        "UNSAFE",
    }:
        return False

    if state in {
        "READY",
        "VALID",
        "CONFIRMED",
        "SAFE",
        "NORMAL",
    }:
        return True

    rr = _first(
        analysis,
        "rr",
        "risk_reward",
        "risk_reward_ratio",
        default=None,
    )

    if rr is not None:
        return _num(rr) >= 1.5

    rr_tp1 = _first(
        risk,
        "rr_tp1",
        "tp1_rr",
        "risk_reward_tp1",
        default=None,
    )

    if rr_tp1 is not None:
        return _num(rr_tp1) >= 1.5

    return False


# ============================================================
# SAFETY GATE
# ============================================================

def extract_safety_ok(
    analysis: Dict[str, Any],
    gagarin: Dict[str, Any],
) -> bool:
    explicit = _first(
        analysis,
        "gagarin_safety_ok",
        "safety_ok",
        default=None,
    )

    if explicit is not None:
        return _bool(explicit)

    safety = _section(
        gagarin,
        "safety",
    )

    explicit_nested = _first(
        safety,
        "ok",
        "valid",
        "confirmed",
        "allowed",
        "safe",
        default=None,
    )

    if explicit_nested is not None:
        return _bool(explicit_nested)

    state = _upper(
        _first(
            safety,
            "state",
            "status",
            "label",
            default="",
        )
    )

    if state in {
        "SAFE",
        "READY",
        "VALID",
        "CONFIRMED",
        "PASS",
        "PASSED",
    }:
        return True

    if state in {
        "BLOCKED",
        "UNSAFE",
        "SHOCK",
        "FAILED",
        "INVALID",
        "REVERSAL",
    }:
        return False

    blockers = _first(
        safety,
        "blockers",
        "safety_blockers",
        "reasons",
        default=[],
    )

    if blockers:
        return False

    return False


# ============================================================
# MACRO DATA
# ============================================================

def build_macro_data(
    analysis: Dict[str, Any],
) -> Dict[str, Any]:
    gagarin = extract_gagarin(
        analysis
    )

    regime_data = _section(
        gagarin,
        "regime",
    )

    return {
        "regime": _first(
            analysis,
            "market_regime",
            "regime",
            "regime_name",
            default=_first(
                regime_data,
                "state",
                "regime",
                "name",
                default="UNKNOWN",
            ),
        ),
        "inflation_bias": _num(
            _first(
                analysis,
                "inflation_bias",
                default=0,
            )
        ),
        "rates_bias": _num(
            _first(
                analysis,
                "rates_bias",
                "interest_rates_bias",
                default=0,
            )
        ),
        "dollar_bias": _num(
            _first(
                analysis,
                "dollar_bias",
                "usd_bias",
                default=0,
            )
        ),
        "energy_bias": _num(
            _first(
                analysis,
                "energy_bias",
                default=0,
            )
        ),
        "geopolitical_bias": _num(
            _first(
                analysis,
                "geopolitical_bias",
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
                default=0,
            )
        ),
        "confidence": _bounded(
            _first(
                analysis,
                "macro_confidence",
                "fundamental_confidence",
                default=0,
            )
        ),
        "reasons": _first(
            analysis,
            "macro_reasons",
            "fundamental_reasons",
            default=[],
        ),
    }


# ============================================================
# MARKET INTELLIGENCE DATA
# ============================================================

def _extract_score_from_nested(
    analysis: Dict[str, Any],
    names: Iterable[str],
) -> float:
    names = list(names)

    direct = _first(
        analysis,
        *names,
        default=None,
    )

    if direct is not None:
        return _bounded(
            direct
        )

    intelligence = _dict(
        _first(
            analysis,
            "market_intelligence",
            "intelligence",
            "market_intelligence_v4",
            default={},
        )
    )

    nested = _first(
        intelligence,
        *names,
        default=None,
    )

    if nested is not None:
        return _bounded(
            nested
        )

    return 0.0


def build_intelligence_data(
    analysis: Dict[str, Any],
) -> Dict[str, Any]:
    direction = extract_direction(
        analysis
    )

    mtf_score = extract_mtf_score(
        analysis,
        direction,
    )

    return {
        "direction": direction,
        "mtf_score": mtf_score,
        "correlation_score": _extract_score_from_nested(
            analysis,
            (
                "correlation_score",
                "cross_commodity_score",
                "cross_market_score",
            ),
        ),
        "news_score": _extract_score_from_nested(
            analysis,
            (
                "news_score",
                "news_confirmation_score",
                "intelligence_score",
            ),
        ),
        "futures_score": _extract_score_from_nested(
            analysis,
            (
                "futures_score",
                "futures_structure_score",
            ),
        ),
        "anomaly_score": _extract_score_from_nested(
            analysis,
            (
                "anomaly_score",
                "anomaly",
            ),
        ),
        "reasons": _first(
            analysis,
            "intelligence_reasons",
            "market_intelligence_reasons",
            default=[],
        ),
    }


# ============================================================
# GAGARIN DATA
# ============================================================

def build_gagarin_data(
    analysis: Dict[str, Any],
) -> Dict[str, Any]:
    gagarin = extract_gagarin(
        analysis
    )

    direction = extract_direction(
        analysis
    )

    regime_ok = extract_regime_ok(
        analysis,
        gagarin,
    )

    structure_ok = extract_structure_ok(
        analysis,
        gagarin,
        direction,
    )

    setup_ok = extract_setup_ok(
        analysis,
        gagarin,
        direction,
    )

    trigger_ok = extract_trigger_ok(
        analysis,
        gagarin,
    )

    risk_ok = extract_risk_ok(
        analysis,
        gagarin,
    )

    safety_ok = extract_safety_ok(
        analysis,
        gagarin,
    )

    blockers = _first(
        analysis,
        "gagarin_blockers",
        default=[],
    )

    if not blockers:
        policy = _section(
            gagarin,
            "entry_policy",
        )

        blockers = _first(
            policy,
            "blockers",
            "reasons",
            default=[],
        )

    reasons = _clean_reasons(
        blockers
    )

    if not regime_ok:
        reasons.append(
            "SOYUZ_REGIME_GATE_BLOCKED"
        )

    if not structure_ok:
        reasons.append(
            "SOYUZ_STRUCTURE_GATE_BLOCKED"
        )

    if not setup_ok:
        reasons.append(
            "SOYUZ_SETUP_GATE_BLOCKED"
        )

    if not trigger_ok:
        reasons.append(
            "SOYUZ_TRIGGER_GATE_BLOCKED"
        )

    if not risk_ok:
        reasons.append(
            "SOYUZ_RISK_GATE_BLOCKED"
        )

    if not safety_ok:
        reasons.append(
            "SOYUZ_SAFETY_GATE_BLOCKED"
        )

    return {
        "regime_ok": regime_ok,
        "structure_ok": structure_ok,
        "setup_ok": setup_ok,
        "trigger_ok": trigger_ok,
        "risk_ok": risk_ok,
        "safety_ok": safety_ok,
        "reasons": _clean_reasons(
            reasons
        ),
    }


# ============================================================
# BOT SNAPSHOT
# ============================================================

def build_bot_snapshot(
    analysis: Dict[str, Any],
) -> Dict[str, Any]:
    gagarin = extract_gagarin(
        analysis
    )

    policy = _section(
        gagarin,
        "entry_policy",
    )

    gagarin_state = _first(
        analysis,
        "gagarin_state",
        default=_first(
            policy,
            "state",
            "status",
            default="UNKNOWN",
        ),
    )

    blockers = _first(
        analysis,
        "gagarin_blockers",
        default=_first(
            policy,
            "blockers",
            "reasons",
            default=[],
        ),
    )

    # Snapshot dei sei gate reali del motore attuale.
    # Questi valori sono letti, non modificati.
    bot_gates = {
        "regime_ok": extract_regime_ok(analysis, gagarin),
        "structure_ok": extract_structure_ok(analysis, gagarin, extract_direction(analysis)),
        "setup_ok": extract_setup_ok(analysis, gagarin, extract_direction(analysis)),
        "trigger_ok": extract_trigger_ok(analysis, gagarin),
        "risk_ok": extract_risk_ok(analysis, gagarin),
        "safety_ok": extract_safety_ok(analysis, gagarin),
    }

    technical_trigger = extract_technical_trigger_ok(analysis)
    prediction_trigger = extract_prediction_trigger_ok(analysis)

    return {
        "direction": extract_direction(analysis),
        "technical_trigger_ok": technical_trigger,
        "prediction_trigger_ok": prediction_trigger if prediction_trigger is not None else technical_trigger,
        "operational_entry_allowed": _bool(
            analysis.get("operational_entry_allowed"),
            default=False,
        ),
        "gagarin_state": _text(gagarin_state),
        "gagarin_blockers": _clean_reasons(blockers),
        "signal": _text(analysis.get("signal")),
        "action_label": _text(analysis.get("action_label")),
        "entry_policy_state": _text(
            _first(policy, "state", "status", default="")
        ),
        "gates": bot_gates,
    }


# ============================================================
# COMPARISON
# ============================================================

def compare_bot_and_soyuz(
    bot_snapshot: Dict[str, Any],
    soyuz_decision: Any,
    soyuz_gates: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Confronto diagnostico per singolo livello.

    Non stabilisce quale motore sia corretto. Dice soltanto dove i due
    motori sono allineati o divergono.
    """
    soyuz_gates = soyuz_gates or {}

    bot_direction = _upper(bot_snapshot.get("direction"), "WAIT")
    soyuz_direction = _upper(
        getattr(soyuz_decision, "direction", "WAIT"),
        "WAIT",
    )

    bot_entry = _bool(bot_snapshot.get("operational_entry_allowed"), False)
    soyuz_entry = bool(getattr(soyuz_decision, "gagarin_authorized", False))

    direction_status = "ALIGNED" if bot_direction == soyuz_direction else "DIVERGE"
    authority_status = "ALIGNED" if bot_entry == soyuz_entry else "DIVERGE"

    bg = _dict(bot_snapshot.get("gates"))

    pairs = {
        "REGIME": ("regime_ok", "regime_ok"),
        "STRUCTURE": ("structure_ok", "structure_ok"),
        "SETUP": ("setup_ok", "setup_ok"),
        "TRIGGER": ("trigger_ok", "trigger_ok"),
        "RISK": ("risk_ok", "risk_ok"),
        "SAFETY": ("safety_ok", "safety_ok"),
    }

    layers: Dict[str, str] = {}
    layer_values: Dict[str, Dict[str, bool]] = {}

    for label, (bk, sk) in pairs.items():
        b = _bool(bg.get(bk), False)
        so = _bool(soyuz_gates.get(sk), False)
        layer_values[label] = {"bot": b, "soyuz": so}
        if b == so:
            layers[label] = "PASS" if b else "FAIL"
        else:
            layers[label] = "DIVERGE"

    divergences = [name for name, status in layers.items() if status == "DIVERGE"]

    if direction_status == "DIVERGE":
        primary = "DIRECTION_DIVERGENCE"
    elif divergences:
        primary = "GATE_DIVERGENCE:" + ",".join(divergences)
    elif authority_status == "DIVERGE":
        primary = "AUTHORITY_DIVERGENCE"
    else:
        primary = "ALIGNED"

    return {
        "status": primary,
        "primary_status": primary,
        "direction_divergence": direction_status == "DIVERGE",
        "entry_authority_divergence": authority_status == "DIVERGE",
        "state_divergence": False,
        "divergence_count": len(divergences) + (1 if direction_status == "DIVERGE" else 0) + (1 if authority_status == "DIVERGE" else 0),
        "bot_direction": bot_direction,
        "soyuz_direction": soyuz_direction,
        "bot_operational_entry_allowed": bot_entry,
        "soyuz_authorized": soyuz_entry,
        "bot_state": _upper(bot_snapshot.get("gagarin_state"), "UNKNOWN"),
        "soyuz_state": _upper(getattr(soyuz_decision, "state", "UNKNOWN"), "UNKNOWN"),
        "layers": layers,
        "layer_values": layer_values,
        "divergences": divergences,
    }


def diagnostic_line(result: Dict[str, Any]) -> str:
    """Formato leggibile per il log del run."""
    commodity = _text(result.get("commodity"), "UNKNOWN")
    bot = _dict(result.get("bot"))
    soyuz = _dict(result.get("soyuz"))
    cmp = _dict(result.get("comparison"))
    layers = _dict(cmp.get("layers"))

    def mark(name: str) -> str:
        return {
            "PASS": "OK",
            "FAIL": "NO",
            "DIVERGE": "DIFF",
        }.get(_upper(layers.get(name), "UNKNOWN"), "?")

    blockers = _list(soyuz.get("gagarin_blockers"))
    first_blocker = blockers[0] if blockers else "NONE"
    technical_trigger = _bool(bot.get("technical_trigger_ok"), False)
    prediction_trigger = _bool(bot.get("prediction_trigger_ok"), False)
    trigger_disagreement = technical_trigger != prediction_trigger

    return (
        f"SOYUZ DIAG | {commodity} | "
        f"BOT={_text(bot.get('direction'), 'WAIT')} | "
        f"SOYUZ={_text(soyuz.get('direction'), 'WAIT')} | "
        f"REG={mark('REGIME')} STR={mark('STRUCTURE')} SET={mark('SETUP')} "
        f"TRG={mark('TRIGGER')} RISK={mark('RISK')} SAFE={mark('SAFETY')} | "
        f"TECH_TRG={'OK' if technical_trigger else 'NO'} "
        f"PRED_TRG={'OK' if prediction_trigger else 'NO'} "
        f"TRG_DIFF={'YES' if trigger_disagreement else 'NO'} | "
        f"FIRST_BLOCKER={first_blocker} | "
        f"SHADOW_AUTH={'DIFF' if cmp.get('entry_authority_divergence') else 'OK'} | "
        f"{_text(cmp.get('primary_status'), 'UNKNOWN')}"
    )


# ============================================================
# MAIN SHADOW EVALUATION
# ============================================================

def evaluate_shadow(
    commodity: str,
    analysis: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Esegue una valutazione SOYUZ completamente separata.

    L'analysis originale NON viene modificata.
    """

    if not isinstance(
        analysis,
        dict,
    ):
        raise TypeError(
            "analysis must be a dict"
        )

    local_analysis = deepcopy(
        analysis
    )

    adapter = SoyuzAdapter()

    macro_data = build_macro_data(
        local_analysis
    )

    intelligence_data = build_intelligence_data(
        local_analysis
    )

    gagarin_data = build_gagarin_data(
        local_analysis
    )

    decision = adapter.fusion.evaluate(
        commodity=commodity,
        macro_data=macro_data,
        intelligence_data=intelligence_data,
        gagarin_data=gagarin_data,
    )

    bot_snapshot = build_bot_snapshot(
        local_analysis
    )

    comparison = compare_bot_and_soyuz(
        bot_snapshot,
        decision,
        soyuz_gates=gagarin_data,
    )

    return {
        "commodity": commodity,
        "mode": "SHADOW",
        "bot": bot_snapshot,
        "soyuz": {
            "direction": decision.direction,
            "state": decision.state,
            "macro_bias": decision.macro_bias,
            "intelligence_score": (
                decision.intelligence_score
            ),
            "gagarin_authorized": (
                decision.gagarin_authorized
            ),
            "gagarin_blockers": list(
                gagarin_data.get("reasons", [])
            ),
            "reasons": list(
                decision.reasons
            ),
            "metadata": dict(
                decision.metadata
            ),
            "gates": {
                "regime_ok": gagarin_data[
                    "regime_ok"
                ],
                "structure_ok": gagarin_data[
                    "structure_ok"
                ],
                "setup_ok": gagarin_data[
                    "setup_ok"
                ],
                "trigger_ok": gagarin_data[
                    "trigger_ok"
                ],
                "risk_ok": gagarin_data[
                    "risk_ok"
                ],
                "safety_ok": gagarin_data[
                    "safety_ok"
                ],
            },
        },
        "comparison": comparison,
        "diagnostic": diagnostic_line({
            "commodity": commodity,
            "bot": bot_snapshot,
            "soyuz": {
                "direction": decision.direction,
                "state": decision.state,
            },
            "comparison": comparison,
        }),
        "summary": decision_summary(decision),
    }


# ============================================================
# SAFE RUNTIME WRAPPER
# ============================================================

def run_shadow_safe(
    commodity: str,
    analysis: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Qualsiasi errore SOYUZ viene isolato.

    Il bot principale NON deve fermarsi
    a causa del modulo shadow.
    """

    try:
        result = evaluate_shadow(
            commodity=commodity,
            analysis=analysis,
        )

        result["error"] = None

        return result

    except Exception as exc:
        return {
            "commodity": commodity,
            "mode": "SHADOW",
            "error": (
                f"{type(exc).__name__}: {exc}"
            ),
            "bot": {},
            "soyuz": {},
            "comparison": {
                "status": "ERROR"
            },
            "summary": (
                f"SOYUZ SHADOW ERROR | "
                f"{commodity} | "
                f"{type(exc).__name__}: {exc}"
            ),
        }


# ============================================================
# MULTI-RESULTS HELPER
# ============================================================

def run_shadow_for_results(
    results: Iterable[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Esegue SOYUZ Shadow su una lista di risultati
    provenienti dal commodity_bot.

    NON modifica results.
    """

    output: List[Dict[str, Any]] = []

    for item in results or []:

        if not isinstance(
            item,
            dict,
        ):
            continue

        commodity = _text(
            _first(
                item,
                "commodity",
                "name",
                "symbol",
                default="UNKNOWN",
            )
        )

        analysis = item.get(
            "analysis"
        )

        if not isinstance(
            analysis,
            dict,
        ):
            continue

        result = run_shadow_safe(
            commodity=commodity,
            analysis=analysis,
        )

        output.append(result)

        # Non modifica il bot; produce solo diagnostica.
        print(result.get("diagnostic") or result.get("summary", ""))

    return output


# ============================================================
# LOG-SAFE SUMMARY
# ============================================================

def compact_shadow_line(
    result: Dict[str, Any],
) -> str:
    """
    Una singola riga diagnostica.
    """

    commodity = _text(
        result.get(
            "commodity",
            "UNKNOWN",
        )
    )

    if result.get(
        "error"
    ):
        return (
            f"SOYUZ SHADOW | "
            f"{commodity} | ERROR"
        )

    soyuz = _dict(
        result.get(
            "soyuz"
        )
    )

    comparison = _dict(
        result.get(
            "comparison"
        )
    )

    direction = _text(
        soyuz.get(
            "direction",
            "WAIT",
        )
    )

    state = _text(
        soyuz.get(
            "state",
            "UNKNOWN",
        )
    )

    authorized = bool(
        soyuz.get(
            "gagarin_authorized",
            False,
        )
    )

    status = _text(
        comparison.get(
            "status",
            "UNKNOWN",
        )
    )

    return (
        f"SOYUZ SHADOW | "
        f"{commodity} | "
        f"{direction} | "
        f"{state} | "
        f"GAGARIN="
        f"{'AUTHORIZED' if authorized else 'BLOCKED'} | "
        f"COMPARE={status}"
    )
