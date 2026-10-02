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

@dataclass
class Decision:
    action: str
    symbol: str
    reason: str
    candidate: Optional[Candidate] = None
    diagnostics: Dict[str, object] = field(default_factory=dict)
