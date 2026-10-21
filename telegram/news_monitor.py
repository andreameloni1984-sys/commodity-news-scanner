"""Event-driven commodity NEWS monitor for Gagarin.

Polls public RSS/GDELT sources every minute. A relevant fresh event triggers an
immediate PAPER analysis. A Telegram alert is sent only when the existing
Gagarin state has a live price, a confirmed trigger and a direction compatible
with the event's provisional impact. This module never places orders.
"""
from __future__ import annotations

import email.utils
import hashlib
import json
import os
import re
import threading
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode

import requests

from engine.public_event_brain import classify as classify_public_intelligence
from sputnik_action_reaction import build_action_reaction_record
from sputnik_catalyst import catalyst_watchlist

POLL_SECONDS = max(30, int(os.getenv("GAGARIN_NEWS_POLL_SECONDS", "60")))
RECHECK_SECONDS = max(300, int(os.getenv("GAGARIN_NEWS_RECHECK_SECONDS", "300")))
PENDING_TTL_SECONDS = 45 * 60
REQUEST_TIMEOUT_SECONDS = 8
# Source-specific throttling: avoid hammering feeds that are timing out or rate-limiting us.
GDELT_MIN_INTERVAL_SECONDS = max(300, int(os.getenv("GAGARIN_GDELT_MIN_INTERVAL_SECONDS", "300")))
SOURCE_BACKOFF_MAX_SECONDS = 60 * 60
_SOURCE_FAILURES: dict[str, int] = {}
_SOURCE_RETRY_AT: dict[str, float] = {}
_SOURCE_LAST_SUCCESS: dict[str, float] = {}
_SOURCE_LOCK = threading.Lock()
STATE_PATH = Path(os.getenv("GAGARIN_NEWS_STATE_PATH", "data/news_monitor_state.json"))
JOURNAL_PATH = Path(os.getenv("GAGARIN_NEWS_JOURNAL_PATH", "data/news_event_journal.jsonl"))


def _journal(record: dict[str, Any]) -> None:
    """Append a durable audit record for news, baseline, reaction and forecast."""
    row = dict(record)
    row.setdefault("recorded_at", _utc_now().isoformat())
    try:
        JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
        with JOURNAL_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    except OSError as exc:
        print(f"NEWS journal save failed | {type(exc).__name__}: {exc}", flush=True)

RSS_FEEDS = (
    ("EIA", "https://www.eia.gov/rss/press_releases.xml"),
    ("Federal Reserve", "https://www.federalreserve.gov/feeds/press_all.xml"),
    # These are the same public primary-source feeds watched by SPUTNIK.
    ("SPUTNIK / WHITE HOUSE", "https://www.whitehouse.gov/news/feed/"),
    ("SPUTNIK / TRUTH ARCHIVE", "https://www.trumpstruth.org/feed"),
)
GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_QUERY = '(oil OR crude OR WTI OR Brent OR gold OR silver OR OPEC OR sanctions OR Trump OR "Federal Reserve" OR Iran OR Hormuz OR energy OR inflation)'

OIL_TERMS = {
    "oil", "crude", "wti", "brent", "opec", "petroleum", "diesel",
    "gasoline", "refinery", "oilfield", "oil fields", "crude oil",
    "oil inventories", "oil stocks", "energy supply", "hormuz",
    "iran", "russia", "sanctions", "eia", "barrel", "barrels",
}
METAL_TERMS = {"gold", "bullion", "precious metal", "precious metals", "xau", "platinum", "platino", "xpt"}
AGRI_TERMS = {
    "coffee", "arabica", "robusta", "caffè", "caffe", "cocoa", "cacao",
    "rice", "riso", "sugar", "zucchero", "raw sugar", "white sugar",
    "coffee futures", "cocoa futures", "rice futures", "sugar futures",
}
MACRO_TERMS = {
    "federal reserve", "fed", "interest rate", "interest rates", "rate cut",
    "rate hike", "inflation", "cpi", "pce", "dollar", "treasury yield",
    "yields", "central bank", "fomc", "tariff", "tariffs", "sanctions",
    "war", "strike", "attack", "conflict", "ceasefire", "trump",
    "white house", "geopolitical", "recession",
}
OIL_BULLISH_TERMS = {
    "supply disruption", "supply disrupted", "production cut", "output cut",
    "opec cut", "oil attack", "attacks oil", "pipeline attack", "port attack",
    "strait closed", "hormuz closed", "shipping disruption", "inventory draw",
    "inventories fell", "stocks fell", "exports halted", "sanctions on oil",
    "oil sanctions", "supply risk",
}
OIL_BEARISH_TERMS = {
    "supply increase", "output increase", "production increase", "opec increase",
    "inventory build", "inventories rose", "stocks rose", "reserve release",
    "release reserves", "sanctions eased", "sanctions lifted", "sanctions relief",
    "ceasefire", "strait reopens", "reopen hormuz", "oil exports resume",
    "exports resume", "production rises", "demand destruction", "demand falls",
    "weak demand", "economic slowdown", "recession risk",
}
OIL_BULLISH_TERMS |= {
    "shipping attacks", "tanker attack", "tanker attacks", "supply threat",
    "supply threats", "production outage", "production outages", "outage",
    "outages", "oilfield shutdown", "oil field shutdown", "refinery shutdown",
    "refinery outage", "export disruption", "exports disrupted", "supply disruption",
    "supply risk", "geopolitical escalation", "escalating conflict",
    "strait of hormuz", "hormuz", "iran sanctions", "russia sanctions",
    "opec production cut", "opec+ cut", "crude inventories fell",
}
OIL_BEARISH_TERMS |= {
    "demand outlook weakens", "demand outlook weakened", "oil demand forecast cut",
    "oil demand downgraded", "opec raises output", "opec+ raises output",
    "spare capacity", "surplus supply", "glut", "oversupply",
}

METAL_BULLISH_TERMS = {
    "rate cut", "cuts rates", "dovish", "yields fall", "yields decline",
    "dollar falls", "dollar weakens", "war", "airstrike", "military strike",
    "escalation", "safe haven", "geopolitical risk",
}
METAL_BEARISH_TERMS = {
    "rate hike", "raises rates", "hawkish", "yields rise", "yields climb",
    "dollar rises", "dollar strengthens", "ceasefire", "peace deal",
}

AGRI_BULLISH_TERMS = {
    "drought", "crop damage", "crop losses", "poor harvest", "harvest shortfall",
    "frost", "freeze", "flood", "flooding", "heatwave", "heat wave",
    "export ban", "exports banned", "export restriction", "supply disruption",
    "production cut", "production falls", "production drop", "lower output",
    "pest outbreak", "disease outbreak", "crop disease", "port closure", "shipping disruption",
    "stocks fall", "inventories fall", "stocks decline", "production forecast cut",
}
AGRI_BEARISH_TERMS = {
    "bumper harvest", "record harvest", "good harvest", "harvest improves",
    "crop forecast raised", "production rises", "production increase", "higher output",
    "output increase", "exports resume", "export ban lifted", "export restrictions eased",
    "supply improves", "supply increase", "stocks rise", "inventories rise",
    "stocks build", "oversupply", "surplus supply", "demand falls", "weak demand",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    try:
        if re.fullmatch(r"\d{8}T\d{6}Z", text):
            return datetime.strptime(text, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        dt = email.utils.parsedate_to_datetime(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        pass
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None


def _normalise_title(title: str) -> str:
    text = " ".join((title or "").lower().split())
    stop = {"the", "and", "for", "with", "from", "after", "before", "says", "said", "over", "into", "its"}
    tokens = [t for t in text.split() if len(t) > 2 and t not in stop]
    return " ".join(tokens[:16])


def _fingerprint(item: dict[str, Any]) -> str:
    # Prefer canonical URL; title fingerprint catches syndicated duplicate headlines.
    url = str(item.get("url") or "").split("?", 1)[0].rstrip("/")
    title = _normalise_title(str(item.get("title") or ""))
    key = url or title
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]


def _title_cluster(item: dict[str, Any]) -> str:
    title = _normalise_title(str(item.get("title") or ""))
    return hashlib.sha256(title.encode("utf-8")).hexdigest()[:20]


def _source_allowed(source: str, min_interval: int = 0) -> bool:
    """Return false while a source is in backoff or within its minimum poll interval."""
    now = time.monotonic()
    with _SOURCE_LOCK:
        retry_at = _SOURCE_RETRY_AT.get(source, 0.0)
        if now < retry_at:
            return False
        last_success = _SOURCE_LAST_SUCCESS.get(source, 0.0)
        return not min_interval or now - last_success >= min_interval


def _source_succeeded(source: str) -> None:
    with _SOURCE_LOCK:
        recovered = _SOURCE_FAILURES.pop(source, 0) > 0
        _SOURCE_RETRY_AT.pop(source, None)
        _SOURCE_LAST_SUCCESS[source] = time.monotonic()
    if recovered:
        print(f"NEWS source recovered | source={source}", flush=True)


def _source_failed(source: str, exc: Exception) -> int:
    """Apply exponential cooldown; honour Retry-After when the server supplies it."""
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    retry_after = None
    try:
        retry_after = float((getattr(response, "headers", {}) or {}).get("Retry-After", ""))
    except (TypeError, ValueError):
        retry_after = None

    with _SOURCE_LOCK:
        failures = _SOURCE_FAILURES.get(source, 0) + 1
        _SOURCE_FAILURES[source] = failures
        if status == 429:
            base = max(15 * 60, retry_after or 0)
        elif source == "EIA":
            base = 10 * 60
        elif source == "GDELT":
            base = 5 * 60
        else:
            base = 2 * 60
        delay = min(SOURCE_BACKOFF_MAX_SECONDS, int(base * (2 ** min(failures - 1, 4))))
        if retry_after is not None:
            delay = min(SOURCE_BACKOFF_MAX_SECONDS, max(delay, int(retry_after)))
        _SOURCE_RETRY_AT[source] = time.monotonic() + delay

    status_text = f" HTTP={status}" if status is not None else ""
    print(
        f"NEWS source failure | source={source} | error={type(exc).__name__}"
        f"{status_text} | retry_in={delay}s",
        flush=True,
    )
    return delay


def _get_rss_items(source: str, url: str) -> list[dict[str, Any]]:
    response = requests.get(
        url,
        headers={"User-Agent": "Gagarin-News-Monitor/1.0 (+public RSS reader)", "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    root = ET.fromstring(response.content)
    items: list[dict[str, Any]] = []
    for node in root.iter():
        tag = node.tag.rsplit("}", 1)[-1].lower()
        if tag != "item" and tag != "entry":
            continue
        fields: dict[str, str] = {}
        for child in list(node):
            name = child.tag.rsplit("}", 1)[-1].lower()
            if name == "link":
                value = child.attrib.get("href") or (child.text or "")
            else:
                value = child.text or ""
            if value:
                fields[name] = value.strip()
        title = fields.get("title", "")
        link = fields.get("link", "")
        published = fields.get("pubdate") or fields.get("published") or fields.get("updated") or fields.get("date")
        parsed = _parse_datetime(published)
        if title and link and parsed:
            items.append({"source": source, "title": title, "url": link, "published_at": parsed.isoformat()})
    return items


def _get_gdelt_items() -> list[dict[str, Any]]:
    response = requests.get(
        GDELT_URL,
        params={
            "query": GDELT_QUERY,
            "mode": "ArtList",
            "format": "json",
            "sort": "DateDesc",
            "maxrecords": 50,
            "timespan": "15min",
        },
        headers={"User-Agent": "Gagarin-News-Monitor/1.0"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    items: list[dict[str, Any]] = []
    for row in payload.get("articles", []):
        title = str(row.get("title") or "").strip()
        url = str(row.get("url") or "").strip()
        published = _parse_datetime(row.get("seendate") or row.get("datetime"))
        if title and url and published:
            items.append({
                "source": str(row.get("domain") or "GDELT"),
                "title": title,
                "url": url,
                "published_at": published.isoformat(),
            })
    return items


def fetch_news_items() -> list[dict[str, Any]]:
    """Fetch public news feeds with per-source cooldowns and rate-limit protection."""
    items: list[dict[str, Any]] = []
    for source, url in RSS_FEEDS:
        # EIA is a low-frequency release feed; do not poll it more than every 5 minutes.
        min_interval = 300 if source == "EIA" else 0
        if not _source_allowed(source, min_interval=min_interval):
            continue
        try:
            source_items = _get_rss_items(source, url)
            _source_succeeded(source)
            items.extend(source_items)
        except Exception as exc:
            _source_failed(source, exc)

    # GDELT was returning timeouts/429s; limit healthy polling to once per 5 minutes.
    if _source_allowed("GDELT", min_interval=GDELT_MIN_INTERVAL_SECONDS):
        try:
            gdelt_items = _get_gdelt_items()
            _source_succeeded("GDELT")
            items.extend(gdelt_items)
        except Exception as exc:
            _source_failed("GDELT", exc)

    # Newest first; source duplicates are handled below. Other feeds remain usable
    # when one provider is cooling down or unavailable.
    items.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    return items


def classify_event(title: str) -> dict[str, Any]:
    """Heuristic event mapping. It is interpretation, never a fact or trade by itself."""
    text = " ".join((title or "").lower().split())
    has_oil = any(term in text for term in OIL_TERMS)
    has_metals = any(term in text for term in METAL_TERMS) or any(term in text for term in {"gold", "oro", "xau"})
    has_macro = any(term in text for term in MACRO_TERMS)
    has_agri = any(term in text for term in AGRI_TERMS)

    assets: list[str] = []
    if has_oil:
        assets.extend(["WTI", "Brent"])
    if has_metals or has_macro:
        # Match the configured commodity universe: silver and palladium are not enabled here.
        assets.extend(["Oro", "Platino"])
    if has_agri:
        for asset, terms in {
            "Caffè": {"coffee", "arabica", "robusta", "caffè", "caffe"},
            "Cacao": {"cocoa", "cacao"},
            "Riso": {"rice", "riso"},
            "Zucchero": {"sugar", "zucchero"},
        }.items():
            if any(term in text for term in terms):
                assets.append(asset)
    assets = list(dict.fromkeys(assets))

    if not assets:
        return {"relevant": False, "assets": [], "impact": {}, "reason": "no commodity exposure keywords"}

    impact: dict[str, str] = {}
    matched_terms: dict[str, dict[str, list[str]]] = {}
    for asset in assets:
        if asset in {"WTI", "Brent"}:
            up_terms, down_terms = OIL_BULLISH_TERMS, OIL_BEARISH_TERMS
        elif asset in {"Caffè", "Cacao", "Riso", "Zucchero"}:
            up_terms, down_terms = AGRI_BULLISH_TERMS, AGRI_BEARISH_TERMS
        else:
            up_terms, down_terms = METAL_BULLISH_TERMS, METAL_BEARISH_TERMS
        up_hits = sorted(term for term in up_terms if term in text)
        down_hits = sorted(term for term in down_terms if term in text)
        matched_terms[asset] = {"bullish": up_hits, "bearish": down_hits}
        if up_hits and down_hits:
            impact[asset] = "MISTA"
        elif up_hits:
            impact[asset] = "RIALZISTA"
        elif down_hits:
            impact[asset] = "RIBASSISTA"
        else:
            impact[asset] = "MISTA"
    directional = [value for value in impact.values() if value != "MISTA"]
    if directional:
        # Confidence is a transparent heuristic, not a calibrated probability.
        strength = max(len(hits["bullish"]) + len(hits["bearish"]) for hits in matched_terms.values())
        confidence = min(75, 35 + 10 * max(0, strength - 1))
    else:
        confidence = 20
    return {
        "relevant": True,
        "assets": assets,
        "impact": impact,
        "matched_terms": matched_terms,
        "confidence_score": confidence,
        "political_intelligence": classify_public_intelligence(title),
        "historical_action_reaction": build_action_reaction_record(
            {"title": title, "domains": classify_public_intelligence(title).get("domains", [])},
            title,
        ),
        "sputnik_watch_candidates": catalyst_watchlist([{
            "source": "GAGARIN_NEWS",
            "event_id": hashlib.sha256(title.encode("utf-8")).hexdigest()[:16],
            "domains": classify_public_intelligence(title).get("domains", []),
            "evidence": "PUBLIC_NEWS_HEADLINE",
        }]),
        "reason": "keyword heuristic; not a calibrated probability; historical analogues are descriptive; watch candidates require live price confirmation",
    }


def _asset_matches(asset: str, state: Any) -> bool:
    name = str(getattr(state, "commodity", "") or "").lower()
    symbol = str(getattr(state, "symbol", "") or "").upper()
    if asset == "WTI":
        return "wti" in name or "WTI" in symbol or symbol in {"WTI/USD", "USOIL"}
    if asset == "Brent":
        return "brent" in name or "BRENT" in symbol or symbol in {"BRENT/USD", "UKOIL"}
    if asset == "Oro":
        return "oro" in name or "gold" in name or "XAU" in symbol
    if asset == "Platino":
        return "platino" in name or "platinum" in name or "XPT" in symbol
    if asset == "Caffè":
        return "caff" in name or "coffee" in name
    if asset == "Cacao":
        return "cacao" in name or "cocoa" in name
    if asset == "Riso":
        return "riso" in name or "rice" in name
    if asset == "Zucchero":
        return "zucchero" in name or "sugar" in name
    return False


def _capture_baseline(event: dict[str, Any], states: list[Any]) -> dict[str, float]:
    """Capture live prices at first analysis after the news; no retrospective attribution."""
    baseline: dict[str, float] = {}
    for asset in event.get("assets") or classify_event(event.get("title", ""))["assets"]:
        for state in states:
            if not _asset_matches(asset, state) or not bool(getattr(state, "live", False)):
                continue
            try:
                value = float(getattr(state, "price", None))
            except (TypeError, ValueError):
                continue
            if value > 0:
                baseline[asset] = value
                break
    return baseline


def _confirmed_setups(event: dict[str, Any], states: list[Any]) -> list[dict[str, Any]]:
    """Require a live Gagarin trigger and measurable price movement after news detection."""
    classified = classify_event(event.get("title", ""))
    baselines = event.get("baseline_prices") or {}
    min_reaction_pct = max(0.0, float(os.getenv("GAGARIN_NEWS_MIN_REACTION_PCT", "0.05")))
    setups: list[dict[str, Any]] = []
    for asset in classified["assets"]:
        impact = classified["impact"].get(asset, "MISTA")
        if impact == "MISTA":
            continue
        try:
            baseline = float(baselines.get(asset))
        except (TypeError, ValueError):
            continue
        if baseline <= 0:
            continue
        expected_direction = "LONG" if impact == "RIALZISTA" else "SHORT"
        for state in states:
            if not _asset_matches(asset, state):
                continue
            direction = str(getattr(state, "setup_direction", "") or "").upper()
            decision = str(getattr(state, "final_decision", "") or "").upper()
            if direction != expected_direction:
                continue
            if not bool(getattr(state, "trigger_confirmed", False)):
                continue
            if not bool(getattr(state, "live", False)):
                continue
            if decision not in {"ENTRY", "PAPER_ENTRY", "PAPER_SIGNAL"}:
                continue
            price = getattr(state, "price", None)
            entry = getattr(state, "entry", None)
            stop = getattr(state, "stop", None)
            tp1 = getattr(state, "tp1", None)
            price_source = str(getattr(state, "data_source", "") or getattr(state, "provider", "")).strip()
            if not price_source or price_source.upper() in {"UNKNOWN", "N/A", "NONE"}:
                continue
            if any(v is None for v in (price, entry, stop, tp1)):
                continue
            try:
                price_value = float(price)
            except (TypeError, ValueError):
                continue
            move_pct = (price_value / baseline - 1.0) * 100.0
            if impact == "RIALZISTA" and move_pct < min_reaction_pct:
                continue
            if impact == "RIBASSISTA" and move_pct > -min_reaction_pct:
                continue
            setups.append({
                "asset": asset,
                "impact": impact,
                "state": state,
                "direction": direction,
                "price": price,
                "entry": entry,
                "stop": stop,
                "tp1": tp1,
                "tp2": getattr(state, "tp2", None),
                "price_source": price_source,
                "move_pct": move_pct,
            })
    return setups


def _format_news_alert(event: dict[str, Any], setup: dict[str, Any]) -> str:
    published = event.get("published_at") or "timestamp non disponibile"
    return (
        "🛰 GAGARIN — NEWS → IMPATTO → SETUP → CONFERMA\n"
        "🧪 PAPER/DEMO — NESSUN ORDINE\n\n"
        f"NEWS: {event.get('title', '')}\n"
        f"Fonte: {event.get('source', 'N/D')}\n"
        f"Pubblicazione UTC: {published}\n"
        f"Rilevata UTC: {event.get('first_seen_at', 'N/D')}\n"
        f"Link: {event.get('url', '')}\n\n"
        f"Strumento: {setup['asset']}\n"
        f"Impatto ipotizzato: {setup['impact']}\n"
        f"Reazione dal rilevamento: {float(setup.get('move_pct', 0.0)):+.3f}%\n"
        f"Setup Gagarin: {setup['direction']} — TRIGGER CONFERMATO\n"
        f"Feed prezzo Gagarin: {setup.get('price_source', 'N/D')}\n"
        f"Prezzo: {float(setup['price']):.6g}\n"
        f"Entry indicativa: {float(setup['entry']):.6g}\n"
        f"SL: {float(setup['stop']):.6g}\n"
        f"TP1: {float(setup['tp1']):.6g}"
        + (f" | TP2: {float(setup['tp2']):.6g}" if setup.get("tp2") is not None else "")
        + "\n\nImpatto e direzione sono ipotesi. I livelli usano il feed Gagarin, non quotazioni CFD Trading 212; l'alert non invia ordini."
    )


def _load_state() -> dict[str, Any]:
    try:
        payload = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload.setdefault("seen", [])
            payload.setdefault("clusters", [])
            payload.setdefault("pending", [])
            payload.setdefault("last_analysis_at", 0)
            payload.setdefault("initialized", False)
            return payload
    except (OSError, json.JSONDecodeError):
        pass
    return {"seen": [], "clusters": [], "pending": [], "last_analysis_at": 0, "initialized": False}


def _save_state(state: dict[str, Any]) -> None:
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = STATE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(STATE_PATH)
    except OSError as exc:
        print(f"NEWS state save failed | {type(exc).__name__}: {exc}", flush=True)


def poll_news_once(
    send_telegram: Callable[[str], bool],
    run_analysis: Callable[[], Any],
    fetcher: Callable[[], list[dict[str, Any]]] = fetch_news_items,
    now: datetime | None = None,
) -> dict[str, int]:
    """One polling pass; immediate analysis on new news, then 5-minute rechecks."""
    now = (now or _utc_now()).astimezone(timezone.utc)
    state = _load_state()
    seen = set(state.get("seen", []))
    clusters = set(state.get("clusters", []))
    pending = list(state.get("pending", []))
    fetched = fetcher()
    new_relevant: list[dict[str, Any]] = []
    fresh_cutoff = now - timedelta(minutes=60)
    initialized = bool(state.get("initialized", False))
    bootstrap_cutoff = now - timedelta(minutes=3)

    for item in fetched:
        published = _parse_datetime(item.get("published_at"))
        if published is None or published < fresh_cutoff or published > now + timedelta(minutes=2):
            continue
        fp = _fingerprint(item)
        cluster = _title_cluster(item)
        if fp in seen or cluster in clusters:
            continue
        # On first successful poll, seed existing headlines without firing stale alerts.
        # Only items published in the last three minutes are eligible for immediate handling.
        if not initialized and published < bootstrap_cutoff:
            seen.add(fp)
            clusters.add(cluster)
            continue
        seen.add(fp)
        clusters.add(cluster)
        classified = classify_event(str(item.get("title") or ""))
        if not classified["relevant"]:
            continue
        event = dict(item)
        event["event_id"] = fp
        event["impact"] = classified["impact"]
        event["assets"] = classified["assets"]
        event["first_seen_at"] = now.isoformat()
        event["expires_at"] = (now + timedelta(seconds=PENDING_TTL_SECONDS)).isoformat()
        _journal({
            "kind": "NEWS_DETECTED",
            "event_id": fp,
            "title": event.get("title"),
            "source": event.get("source"),
            "url": event.get("url"),
            "published_at": event.get("published_at"),
            "first_seen_at": event.get("first_seen_at"),
            "assets": event.get("assets"),
            "impact": event.get("impact"),
            "political_intelligence": classified.get("political_intelligence"),
            "historical_action_reaction": classified.get("historical_action_reaction"),
            "sputnik_watch_candidates": classified.get("sputnik_watch_candidates"),
            "classification_reason": classified.get("reason"),
        })
        pending.append(event)
        new_relevant.append(event)

    if fetched:
        state["initialized"] = True

    # Expire pending items after 45 minutes to avoid stale headlines.
    valid_pending = []
    for event in pending:
        expires = _parse_datetime(event.get("expires_at"))
        if expires and expires > now:
            valid_pending.append(event)
    pending = valid_pending

    should_analyze = bool(new_relevant)
    last_analysis = float(state.get("last_analysis_at") or 0)
    if pending and not should_analyze and now.timestamp() - last_analysis >= RECHECK_SECONDS:
        should_analyze = True

    sent = 0
    if should_analyze:
        try:
            raw_results = run_analysis()
            states = list(raw_results or [])
            state["last_analysis_at"] = now.timestamp()
            still_pending = []
            for event in pending:
                # Capture a baseline at the first analysis after detection.
                # Later checks require a measurable move aligned with the news bias.
                if not event.get("baseline_prices"):
                    baseline = _capture_baseline(event, states)
                    if baseline:
                        event["baseline_prices"] = baseline
                        event["baseline_at"] = now.isoformat()
                        _journal({
                            "kind": "NEWS_BASELINE",
                            "event_id": event.get("event_id"),
                            "title": event.get("title"),
                            "baseline_at": event.get("baseline_at"),
                            "baseline_prices": baseline,
                        })
                    else:
                        _journal({
                            "kind": "NEWS_BASELINE_MISSING",
                            "event_id": event.get("event_id"),
                            "title": event.get("title"),
                            "reason": "no live matching commodity price",
                        })
                    still_pending.append(event)
                    continue
                matches = _confirmed_setups(event, states)
                classified = classify_event(event.get("title", ""))
                for asset in classified.get("assets", []):
                    baseline_value = (event.get("baseline_prices") or {}).get(asset)
                    for observed in states:
                        if not _asset_matches(asset, observed) or not bool(getattr(observed, "live", False)):
                            continue
                        try:
                            current_price = float(getattr(observed, "price", None))
                            baseline_price = float(baseline_value)
                            move_pct = (current_price / baseline_price - 1.0) * 100.0
                        except (TypeError, ValueError, ZeroDivisionError):
                            continue
                        _journal({
                            "kind": "NEWS_REACTION",
                            "event_id": event.get("event_id"),
                            "title": event.get("title"),
                            "asset": asset,
                            "impact": classified.get("impact", {}).get(asset, "MISTA"),
                            "baseline_at": event.get("baseline_at"),
                            "observed_at": now.isoformat(),
                            "baseline_price": baseline_price,
                            "current_price": current_price,
                            "move_pct": round(move_pct, 6),
                            "direction": getattr(observed, "setup_direction", None),
                            "final_decision": getattr(observed, "final_decision", None),
                            "trigger_confirmed": bool(getattr(observed, "trigger_confirmed", False)),
                            "probability_score": getattr(observed, "probability", None),
                            "quality_score": getattr(observed, "quality", None),
                            "confidence_score": getattr(observed, "confidence", None),
                            "price_source": getattr(observed, "data_source", None) or getattr(observed, "provider", None),
                            "aligned_setup_count": len(matches),
                        })
                        break
                delivered = False
                for setup in matches:
                    if send_telegram(_format_news_alert(event, setup)):
                        sent += 1
                        delivered = True
                        _journal({
                            "kind": "NEWS_ALERT_SENT",
                            "event_id": event.get("event_id"),
                            "title": event.get("title"),
                            "asset": setup.get("asset"),
                            "impact": setup.get("impact"),
                            "direction": setup.get("direction"),
                            "move_pct": setup.get("move_pct"),
                            "price": setup.get("price"),
                            "price_source": setup.get("price_source"),
                            "entry": setup.get("entry"),
                            "stop": setup.get("stop"),
                            "tp1": setup.get("tp1"),
                        })
                        break
                if not delivered:
                    still_pending.append(event)
            pending = still_pending
        except Exception as exc:
            print(f"NEWS event analysis failed | {type(exc).__name__}: {exc}", flush=True)

    # Bound state size. Fingerprints and clusters are separate to dedupe URLs and syndication.
    state["seen"] = list(seen)[-1500:]
    state["clusters"] = list(clusters)[-1500:]
    state["pending"] = pending[-100:]
    _save_state(state)
    print(
        f"NEWS poll | fetched={len(fetched)} | new_relevant={len(new_relevant)} | "
        f"pending={len(pending)} | analysis={'YES' if should_analyze else 'NO'} | alerts={sent}",
        flush=True,
    )
    return {"fetched": len(fetched), "new_relevant": len(new_relevant), "pending": len(pending), "alerts": sent, "analysis": int(should_analyze)}


def news_monitor_loop(
    send_telegram: Callable[[str], bool],
    run_analysis: Callable[[], Any],
) -> None:
    print(
        f"GAGARIN NEWS monitor started | poll={POLL_SECONDS}s | "
        f"recheck={RECHECK_SECONDS}s | PAPER/DEMO",
        flush=True,
    )
    while True:
        started = time.monotonic()
        try:
            poll_news_once(send_telegram, run_analysis)
        except Exception as exc:
            print(f"NEWS monitor error | {type(exc).__name__}: {exc}", flush=True)
        elapsed = time.monotonic() - started
        time.sleep(max(1, POLL_SECONDS - elapsed))
