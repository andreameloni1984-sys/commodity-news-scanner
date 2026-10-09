"""SOYUZ — day trading filter. Paper only.

Ramo separato dal motore commodity. Non promuove regole e non manda ordini.
Il filtro dice solo se uno strumento è candidabile oggi.

Strumenti: SPY, QQQ, ES, NQ, MES, MNQ, EURUSD, GBPUSD.
Variabili: weekly_bias, session, opening_range, volume, atr, vwap, gap, news_window, spread.
Un dato mancante blocca l'ingresso. Nessun valore inventato.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

INSTRUMENTS = {
    "SPY": {"class": "etf", "session": "us_rth", "primary": True},
    "QQQ": {"class": "etf", "session": "us_rth", "primary": True},
    "ES": {"class": "future", "session": "us_rth", "primary": False},
    "NQ": {"class": "future", "session": "us_rth", "primary": False},
    "MES": {"class": "future", "session": "us_rth", "primary": False},
    "MNQ": {"class": "future", "session": "us_rth", "primary": False},
    "EURUSD": {"class": "fx", "session": "london_ny", "primary": False},
    "GBPUSD": {"class": "fx", "session": "london_ny", "primary": False},
}

VARIABLES = (
    "weekly_bias",
    "session",
    "opening_range",
    "volume",
    "atr",
    "vwap",
    "gap",
    "news_window",
    "spread",
)

CONFIG_PATH = Path("data/day_trading_config.json")
OUT_PATH = Path("data/day_trading_filter.json")


def load_config(path: Path = CONFIG_PATH) -> dict:
    if not path.exists():
        return {"paper_only": True, "instruments": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def _missing(snapshot: dict) -> list[str]:
    return [name for name in VARIABLES if snapshot.get(name) in (None, "", "UNKNOWN")]


def evaluate(symbol: str, snapshot: dict | None) -> dict:
    """Ritorna ALLOW o BLOCK con il motivo. Non è un ordine."""
    snapshot = snapshot or {}
    spec = INSTRUMENTS.get(symbol)
    if spec is None:
        return {
            "symbol": symbol,
            "decision": "BLOCK",
            "reason": "strumento fuori lista day trading",
            "paper_only": True,
            "order": None,
        }
    missing = _missing(snapshot)
    if missing:
        return {
            "symbol": symbol,
            "decision": "BLOCK",
            "reason": "dati mancanti: " + ", ".join(missing),
            "paper_only": True,
            "order": None,
        }

    reasons = []
    weekly = str(snapshot["weekly_bias"]).upper()
    if weekly not in ("LONG", "SHORT"):
        reasons.append("weekly bias non direzionale")
    session = str(snapshot["session"]).upper()
    if session not in ("OPENING_RANGE", "LONDON_NY"):
        reasons.append("fuori finestra: solo primi 30 minuti US o overlap Londra-NY")
    if str(snapshot["opening_range"]).upper() != "BROKEN":
        reasons.append("range di apertura non rotto")
    if str(snapshot["volume"]).upper() != "ABOVE_AVERAGE":
        reasons.append("volume non sopra la media")
    if str(snapshot["atr"]).upper() == "TOO_QUIET":
        reasons.append("ATR troppo stretto per coprire lo spread")
    side = str(snapshot["vwap"]).upper()
    if weekly == "LONG" and side != "ABOVE":
        reasons.append("prezzo non sopra il VWAP")
    if weekly == "SHORT" and side != "BELOW":
        reasons.append("prezzo non sotto il VWAP")
    if str(snapshot["news_window"]).upper() == "ACTIVE":
        reasons.append("finestra news macro attiva")
    try:
        spread = float(snapshot["spread"])
    except (TypeError, ValueError):
        spread = 999.0
    if spread > float(snapshot.get("max_spread", 0.05)):
        reasons.append("spread sopra il massimo ammesso")

    if reasons:
        return {
            "symbol": symbol,
            "decision": "BLOCK",
            "reason": "; ".join(reasons),
            "paper_only": True,
            "order": None,
        }

    direction = weekly
    return {
        "symbol": symbol,
        "decision": "ALLOW",
        "reason": "contesto, range, volume, VWAP e costi allineati",
        "direction": direction,
        "paper_only": True,
        "promoted": None,
        "order": None,
        "risk": {
            "risk_pct": 0.01,
            "daily_loss_cap_pct": 0.03,
            "stop": "dentro il range di apertura, non oltre 1 ATR",
            "exit": "ritorno oltre il VWAP, oppure cap giornaliero",
            "max_losses": 3,
        },
    }


def run(config: dict | None = None) -> dict:
    config = config if config is not None else load_config()
    snaps = config.get("instruments", {})
    rows = [evaluate(symbol, snaps.get(symbol, {})) for symbol in INSTRUMENTS]
    allowed = [row["symbol"] for row in rows if row["decision"] == "ALLOW"]
    report = {
        "paper_only": True,
        "promoted": None,
        "automation": "filter_only",
        "broker": None,
        "read_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "allowed": allowed,
        "rows": rows,
        "note": "ALLOW non è un ordine. Il broker resta spento finché il paper non batte il long passivo.",
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
