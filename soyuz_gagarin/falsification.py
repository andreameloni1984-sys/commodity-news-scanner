from dataclasses import dataclass
from typing import Iterable

@dataclass(frozen=True)
class FalsificationStatus:
    status: str
    sample_size: int
    expectancy: float
    max_drawdown: float
    oos_ready: bool


def evaluate(sample_size: int, expectancy: float, max_drawdown: float, oos_ready: bool, min_trades: int = 30) -> FalsificationStatus:
    if sample_size < min_trades:
        return FalsificationStatus("INSUFFICIENT_SAMPLE", sample_size, expectancy, max_drawdown, oos_ready)
    if expectancy <= 0:
        return FalsificationStatus("FAILED", sample_size, expectancy, max_drawdown, oos_ready)
    if not oos_ready:
        return FalsificationStatus("OOS_REQUIRED", sample_size, expectancy, max_drawdown, oos_ready)
    return FalsificationStatus("PASS_CANDIDATE", sample_size, expectancy, max_drawdown, oos_ready)
