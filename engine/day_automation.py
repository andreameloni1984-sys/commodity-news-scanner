"""Decisione day trading pronta per un'automazione. PAPER only.

Non manda ordini. Produce un oggetto con azione, prezzi e motivo.
Se manca un numero, l'azione è NONE.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

OUT = Path("data/day_automation.json")


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
    base = {
        "symbol": symbol,
        "action": "NONE",
        "side": None,
        "entry": None,
        "stop": None,
        "exit": None,
        "reason": "",
        "paper_only": True,
        "send_order": False,
    }
    weekly = str(snapshot.get("weekly_bias", "UNKNOWN")).upper()
    if weekly not in {"LONG", "SHORT"}:
        base["reason"] = "settimana non direzionale"
        return base
    if str(snapshot.get("session", "")).upper() not in {"OPENING_RANGE", "LONDON_NY"}:
        base["reason"] = "fuori finestra"
        return base
    if str(snapshot.get("news_window", "")).upper() == "ACTIVE":
        base["reason"] = "dato macro in uscita"
        return base
    if str(snapshot.get("opening_range", "")).upper() != "BROKEN":
        base["reason"] = "range non rotto"
        return base
    if str(snapshot.get("volume", "")).upper() != "ABOVE_AVERAGE":
        base["reason"] = "volume basso"
        return base
    price = _num(snapshot.get("price"))
    range_high = _num(snapshot.get("range_high"))
    range_low = _num(snapshot.get("range_low"))
    vwap = _num(snapshot.get("vwap"))
    spread = _num(snapshot.get("spread"))
    max_spread = _num(snapshot.get("max_spread"))
    if None in (price, range_high, range_low, vwap, spread, max_spread):
        base["reason"] = "manca prezzo, range, VWAP o spread"
        return base
    if spread > max_spread:
        base["reason"] = "spread troppo largo"
        return base
    if weekly == "LONG" and not (price > range_high and price > vwap):
        base["reason"] = "rottura long non confermata"
        return base
    if weekly == "SHORT" and not (price < range_low and price < vwap):
        base["reason"] = "rottura short non confermata"
        return base
    if weekly == "LONG":
        stop = range_low
        exit_rule = "sotto VWAP"
    else:
        stop = range_high
        exit_rule = "sopra VWAP"
    risk = abs(price - stop)
    if risk <= 0:
        base["reason"] = "stop non valido"
        return base
    base.update({
        "action": "ENTER",
        "side": weekly,
        "entry": price,
        "stop": stop,
        "exit": exit_rule,
        "exit_price": vwap,
        "reason": "settimana, range e VWAP allineati",
        "risk": risk,
        "send_order": False,
    })
    return base


def run(config: dict | None = None) -> dict:
    config = config or {}
    snaps = config.get("instruments", {})
    rows = [decide(symbol, snap) for symbol, snap in snaps.items()]
    report = {
        "paper_only": True,
        "send_order": False,
        "automation": "decision_only",
        "read_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rows": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def line(decision: dict) -> str:
    if decision.get("action") != "ENTER":
        return f"{decision.get('symbol', 'DAY')}\nNiente\n{decision.get('reason', '')}".strip()
    return (
        f"{decision['symbol']} {decision['side']}\n"
        f"entra {decision['entry']}\n"
        f"stop {decision['stop']}\n"
        f"esci {decision['exit']}"
    )
