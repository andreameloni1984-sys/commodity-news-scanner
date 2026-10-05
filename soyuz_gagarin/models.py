from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class MarketSnapshot:
    symbol: str
    timestamp: str
    price: float
    atr: float = 0.0
    volume: float = 0.0
    spread: float = 0.0
    depth: float = 0.0
    realized_vol: float = 0.0
    liquidity_score: float = 0.0
    market_quality_score: float = 0.0
    regime: str = "UNKNOWN"
    session: str = "UNKNOWN"


@dataclass
class Candidate:
    symbol: str
    side: str
    probability: float
    quality: float
    confidence: float
    rr: float
    stop_distance_atr: float
    reasons: List[str] = field(default_factory=list)
    blocked: bool = False
    block_reason: Optional[str] = None

    data_ok: bool = False
    live: bool = False
    trigger_confirmed: bool = False
    structure_direction: str = "NONE"
    mtf_direction: str = "NONE"
    entry: Optional[float] = None
    stop: Optional[float] = None
    tp1: Optional[float] = None
    tp2: Optional[float] = None
    tp3: Optional[float] = None
    rr1: Optional[float] = None
    rr2: Optional[float] = None
    rr3: Optional[float] = None

    # Operational gates. These are explicit evidence fields rather than
    # hidden assumptions. Adapter code may populate them from metadata.
    paper_only: bool = True
    data_quality_ok: bool = False
    freshness_ok: bool = False
    contract_ok: bool = False
    liquidity_ok: bool = False
    volatility_ok: bool = False
    regime_ok: bool = False
    session_ok: bool = False
    curve_ok: bool = False


@dataclass
class Decision:
    action: str
    symbol: str
    reason: str
    candidate: Optional[Candidate] = None
    diagnostics: Dict[str, object] = field(default_factory=dict)
