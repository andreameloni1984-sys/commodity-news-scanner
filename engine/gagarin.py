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
from engine.forecast_ensemble import forecast_ensemble
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
                (asset == "Argento" and ("argento" in asset_name or "silver" in asset_name or "XAG" in symbol)) or
                (asset == "Platino" and ("platino" in asset_name or "platinum" in asset_name or "XPT" in symbol)) or
                (asset == "Palladio" and ("palladio" in asset_name or "palladium" in asset_name or "XPD" in symbol)) or
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
# Embedded public-news intelligence: no runtime dependency on the separate SPUTNIK service.
_GAGARIN_NEWS_CACHE = {"loaded_at": 0.0, "events": []}


def apply_sputnik_intelligence(state):
    """Apply copied SPUTNIK-style intelligence locally from Gagarin's news engine.

    Reads the local event journal first; if it has no usable recent events,
    reuses Gagarin's own public RSS/GDELT fetcher. This is context/scoring only:
    it cannot create a setup or bypass trigger, risk, or safety.
    """
    import json
    import os
    import time
    from datetime import datetime, timezone
    from pathlib import Path

    try:
        from telegram.news_monitor import classify_event, fetch_news_items
        from sputnik_action_reaction import build_action_reaction_record
        from sputnik_catalyst import catalyst_watchlist
        from engine.public_event_brain import classify as classify_public_intelligence

        now = time.time()
        if now - float(_GAGARIN_NEWS_CACHE.get("loaded_at", 0.0)) > 300:
            recent = []
            journal_path = Path(os.getenv("GAGARIN_NEWS_JOURNAL_PATH", "data/news_event_journal.jsonl"))
            cutoff = now - 72 * 3600
            try:
                if journal_path.exists():
                    for line in journal_path.read_text(encoding="utf-8").splitlines()[-500:]:
                        try:
                            row = json.loads(line)
                        except (json.JSONDecodeError, TypeError):
                            continue
                        if row.get("kind") != "NEWS_DETECTED" or not row.get("title"):
                            continue
                        stamp = row.get("first_seen_at") or row.get("published_at") or row.get("recorded_at")
                        try:
                            dt = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                            if dt.timestamp() < cutoff:
                                continue
                        except (TypeError, ValueError, OverflowError):
                            continue
                        recent.append({
                            "event_id": str(row.get("event_id") or ""),
                            "source": str(row.get("source") or "GAGARIN_NEWS_JOURNAL"),
                            "title": str(row.get("title") or ""),
                            "url": str(row.get("url") or ""),
                            "detected_at": str(stamp or ""),
                            "evidence": "LOCAL_NEWS_JOURNAL",
                        })
            except OSError:
                pass

            # Self-contained fallback: use Gagarin's own public-source collector,
            # not the separate SPUTNIK service or its remote state endpoint.
            if not recent:
                try:
                    for item in fetch_news_items()[:80]:
                        title = str(item.get("title") or "").strip()
                        if not title:
                            continue
                        published = str(item.get("published_at") or "")
                        try:
                            dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                            if dt.timestamp() < cutoff:
                                continue
                        except (TypeError, ValueError, OverflowError):
                            continue
                        recent.append({
                            "event_id": str(item.get("url") or title),
                            "source": str(item.get("source") or "PUBLIC_RSS"),
                            "title": title,
                            "url": str(item.get("url") or ""),
                            "detected_at": published,
                            "evidence": "PUBLIC_RSS_ITEM",
                        })
                except Exception:
                    pass

            # De-duplicate on event identity and title; newest/recent item wins.
            deduped = {}
            for item in recent:
                key = item.get("event_id") or item.get("title")
                deduped[str(key)] = item
            _GAGARIN_NEWS_CACHE["events"] = list(deduped.values())[-100:]
            _GAGARIN_NEWS_CACHE["loaded_at"] = now

        name = str(getattr(state, "commodity", "") or "").lower()
        symbol = str(getattr(state, "symbol", "") or "").upper()
        matches = []
        for item in _GAGARIN_NEWS_CACHE.get("events", []):
            title = str(item.get("title") or "")
            classified = classify_event(title)
            intel = classify_public_intelligence(title)
            assets = classified.get("assets") or []
            impact = classified.get("impact") or {}
            asset_match = False
            for asset in assets:
                asset_match = (
                    (asset == 'WTI' and ('wti' in name or 'wti' in symbol or symbol == 'USOIL'))
                    or (asset == 'Brent' and ('brent' in name or 'brent' in symbol or symbol == 'UKOIL'))
                    or (asset == 'Oro' and ('oro' in name or 'gold' in name or 'XAU' in symbol))
                    or (asset == 'Argento' and ('argento' in name or 'silver' in name or 'XAG' in symbol))
                    or (asset == 'Rame' and ('rame' in name or 'copper' in name or 'COPPER' in symbol or symbol == 'HG=F'))
                    or (asset == 'Grano' and ('grano' in name or 'wheat' in name or 'WHEAT' in symbol or symbol == 'ZW=F'))
                    or (asset == 'Mais' and ('mais' in name or 'corn' in name or 'CORN' in symbol or symbol == 'ZC=F'))
                    or (asset == 'Soia' and ('soia' in name or 'soybean' in name or 'SOYBEAN' in symbol or symbol == 'ZS=F'))
                )
                if asset_match:
                    break
            # A domain-only match is retained as context but cannot score direction.
            domain_match = bool(set(intel.get("domains") or []) & {
                "ENERGY", "METALS", "AGRICULTURE", "TRADE_POLICY", "RATES_MACRO", "GEOPOLITICS", "AI_TECH", "DATA_CENTERS", "POWER_INFRA"
            })
            if asset_match or domain_match:
                action_reaction = build_action_reaction_record(
                    {"event_id": item.get("event_id"), "domains": intel.get("domains") or []},
                    title,
                )
                candidates = catalyst_watchlist([{
                    "source": item.get("source", "PUBLIC_RSS"),
                    "event_id": item.get("event_id", ""),
                    "domains": intel.get("domains") or [],
                    "evidence": item.get("evidence", "PUBLIC_RSS_ITEM"),
                }], limit=8)
                matches.append({
                    "event_id": item.get("event_id", ""),
                    "source": item.get("source", "PUBLIC_RSS"),
                    "title": title[:300],
                    "url": item.get("url", ""),
                    "detected_at": item.get("detected_at", ""),
                    "domains": intel.get("domains") or [],
                    "assets": assets,
                    "impact": impact,
                    "confidence_score": classified.get("confidence_score", 0),
                    "historical_action_reaction": action_reaction,
                    "watch_candidates": candidates,
                    "directional_text_found": any(v in {"RIALZISTA", "RIBASSISTA"} for v in impact.values()),
                    "evidence": item.get("evidence", "PUBLIC_RSS_ITEM"),
                })

        state.metadata["sputnik_intelligence"] = {
            "status": "MATCHED" if matches else ("NO_RELEVANT_MATCH" if _GAGARIN_NEWS_CACHE.get("events") else "NO_RECENT_NEWS"),
            "events": matches[:8],
            "window_hours": 72,
            "source": "GAGARIN_EMBEDDED_PUBLIC_INTELLIGENCE",
            "runtime_sputnik_dependency": False,
            "cache_age_seconds": max(0, int(now - float(_GAGARIN_NEWS_CACHE.get("loaded_at", now)))),
        }
        directional = [m for m in matches if m.get("directional_text_found")]
        if directional:
            state.metadata["news_context_active"] = True
            state.metadata["news_context_count"] = len(directional)
            state.metadata["news_context_note"] = "Embedded public-news intelligence; technical trigger, risk and safety remain mandatory."
        return state
    except Exception as exc:
        state.metadata["sputnik_intelligence"] = {
            "status": "ERROR",
            "error": type(exc).__name__,
            "runtime_sputnik_dependency": False,
        }
        return state


def analyze_one(commodity: Commodity) -> SoyuzState:
    state = SoyuzState(
        commodity=commodity.name,
        symbol=commodity.symbol,
        analysis_timestamp=datetime.now(timezone.utc).isoformat(),
    )

    state = load_data(state, commodity)
    state = evaluate_pre_move(state)
    # Independent, auditable regime/momentum ensemble; ranking context only.
    state.metadata["forecast_ensemble"] = forecast_ensemble(state.candles)
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
            float((state.metadata.get("forecast_ensemble") or {}).get("score", 0.0)),
            float(state.opportunity_score or 0.0),
            float(state.probability or 0.0),
            float(state.quality or 0.0),
            float(state.confidence or 0.0),
        ),
        reverse=True,
    )
    return results
