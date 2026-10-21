from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any
import threading
import math

from engine.order_preflight import validate_paper_signal

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
        self.daily_pnl_date = datetime.now(timezone.utc).date().isoformat()
        self.daily_realized_pnl = 0.0
        self._lock = threading.Lock()

    def _roll_daily_pnl_day(self) -> None:
        today = datetime.now(timezone.utc).date().isoformat()
        if self.daily_pnl_date != today:
            self.daily_pnl_date = today
            self.daily_realized_pnl = 0.0

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

    def export_state(self) -> dict[str, Any]:
        """Return the complete serializable state for durable persistence."""
        with self._lock:
            return {
                "initial_capital": self.initial_capital,
                "cash": self.cash,
                "positions": [asdict(p) for p in self.positions],
                "history": list(self.history),
                "daily_pnl_date": self.daily_pnl_date,
                "daily_realized_pnl": self.daily_realized_pnl,
            }

    def restore_state(self, state: dict[str, Any] | None) -> None:
        """Restore a previously persisted portfolio after a process restart."""
        if not isinstance(state, dict):
            return
        try:
            initial_capital = float(state.get("initial_capital", INITIAL_CAPITAL))
            cash = float(state.get("cash", initial_capital))
            positions = [Position(**item) for item in state.get("positions", [])]
            history = list(state.get("history", []))
            saved_pnl_date = str(state.get("daily_pnl_date", ""))
            saved_daily_pnl = float(state.get("daily_realized_pnl", 0.0))
            if not math.isfinite(saved_daily_pnl):
                return
        except (TypeError, ValueError, KeyError):
            return
        with self._lock:
            self.initial_capital = initial_capital
            self.cash = cash
            self.positions = positions
            self.history = history
            today = datetime.now(timezone.utc).date().isoformat()
            self.daily_pnl_date = saved_pnl_date if saved_pnl_date == today else today
            self.daily_realized_pnl = saved_daily_pnl if saved_pnl_date == today else 0.0

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
            self._roll_daily_pnl_day()
            return {
                "initial_capital": self.initial_capital,
                "cash": round(self.cash, 2),
                "daily_realized_pnl": round(self.daily_realized_pnl, 2),
                "daily_loss_limit": round(self.initial_capital * 0.025, 2),
                "daily_loss_breaker_active": self.daily_realized_pnl <= -self.initial_capital * 0.025,
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
        preflight_ok, _preflight_reason = validate_paper_signal(row)
        if not preflight_ok:
            return None
        try:
            entry = float(row.get("entry"))
            stop = float(row.get("stop"))
            tp1, tp2, tp3 = (float(row.get(k)) for k in ("tp1", "tp2", "tp3"))
        except (TypeError, ValueError):
            return None
        prices = (entry, stop, tp1, tp2, tp3)
        if not all(math.isfinite(value) and value > 0 for value in prices):
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
        if not math.isfinite(stop_move) or stop_move <= 0:
            return None
        if not math.isfinite(risk_pct) or risk_pct <= 0:
            return None
        if not math.isfinite(max_allocation_pct) or max_allocation_pct <= 0:
            return None

        risk_distance = abs(entry - stop)
        rewards = (
            abs(tp1 - entry),
            abs(tp2 - entry),
            abs(tp3 - entry),
        )
        reward_risk = tuple(reward / risk_distance for reward in rewards)
        if reward_risk[0] < 1.5 or reward_risk[1] < 2.0 or reward_risk[2] < 2.5:
            return None
        symbol = str(row.get("symbol") or "").strip().upper()
        if not symbol:
            return None

        with self._lock:
            self._roll_daily_pnl_day()
            if self.daily_realized_pnl <= -self.initial_capital * 0.025:
                return None
            open_positions = [p for p in self.positions if p.status == "OPEN"]
            if len(open_positions) >= 3:
                return None
            if any(p.symbol == symbol for p in open_positions):
                return None
            try:
                requested_cap = max_allocation_pct if allocation_pct is None else float(allocation_pct)
            except (TypeError, ValueError):
                return None
            cap_pct = min(max_allocation_pct, requested_cap)
            risk_budget = self.cash * float(risk_pct)
            risk_allocation = risk_budget / stop_move
            allocation = min(self.cash, self.cash * cap_pct, risk_allocation)
            if not math.isfinite(allocation) or allocation <= 0:
                return None

            current_open_risk = sum(
                p.allocation * p.remaining_fraction * abs(p.entry - p.stop) / p.entry
                for p in open_positions if p.stop is not None and p.entry > 0
            )
            proposed_risk = allocation * stop_move
            if current_open_risk + proposed_risk > self.initial_capital * 0.02 + 1e-9:
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
        self._roll_daily_pnl_day()
        self.daily_realized_pnl = round(self.daily_realized_pnl + realized_piece, 2)
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
