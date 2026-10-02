from datetime import datetime, timezone
from .engine import GagarinEngine
from .models import Candidate, MarketSnapshot


def demo() -> None:
    market = MarketSnapshot(
        symbol="GOLD",
        timestamp=datetime.now(timezone.utc).isoformat(),
        price=1.0,
        regime="UNKNOWN",
        session="UNKNOWN",
    )
    candidate = Candidate("GOLD", "WAIT", 0, 0, 0, 0, 0)
    decision = GagarinEngine().evaluate(market, candidate)
    print({"architecture": "SOYUZ GAGARIN", "paper_only": True, "decision": decision.action, "reason": decision.reason})

if __name__ == "__main__":
    demo()
