from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class ExecutionOrder:
    symbol: str
    side: str
    quantity: float
    entry: float
    stop: Optional[float]
    tp1: Optional[float]
    tp2: Optional[float]
    tp3: Optional[float]
    source: str = "GAGARIN"

@dataclass(frozen=True)
class ExecutionResult:
    accepted: bool
    mode: str
    symbol: str
    order_id: str = ""
    message: str = ""
