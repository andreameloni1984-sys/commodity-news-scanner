from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any
import threading

INITIAL_CAPITAL = 100.0
PAPER_ENTRY_ACTIONS = {"PAPER_ENTRY", "PAPER_SIGNAL"}


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


class PaperPortfolio:
    """Deterministic paper portfolio for Gagarin signals.

    Cash is reserved when a position opens. Equity includes the
    marked value of open allocations plus unrealized P/L.
    """

    def __init__(self, capital: float = INITIAL_CAPITAL):
        self.initial_capital = capital
        self.cash = capital
        self.positions: list[Position] = []
        self.history: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    @staticmethod
    def _move(direction: str, entry: float, price: float) -> float:
        move = (price - entry) / entry
        return -move if direction == "SHORT" else move

    def mark_to_market(self, prices: dict[str, float]) -> None:
        with self._lock:
            for p in self.positions:
                if p.status != "OPEN" or p.symbol not in prices:
                    continue
                price = float(prices[p.symbol])
                p.mark_price = price
                p.unrealized_pnl = round(p.allocation * self._move(p.direction, p.entry, price), 2)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            open_positions = [asdict(p) for p in self.positions if p.status == "OPEN"]
            closed = [asdict(p) for p in self.positions if p.status == "CLOSED"]
            realized = sum(p.pnl for p in self.positions if p.status == "CLOSED")
            unrealized = sum(p.unrealized_pnl for p in self.positions if p.status == "OPEN")
            open_allocations = sum(p.allocation for p in self.positions if p.status == "OPEN")
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

    def open_signal(self, row: dict[str, Any], allocation_pct: float = 0.25) -> dict[str, Any] | None:
        if str(row.get("action") or "").upper() not in PAPER_ENTRY_ACTIONS:
            return None
        entry = row.get("entry")
        if not entry or entry <= 0:
            return None
        symbol = str(row.get("symbol") or "").upper()
        with self._lock:
            if any(p.status == "OPEN" and p.symbol == symbol for p in self.positions):
                return None
            allocation = min(self.cash, max(0.0, self.cash * allocation_pct))
            if allocation <= 0:
                return None
            now = datetime.now(timezone.utc).isoformat()
            position = Position(
                id=f"P{len(self.positions)+1:04d}",
                symbol=symbol,
                commodity=str(row.get("commodity") or symbol),
                direction=str(row.get("direction") or ""),
                entry=float(entry),
                stop=row.get("stop"),
                tp1=row.get("tp1"),
                tp2=row.get("tp2"),
                tp3=row.get("tp3"),
                allocation=round(allocation, 2),
                opened_at=now,
            )
            self.cash = round(self.cash - allocation, 2)
            self.positions.append(position)
            return asdict(position)

    def evaluate_exits(self, prices: dict[str, float]) -> list[dict[str, Any]]:
        closed = []
        with self._lock:
            for p in self.positions:
                if p.status != "OPEN" or p.symbol not in prices:
                    continue
                price = float(prices[p.symbol])
                p.mark_price = price
                stop_hit = p.stop is not None and (
                    (p.direction == "LONG" and price <= p.stop)
                    or (p.direction == "SHORT" and price >= p.stop)
                )
                tp_hit = p.tp3 if p.tp3 is not None else (p.tp2 if p.tp2 is not None else p.tp1)
                tp_hit = tp_hit is not None and (
                    (p.direction == "LONG" and price >= tp_hit)
                    or (p.direction == "SHORT" and price <= tp_hit)
                )
                if not (stop_hit or tp_hit):
                    p.unrealized_pnl = round(p.allocation * self._move(p.direction, p.entry, price), 2)
                    continue
                exit_price = float(p.stop if stop_hit else tp_hit)
                p.pnl = round(p.allocation * self._move(p.direction, p.entry, exit_price), 2)
                p.unrealized_pnl = 0.0
                p.exit = exit_price
                p.status = "CLOSED"
                p.closed_at = datetime.now(timezone.utc).isoformat()
                self.cash = round(self.cash + p.allocation + p.pnl, 2)
                self.history.append(asdict(p))
                closed.append(asdict(p))
        return closed
