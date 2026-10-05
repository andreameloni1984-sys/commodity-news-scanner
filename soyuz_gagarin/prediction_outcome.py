"""SOYUZ GAGARIN — deterministic PAPER prediction outcome evaluator.

This module does not generate signals and never places orders. It evaluates an
already-recorded paper prediction against supplied OHLC bars.

Rules:
- Entry must be touched before an outcome can be counted.
- After entry, the first touched risk/target level determines the outcome.
- If SL and a TP are both inside the same OHLC bar, the result is AMBIGUOUS
  because the intrabar path is unknown.
- R is calculated from the prediction's actual entry/stop geometry.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Optional


@dataclass(frozen=True)
class PredictionOutcome:
    status: str
    entry_hit: bool
    outcome: str
    target_reached: Optional[str]
    r_multiple: Optional[float]
    bars_evaluated: int


def _touches(bar: Mapping[str, float], level: float) -> bool:
    return float(bar["low"]) <= level <= float(bar["high"])


def evaluate_prediction(
    prediction: Mapping[str, object],
    bars: Iterable[Mapping[str, float]],
) -> PredictionOutcome:
    """Evaluate one prediction against chronologically ordered OHLC bars."""

    direction = str(prediction["direction"]).upper()
    if direction not in {"LONG", "SHORT"}:
        raise ValueError("direction must be LONG or SHORT")

    entry = float(prediction["entry"])
    stop = float(prediction["stop"])
    targets = [
        ("TP1", float(prediction["tp1"])),
        ("TP2", float(prediction["tp2"])),
        ("TP3", float(prediction["tp3"])),
    ]

    if direction == "LONG":
        if not (stop < entry < targets[0][1] <= targets[1][1] <= targets[2][1]):
            raise ValueError("invalid LONG geometry")
    else:
        if not (targets[2][1] <= targets[1][1] <= targets[0][1] < entry < stop):
            raise ValueError("invalid SHORT geometry")

    risk = abs(entry - stop)
    entry_hit = False
    bars_evaluated = 0

    for bar in bars:
        bars_evaluated += 1
        high = float(bar["high"])
        low = float(bar["low"])

        if not entry_hit:
            if low <= entry <= high:
                entry_hit = True
            else:
                continue

        stop_hit = _touches(bar, stop)
        touched_targets = [
            (name, level) for name, level in targets if _touches(bar, level)
        ]

        if stop_hit and touched_targets:
            return PredictionOutcome(
                "MATURED", True, "AMBIGUOUS", None, None, bars_evaluated
            )

        if stop_hit:
            return PredictionOutcome(
                "MATURED", True, "SL", None, -1.0, bars_evaluated
            )

        if touched_targets:
            highest_name, highest_level = touched_targets[-1]
            r_multiple = (
                (highest_level - entry) / risk
                if direction == "LONG"
                else (entry - highest_level) / risk
            )
            return PredictionOutcome(
                "MATURED",
                True,
                highest_name,
                highest_name,
                r_multiple,
                bars_evaluated,
            )

    if not entry_hit:
        return PredictionOutcome(
            "NOT_TRIGGERED", False, "NOT_TRIGGERED", None, None, bars_evaluated
        )

    return PredictionOutcome(
        "OPEN", True, "OPEN", None, None, bars_evaluated
    )
