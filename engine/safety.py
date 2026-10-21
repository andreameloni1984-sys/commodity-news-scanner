from math import isfinite

from engine.state import SoyuzState
from soyuz_gagarin.config import GagarinConfig


# ============================================================
# SOYUZ GAGARIN v1.2
# SAFETY ENGINE
# ============================================================
#
# DATA
#   ↓
# REGIME
#   ↓
# STRUCTURE
#   ↓
# SETUP
#   ↓
# TRIGGER
#   ↓
# RISK
#   ↓
# SAFETY
#   ↓
# GAGARIN
#
# SAFETY = ULTIMO CANCELLO OPERATIVO
#
# Questo modulo NON crea segnali.
#
# Questo modulo NON corregge:
# - regime
# - struttura
# - setup
# - trigger
# - risk
#
# Controlla solamente che il segnale prodotto dalla catena
# sia sufficientemente coerente per poter diventare ENTRY.
#
# Se anche UN cancello fallisce:
#
#       SAFETY = BLOCKED
#       FINAL_DECISION = WAIT
#
# Solo se tutti i cancelli passano:
#
#       SAFETY = SAFE
#       FINAL_DECISION = ENTRY
# ============================================================


def _finite_number(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if isfinite(number) else None


def _has_value(value) -> bool:
    """
    Verifica semplice della presenza di un valore.
    """
    return value is not None


def apply_safety(
    state: SoyuzState,
) -> SoyuzState:
    """
    Valuta tutti i principali cancelli di sicurezza
    sullo stato canonico.
    """

    cfg = GagarinConfig()
    blockers = []

    # NaN bypasses ordinary threshold comparisons; fail closed on invalid numerics.
    numeric_fields = ("price", "atr", "entry", "stop", "tp1", "tp2", "tp3", "stop_atr", "rr1", "rr2", "rr3", "probability", "quality", "confidence")
    invalid_numeric_fields = [name for name in numeric_fields if getattr(state, name, None) is not None and _finite_number(getattr(state, name)) is None]
    if invalid_numeric_fields:
        blockers.append("NUMERIC_FIELD_NON_FINITE")
        state.metadata["safety_numeric_diagnostics"] = {"status": "REJECTED_NON_FINITE", "fields": invalid_numeric_fields}
    else:
        state.metadata["safety_numeric_diagnostics"] = {"status": "FINITE_OR_MISSING"}

    # ========================================================
    # 1. DATA
    # ========================================================

    if not state.data_ok:

        blockers.append(
            "DATA_NOT_OK"
        )

    # ========================================================
    # 2. LIVE DATA
    # ========================================================

    if not state.live:

        blockers.append(
            "LIVE_DATA_NOT_FRESH"
        )

    # ========================================================
    # 3. SETUP
    # ========================================================

    if (
        state.setup == "NONE"
        or state.setup_direction
        not in {
            "LONG",
            "SHORT",
        }
    ):

        blockers.append(
            "NO_VALID_SETUP"
        )

    # ========================================================
    # 4. TRIGGER
    # ========================================================

    if not state.trigger_confirmed:

        blockers.append(
            "TRIGGER_NOT_CONFIRMED"
        )

    # ========================================================
    # 5. TRIGGER / SETUP ALIGNMENT
    # ========================================================

    if (
        state.setup_direction
        not in {
            "LONG",
            "SHORT",
        }
    ):

        blockers.append(
            "INVALID_SETUP_DIRECTION"
        )

    elif (
        state.trigger_direction
        != state.setup_direction
    ):

        blockers.append(
            "TRIGGER_DIRECTION_MISMATCH"
        )

    # ========================================================
    # 6. STRUCTURE ALIGNMENT
    # ========================================================

    # Trend continuation needs directional structure. Range/reversal
    # opportunities rely on their own setup evidence plus MTF direction.
    if state.opportunity_type == "TREND_CONTINUATION":
        if state.setup_direction == "LONG" and state.structure_direction != "LONG":
            blockers.append("STRUCTURE_NOT_LONG")
        elif state.setup_direction == "SHORT" and state.structure_direction != "SHORT":
            blockers.append("STRUCTURE_NOT_SHORT")

    # ========================================================
    # 7. MTF ALIGNMENT
    # ========================================================
    #
    # Il setup deve essere coerente con la direzione MTF.
    #
    # ========================================================

    if state.opportunity_type == "TREND_CONTINUATION" and state.setup_direction in {"LONG", "SHORT"}:
        if state.mtf_direction != state.setup_direction:
            blockers.append("MTF_DIRECTION_MISMATCH")

    # ========================================================
    # 8. ENTRY
    # ========================================================

    if not _has_value(
        state.entry
    ):

        blockers.append(
            "ENTRY_MISSING"
        )

    # ========================================================
    # 9. STOP
    # ========================================================

    if not _has_value(
        state.stop
    ):

        blockers.append(
            "STOP_MISSING"
        )

    # ========================================================
    # 10. TARGETS
    # ========================================================

    if not _has_value(
        state.tp1
    ):

        blockers.append(
            "TP1_MISSING"
        )

    if not _has_value(
        state.tp2
    ):

        blockers.append(
            "TP2_MISSING"
        )

    if not _has_value(
        state.tp3
    ):

        blockers.append(
            "TP3_MISSING"
        )

    # ========================================================
    # 11. STOP / ATR
    # ========================================================

    if not _has_value(
        state.stop_atr
    ):

        blockers.append(
            "STOP_ATR_MISSING"
        )

    elif state.stop_atr <= 0:

        blockers.append(
            "STOP_ATR_INVALID"
        )

    elif (
        state.stop_atr
        > cfg.max_stop_atr
    ):

        blockers.append(
            "STOP_GT_MAX_ATR"
        )

    # ========================================================
    # 11b. MINIMUM STOP / ATR
    # ========================================================

    elif state.stop_atr < cfg.sl_min_atr:

        blockers.append(
            "STOP_LT_MIN_ATR"
        )

    # ========================================================
    # 12. LONG RISK GEOMETRY
    # ========================================================

    if (
        state.setup_direction
        == "LONG"
        and state.entry is not None
        and state.stop is not None
    ):

        if state.stop >= state.entry:

            blockers.append(
                "LONG_STOP_INVALID"
            )

    # ========================================================
    # 13. SHORT RISK GEOMETRY
    # ========================================================

    if (
        state.setup_direction
        == "SHORT"
        and state.entry is not None
        and state.stop is not None
    ):

        if state.stop <= state.entry:

            blockers.append(
                "SHORT_STOP_INVALID"
            )

    # ========================================================
    # 14. LONG TARGET GEOMETRY
    # ========================================================

    if (
        state.setup_direction
        == "LONG"
        and state.entry is not None
    ):

        if (
            state.tp1 is not None
            and state.tp1 <= state.entry
        ):

            blockers.append(
                "LONG_TP1_INVALID"
            )

        if (
            state.tp2 is not None
            and state.tp2 <= state.entry
        ):

            blockers.append(
                "LONG_TP2_INVALID"
            )

        if (
            state.tp3 is not None
            and state.tp3 <= state.entry
        ):

            blockers.append(
                "LONG_TP3_INVALID"
            )

    # ========================================================
    # 15. SHORT TARGET GEOMETRY
    # ========================================================

    if (
        state.setup_direction
        == "SHORT"
        and state.entry is not None
    ):

        if (
            state.tp1 is not None
            and state.tp1 >= state.entry
        ):

            blockers.append(
                "SHORT_TP1_INVALID"
            )

        if (
            state.tp2 is not None
            and state.tp2 >= state.entry
        ):

            blockers.append(
                "SHORT_TP2_INVALID"
            )

        if (
            state.tp3 is not None
            and state.tp3 >= state.entry
        ):

            blockers.append(
                "SHORT_TP3_INVALID"
            )

    # ========================================================
    # 16. RISK / REWARD
    # ========================================================

    if (
        state.rr1 is None
        or state.rr2 is None
        or state.rr3 is None
    ):

        blockers.append(
            "RR_MISSING"
        )

    else:

        if all(_finite_number(getattr(state, name)) is not None for name in ("entry", "stop", "tp1", "tp2", "tp3")):
            entry = _finite_number(state.entry)
            stop = _finite_number(state.stop)
            targets = tuple(_finite_number(getattr(state, name)) for name in ("tp1", "tp2", "tp3"))
            risk = entry - stop if state.setup_direction == "LONG" else stop - entry
            if risk <= 0:
                blockers.append("RR_PRICE_GEOMETRY_INVALID")
            else:
                rewards = tuple(target - entry if state.setup_direction == "LONG" else entry - target for target in targets)
                actual_rr = tuple(reward / risk for reward in rewards)
                if not all(isfinite(value) for value in (*rewards, *actual_rr)):
                    blockers.append("RR_CALCULATION_NON_FINITE")
                else:
                    declared_rr = tuple(_finite_number(getattr(state, name)) for name in ("rr1", "rr2", "rr3"))
                    if any(value is None or abs(value - actual) > max(0.01, abs(actual) * 0.01) for value, actual in zip(declared_rr, actual_rr)):
                        blockers.append("RR_GEOMETRY_MISMATCH")
                    if actual_rr[0] < 1.5:
                        blockers.append("RR1_FAIL")
                    if actual_rr[1] < 2.0:
                        blockers.append("RR2_FAIL")
                    if actual_rr[2] < cfg.min_rr:
                        blockers.append("RR_FAIL")
        else:
            blockers.append("RR_PRICE_GEOMETRY_INVALID")

    # ========================================================
    # 17. PROBABILITY
    # ========================================================

    if (
        state.probability
        < cfg.min_probability
    ):

        blockers.append(
            "PROBABILITY_FAIL"
        )

    # ========================================================
    # 18. QUALITY
    # ========================================================

    if (
        state.quality
        < cfg.min_quality
    ):

        blockers.append(
            "QUALITY_FAIL"
        )

    # ========================================================
    # 19. CONFIDENCE
    # ========================================================

    if (
        state.confidence
        < cfg.min_confidence
    ):

        blockers.append(
            "CONFIDENCE_FAIL"
        )

    # ========================================================
    # 20. FINAL CONFLUENCE
    # ========================================================
    #
    # Questo è il controllo finale della catena.
    #
    # ENTRY richiede:
    #
    # DATA
    # + LIVE
    # + SETUP
    # + TRIGGER
    # + STRUCTURE
    # + MTF
    # + RISK
    # + PROBABILITY
    # + QUALITY
    # + CONFIDENCE
    #
    # ========================================================

    if (
        state.data_ok
        and state.live
        and state.setup_direction
        in {
            "LONG",
            "SHORT",
        }
        and state.trigger_confirmed
        and (state.opportunity_type != "TREND_CONTINUATION" or state.structure_direction == state.setup_direction)
        and state.mtf_direction
        == state.setup_direction
        and state.entry is not None
        and state.stop is not None
        and state.tp1 is not None
        and state.tp2 is not None
        and state.tp3 is not None
        and state.stop_atr is not None
        and state.rr3 is not None
        and state.probability
        >= cfg.min_probability
        and state.quality
        >= cfg.min_quality
        and state.confidence
        >= cfg.min_confidence
    ):

        pass

    else:

        blockers.append(
            "FINAL_CONFLUENCE_FAIL"
        )

    # ========================================================
    # NORMALIZZAZIONE BLOCKERS
    # ========================================================

    state.blockers = list(
        dict.fromkeys(
            blockers
        )
    )

    # ========================================================
    # SAFETY DECISION
    # ========================================================

    if state.blockers:

        state.safety = "BLOCKED"

        state.final_decision = "WAIT"

    else:

        state.safety = "SAFE"

        state.final_decision = "ENTRY"

    return state