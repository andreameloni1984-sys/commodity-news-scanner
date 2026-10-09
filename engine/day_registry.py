"""Registro paper del day trading.

Separato dal portafoglio commodity. Capitale proprio, rischio 1%,
tetto 25% per posizione, una sola posizione per simbolo.

Quando il filtro day dice ENTER, apre la posizione con entrata,
stop e uscita scritti. Quando il prezzo tocca lo stop o torna sul
VWAP, la chiude e calcola il P/L. Se il prezzo non e' ancora
arrivato, resta aperta e il P/L non realizzato si aggiorna.

Nessun ordine. Nessuna esecuzione.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

OUT = Path("data/day_registry.json")

INITIAL_CAPITAL = 100.0
RISK_PER_TRADE = 0.01
MAX_POSITION_PCT = 0.25


def _num(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load() -> dict:
    if OUT.exists():
        return json.loads(OUT.read_text(encoding="utf-8"))
    return {
        "paper_only": True,
        "send_order": False,
        "capital": INITIAL_CAPITAL,
        "risk_per_trade": RISK_PER_TRADE,
        "max_position_pct": MAX_POSITION_PCT,
        "positions": [],
        "closed": [],
        "updated_at": _now(),
    }


def save(registry: dict) -> dict:
    registry["updated_at"] = _now()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
    return registry


def open_position(registry: dict, decision: dict) -> dict:
    """Apre una posizione paper da una decisione ENTER del filtro day."""
    if decision.get("action") != "ENTER":
        return registry
    symbol = decision["symbol"]
    if any(p["symbol"] == symbol and p["status"] == "OPEN" for p in registry["positions"]):
        return registry
    price = _num(decision.get("entry"))
    stop = _num(decision.get("stop"))
    if None in (price, stop) or price == stop:
        return registry
    risk = abs(price - stop)
    if risk <= 0:
        return registry
    cash = registry["capital"]
    qty = (cash * RISK_PER_TRADE) / risk
    max_qty = (cash * MAX_POSITION_PCT) / price
    qty = min(qty, max_qty)
    if qty <= 0:
        return registry
    side = decision.get("side", "LONG")
    position = {
        "id": f"DAY-{symbol}-{len(registry['positions']) + 1}",
        "symbol": symbol,
        "name": decision.get("name", symbol),
        "side": side,
        "status": "OPEN",
        "entry": price,
        "stop": stop,
        "exit_rule": decision.get("exit"),
        "exit_price": decision.get("exit_price"),
        "qty": round(qty, 4),
        "opened_at": _now(),
        "reason": decision.get("reason", ""),
    }
    registry["positions"].append(position)
    return save(registry)


def update_open(registry: dict, symbol: str, price: float) -> dict:
    """Aggiorna il P/L non realizzato delle posizioni aperte."""
    price = _num(price)
    if price is None:
        return registry
    changed = False
    for position in registry["positions"]:
        if position["symbol"] == symbol and position["status"] == "OPEN":
            entry = position["entry"]
            qty = position["qty"]
            if position["side"] == "LONG":
                position["unrealized_pnl"] = round((price - entry) * qty, 2)
            else:
                position["unrealized_pnl"] = round((entry - price) * qty, 2)
            position["last_price"] = price
            changed = True
    if changed:
        return save(registry)
    return registry


def close_position(registry: dict, symbol: str, price: float, reason: str) -> dict:
    """Chiude una posizione: stop toccato o ritorno sul VWAP."""
    price = _num(price)
    if price is None:
        return registry
    for position in registry["positions"]:
        if position["symbol"] == symbol and position["status"] == "OPEN":
            entry = position["entry"]
            qty = position["qty"]
            if position["side"] == "LONG":
                pnl = round((price - entry) * qty, 2)
            else:
                pnl = round((entry - price) * qty, 2)
            position["status"] = "CLOSED"
            position["exit_price"] = price
            position["realized_pnl"] = pnl
            position["closed_at"] = _now()
            position["close_reason"] = reason
            registry["closed"].append(position)
            registry["capital"] = round(registry["capital"] + pnl, 2)
            registry["positions"] = [p for p in registry["positions"] if p["id"] != position["id"]]
            return save(registry)
    return registry


def check_exits(registry: dict, symbol: str, price: float) -> dict:
    """Controlla stop e uscita VWAP per le posizioni aperte."""
    price = _num(price)
    if price is None:
        return registry
    for position in list(registry["positions"]):
        if position["symbol"] != symbol or position["status"] != "OPEN":
            continue
        stop = position["stop"]
        if position["side"] == "LONG" and price <= stop:
            return close_position(registry, symbol, price, "stop toccato")
        if position["side"] == "SHORT" and price >= stop:
            return close_position(registry, symbol, price, "stop toccato")
        exit_price = position.get("exit_price")
        if exit_price is not None:
            if position["side"] == "LONG" and price <= exit_price:
                return close_position(registry, symbol, price, "ritorno sotto VWAP")
            if position["side"] == "SHORT" and price >= exit_price:
                return close_position(registry, symbol, price, "ritorno sopra VWAP")
    return update_open(registry, symbol, price)


def summary(registry: dict) -> dict:
    open_positions = [p for p in registry["positions"] if p["status"] == "OPEN"]
    unrealized = sum(p.get("unrealized_pnl", 0) for p in open_positions)
    realized = sum(p.get("realized_pnl", 0) for p in registry["closed"])
    return {
        "paper_only": True,
        "send_order": False,
        "capital": registry["capital"],
        "open_count": len(open_positions),
        "closed_count": len(registry["closed"]),
        "unrealized_pnl": round(unrealized, 2),
        "realized_pnl": round(realized, 2),
        "equity": round(registry["capital"] + unrealized, 2),
        "positions": open_positions,
    }


def run(config: dict | None = None) -> dict:
    """Aggiorna il registro con i prezzi del config, se presenti."""
    registry = load()
    if config:
        for symbol, snap in config.get("instruments", {}).items():
            price = _num(snap.get("price"))
            if price is not None:
                registry = check_exits(registry, symbol, price)
    return save(registry)
