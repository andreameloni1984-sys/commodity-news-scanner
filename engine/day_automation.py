"""Decisione unica per day trading e commodity. PAPER only.

Stesso cervello: settimana, finestra, range, volume, VWAP, spread, news.
Se i dati ci sono, può dire ENTER anche su una commodity.
Se manca un numero, l'azione è NONE. Non manda ordini.

Aggiunto: lista di condizioni mancanti e flag near quando manca una sola cosa.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

OUT = Path("data/day_automation.json")
CONFIG = Path("data/day_universe.json")

# class: etf, future, fx, commodity
# window: OPENING_RANGE per indici e future, LONDON_NY per forex e metalli spot
UNIVERSE = {
    "SPY": {"class": "etf", "window": "OPENING_RANGE", "max_spread": 0.03},
    "QQQ": {"class": "etf", "window": "OPENING_RANGE", "max_spread": 0.04},
    "ES": {"class": "future", "window": "OPENING_RANGE", "max_spread": 0.5},
    "NQ": {"class": "future", "window": "OPENING_RANGE", "max_spread": 1.0},
    "MES": {"class": "future", "window": "OPENING_RANGE", "max_spread": 0.5},
    "MNQ": {"class": "future", "window": "OPENING_RANGE", "max_spread": 1.0},
    "EURUSD": {"class": "fx", "window": "LONDON_NY", "max_spread": 0.00012},
    "GBPUSD": {"class": "fx", "window": "LONDON_NY", "max_spread": 0.00015},
    "USDJPY": {"class": "fx", "window": "LONDON_NY", "max_spread": 0.012},
    "XAUUSD": {"class": "commodity", "name": "Oro", "window": "LONDON_NY", "max_spread": 0.4},
    "XAGUSD": {"class": "commodity", "name": "Argento", "window": "LONDON_NY", "max_spread": 0.03},
    "XPTUSD": {"class": "commodity", "name": "Platino", "window": "LONDON_NY", "max_spread": 1.5},
    "XPDUSD": {"class": "commodity", "name": "Palladio", "window": "LONDON_NY", "max_spread": 3.0},
    "WTI": {"class": "commodity", "name": "Petrolio WTI", "window": "OPENING_RANGE", "max_spread": 0.04},
    "BRENT": {"class": "commodity", "name": "Petrolio Brent", "window": "OPENING_RANGE", "max_spread": 0.05},
    "RICE": {"class": "commodity", "name": "Riso", "window": "OPENING_RANGE", "max_spread": 0.2},
    "SUGAR": {"class": "commodity", "name": "Zucchero", "window": "OPENING_RANGE", "max_spread": 0.04},
    "COCOA": {"class": "commodity", "name": "Cacao", "window": "OPENING_RANGE", "max_spread": 8.0},
    "COFFEE": {"class": "commodity", "name": "Caffè", "window": "OPENING_RANGE", "max_spread": 0.4},
}


def _num(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


def decide(symbol: str, snapshot: dict | None) -> dict:
    snapshot = snapshot or {}
    spec = UNIVERSE.get(symbol, {})
    base = {
        "symbol": symbol,
        "name": spec.get("name", symbol),
        "class": spec.get("class", "unknown"),
        "action": "NONE",
        "side": None,
        "entry": None,
        "stop": None,
        "exit": None,
        "reason": "",
        "missing": [],
        "near": False,
        "paper_only": True,
        "send_order": False,
    }
    if not spec:
        base["reason"] = "strumento fuori lista"
        base["missing"] = ["strumento"]
        return base

    missing = []
    weekly = str(snapshot.get("weekly_bias", "UNKNOWN")).upper()
    if weekly not in {"LONG", "SHORT"}:
        missing.append("settimana non direzionale")

    window = spec["window"]
    if str(snapshot.get("session", "")).upper() != window:
        missing.append("fuori finestra")

    if str(snapshot.get("news_window", "")).upper() == "ACTIVE":
        missing.append("dato macro in uscita")

    if str(snapshot.get("opening_range", "")).upper() != "BROKEN":
        missing.append("range non rotto")

    if str(snapshot.get("volume", "")).upper() != "ABOVE_AVERAGE":
        missing.append("volume basso")

    price = _num(snapshot.get("price"))
    range_high = _num(snapshot.get("range_high"))
    range_low = _num(snapshot.get("range_low"))
    vwap = _num(snapshot.get("vwap"))
    spread = _num(snapshot.get("spread"))
    max_spread = _num(snapshot.get("max_spread", spec["max_spread"]))

    if None in (price, range_high, range_low, vwap, spread, max_spread):
        missing.append("manca prezzo, range, VWAP o spread")
    else:
        if spread > max_spread:
            missing.append("spread troppo largo")
        if weekly == "LONG" and not (price > range_high and price > vwap):
            missing.append("rottura long non confermata")
        if weekly == "SHORT" and not (price < range_low and price < vwap):
            missing.append("rottura short non confermata")
        risk = abs(price - (range_low if weekly == "LONG" else range_high))
        if risk <= 0:
            missing.append("stop non valido")

    base["missing"] = missing
    base["near"] = len(missing) == 1 and "manca prezzo" not in missing[0]

    if missing:
        base["reason"] = missing[0]
        return base

    # Tutte le condizioni ok
    stop = range_low if weekly == "LONG" else range_high
    risk = abs(price - stop)
    base.update({
        "action": "ENTER",
        "side": weekly,
        "entry": price,
        "stop": stop,
        "exit": "sotto VWAP" if weekly == "LONG" else "sopra VWAP",
        "exit_price": vwap,
        "reason": "settimana, range e VWAP allineati",
        "risk": risk,
        "send_order": False,
    })
    return base


def empty_snapshot(symbol: str) -> dict:
    spec = UNIVERSE[symbol]
    return {
        "weekly_bias": "UNKNOWN",
        "session": "UNKNOWN",
        "opening_range": "UNKNOWN",
        "volume": "UNKNOWN",
        "price": None,
        "range_high": None,
        "range_low": None,
        "vwap": None,
        "spread": None,
        "news_window": "UNKNOWN",
        "max_spread": spec["max_spread"],
    }


def run(config: dict | None = None) -> dict:
    if config is None and CONFIG.exists():
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
    config = config or {}
    snaps = config.get("instruments", {})
    rows = [decide(symbol, snaps.get(symbol, empty_snapshot(symbol))) for symbol in UNIVERSE]
    report = {
        "paper_only": True,
        "send_order": False,
        "automation": "decision_only",
        "read_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "universe": list(UNIVERSE),
        "entries": [row["symbol"] for row in rows if row["action"] == "ENTER"],
        "near": [row["symbol"] for row in rows if row.get("near")],
        "rows": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def line(decision: dict) -> str:
    if decision.get("action") == "ENTER":
        return (
            f"{decision['symbol']} {decision['side']}\n"
            f"entra {decision['entry']}\n"
            f"stop {decision['stop']}\n"
            f"esci {decision['exit']}"
        )
    if decision.get("near"):
        return f"{decision.get('symbol', 'DAY')}\nVicino\n{decision.get('reason', '')}"
    return f"{decision.get('symbol', 'DAY')}\nNiente\n{decision.get('reason', '')}".strip()
