from .models import Candidate


def approve(candidate: Candidate, paper_only: bool = True) -> tuple[bool, str]:
    if not paper_only:
        return False, "LIVE_EXECUTION_DISABLED_IN_V1"
    if candidate.blocked:
        return False, candidate.block_reason or "BLOCKED"
    if candidate.probability < 62:
        return False, "PROBABILITY_BELOW_THRESHOLD"
    if candidate.quality < 55:
        return False, "QUALITY_BELOW_THRESHOLD"
    if candidate.confidence < 60:
        return False, "CONFIDENCE_BELOW_THRESHOLD"
    if candidate.rr < 2.5:
        return False, "RR_BELOW_THRESHOLD"
    if candidate.stop_distance_atr > 2.5:
        return False, "STOP_TOO_WIDE"
    return True, "APPROVED_FOR_PAPER"
