import os
from dataclasses import dataclass, field
from typing import Tuple


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return float(default)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return int(default)


@dataclass(frozen=True)
class GagarinConfig:
    """Single source of truth for Gagarin operational thresholds.

    Environment overrides are deliberately limited to configuration values;
    they never enable live execution. PAPER ONLY remains the invariant.
    """

    paper_only: bool = True
    timeframes: Tuple[str, ...] = ("4H", "1H", "15M", "5M")
    min_probability: float = field(default_factory=lambda: _env_float("MIN_ENTRY_PROBABILITY", 62.0))
    min_quality: float = field(default_factory=lambda: _env_float("MIN_ENTRY_QUALITY", 55.0))
    min_confidence: float = field(default_factory=lambda: _env_float("MIN_ENTRY_CONFIDENCE", 60.0))
    min_rr: float = field(default_factory=lambda: _env_float("MIN_ENTRY_RR", 2.5))
    max_stop_atr: float = field(default_factory=lambda: _env_float("MAX_ENTRY_STOP_ATR", 2.5))
    sl_min_atr: float = field(default_factory=lambda: _env_float("SL_MIN_ATR", 0.80))
    sl_structure_buffer_atr: float = field(default_factory=lambda: _env_float("SL_STRUCTURE_BUFFER_ATR", 0.15))
    falsification_min_trades: int = field(default_factory=lambda: _env_int("FALSIFICATION_MIN_TRADES", 30))
    allowed_assets: Tuple[str, ...] = (
        "XAU/USD", "XAG/USD", "XPT/USD", "XPD/USD",
        "WTI/USD", "BRENT/USD", "RICE/USD", "SUGAR/USD",
        "COCOA/USD", "COFFEE/USD",
    )
    blocked_if_stale_seconds: int = field(default_factory=lambda: _env_int("LIVE_MAX_AGE_SECONDS", 900))
    modules: Tuple[str, ...] = field(default=(
        "DATA", "CONTRACT", "LIQUIDITY", "VOLATILITY", "REGIME", "SESSION", "CURVE",
        "STRUCTURE", "SETUP", "TRIGGER", "EXECUTION", "RISK_GOVERNOR", "SAFETY",
        "SIGNAL_FALSIFICATION", "PAPER_TEST"
    ))
