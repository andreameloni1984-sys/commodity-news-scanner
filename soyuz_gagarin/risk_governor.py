from math import isclose

from .config import GagarinConfig
from .models import Candidate


def _target_geometry_ok(candidate: Candidate) -> bool:
    """Require every target to be on the profitable side of entry."""
    if candidate.entry is None:
        return False
    if candidate.side == "LONG":
        return (
            candidate.tp1 is not None and candidate.tp1 > candidate.entry
            and candidate.tp2 is not None and candidate.tp2 > candidate.tp1
            and candidate.tp3 is not None and candidate.tp3 > candidate.tp2
        )
    if candidate.side == "SHORT":
        return (
            candidate.tp1 is not None and candidate.tp1 < candidate.entry
            and candidate.tp2 is not None and candidate.tp2 < candidate.tp1
            and candidate.tp3 is not None and candidate.tp3 < candidate.tp2
        )
    return False


def _stop_geometry_ok(candidate: Candidate) -> bool:
    """Require the stop to be on the loss side of entry."""
    if candidate.entry is None or candidate.stop is None:
        return False
    if candidate.side == "LONG":
        return candidate.stop < candidate.entry
    if candidate.side == "SHORT":
        return candidate.stop > candidate.entry
    return False


def _rr_geometry_ok(candidate: Candidate) -> bool:
    """Require declared R/R tiers to match the actual price geometry."""
    if candidate.entry is None or candidate.stop is None:
        return False

    if candidate.side == "LONG":
        risk = candidate.entry - candidate.stop
        rewards = (
            None if candidate.tp1 is None else candidate.tp1 - candidate.entry,
            None if candidate.tp2 is None else candidate.tp2 - candidate.entry,
            None if candidate.tp3 is None else candidate.tp3 - candidate.entry,
        )
    elif candidate.side == "SHORT":
        risk = candidate.stop - candidate.entry
        rewards = (
            None if candidate.tp1 is None else candidate.entry - candidate.tp1,
            None if candidate.tp2 is None else candidate.entry - candidate.tp2,
            None if candidate.tp3 is None else candidate.entry - candidate.tp3,
        )
    else:
        return False

    if risk <= 0 or any(value is None for value in rewards):
        return False

    declared = (candidate.rr1, candidate.rr2, candidate.rr3)
    if any(value is None for value in declared):
        return False

    calculated = tuple(reward / risk for reward in rewards)
    return all(
        isclose(actual, expected, rel_tol=1e-3, abs_tol=1e-6)
        for actual, expected in zip(declared, calculated)
    )


def _rr_tiers_ok(candidate: Candidate) -> bool:
    """Protect the staged exit plan instead of validating only TP3."""
    return (
        candidate.rr1 >= 1.5
        and candidate.rr2 >= 2.0
        and candidate.rr3 >= 2.5
    )


def approve(
    candidate: Candidate,
    config: GagarinConfig | None = None,
) -> tuple[bool, str]:
    """Final PAPER-only governor.

    Gagarin approves a signal only when the complete technical/risk
    evidence is internally consistent. This function never places orders.
    """

    cfg = config or GagarinConfig()

    if not cfg.paper_only:
        return False, "LIVE_EXECUTION_DISABLED"

    if candidate.blocked:
        return False, candidate.block_reason or "BLOCKED"

    operational = (
        ("paper_only", candidate.paper_only, "PAPER_ONLY_REQUIRED"),
        ("data_quality_ok", candidate.data_quality_ok, "DATA_QUALITY_FAIL"),
        ("freshness_ok", candidate.freshness_ok, "FRESHNESS_FAIL"),
        ("contract_ok", candidate.contract_ok, "CONTRACT_FAIL"),
        ("liquidity_ok", candidate.liquidity_ok, "LIQUIDITY_FAIL"),
        ("volatility_ok", candidate.volatility_ok, "VOLATILITY_FAIL"),
        ("regime_ok", candidate.regime_ok, "REGIME_FAIL"),
        ("session_ok", candidate.session_ok, "SESSION_FAIL"),
        ("curve_ok", candidate.curve_ok, "CURVE_FAIL"),
    )
    for _, ok, reason in operational:
        if not ok:
            return False, reason

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

    if not _stop_geometry_ok(candidate):
        return False, "STOP_GEOMETRY_INVALID"

    if not _target_geometry_ok(candidate):
        return False, "TARGET_GEOMETRY_INVALID"

    if not _rr_geometry_ok(candidate):
        return False, "RR_GEOMETRY_MISMATCH"

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

    if not _rr_tiers_ok(candidate):
        return False, "RR_TIER_BELOW_THRESHOLD"

    if candidate.probability < cfg.min_probability:
        return False, "PROBABILITY_BELOW_THRESHOLD"

    if candidate.quality < cfg.min_quality:
        return False, "QUALITY_BELOW_THRESHOLD"

    if candidate.confidence < cfg.min_confidence:
        return False, "CONFIDENCE_BELOW_THRESHOLD"

    return True, "APPROVED_FOR_PAPER"
