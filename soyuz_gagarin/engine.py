from .config import GagarinConfig
from .models import Candidate, Decision, MarketSnapshot
from .risk_governor import approve

class GagarinEngine:
    def __init__(self, config: GagarinConfig | None = None):
        self.config = config or GagarinConfig()

    def evaluate(self, market: MarketSnapshot, candidate: Candidate | None) -> Decision:
        if market.symbol not in self.config.allowed_assets:
            return Decision("WAIT", market.symbol, "ASSET_NOT_IN_UNIVERSE")
        if market.price <= 0:
            return Decision("WAIT", market.symbol, "INVALID_PRICE")
        if candidate is None:
            return Decision("WAIT", market.symbol, "NO_VALIDATED_SETUP")
        ok, reason = approve(candidate, self.config.paper_only)
        return Decision("PAPER_SIGNAL" if ok else "WAIT", market.symbol, reason, candidate)
