from dataclasses import dataclass, field
from typing import Tuple

@dataclass(frozen=True)
class GagarinConfig:
    paper_only: bool = True
    timeframes: Tuple[str, ...] = ("4H", "1H", "15M", "5M", "1M")
    min_probability: float = 62.0
    min_quality: float = 55.0
    min_confidence: float = 60.0
    min_rr: float = 2.5
    max_stop_atr: float = 2.5
    sl_min_atr: float = 0.80
    sl_structure_buffer_atr: float = 0.15
    falsification_min_trades: int = 30
    allowed_assets: Tuple[str, ...] = (
        "XAU/USD", "XAG/USD", "XPT/USD", "XPD/USD",
        "WTI/USD", "BRENT/USD", "RICE/USD", "SUGAR/USD",
        "COCOA/USD", "COFFEE/USD",
    )
    blocked_if_stale_seconds: int = 900
    modules: Tuple[str, ...] = field(default=(
        "DATA", "CONTRACT", "LIQUIDITY", "VOLATILITY", "REGIME", "SESSION", "CURVE",
        "STRUCTURE", "SETUP", "TRIGGER", "EXECUTION", "RISK_GOVERNOR", "SAFETY",
        "SIGNAL_FALSIFICATION", "PAPER_TEST"
    ))
