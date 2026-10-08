from engine.state import SoyuzState
from engine.weekly_trend import weekly_trend_blocks_entry
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


def _has_value(value) -> bool:
    """
    Verifica semplice della presenza di un valore.
    """
    return value is not None


def _trend_alignment_required(state: SoyuzState) -> bool:
    """Structure and MTF must match only on trend continuation."""
    return state.opportunity_type == "TREND_CONTINUATION"


def apply_safety(
    state: SoyuzState,
) -> SoyuzState:
    """
    Valuta tutti i principali cancelli di sicurezza
    sullo stato canonico.
    """

    cfg = GagarinConfig()
    blockers = []

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
    if _trend_alignment_required(state):
        if state.setup_direction == "LONG" and state.structure_direction != "LONG":
            blockers.append("STRUCTURE_NOT_LONG")
        elif state.setup_direction == "SHORT" and state.structure_direction != "SHORT":
            blockers.append("STRUCTURE_NOT_SHORT")

    # ========================================================
    # 7. MTF ALIGNMENT
    # ========================================================
    #
    # Il setup deve essere coerente con la direzione MTF
    # solo in trend continuation. Range e reversal non
    # vengono bocciati qui se l'MTF non coincide.
    #
    # ========================================================

    if _trend_alignment_required(state) and state.setup_direction in {"LONG", "SHORT"}:
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

        if (
            state.tp1 is not None
            and state.tp2 is not None
            and state.tp3 is not None
            and not (state.entry < state.tp1 < state.tp2 < state.tp3)
        ):
            blockers.append(
                "LONG_TARGET_LADDER_INVALID"
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

        if (
            state.tp1 is not None
            and state.tp2 is not None
            and state.tp3 is not None
            and not (state.entry > state.tp1 > state.tp2 > state.tp3)
        ):
            blockers.append(
                "SHORT_TARGET_LADDER_INVALID"
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

        if state.rr1 < 1.5:
            blockers.append("RR1_FAIL")

        if state.rr2 < 2.0:
            blockers.append("RR2_FAIL")

        if state.rr3 < cfg.min_rr:
            blockers.append("RR_FAIL")

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
    # + STRUCTURE (solo trend continuation)
    # + MTF (solo trend continuation)
    # + RISK
    # + PROBABILITY
    # + QUALITY
    # + CONFIDENCE
    # + WEEKLY TREND (se classificato, deve coincidere)
    #
    # Il controllo MTF deve usare la stessa regola del gate 7.
    # Prima richiedeva sempre mtf_direction == setup_direction,
    # quindi un range/reversal valido veniva marcato
    # FINAL_CONFLUENCE_FAIL anche senza MTF_DIRECTION_MISMATCH.
    #
    # ========================================================

    structure_ok = (
        not _trend_alignment_required(state)
        or state.structure_direction == state.setup_direction
    )
    mtf_ok = (
        not _trend_alignment_required(state)
        or state.mtf_direction == state.setup_direction
    )
    ladder_ok = True
    if state.setup_direction == "LONG" and None not in {state.entry, state.tp1, state.tp2, state.tp3}:
        ladder_ok = state.entry < state.tp1 < state.tp2 < state.tp3
    elif state.setup_direction == "SHORT" and None not in {state.entry, state.tp1, state.tp2, state.tp3}:
        ladder_ok = state.entry > state.tp1 > state.tp2 > state.tp3

    if (
        state.data_ok
        and state.live
        and state.setup_direction
        in {
            "LONG",
            "SHORT",
        }
        and state.trigger_confirmed
        and structure_ok
        and mtf_ok
        and ladder_ok
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
    # 21. WEEKLY TREND GATE
    # ========================================================
    #
    # Research basis: Kurth, Eisler, Rej, Bouchaud (2026) —
    # trend-following Sharpe survives only on large-tick contracts
    # (many commodities) and only at horizons of weeks, not days.
    # Intraday momentum is dead post-2008.
    #
    # If the weekly trend is classified (LONG/SHORT) and it opposes
    # the setup direction, the entry is blocked. Fail-open when the
    # weekly trend is missing or NONE: a missing weekly trend must
    # not block entries.
    #
    # This gate runs AFTER the final confluence check so that a
    # weekly mismatch is always visible as its own blocker, even
    # when FINAL_CONFLUENCE_FAIL is already present.
    #
    # ========================================================

    weekly_blocker = weekly_trend_blocks_entry(state)
    if weekly_blocker:
        blockers.append(weekly_blocker)

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
