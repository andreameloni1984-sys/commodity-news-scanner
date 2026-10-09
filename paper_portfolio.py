from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any
import threading

INITIAL_CAPITAL = 100.0
PAPER_ENTRY_ACTIONS = {"PAPER_ENTRY", "PAPER_SIGNAL"}
TARGET_FRACTION = 1.0 / 3.0


@dataclass
class Position:
    id: str
    symbol: str
    commodity: str
    direction: str
    entry: float
    stop: float | None
    tp1: float | None
    tp2: float | None
    tp3: float | None
    allocation: float
    opened_at: str
    status: str = "OPEN"
    mark_price: float | None = None
    exit: float | None = None
    pnl: float = 0.0
    unrealized_pnl: float = 0.0
    closed_at: str | None = None
    remaining_fraction: float = 1.0
    tp1_hit: bool = False
    tp2_hit: bool = False
    tp3_hit: bool = False


class PaperPortfolio:
    """Deterministic paper portfolio with staged TP1/TP2/TP3 exits.

    One third of the original notional is closed at each target. If the stop
    is reached, the remaining fraction is closed at the stop. Prices are
    sampled snapshots, not OHLC bars, so intrabar ordering and slippage are
    not simulated.
    """

    def __init__(self, capital: float = INITIAL_CAPITAL):
        self.initial_capital = float(capital)
        self.cash = float(capital)
        self.positions: list[Position] = []
        self.history: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    @staticmethod
    def _move(direction: str, entry: float, price: float) -> float:
        move = (price - entry) / entry
        return -move if direction == "SHORT" else move

    @staticmethod
    def _target_hit(direction: str, price: float, target: float) -> bool:
        return price >= target if direction == "LONG" else price <= target

    def mark_to_market(self, prices: dict[str, float]) -> None:
        with self._lock:
            for p in self.positions:
                if p.status != "OPEN" or p.symbol not in prices:
                    continue
                price = float(prices[p.symbol])
                p.mark_price = price
                p.unrealized_pnl = round(
                    p.allocation * p.remaining_fraction
                    * self._move(p.direction, p.entry, price), 2
                )

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            open_positions = [asdict(p) for p in self.positions if p.status == "OPEN"]
            closed = [asdict(p) for p in self.positions if p.status == "CLOSED"]
            realized = sum(p.pnl for p in self.positions)
            unrealized = sum(p.unrealized_pnl for p in self.positions if p.status == "OPEN")
            open_allocations = sum(
                p.allocation * p.remaining_fraction
                for p in self.positions if p.status == "OPEN"
            )
            return {
                "initial_capital": self.initial_capital,
                "cash": round(self.cash, 2),
                "realized_pnl": round(realized, 2),
                "unrealized_pnl": round(unrealized, 2),
                "open_positions": open_positions,
                "closed_positions": closed,
                "equity": round(self.cash + open_allocations + unrealized, 2),
                "total_pnl": round(realized + unrealized, 2),
            }

    def open_signal(
        self,
        row: dict[str, Any],
        allocation_pct: float | None = None,
        risk_pct: float = 0.01,
        max_allocation_pct: float = 0.25,
    ) -> dict[str, Any] | None:
        if str(row.get("action") or "").upper() not in PAPER_ENTRY_ACTIONS:
            return None
        try:
            entry = float(row.get("entry"))
            stop = float(row.get("stop"))
            tp1, tp2, tp3 = (float(row.get(k)) for k in ("tp1", "tp2", "tp3"))
        except (TypeError, ValueError):
            return None
        if min(entry, stop, tp1, tp2, tp3) <= 0:
            return None

        direction = str(row.get("direction") or "").upper()
        if direction not in {"LONG", "SHORT"}:
            return None
        if direction == "LONG":
            if not stop < entry < tp1 < tp2 < tp3:
                return None
        else:
            if not tp3 < tp2 < tp1 < entry < stop:
                return None

        stop_move = abs(entry - stop) / entry
        if stop_move <= 0 or risk_pct <= 0 or max_allocation_pct <= 0:
            return None
        symbol = str(row.get("symbol") or "").strip().upper()
        if not symbol:
            return None

        with self._lock:
            if any(p.status == "OPEN" and p.symbol == symbol for p in self.positions):
                return None
            try:
                requested_cap = max_allocation_pct if allocation_pct is None else float(allocation_pct)
            except (TypeError, ValueError):
                return None
            cap_pct = min(max_allocation_pct, requested_cap)
            risk_budget = self.cash * float(risk_pct)
            risk_allocation = risk_budget / stop_move
            allocation = min(self.cash, self.cash * cap_pct, risk_allocation)
            if allocation <= 0:
                return None

            now = datetime.now(timezone.utc).isoformat()
            position = Position(
                id=f"P{len(self.positions)+1:04d}",
                symbol=symbol,
                commodity=str(row.get("commodity") or symbol),
                direction=direction,
                entry=entry,
                stop=stop,
                tp1=tp1,
                tp2=tp2,
                tp3=tp3,
                allocation=round(allocation, 2),
                opened_at=now,
            )
            self.cash = round(self.cash - position.allocation, 2)
            self.positions.append(position)
            return asdict(position)

    def _close_fraction(self, p: Position, fraction: float, exit_price: float) -> None:
        fraction = min(p.remaining_fraction, fraction)
        if fraction <= 0:
            return
        notional = p.allocation * fraction
        realized_piece = round(notional * self._move(p.direction, p.entry, exit_price), 2)
        self.cash = round(self.cash + notional + realized_piece, 2)
        p.pnl = round(p.pnl + realized_piece, 2)
        p.remaining_fraction = max(0.0, round(p.remaining_fraction - fraction, 8))
        p.exit = float(exit_price)
        if p.remaining_fraction <= 1e-8:
            p.remaining_fraction = 0.0
            p.status = "CLOSED"
            p.closed_at = datetime.now(timezone.utc).isoformat()
            p.unrealized_pnl = 0.0
            self.history.append(asdict(p))

    def evaluate_exits(self, prices: dict[str, float]) -> list[dict[str, Any]]:
        closed = []
        with self._lock:
            for p in self.positions:
                if p.status != "OPEN" or p.symbol not in prices:
                    continue
                price = float(prices[p.symbol])
                if price <= 0:
                    continue
                p.mark_price = price

                # Conservative priority: if the sampled price is at/beyond
                # the stop, close the remaining position before evaluating TPs.
                stop_hit = (
                    p.stop is not None
                    and ((p.direction == "LONG" and price <= p.stop)
                         or (p.direction == "SHORT" and price >= p.stop))
                )
                if stop_hit:
                    self._close_fraction(p, p.remaining_fraction, float(p.stop))
                else:
                    targets = (
                        ("tp1", "tp1_hit", p.tp1),
                        ("tp2", "tp2_hit", p.tp2),
                        ("tp3", "tp3_hit", p.tp3),
                    )
                    for _, hit_attr, target in targets:
                        if (
                            target is not None
                            and not getattr(p, hit_attr)
                            and self._target_hit(p.direction, price, float(target))
                        ):
                            setattr(p, hit_attr, True)
                            self._close_fraction(p, TARGET_FRACTION, float(target))
                            if p.status == "CLOSED":
                                break

                if p.status == "OPEN":
                    p.unrealized_pnl = round(
                        p.allocation * p.remaining_fraction
                        * self._move(p.direction, p.entry, price), 2
                    )
                else:
                    p.unrealized_pnl = 0.0
                    closed.append(asdict(p))
        return closed
