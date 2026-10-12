"""Single source of truth for Gagarin operational thresholds."""
import os
from dataclasses import dataclass, field
from typing import Tuple

from .trading_profiles import get_profile


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


def _active_profile():
    return get_profile(os.getenv("GAGARIN_TRADING_PROFILE", "SOFT"))


@dataclass(frozen=True)
class GagarinConfig:
    """Profile-adjustable signal thresholds; execution remains PAPER ONLY.

    Set GAGARIN_TRADING_PROFILE=SOFT or AGGRESSIVE. Profile selection never
    disables data freshness, trigger, geometry, operational or safety gates.
    Explicit MIN_ENTRY_* environment overrides still take precedence.
    """

    paper_only: bool = True
    profile_name: str = field(default_factory=lambda: _active_profile().name)
    timeframes: Tuple[str, ...] = ("4H", "1H", "15M", "5M")
    min_probability: float = field(default_factory=lambda: _env_float("MIN_ENTRY_PROBABILITY", _active_profile().min_probability))
    min_quality: float = field(default_factory=lambda: _env_float("MIN_ENTRY_QUALITY", _active_profile().min_quality))
    min_confidence: float = field(default_factory=lambda: _env_float("MIN_ENTRY_CONFIDENCE", _active_profile().min_confidence))
    min_rr: float = field(default_factory=lambda: _env_float("MIN_ENTRY_RR", _active_profile().min_rr))
    max_stop_atr: float = field(default_factory=lambda: _env_float("MAX_ENTRY_STOP_ATR", _active_profile().max_stop_atr))
    sl_min_atr: float = field(default_factory=lambda: _env_float("SL_MIN_ATR", 0.80))
    sl_structure_buffer_atr: float = field(default_factory=lambda: _env_float("SL_STRUCTURE_BUFFER_ATR", 0.15))
    falsification_min_trades: int = field(default_factory=lambda: _env_int("FALSIFICATION_MIN_TRADES", 30))
    allowed_assets: Tuple[str, ...] = (
        "XAU/USD", "XAG/USD", "XPT/USD", "XPD/USD",
        "WTI/USD", "BRENT/USD", "RICE/USD", "SUGAR/USD",
        "COCOA/USD", "COFFEE/USD",
        "EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF",
        "AUD/USD", "USD/CAD", "NZD/USD", "EUR/JPY",
    )
    blocked_if_stale_seconds: int = field(default_factory=lambda: _env_int("LIVE_MAX_AGE_SECONDS", 900))
    modules: Tuple[str, ...] = field(default=(
        "DATA", "CONTRACT", "LIQUIDITY", "VOLATILITY", "REGIME", "SESSION", "CURVE",
        "STRUCTURE", "SETUP", "TRIGGER", "EXECUTION", "RISK_GOVERNOR", "SAFETY",
        "SIGNAL_FALSIFICATION", "PAPER_TEST"
    ))
