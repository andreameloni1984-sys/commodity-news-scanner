from .config import GagarinConfig
from .models import Candidate


def approve(
    candidate: Candidate,
    config: GagarinConfig | None = None,
) -> tuple[bool, str]:
    """Final PAPER-only governor.

    This is deliberately independent from the legacy engine's
    final_decision. The legacy engine supplies evidence; Gagarin
    decides whether that evidence is sufficient.
    """

    cfg = config or GagarinConfig()

    if not cfg.paper_only:
        return False, "LIVE_EXECUTION_DISABLED"

    if candidate.blocked:
        return False, candidate.block_reason or "BLOCKED"

    if not candidate.data_ok:
        return False, "DATA_NOT_OK"

    if not candidate.live:
        return False, "LIVE_DATA_NOT_FRESH"

    if candidate.side not in {"LONG", "SHORT"}:
        return False, "NO_VALID_SETUP"

    if not candidate.trigger_confirmed:
        return False, "TRIGGER_NOT_CONFIRMED"

    if candidate.structure_direction != candidate.side:
        return False, "STRUCTURE_DIRECTION_MISMATCH"

    if candidate.mtf_direction != candidate.side:
        return False, "MTF_DIRECTION_MISMATCH"

    if candidate.entry is None:
        return False, "ENTRY_MISSING"

    if candidate.stop is None:
        return False, "STOP_MISSING"

    if candidate.tp1 is None or candidate.tp2 is None or candidate.tp3 is None:
        return False, "TARGETS_MISSING"

    if candidate.stop_distance_atr <= 0:
        return False, "STOP_ATR_INVALID"

    if candidate.stop_distance_atr < cfg.sl_min_atr:
        return False, "STOP_TOO_TIGHT"

    if candidate.stop_distance_atr > cfg.max_stop_atr:
        return False, "STOP_TOO_WIDE"

    if candidate.rr3 <= 0:
        return False, "RR_MISSING"

    if candidate.rr3 < cfg.min_rr:
        return False, "RR_BELOW_THRESHOLD"

    if candidate.probability < cfg.min_probability:
        return False, "PROBABILITY_BELOW_THRESHOLD"

    if candidate.quality < cfg.min_quality:
        return False, "QUALITY_BELOW_THRESHOLD"

    if candidate.confidence < cfg.min_confidence:
        return False, "CONFIDENCE_BELOW_THRESHOLD"

    return True, "APPROVED_FOR_PAPER"
