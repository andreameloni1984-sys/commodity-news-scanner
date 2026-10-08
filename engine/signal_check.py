"""SOYUZ — engine/signal_check.py

Verifica dei segnali. Non esegue ordini.
Controlla che il biglietto delle tre regole congelate sia coerente:
direzione, stop sotto il prezzo, take profit in ordine, paper_only.
"""

from __future__ import annotations

from engine.month_trend import month_trend
from engine.slow_trend import slow_trend
from engine.weekly_trend import weekly_trend

RULES = {
    "weekly_20": weekly_trend,
    "month_21": month_trend,
    "slow_3m_12m": slow_trend,
}


def _checks(name: str, signal: dict) -> list[str]:
    errors: list[str] = []
    status = signal.get("status")
    direction = signal.get("direction")
    if status != "OK":
        return [f"{name}: status {status}"]
    if signal.get("paper_only") is not True:
        errors.append(f"{name}: paper_only mancante")
    if direction not in {"LONG", "FLAT"}:
        errors.append(f"{name}: direzione non ammessa {direction}")
    price = signal.get("price")
    atr = signal.get("atr")
    if not isinstance(price, (int, float)) or price <= 0:
        errors.append(f"{name}: prezzo non valido")
    if not isinstance(atr, (int, float)) or atr <= 0:
        errors.append(f"{name}: ATR non valido")
    if direction == "FLAT":
        if signal.get("stop") is not None or signal.get("tp1") is not None:
            errors.append(f"{name}: flat con stop o take profit")
        return errors
    stop = signal.get("stop")
    tp1 = signal.get("tp1")
    tp2 = signal.get("tp2")
    if not all(isinstance(x, (int, float)) for x in (stop, tp1, tp2)):
        errors.append(f"{name}: stop o take profit mancante")
        return errors
    if not (stop < price < tp1 < tp2):
        errors.append(f"{name}: ordine prezzi stop < entry < tp1 < tp2 non rispettato")
    return errors


def verify_signals(closes: list[float], risk_cash: float = 100.0) -> dict:
    """Ritorna i tre segnali e gli errori di coerenza. Nessun ordine."""
    from engine.month_trend import position_units as month_units
    from engine.slow_trend import position_units as slow_units
    from engine.weekly_trend import position_units as weekly_units

    sizing = {
        "weekly_20": weekly_units,
        "month_21": month_units,
        "slow_3m_12m": slow_units,
    }
    report = {"paper_only": True, "signals": {}, "errors": [], "ok": True}
    for name, fn in RULES.items():
        signal = fn(closes)
        signal = dict(signal)
        signal["units"] = sizing[name](signal, risk_cash)
        report["signals"][name] = signal
        found = _checks(name, signal)
        report["errors"].extend(found)
    report["ok"] = not report["errors"]
    return report
