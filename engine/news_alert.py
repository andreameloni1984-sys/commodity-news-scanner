"""Transparent, rule-based news-to-commodity impact desk.

This is a heuristic research aid, not a live news feed or trading signal.
It never authorizes entries and deliberately labels ambiguous catalysts as mixed.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

ROME = ZoneInfo("Europe/Rome")

_RULES = [
    (("sanzion", "sanction", "embargo", "blocco export", "export ban"), [
        ("Petrolio WTI", "MISTA", "Possibile rischio di offerta; dipende da paese, volumi e applicazione."),
        ("Petrolio Brent", "MISTA", "Possibile rischio di offerta globale; verificare flussi e reazione del prezzo."),
        ("Oro", "MISTA", "Possibile domanda difensiva, ma dollaro e tassi possono prevalere."),
    ]),
    (("dazi", "tariff", "guerra commerciale", "trade war"), [
        ("Oro", "MISTA", "Rifugio possibile, ma dollaro e aspettative sui tassi possono contrastarlo."),
        ("Argento", "MISTA", "Domanda difensiva contro rischio di rallentamento industriale."),
        ("Petrolio WTI", "MISTA", "Domanda attesa e rischio geopolitico possono spingere in direzioni opposte."),
        ("Petrolio Brent", "MISTA", "Domanda globale e rischio di offerta possono compensarsi."),
    ]),
    (("guerra", "attacco", "escalation", "missile", "stretto di hormuz", "middle east"), [
        ("Petrolio WTI", "MISTA", "Premio geopolitico possibile se l'offerta o i trasporti sono minacciati."),
        ("Petrolio Brent", "MISTA", "Sensibile al rischio di offerta internazionale e rotte marittime."),
        ("Oro", "MISTA", "Possibile domanda difensiva; confermare con dollaro, tassi e prezzo."),
    ]),
    (("opec", "aumento produzione", "production increase", "output hike"), [
        ("Petrolio WTI", "POTENZIALMENTE RIBASSISTA", "Maggiore offerta attesa, se l'aumento è reale e non già scontato."),
        ("Petrolio Brent", "POTENZIALMENTE RIBASSISTA", "Maggiore offerta attesa, da verificare contro domanda e scorte."),
    ]),
    (("taglio produzione", "production cut", "supply cut"), [
        ("Petrolio WTI", "POTENZIALMENTE RIALZISTA", "Offerta attesa più bassa, se il taglio è credibile e rispettato."),
        ("Petrolio Brent", "POTENZIALMENTE RIALZISTA", "Offerta attesa più bassa; confermare con prezzi e dati sulle scorte."),
    ]),
    (("federal reserve", "fed ", "tassi", "interest rate", "inflazione", "inflation"), [
        ("Oro", "MISTA", "Tassi reali e dollaro sono spesso determinanti; la sola headline non basta."),
        ("Argento", "MISTA", "Sensibile a dollaro, tassi e prospettive industriali."),
    ]),
]


def analyze_headline(headline: str, source: str = "non specificata",
                     published_at: str | None = None,
                     now: datetime | None = None) -> dict[str, Any]:
    """Map a user-provided headline to transparent candidate exposures."""
    text = " ".join(str(headline or "").split())
    lower = text.casefold()
    matched = []
    seen = set()
    for keywords, impacts in _RULES:
        if any(k in lower for k in keywords):
            for commodity, bias, rationale in impacts:
                key = (commodity, bias)
                if key not in seen:
                    seen.add(key)
                    matched.append({"commodity": commodity, "bias": bias, "rationale": rationale})
    now = (now or datetime.now(ROME)).astimezone(ROME)
    return {
        "headline": text,
        "source": str(source or "non specificata").strip()[:200],
        "published_at": str(published_at or "non indicata").strip()[:100],
        "analyzed_at": now.strftime("%d/%m/%Y %H:%M %Z"),
        "matched": matched,
        "matched_rules": bool(matched),
        "status": "IPOTESI DA CONFERMARE" if matched else "NESSUNA REGOLA SPECIFICA TROVATA",
    }


def format_news_alert(result: dict[str, Any]) -> str:
    lines = [
        "📰 GAGARIN — NEWS IMPACT DESK",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "SOLO ANALISI | NESSUN ORDINE",
        f"Notizia: {result.get('headline') or '(vuota)'}",
        f"Fonte: {result.get('source', 'non specificata')}",
        f"Pubblicata: {result.get('published_at', 'non indicata')}",
        f"Analizzata: {result.get('analyzed_at', 'non disponibile')}",
        f"Stato: {result.get('status', 'NON VERIFICATO')}",
        "",
    ]
    matched = result.get("matched") or []
    if not matched:
        lines.append("Nessuna esposizione mappata dalle regole attuali. Non dedurre assenza di impatto.")
    else:
        lines.append("STRUMENTI DA OSSERVARE (non sono segnali di trading):")
        for item in matched:
            lines.append(f"• {item['commodity']} — {item['bias']}")
            lines.append(f"  Motivo: {item['rationale']}")
    lines.extend([
        "",
        "PROSSIMO PASSO: verificare fonte primaria, ora della notizia e prezzo/volume.",
        "Una notizia non autorizza un ingresso: servono setup e trigger Gagarin coerenti.",
        "Direzione e impatto sono euristiche, non probabilità calibrate.",
        "Modulo sperimentale; nessun cambiamento a ranking, soglie, rischio o esecuzione. PAPER/DEMO ONLY.",
    ])
    return "\n".join(lines)
