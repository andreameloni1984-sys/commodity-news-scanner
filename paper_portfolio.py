from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any
import threading

INITIAL_CAPITAL = 100.0

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
    exit: float | None = None
    pnl: float = 0.0
    closed_at: str | None = None

class PaperPortfolio:
    def __init__(self, capital: float = INITIAL_CAPITAL):
        self.initial_capital = capital
        self.cash = capital
        self.positions: list[Position] = []
        self.history: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            open_positions = [asdict(p) for p in self.positions if p.status == "OPEN"]
            closed = [asdict(p) for p in self.positions if p.status == "CLOSED"]
            realized = sum(p.pnl for p in self.positions if p.status == "CLOSED")
            return {
                "initial_capital": self.initial_capital,
                "cash": round(self.cash, 2),
                "realized_pnl": round(realized, 2),
                "open_positions": open_positions,
                "closed_positions": closed,
                "equity": round(self.cash + sum(p.allocation for p in self.positions if p.status == "OPEN"), 2),
            }

    def open_signal(self, row: dict[str, Any], allocation_pct: float = 0.25) -> dict[str, Any] | None:
        if row.get("action") != "PAPER_SIGNAL":
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
                stop_hit = p.stop is not None and ((p.direction == "LONG" and price <= p.stop) or (p.direction == "SHORT" and price >= p.stop))
                tp_hit = p.tp3 if p.tp3 is not None else (p.tp2 if p.tp2 is not None else p.tp1)
                tp_hit = tp_hit is not None and ((p.direction == "LONG" and price >= tp_hit) or (p.direction == "SHORT" and price <= tp_hit))
                if not (stop_hit or tp_hit):
                    continue
                exit_price = float(p.stop if stop_hit else tp_hit)
                move = (exit_price - p.entry) / p.entry
                if p.direction == "SHORT":
                    move = -move
                p.pnl = round(p.allocation * move, 2)
                p.exit = exit_price
                p.status = "CLOSED"
                p.closed_at = datetime.now(timezone.utc).isoformat()
                self.cash = round(self.cash + p.allocation + p.pnl, 2)
                closed.append(asdict(p))
        return closed
