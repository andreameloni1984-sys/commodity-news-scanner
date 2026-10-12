"""Paper-trading profiles for Soyuz Gagarin.

These profiles parameterize signal thresholds and publish risk-budget targets.
They do not place orders or bypass any data, trigger, geometry or safety gate.
The targets require portfolio-level enforcement before they can cap real
paper positions; until then they are configuration, not an execution guarantee.
"""
from dataclasses import dataclass
from typing import Literal


ProfileName = Literal["SOFT", "AGGRESSIVE"]


@dataclass(frozen=True)
class TradingProfile:
    name: ProfileName
    min_probability: float
    min_quality: float
    min_confidence: float
    min_rr: float
    risk_per_trade_pct: float
    max_total_open_risk_pct: float
    max_daily_loss_pct: float
    max_open_positions: int
    max_stop_atr: float = 2.5
    paper_only: bool = True


PROFILES = {
    "SOFT": TradingProfile(
        name="SOFT",
        min_probability=68.0,
        min_quality=60.0,
        min_confidence=65.0,
        min_rr=2.5,
        risk_per_trade_pct=0.35,
        max_total_open_risk_pct=0.75,
        max_daily_loss_pct=1.0,
        max_open_positions=2,
    ),
    "AGGRESSIVE": TradingProfile(
        name="AGGRESSIVE",
        min_probability=55.0,
        min_quality=45.0,
        min_confidence=50.0,
        # Keep the existing staged-target governor: TP1>=1.5R, TP2>=2R, TP3>=2.5R.
        min_rr=2.5,
        risk_per_trade_pct=0.75,
        max_total_open_risk_pct=2.0,
        max_daily_loss_pct=2.5,
        max_open_positions=3,
    ),
}


def get_profile(name: str = "SOFT") -> TradingProfile:
    """Return a known profile; invalid names fail safely to SOFT."""
    key = str(name or "SOFT").strip().upper()
    return PROFILES.get(key, PROFILES["SOFT"])


def risk_budget(equity: float, name: str = "SOFT") -> dict:
    """Return target paper risk budgets in account currency for positive equity."""
    profile = get_profile(name)
    equity = float(equity)
    if equity <= 0:
        raise ValueError("equity must be positive")
    return {
        "profile": profile.name,
        "paper_only": True,
        "risk_per_trade": round(equity * profile.risk_per_trade_pct / 100.0, 2),
        "max_total_open_risk": round(equity * profile.max_total_open_risk_pct / 100.0, 2),
        "max_daily_loss": round(equity * profile.max_daily_loss_pct / 100.0, 2),
        "max_open_positions": profile.max_open_positions,
    }
