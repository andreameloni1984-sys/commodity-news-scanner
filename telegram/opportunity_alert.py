"""Informational early-opportunity alerts; never authorizes or places orders."""
from typing import Any, Iterable
from engine.pattern_exit import analyze_pattern_and_exit

_PATTERNS = {"HH/HL — TREND RIALZISTA", "LH/LL — TREND RIBASSISTA",
             "BREAKOUT RIALZISTA", "BREAKOUT RIBASSISTA",
             "POSSIBILE INVERSIONE RIBASSISTA", "POSSIBILE INVERSIONE RIALZISTA",
             "COMPRESSIONE / POSSIBILE BREAKOUT"}
_MARKET = {"WATCH", "OPPORTUNITY", "STRONG_MOVE"}
_PRE = {"PRE_MOVE_WATCH", "PRE_MOVE_ELEVATED", "PRE_MOVE_HIGH"}


def _num(value, default=0.0):
    try:
        n = float(value)
        return n if n == n else default
    except (TypeError, ValueError):
        return default


def _price(value):
    n = _num(value, -1)
    return f"{n:.6g}" if n > 0 else "N/D"


def find_early_opportunities(states: Iterable[Any]) -> list[dict]:
    found = []
    for s in states:
        price = _price(getattr(s, "price", None))
        if not getattr(s, "data_ok", False) or price == "N/D":
            continue
        closes = getattr(s, "closes", []) or []
        direction = "NONE"
        for key in ("setup_direction", "pre_move_direction", "opportunity_direction",
                    "breakout_direction", "retest_direction"):
            d = str(getattr(s, key, "NONE") or "NONE").upper()
            if d in {"LONG", "SHORT"}:
                direction = d
                break
        if direction == "NONE":
            d = str(getattr(s, "structure_direction", "NONE")).upper()
            direction = "LONG" if d == "BULLISH" else "SHORT" if d == "BEARISH" else "NONE"
        if direction == "NONE":
            try:
                if len(closes) >= 4 and float(closes[-1]) != float(closes[-4]):
                    direction = "LONG" if float(closes[-1]) > float(closes[-4]) else "SHORT"
            except (TypeError, ValueError):
                pass
        if direction == "NONE":
            continue
        pattern = analyze_pattern_and_exit(
            direction=direction, closes=closes, highs=getattr(s, "highs", []),
            lows=getattr(s, "lows", []), entry=getattr(s, "entry", None),
            stop=getattr(s, "stop", None), tp1=getattr(s, "tp1", None),
            atr=getattr(s, "atr", None))
        decision = str(getattr(s, "final_decision", "WAIT")).upper()
        confirmed = (decision in {"ENTRY", "PAPER_ENTRY", "PAPER_SIGNAL"}
                     and getattr(s, "trigger_confirmed", False) and getattr(s, "live", False)
                     and getattr(s, "entry", None) is not None
                     and getattr(s, "stop", None) is not None and getattr(s, "tp1", None) is not None)
        if confirmed:
            continue
        market = str(getattr(s, "opportunity_alert", "NONE")).upper()
        pre = str(getattr(s, "pre_move_alert", "NONE")).upper()
        opp_score, pre_score = _num(getattr(s, "opportunity_score", 0)), _num(getattr(s, "pre_move_score", 0))
        setup_q = _num(getattr(s, "setup_quality", 0))
        has_setup = str(getattr(s, "setup_direction", "NONE")).upper() in {"LONG", "SHORT"} and setup_q >= 30
        has_pre = pre in _PRE and pre_score >= 45
        has_pattern = pattern["pattern"] in _PATTERNS
        if not (has_setup or market in _MARKET or has_pre or has_pattern):
            continue
        reasons = []
        if has_setup:
            reasons.append("setup presente; " + ("trigger confermato" if getattr(s, "trigger_confirmed", False) else "trigger da confermare"))
        if market in _MARKET:
            reasons.append(f"scanner mercato {market} ({opp_score:.0f}/100)")
        if has_pre:
            reasons.append(f"pre-movimento {pre} ({pre_score:.0f}/100)")
        if has_pattern:
            reasons.append("pattern " + pattern["pattern"])
        found.append({"state": s, "direction": direction, "pattern": pattern,
                      "reasons": reasons, "score": max(opp_score, pre_score, setup_q, 35 if has_pattern else 0)})
    found.sort(key=lambda x: x["score"], reverse=True)
    return found[:3]


def format_early_opportunity_alert(states: Iterable[Any]) -> str:
    rows = find_early_opportunities(states)
    if not rows:
        return ""
    lines = ["🟡 GAGARIN — POSSIBILE OPPORTUNITÀ",
             "Alert anticipato: non è un ingresso confermato.",
             "🧪 PAPER ONLY — nessun ordine inviato.", ""]
    for i, row in enumerate(rows, 1):
        s, p = row["state"], row["pattern"]
        name = getattr(s, "commodity", None) or getattr(s, "symbol", None) or "Strumento"
        lines += [f"{i}. {name} — possibile {row['direction']}",
                  f"Prezzo: {_price(getattr(s, 'price', None))} | Dati: {'LIVE' if getattr(s, 'live', False) else 'NON LIVE — solo monitoraggio'}",
                  f"Pattern: {p['pattern']} | Bias: {p['bias']}",
                  "Motivo: " + "; ".join(row["reasons"]),
                  "Trigger: " + ("presente, ma ingresso non autorizzato" if getattr(s, "trigger_confirmed", False) else "DA CONFERMARE")]
        for key, label in (("breakout_level", "Breakout da verificare"), ("retest_level", "Retest da verificare"),
                           ("entry", "Entry potenziale indicativa"), ("stop", "Stop indicativo")):
            value = getattr(s, key, None)
            if value is not None:
                lines.append(f"{label}: {_price(value)}")
        targets = [f"{k.upper()}: {_price(getattr(s, k, None))}" for k in ("tp1", "tp2", "tp3") if getattr(s, k, None) is not None]
        if targets:
            lines.append("Target indicativi: " + " | ".join(targets))
        if getattr(s, "entry", None) is None or getattr(s, "stop", None) is None:
            lines.append("Livelli incompleti: Gagarin non inventa entry o stop.")
        lines += [f"Gestione uscita: {p['exit_action']} — {p['reason']}",
                  f"Score contesto: {row['score']:.0f}/100 (euristico, non probabilità statistica)", ""]
    lines.append("Un alert anticipato indica un'opportunità da osservare, non un'autorizzazione a entrare.")
    return "\n".join(lines)
