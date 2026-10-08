"""SOYUZ GAGARIN — engine/research_validation.py

Modalità RESEARCH / PAPER VALIDATION.
Non promuove una regola. Accumula osservazioni e confronta tre ipotesi.
Una candidata esiste solo se il vantaggio è su un campione non usato
per sceglierla, e resta paper_only.
"""

from __future__ import annotations

import statistics

MIN_SAMPLE = 30
PAPER_ONLY = True

STRATEGIES = (
    "A_GAGARIN_ATTUALE",
    "B_WEEKLY_REGIME_INTRADAY",
    "C_COMMODITY_SPECIFIC",
)


def empty_book() -> dict:
    return {
        "mode": "RESEARCH_PAPER_VALIDATION",
        "paper_only": PAPER_ONLY,
        "min_sample": MIN_SAMPLE,
        "observations": {name: [] for name in STRATEGIES},
        "promoted": None,
    }


def record(
    book: dict,
    *,
    strategy: str,
    commodity: str,
    setup: str,
    regime: str,
    weekly_bias: str,
    mfe_atr: float,
    mae_atr: float,
    hit_tp1_before_sl: bool,
    net: float,
    out_of_sample: bool,
) -> dict:
    if strategy not in STRATEGIES:
        raise ValueError(f"strategia non prevista: {strategy}")
    book["observations"][strategy].append({
        "commodity": commodity,
        "setup": setup,
        "regime": regime,
        "weekly_bias": weekly_bias,
        "mfe_atr": mfe_atr,
        "mae_atr": mae_atr,
        "hit_tp1_before_sl": hit_tp1_before_sl,
        "net": net,
        "out_of_sample": out_of_sample,
        "paper_only": True,
    })
    book["promoted"] = None
    return book


def _slice(rows: list[dict], commodity: str, setup: str, regime: str, weekly_bias: str) -> list[dict]:
    return [
        r for r in rows
        if r["commodity"] == commodity
        and r["setup"] == setup
        and r["regime"] == regime
        and r["weekly_bias"] == weekly_bias
    ]


def _profit_factor(nets: list[float]) -> float | None:
    gains = sum(x for x in nets if x > 0)
    losses = sum(-x for x in nets if x < 0)
    if losses == 0:
        return None
    return gains / losses


def describe(rows: list[dict]) -> dict:
    """Frase misurata, non uno stop imposto."""
    if len(rows) < MIN_SAMPLE:
        return {
            "status": "CAMPIONE_INSUFFICIENTE",
            "n": len(rows),
            "need": MIN_SAMPLE,
            "paper_only": True,
        }
    oos = [r for r in rows if r["out_of_sample"]]
    used = oos if len(oos) >= MIN_SAMPLE else rows
    nets = [r["net"] for r in used]
    wins = [x for x in nets if x > 0]
    return {
        "status": "OSSERVAZIONE" if used is oos else "IN_SAMPLE_NON_PROMOSSA",
        "paper_only": True,
        "n": len(used),
        "mfe_atr_median": statistics.median(r["mfe_atr"] for r in used),
        "mae_atr_median": statistics.median(r["mae_atr"] for r in used),
        "tp1_before_sl": sum(1 for r in used if r["hit_tp1_before_sl"]) / len(used),
        "net_median": statistics.median(nets),
        "net_mean": statistics.mean(nets),
        "win_rate": len(wins) / len(nets),
        "profit_factor": _profit_factor(nets),
    }


def compare(book: dict, commodity: str, setup: str, regime: str, weekly_bias: str) -> dict:
    report = {"paper_only": True, "promoted": None, "strategies": {}}
    for name in STRATEGIES:
        rows = _slice(book["observations"][name], commodity, setup, regime, weekly_bias)
        report["strategies"][name] = describe(rows)
    oos = {
        name: row for name, row in report["strategies"].items()
        if row.get("status") == "OSSERVAZIONE"
    }
    if len(oos) >= 2:
        best = max(oos, key=lambda name: oos[name]["net_median"])
        others = [oos[n]["net_median"] for n in oos if n != best]
        if others and oos[best]["net_median"] > max(others):
            report["candidate"] = best
            report["note"] = "Candidata paper. Non è una regola del motore."
    return report


def annotate(state):
    """Aggiunge le tre ipotesi allo stato. Non cambia final_decision."""
    from engine.weekly_trend import weekly_trend

    closes = [float(x) for x in (getattr(state, "closes", []) or []) if x]
    weekly = weekly_trend(closes) if closes else {"direction": "FLAT", "status": "NO_CLOSES"}
    regime = getattr(state, "regime", None)
    trigger = bool(getattr(state, "trigger_confirmed", False))
    setup = getattr(state, "setup_direction", None)
    weekly_long = weekly.get("direction") == "LONG"
    b_on = weekly_long and regime == "TREND_UP" and trigger and setup == "LONG"
    state.metadata["research"] = {
        "mode": "RESEARCH_PAPER_VALIDATION",
        "paper_only": True,
        "promoted": None,
        "weekly_bias": "FAVOREVOLE" if weekly_long else "CONTRARIO",
        "weekly_status": weekly.get("status"),
        "A_GAGARIN_ATTUALE": "OSSERVA",
        "B_WEEKLY_REGIME_INTRADAY": "CONTESTO_OK" if b_on else "CONTESTO_SPENTO",
        "C_COMMODITY_SPECIFIC": "CAMPIONE_INSUFFICIENTE",
        "note": "Il day trading è solo il trigger di B, e solo se settimana e regime sono long.",
    }
    return state
