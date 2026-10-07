from .config import GagarinConfig
from .execution_economics import (
    executable_price,
    rr_from_prices,
    spread,
    spread_bps,
)
from .models import Candidate, Decision, MarketSnapshot
from .risk_governor import approve


class GagarinEngine:
    def __init__(self, config: GagarinConfig | None = None):
        self.config = config or GagarinConfig()

    def evaluate(
        self,
        market: MarketSnapshot,
        candidate: Candidate | None,
    ) -> Decision:
        if market.symbol not in self.config.allowed_assets:
            return Decision("WAIT", market.symbol, "ASSET_NOT_IN_UNIVERSE")

        if market.price <= 0:
            return Decision("WAIT", market.symbol, "INVALID_PRICE")

        if candidate is None:
            return Decision("WAIT", market.symbol, "NO_CANDIDATE")

        ok, reason = approve(candidate, self.config)

        diagnostics = {
            "legacy_reasons": candidate.reasons[:8],
            "trigger_confirmed": candidate.trigger_confirmed,
            "structure_direction": candidate.structure_direction,
            "mtf_direction": candidate.mtf_direction,
            "rr3": candidate.rr3,
            "stop_distance_atr": candidate.stop_distance_atr,
        }

        # Execution economics are diagnostic evidence only. They never create
        # an ENTRY and never replace the intraday trigger. Missing quotes remain
        # None rather than being estimated from price or spread defaults.
        if market.bid is not None or market.ask is not None:
            diagnostics["bid"] = market.bid
            diagnostics["ask"] = market.ask
            diagnostics["spread"] = spread(market.bid, market.ask)
            diagnostics["spread_bps"] = spread_bps(market.bid, market.ask)
            diagnostics["executable_price"] = executable_price(
                candidate.side, market.bid, market.ask
            )

        diagnostics["rr3_from_prices"] = rr_from_prices(
            candidate.side,
            candidate.entry,
            candidate.stop,
            candidate.tp3,
        )

        return Decision(
            "PAPER_SIGNAL" if ok else "WAIT",
            market.symbol,
            reason,
            candidate,
            diagnostics,
        )
