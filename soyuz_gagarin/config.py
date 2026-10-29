"""Single source of truth for Gagarin operational thresholds."""
import os
from math import isfinite
from dataclasses import dataclass, field
from typing import Optional, Tuple

from .trading_profiles import get_profile


def _env_float(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except (TypeError, ValueError, OverflowError):
        return float(default)
    return value if isfinite(value) else float(default)


def _bounded_env_float(
    name: str,
    default: float,
    minimum: float,
    maximum: float | None = None,
) -> float:
    """Accept an environment override only when it stays inside safe bounds."""
    value = _env_float(name, default)
    if value < minimum or (maximum is not None and value > maximum):
        return float(default)
    return value


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError, OverflowError):
        return int(default)


def _active_profile():
    return get_profile(os.getenv("GAGARIN_TRADING_PROFILE", "SOFT"))


def _resolve_profile(profile_name: Optional[str]):
    if profile_name is None:
        return _active_profile()
    return get_profile(profile_name)


@dataclass
class GagarinConfig:
    """Profile-adjustable signal thresholds; execution remains PAPER ONLY.

    Set GAGARIN_TRADING_PROFILE=SOFT or AGGRESSIVE. Profile selection never
    disables data freshness, trigger, geometry, operational or safety gates.
    Explicit MIN_ENTRY_* environment overrides still take precedence.
    """

    paper_only: bool = True
    profile_name: str = field(default_factory=lambda: _active_profile().name)
    timeframes: Tuple[str, ...] = ("4H", "1H", "15M", "5M")
    min_probability: float = field(default=68.0)
    min_quality: float = field(default=60.0)
    min_confidence: float = field(default=65.0)
    min_rr: float = field(default=2.5)
    max_stop_atr: float = field(default=2.5)
    sl_min_atr: float = field(default=0.80)
    sl_structure_buffer_atr: float = field(default=0.15)
    falsification_min_trades: int = field(default=30)
    allowed_assets: Tuple[str, ...] = (
        # Universo trimmed a 10 core: metalli, energia, agri + 2 forex.
        "XAU/USD", "XAG/USD", "COPPER/USD", "WTI/USD", "BRENT/USD",
        "WHEAT/USD", "CORN/USD", "SOYBEAN/USD",
        "EUR/USD", "GBP/USD",
    )
    blocked_if_stale_seconds: int = field(default=900)
    modules: Tuple[str, ...] = field(default=(
        "DATA", "CONTRACT", "LIQUIDITY", "VOLATILITY", "REGIME", "SESSION", "CURVE",
        "STRUCTURE", "SETUP", "TRIGGER", "EXECUTION", "RISK_GOVERNOR", "SAFETY",
        "SIGNAL_FALSIFICATION", "PAPER_TEST"
    ))

    def __post_init__(self):
        profile = _resolve_profile(self.profile_name)
        self.profile_name = profile.name
        self.min_probability = (
            _bounded_env_float("MIN_ENTRY_PROBABILITY", profile.min_probability, 0.0, 100.0)
            if "MIN_ENTRY_PROBABILITY" in os.environ else profile.min_probability
        )
        self.min_quality = (
            _bounded_env_float("MIN_ENTRY_QUALITY", profile.min_quality, 0.0, 100.0)
            if "MIN_ENTRY_QUALITY" in os.environ else profile.min_quality
        )
        self.min_confidence = (
            _bounded_env_float("MIN_ENTRY_CONFIDENCE", profile.min_confidence, 0.0, 100.0)
            if "MIN_ENTRY_CONFIDENCE" in os.environ else profile.min_confidence
        )
        self.min_rr = (
            _bounded_env_float("MIN_ENTRY_RR", profile.min_rr, 0.000001)
            if "MIN_ENTRY_RR" in os.environ else profile.min_rr
        )
        self.max_stop_atr = (
            _bounded_env_float("MAX_ENTRY_STOP_ATR", profile.max_stop_atr, self.sl_min_atr)
            if "MAX_ENTRY_STOP_ATR" in os.environ else profile.max_stop_atr
        )


if __name__ == "__main__":
    soft = GagarinConfig()
    print("SOFT", soft.profile_name, soft.min_probability, soft.min_quality, soft.min_confidence, soft.min_rr)
    agg = GagarinConfig(profile_name="AGGRESSIVE")
    print("AGG", agg.profile_name, agg.min_probability, agg.min_quality, agg.min_confidence, agg.min_rr)
    os.environ["MIN_ENTRY_PROBABILITY"] = "62"
    print("OVERRIDE", GagarinConfig(profile_name="AGGRESSIVE").min_probability)
