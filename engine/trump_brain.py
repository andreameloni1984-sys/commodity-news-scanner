"""Trump Brain — elevated SPUTNIK/Trump catalyst layer for commodity decisions.

Turns public Trump/policy events (White House, GDELT, SEC filings) into a
primary ranking signal for commodities. Still never authorizes execution alone;
technical trigger, risk and safety gates remain mandatory.
"""
from __future__ import annotations

from typing import Any

from sputnik_catalyst import catalyst_watchlist
from sputnik_action_reaction import match_historical_reactions, infer_direction, classify_event


def trump_brain_score(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Score commodity instruments by strength of Trump/policy catalysts.

    Returns a ranked list of instruments with catalyst score, historical bias
    and primary sources. Higher score = stronger priority for the commodity bot.
    """
    if not findings:
        return []

    watches = catalyst_watchlist(findings, limit=20)
    scored = []
    for w in watches:
        # Aggregate historical directions from related events
        hist_dirs: dict[str, str] = {}
        event_types = set()
        for finding in findings:
            domains = set(finding.get("domains") or [])
            if not domains.intersection(set(w.get("domains") or [])):
                continue
            text = " ".join([
                str(finding.get("title") or ""),
                " ".join(finding.get("domains") or []),
            ])
            matches = match_historical_reactions(text, limit=2)
            if matches:
                hist_dirs.update(infer_direction(matches))
                event_types.add(classify_event(text))

        # Bias mapping for commodities
        bias = "NEUTRAL"
        for asset, direction in hist_dirs.items():
            if asset in {"OIL", "WTI", "BRENT"} and direction == "UP":
                bias = "LONG"
            elif asset in {"OIL", "WTI", "BRENT"} and direction == "DOWN":
                bias = "SHORT"
            elif asset in {"GOLD"} and direction == "UP":
                bias = "LONG"
            elif asset in {"GOLD"} and direction == "DOWN":
                bias = "SHORT"

        base = float(w.get("score") or 0)
        # Primary source bonus (White House / SEC)
        if w.get("primary_source"):
            base += 15
        # Historical analogue bonus
        if hist_dirs:
            base += 10

        scored.append({
            "instrument": w["instrument"],
            "description": w.get("description", ""),
            "catalyst_score": min(100.0, base),
            "bias": bias,
            "domains": w.get("domains") or [],
            "sources": w.get("sources") or [],
            "primary_source": bool(w.get("primary_source")),
            "historical_bias": hist_dirs,
            "event_types": sorted(event_types),
            "events": w.get("events", 0),
            "reason": "Trump/policy catalyst prioritised by Trump Brain",
        })

    scored.sort(key=lambda x: -x["catalyst_score"])
    return scored


def apply_trump_brain_boost(state: Any, brain_scores: list[dict[str, Any]]) -> Any:
    """Apply a larger score boost when a Trump Brain catalyst matches the instrument.

    This elevates the catalyst from a small confluence (+3) to a primary driver
    (up to +12 probability / +8 quality when aligned).
    """
    if not brain_scores:
        return state

    name = str(getattr(state, "commodity", "") or "").lower()
    symbol = str(getattr(state, "symbol", "") or "").upper()

    best = None
    for item in brain_scores:
        inst = str(item.get("instrument") or "").upper()
        if (
            (inst in {"WTI", "BRENT"} and ("wti" in name or "brent" in name or symbol in {"USOIL", "UKOIL", "CL"}))
            or (inst == "GOLD" and ("gold" in name or "oro" in name or "XAU" in symbol))
            or (inst in {"SILVER", "PLATINUM", "PALLADIUM"} and any(m in name for m in ("silver", "argento", "platino", "palladio")))
            or (inst in {"CORN", "WHEAT", "SUGAR", "COFFEE", "COCOA", "RICE"} and any(m in name for m in ("corn", "wheat", "sugar", "coffee", "cocoa", "rice")))
        ):
            if best is None or item["catalyst_score"] > best["catalyst_score"]:
                best = item

    if best is None:
        return state

    metadata = getattr(state, "metadata", None)
    if not isinstance(metadata, dict):
        metadata = {}
        state.metadata = metadata

    metadata["trump_brain"] = {
        "instrument": best["instrument"],
        "catalyst_score": best["catalyst_score"],
        "bias": best["bias"],
        "primary_source": best["primary_source"],
        "historical_bias": best.get("historical_bias") or {},
    }

    # Larger boost than the previous +3 confluence
    boost_prob = min(12.0, best["catalyst_score"] * 0.10)
    boost_qual = min(8.0, best["catalyst_score"] * 0.07)

    if best["bias"] in {"LONG", "SHORT"} and state.setup_direction in {"LONG", "SHORT"}:
        if best["bias"] == state.setup_direction:
            state.probability = min(99.0, float(getattr(state, "probability", 40.0)) + boost_prob)
            state.quality = min(100.0, float(getattr(state, "quality", 0.0)) + boost_qual)
            metadata["trump_brain_confluence"] = "ALIGNED_STRONG"
        else:
            state.probability = max(0.0, float(getattr(state, "probability", 40.0)) - 6.0)
            state.quality = max(0.0, float(getattr(state, "quality", 0.0)) - 4.0)
            metadata["trump_brain_confluence"] = "CONFLICT"
    else:
        # Context-only boost (still elevates priority)
        state.quality = min(100.0, float(getattr(state, "quality", 0.0)) + boost_qual * 0.5)
        metadata["trump_brain_confluence"] = "CONTEXT_PRIORITY"

    return state
