"""Bridge SPUTNIK (trump-trucker) → sezione Invest.

Legge lo stato pubblico di SPUTNIK e converte i catalizzatori
in segnali paper per la sezione Invest.
Nessun ordine. Solo osservazione e ranking.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.request import urlopen, Request

SPUTNIK_STATE_URL = (
    "https://raw.githubusercontent.com/andreameloni1984-sys/"
    "trump-trucker/main/sputnik_state.json"
)

# Mappa domini SPUTNIK → ticker Invest (Trading 212 style)
DOMAIN_TO_INVEST = {
    "AI_TECH": ["QQQ", "NVDA", "MSFT", "AAPL"],
    "ENERGY": ["SPY"],  # proxy; commodities restano nel desk principale
    "DEFENSE": ["SPY"],
    "MEDIA": ["SPY"],
    "REAL_ESTATE": ["SPY"],
    "SPACE": ["SPY"],
    "METALS": ["SPY"],
    "CRYPTO": ["SPY"],
}

def fetch_sputnik_state(timeout: int = 10) -> Optional[dict[str, Any]]:
    """Scarica lo stato pubblico di SPUTNIK. Ritorna None se fallisce."""
    try:
        req = Request(SPUTNIK_STATE_URL, headers={"User-Agent": "SOYUZ-GAGARIN"})
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None

def extract_active_domains(state: dict[str, Any], hours: int = 72) -> list[dict[str, Any]]:
    """Estrae i domini attivi dalle ultime N ore di intelligence_history."""
    history = state.get("intelligence_history") or {}
    if not isinstance(history, dict):
        return []

    cutoff = datetime.now(timezone.utc).timestamp() - hours * 3600
    active = []

    for event_id, event in history.items():
        if not isinstance(event, dict):
            continue
        detected = event.get("detected_at")
        if not detected:
            continue
        try:
            ts = datetime.fromisoformat(detected.replace("Z", "+00:00")).timestamp()
        except ValueError:
            continue
        if ts < cutoff:
            continue

        domains = event.get("domains") or []
        source = event.get("source", "UNKNOWN")
        for domain in domains:
            active.append({
                "domain": str(domain).upper(),
                "source": source,
                "event_id": event_id,
                "detected_at": detected,
                "evidence": event.get("evidence", "PUBLIC_SOURCE_TEXT"),
            })

    return active

def sputnik_to_invest_signals(state: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    """Converte i catalizzatori SPUTNIK in segnali Invest paper."""
    if state is None:
        state = fetch_sputnik_state()
    if not state:
        return []

    active = extract_active_domains(state, hours=72)
    if not active:
        return []

    # Conta occorrenze per dominio
    domain_count: dict[str, int] = {}
    domain_sources: dict[str, set] = {}
    for item in active:
        d = item["domain"]
        domain_count[d] = domain_count.get(d, 0) + 1
        domain_sources.setdefault(d, set()).add(item["source"])

    signals = []
    seen_tickers = set()

    for domain, count in sorted(domain_count.items(), key=lambda x: -x[1]):
        tickers = DOMAIN_TO_INVEST.get(domain, [])
        primary = "WHITE_HOUSE" in domain_sources.get(domain, set()) or "OGE" in domain_sources.get(domain, set())
        score = min(100, 40 + (15 if primary else 0) + min(30, count * 5))

        for ticker in tickers:
            if ticker in seen_tickers:
                continue
            seen_tickers.add(ticker)
            signals.append({
                "name": ticker,
                "ticker": f"{ticker}_US_EQ",
                "symbol": ticker,
                "direction": "WATCH",
                "score": score,
                "price": None,
                "reason": f"SPUTNIK {domain} ({count} eventi recenti, fonti: {', '.join(sorted(domain_sources.get(domain, [])))}). Paper only.",
                "source": "SPUTNIK",
                "domain": domain,
            })

    signals.sort(key=lambda s: s["score"], reverse=True)
    return signals[:8]
