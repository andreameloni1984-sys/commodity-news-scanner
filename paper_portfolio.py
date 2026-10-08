from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any
import threading

INITIAL_CAPITAL = 100.0
DEFAULT_RISK_PCT = 0.01
MAX_ALLOCATION_PCT = 0.25
MAX_OPEN_POSITIONS = 4
MAX_DAILY_LOSS_PCT = 0.05


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
    initial_allocation: float = 0.0
    tp_hits: list[str] = field(default_factory=list)
    exit_reason: str | None = None


class PaperPortfolio:
    """Deterministic paper portfolio for Gagarin signals.

    Cash is reserved when a position opens. Equity includes the
    marked value of open allocations plus unrealized P/L.
    Size is risk-based: 1% of equity to the stop, capped at 25%.
    Take-profits scale out (50/30/20) at the level actually touched.
    """

    def __init__(self, capital: float = INITIAL_CAPITAL):
        self.initial_capital = capital
        self.cash = capital
        self.positions: list[Position] = []
        self.history: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    @staticmethod
    def _move(direction: str, entry: float, price: float) -> float:
        if entry <= 0:
            return 0.0
        move = (price - entry) / entry
        return -move if direction == "SHORT" else move

    def _equity_unlocked(self) -> float:
        unrealized = sum(p.unrealized_pnl for p in self.positions if p.status == "OPEN")
        open_allocations = sum(p.allocation for p in self.positions if p.status == "OPEN")
        return self.cash + open_allocations + unrealized

    def _daily_realized_unlocked(self, day: str) -> float:
        total = 0.0
        for p in self.positions:
            if p.closed_at and p.closed_at[:10] == day:
                total += p.pnl
        return total

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

    def _allocation_for(self, entry: float, stop: float | None, direction: str) -> float:
        equity = max(self._equity_unlocked(), 0.0)
        cap = equity * MAX_ALLOCATION_PCT
        if stop is None or entry <= 0:
            return min(self.cash, round(equity * 0.10, 2))
        distance = abs(entry - float(stop)) / entry
        if distance <= 0:
            return 0.0
        if direction == "LONG" and float(stop) >= entry:
            return 0.0
        if direction == "SHORT" and float(stop) <= entry:
            return 0.0
        risk_cash = equity * DEFAULT_RISK_PCT
        sized = risk_cash / distance
        return round(min(self.cash, cap, sized), 2)

    def open_signal(self, row: dict[str, Any], allocation_pct: float = 0.25) -> dict[str, Any] | None:
        if row.get("action") != "PAPER_SIGNAL":
            return None
        entry = row.get("entry")
        if not entry or entry <= 0:
            return None
        symbol = str(row.get("symbol") or "").upper()
        direction = str(row.get("direction") or "").upper()
        if direction not in {"LONG", "SHORT"}:
            return None
        with self._lock:
            open_count = sum(1 for p in self.positions if p.status == "OPEN")
            if open_count >= MAX_OPEN_POSITIONS:
                return None
            if any(p.status == "OPEN" and p.symbol == symbol for p in self.positions):
                return None
            day = datetime.now(timezone.utc).date().isoformat()
            if self._daily_realized_unlocked(day) <= -self.initial_capital * MAX_DAILY_LOSS_PCT:
                return None
            stop = row.get("stop")
            allocation = self._allocation_for(float(entry), stop, direction)
            if allocation_pct and allocation_pct != 0.25:
                allocation = min(allocation, round(self.cash * allocation_pct, 2))
            if allocation <= 0:
                return None
            now = datetime.now(timezone.utc).isoformat()
            position = Position(
                id=f"P{len(self.positions)+1:04d}",
                symbol=symbol,
                commodity=str(row.get("commodity") or symbol),
                direction=direction,
                entry=float(entry),
                stop=float(stop) if stop is not None else None,
                tp1=row.get("tp1"),
                tp2=row.get("tp2"),
                tp3=row.get("tp3"),
                allocation=allocation,
                initial_allocation=allocation,
                opened_at=now,
            )
            self.cash = round(self.cash - allocation, 2)
            self.positions.append(position)
            return asdict(position)

    def _close_slice(self, p: Position, price: float, fraction: float, reason: str) -> dict[str, Any]:
        fraction = min(1.0, max(0.0, fraction))
        slice_alloc = round(p.allocation * fraction, 2)
        if slice_alloc <= 0 or slice_alloc >= p.allocation:
            slice_alloc = p.allocation
        pnl = round(slice_alloc * self._move(p.direction, p.entry, price), 2)
        p.pnl = round(p.pnl + pnl, 2)
        p.allocation = round(p.allocation - slice_alloc, 2)
        p.exit = price
        p.exit_reason = reason
        self.cash = round(self.cash + slice_alloc + pnl, 2)
        event = {"id": p.id, "symbol": p.symbol, "reason": reason, "exit": price, "pnl": pnl, "allocation_closed": slice_alloc}
        if p.allocation <= 0.01:
            p.allocation = 0.0
            p.unrealized_pnl = 0.0
            p.status = "CLOSED"
            p.closed_at = datetime.now(timezone.utc).isoformat()
            self.history.append(asdict(p))
        else:
            p.unrealized_pnl = round(p.allocation * self._move(p.direction, p.entry, price), 2)
        return event

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
                if stop_hit:
                    closed.append(self._close_slice(p, float(p.stop), 1.0, "STOP"))
                    continue
                levels = [("TP1", p.tp1, 0.50), ("TP2", p.tp2, 0.60), ("TP3", p.tp3, 1.0)]
                progressed = False
                for name, level, fraction in levels:
                    if level is None or name in p.tp_hits or p.status != "OPEN":
                        continue
                    touched = (p.direction == "LONG" and price >= float(level)) or (
                        p.direction == "SHORT" and price <= float(level)
                    )
                    if not touched:
                        break
                    p.tp_hits.append(name)
                    closed.append(self._close_slice(p, float(level), fraction, name))
                    progressed = True
                if not progressed and p.status == "OPEN":
                    p.unrealized_pnl = round(p.allocation * self._move(p.direction, p.entry, price), 2)
        return closed
