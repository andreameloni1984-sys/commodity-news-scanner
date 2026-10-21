from datetime import datetime, timezone

from commodities.universe import Commodity
from engine.state import SoyuzState
from engine.data import load_data
from engine.regime import apply_regime
from engine.structure import apply_structure
from engine.setup import apply_setup
from engine.trigger import apply_trigger
from engine.risk import apply_risk
from engine.safety import apply_safety
from engine.predictive import evaluate_pre_move
from engine.research_validation import annotate
from engine.energy_confluence import stamp_energy
from engine.energy_chain import stamp_paper

STRONG_MOVE_ATR = 1.5
OPPORTUNITY_MOVE_PCT_24H = 1.0
WATCH_MOVE_PCT_24H = 0.5


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, float(value)))


def scan_market_opportunity(state: SoyuzState) -> SoyuzState:
    closes = list(getattr(state, "closes", []) or [])
    candles = list(getattr(state, "candles", []) or [])
    timestamps = [float(x.get("timestamp", 0.0)) for x in candles]
    atr = float(state.atr or 0.0)
    if len(closes) < 2 or len(timestamps) != len(closes):
        return state

    latest = float(closes[-1])
    if latest <= 0:
        return state

    def pct_from_hours(hours: float):
        target = timestamps[-1] - hours * 3600.0
        idx = min(range(len(timestamps)), key=lambda i: abs(timestamps[i] - target))
        base = float(closes[idx])
        return ((latest / base) - 1.0) * 100.0 if base > 0 else None

    move_4h = pct_from_hours(4.0)
    move_24h = pct_from_hours(24.0)
    lookback_index = max(0, len(closes) - 49)
    move_atr = abs(latest - float(closes[lookback_index])) / atr if atr > 0 else None

    direction_value = float(move_24h if move_24h is not None else move_4h or 0.0)
    direction = "LONG" if direction_value > 0 else "SHORT" if direction_value < 0 else "NONE"
    abs_4h = abs(float(move_4h or 0.0))
    abs_24h = abs(float(move_24h or 0.0))

    score = 0.0
    if abs_24h >= 1.0:
        score += min(40.0, abs_24h * 10.0)
    if abs_4h >= 0.75:
        score += min(30.0, abs_4h * 10.0)
    if move_atr is not None and move_atr >= 1.0:
        score += min(30.0, move_atr * 10.0)
    score = _clamp(score, 0.0, 100.0)

    if move_atr is not None and move_atr >= STRONG_MOVE_ATR:
        alert = "STRONG_MOVE"
    elif move_atr is not None and move_atr >= 1.0:
        alert = "OPPORTUNITY"
    elif move_atr is not None and move_atr >= 0.5:
        alert = "WATCH"
    else:
        alert = "NONE"

    state.move_4h_pct = round(float(move_4h), 4) if move_4h is not None else None
    state.move_24h_pct = round(float(move_24h), 4) if move_24h is not None else None
    state.move_atr = round(float(move_atr), 4) if move_atr is not None else None
    state.opportunity_score = round(score, 2)
    state.opportunity_alert = alert
    state.opportunity_direction = direction
    if atr > 0 and latest > 0:
        atr_pct = (atr / latest) * 100.0
        energy = 1.0 + (float(getattr(state, "pre_move_score", 0.0)) / 100.0)
        state.expected_move_pct = round(max(atr_pct, atr_pct * energy * 1.5), 4)
        state.expected_move_duration_hours = round(2.0 + min(22.0, float(getattr(state, "pre_move_score", 0.0)) * 0.20), 2)
        state.continuation_score = round(min(100.0, float(getattr(state, "pre_move_score", 0.0)) * 0.9 + (20.0 if direction == getattr(state, "pre_move_direction", "NONE") else 0.0)), 2)
        state.reversal_score = round(max(0.0, 100.0 - state.continuation_score), 2)
    state.metadata["market_move_4h_pct"] = state.move_4h_pct
    state.metadata["market_move_24h_pct"] = state.move_24h_pct
    state.metadata["market_move_atr"] = state.move_atr
    state.metadata["opportunity_score"] = state.opportunity_score
    state.metadata["opportunity_alert"] = state.opportunity_alert
    state.metadata["opportunity_direction"] = state.opportunity_direction
    state.metadata["strong_move_atr"] = STRONG_MOVE_ATR
    state.metadata["expected_move_pct"] = state.expected_move_pct
    state.metadata["expected_move_duration_hours"] = state.expected_move_duration_hours
    state.metadata["continuation_score"] = state.continuation_score
    state.metadata["reversal_score"] = state.reversal_score
    return state


def calculate_quality(state: SoyuzState) -> SoyuzState:
    probability = 40.0
    quality = 0.0
    confidence = 0.0

    if state.data_ok:
        quality += 15.0
        confidence += 10.0

    if state.regime in {"TREND_UP", "TREND_DOWN"}:
        probability += 10.0
        quality += 15.0
        confidence += 10.0
    elif state.regime == "RANGE" and state.opportunity_type == "MEAN_REVERSION":
        probability += 8.0
        quality += 12.0
        confidence += 8.0
    elif state.opportunity_type == "REVERSAL":
        probability += 5.0
        quality += 8.0
        confidence += 5.0

    if state.regime == "HIGH_VOLATILITY":
        probability -= 10.0
        quality -= 15.0
        confidence -= 10.0

    if state.structure in {"BULLISH", "BEARISH"}:
        probability += 8.0
        quality += 15.0
        confidence += 10.0

    if state.setup_direction in {"LONG", "SHORT"}:
        probability += 5.0
        quality += max(0.0, min(15.0, state.setup_quality * 0.15))
        confidence += 10.0

    if state.trigger_confirmed:
        probability += 12.0
        quality += 15.0
        confidence += 20.0

    # News is a small, auditable confluence factor only when the mapped asset
    # and the technical setup agree. It never creates a direction or bypasses
    # trigger, risk, or safety gates.
    intelligence = (getattr(state, "metadata", {}) or {}).get("sputnik_intelligence", {})
    news_events = intelligence.get("events", []) if isinstance(intelligence, dict) else []
    news_direction = None
    asset_name = str(getattr(state, "commodity", "") or "").lower()
    symbol = str(getattr(state, "symbol", "") or "").upper()
    for event in news_events:
        impacts = event.get("impact", {}) or {}
        for asset, impact in impacts.items():
            asset_l = str(asset).lower()
            matches_asset = (
                (asset == "WTI" and ("wti" in asset_name or "wti" in symbol or symbol == "USOIL")) or
                (asset == "Brent" and ("brent" in asset_name or "brent" in symbol or symbol == "UKOIL")) or
                (asset == "Oro" and ("oro" in asset_name or "gold" in asset_name or "XAU" in symbol)) or
                (asset == "Platino" and ("platino" in asset_name or "platinum" in asset_name or "XPT" in symbol)) or
                (asset == "Caffè" and ("caff" in asset_name or "coffee" in asset_name)) or
                (asset == "Cacao" and ("cacao" in asset_name or "cocoa" in asset_name)) or
                (asset == "Riso" and ("riso" in asset_name or "rice" in asset_name)) or
                (asset == "Zucchero" and ("zucchero" in asset_name or "sugar" in asset_name))
            )
            if matches_asset and impact in {"RIALZISTA", "RIBASSISTA"}:
                news_direction = "LONG" if impact == "RIALZISTA" else "SHORT"
                break
        if news_direction:
            break
    if news_direction and state.setup_direction in {"LONG", "SHORT"}:
        if news_direction == state.setup_direction:
            probability += 3.0
            quality += 2.0
            confidence += 2.0
            state.metadata["sputnik_confluence"] = "ALIGNED"
        else:
            probability -= 4.0
            quality -= 3.0
            confidence -= 3.0
            state.metadata["sputnik_confluence"] = "CONFLICT"
    elif news_events:
        state.metadata["sputnik_confluence"] = "CONTEXT_ONLY_NO_DIRECTIONAL_MATCH"

    if state.opportunity_type in {"MEAN_REVERSION", "REVERSAL"}:
        quality += 10.0
        confidence += 5.0

    if state.trigger in {"WAIT_LIVE", "NOT_CONFIRMED"}:
        confidence -= 5.0

    if state.live and state.data_ok:
        probability += 5.0
        quality += 5.0
        confidence += 10.0

    chain_complete = (
        state.data_ok
        and state.live
        and state.opportunity_type == "TREND_CONTINUATION"
        and state.regime in {"TREND_UP", "TREND_DOWN"}
        and state.structure in {"BULLISH", "BEARISH"}
        and state.setup_direction in {"LONG", "SHORT"}
        and state.trigger_confirmed
    )

    if not chain_complete:
        confidence = min(confidence, 55.0)

    if state.setup_direction not in {"LONG", "SHORT"}:
        quality = min(quality, 40.0)

    state.probability = _clamp(probability, 0.0, 99.0)
    state.quality = _clamp(quality, 0.0, 100.0)
    state.confidence = _clamp(confidence, 0.0, 100.0)

    return state



# Public-source intelligence bridge: news can adjust context, never bypass triggers/safety.
def apply_sputnik_intelligence(state):
    try:
        from engine.sputnik_bridge import fetch_sputnik_state, extract_active_domains
        from telegram.news_monitor import classify_event
        from datetime import datetime, timezone
        import re

        payload = fetch_sputnik_state(timeout=5)
        if not payload:
            state.metadata["sputnik_intelligence"] = {"status": "UNAVAILABLE"}
            return state

        history = payload.get("intelligence_history") or {}
        cutoff = datetime.now(timezone.utc).timestamp() - 72 * 3600
        matches = []
        name = str(getattr(state, "commodity", "") or "").lower()
        symbol = str(getattr(state, "symbol", "") or "").upper()
        for event_id, event in history.items():
            if not isinstance(event, dict):
                continue
            detected = event.get("detected_at")
            try:
                ts = datetime.fromisoformat(str(detected).replace("Z", "+00:00")).timestamp()
            except Exception:
                continue
            if ts < cutoff:
                continue
            domains = [str(x).upper() for x in (event.get("domains") or [])]
            text = " ".join(str(event.get(k) or "") for k in ("title", "text", "summary", "excerpt"))
            classified = classify_event(text) if text.strip() else {"assets": [], "impact": {}, "relevant": False, "reason": "no event text"}
            assets = classified.get("assets") or []
            # Match only explicitly mapped commodity exposure; AI/media are contextual,
            # not assumed to move every commodity.
            match = False
            for asset in assets:
                a = str(asset).lower()
                if (asset == "WTI" and ("wti" in name or "wti" in symbol or symbol == "USOIL")) or \
                   (asset == "Brent" and ("brent" in name or "brent" in symbol or symbol == "UKOIL")) or \
                   (asset == "Oro" and ("gold" in name or "oro" in name or "XAU" in symbol)) or \
                   (asset == "Platino" and ("platino" in name or "platinum" in name or "XPT" in symbol)) or \
                   (asset == "Caffè" and ("caff" in name or "coffee" in name)) or \
                   (asset == "Cacao" and ("cacao" in name or "cocoa" in name)) or \
                   (asset == "Riso" and ("riso" in name or "rice" in name)) or \
                   (asset == "Zucchero" and ("zucchero" in name or "sugar" in name)):
                    match = True
            domain_match = (
                ("AI_TECH" in domains and any(x in name or x in symbol for x in ("nasdaq", "qqq", "tech", "nvda", "msft", "aapl"))) or
                ("ENERGY" in domains and any(x in name or x in symbol for x in ("wti", "brent", "oil", "energy"))) or
                ("MEDIA" in domains and any(x in name or x in symbol for x in ("media", "communication", "spy")))
            )
            if match or domain_match:
                matches.append({
                    "event_id": str(event_id), "source": event.get("source", "TRUTH_ARCHIVE"),
                    "domains": domains, "detected_at": detected,
                    "assets": assets, "impact": classified.get("impact", {}),
                    "directional_text_found": bool(classified.get("relevant") and any(v in {"RIALZISTA", "RIBASSISTA"} for v in (classified.get("impact") or {}).values())),
                    "reason": classified.get("reason", "domain match; direction unconfirmed"),
                })

        state.metadata["sputnik_intelligence"] = {
            "status": "MATCHED" if matches else "NO_RELEVANT_MATCH",
            "events": matches[:5],
            "window_hours": 72,
            "source": "SPUTNIK/TRUTH_ARCHIVE",
        }
        # Only directional, asset-specific news changes model scores. Ambiguous
        # domain mentions are logged as context and never fabricate LONG/SHORT.
        directional = [m for m in matches if m.get("directional_text_found")]
        if directional:
            state.metadata["news_context_active"] = True
            state.metadata["news_context_count"] = len(directional)
            state.metadata["news_context_note"] = "Sputnik public-source event matched; technical trigger and safety gates remain mandatory."
        return state
    except Exception as exc:
        state.metadata["sputnik_intelligence"] = {"status": "ERROR", "error": type(exc).__name__}
        return state


def analyze_one(commodity: Commodity) -> SoyuzState:
    state = SoyuzState(
        commodity=commodity.name,
        symbol=commodity.symbol,
        analysis_timestamp=datetime.now(timezone.utc).isoformat(),
    )

    state = load_data(state, commodity)
    state = evaluate_pre_move(state)
    state = apply_sputnik_intelligence(state)
    state = scan_market_opportunity(state)
    state = apply_regime(state)
    state = apply_structure(state)
    state = apply_setup(state)
    state = apply_trigger(state)
    state = calculate_quality(state)
    state = apply_risk(state)
    state = apply_safety(state)
    state = annotate(state)
    return state


def analyze_universe(commodities):
    results = []
    for commodity in commodities:
        results.append(analyze_one(commodity))
    stamp_energy(results)
    stamp_paper(results)
    results.sort(
        key=lambda state: (
            state.final_decision == "ENTRY",
            bool((state.metadata.get("energy") or {}).get("in_complex")),
            state.opportunity_alert == "STRONG_MOVE",
            state.opportunity_alert == "OPPORTUNITY",
            float(state.opportunity_score or 0.0),
            float(state.probability or 0.0),
            float(state.quality or 0.0),
            float(state.confidence or 0.0),
        ),
        reverse=True,
    )
    return results
