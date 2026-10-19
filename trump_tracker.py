"""SPUTNIK v4 — public filing intelligence engine.

SPUTNIK is deliberately separate from GAGARIN.
It monitors only publicly documented SEC filings configured through CIKs,
normalizes and deduplicates events, tracks filing timing, and sends
informational Telegram alerts. It does not place trades or infer private activity.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sputnik_action_reaction import build_action_reaction_record
from sputnik_public_sources import parse_public_feed

SEC_SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik}.json"
STATE_FILE = Path(os.getenv("SPUTNIK_STATE_FILE", "sputnik_state.json"))
MAX_STATE_EVENTS = 5000
TELEGRAM_POLL_TIMEOUT = int(os.getenv("SPUTNIK_TELEGRAM_POLL_TIMEOUT", "20"))
TELEGRAM_HTTP_TIMEOUT = int(os.getenv("SPUTNIK_TELEGRAM_HTTP_TIMEOUT", "35"))
TELEGRAM_LISTEN_SECONDS = int(os.getenv("SPUTNIK_TELEGRAM_LISTEN_SECONDS", "240"))


@dataclass
class FilingEvent:
    source: str
    cik: str
    accession: str
    form: str
    filed_at: str
    primary_document: str
    company: str
    source_url: str
    event_id: str
    evidence: str = "PRIMARY_DOCUMENT"
    status: str = "CONFIRMED"
    transaction_type: str = "DISCLOSURE_ONLY"


@dataclass
class TransactionRecord:
    event_id: str
    cik: str
    company: str
    form: str
    action: str
    security: str
    shares: str = ""
    price: str = ""
    transaction_date: str = ""
    reporting_owner: str = ""
    source_url: str = ""
    evidence: str = "PRIMARY_DOCUMENT"
    status: str = "CONFIRMED"
    transaction_code: str = ""
    filing_date: str = ""
    source_kind: str = "FORM4_TRANSACTION"


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def xml_text(node: Any, name: str) -> str:
    for child in node.iter():
        if local_name(str(child.tag)) != name:
            continue
        value = (child.text or "").strip()
        if value:
            return value
        # SEC ownership XML commonly stores the actual value in a nested
        # <value> element inside fields such as securityTitle/transactionDate.
        nested = " ".join(
            (part.text or "").strip()
            for part in child.iter()
            if part is not child and (part.text or "").strip()
        ).strip()
        if nested:
            return nested
    return ""


def fetch_public_document(url: str, user_agent: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/xml,text/xml,text/html,application/xhtml+xml,text/plain",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def _form4_xml_urls(event: FilingEvent, user_agent: str) -> list[str]:
    """Return verified XML candidates for a Form 3/4/5 filing.
    
    SEC submissions can expose an HTML primary document while the structured
    transaction data is stored in a sibling XML document. Never treat the HTML
    filing page as XML; discover the sibling from the SEC filing index.
    """
    candidates: list[str] = []
    if str(event.primary_document).lower().endswith(".xml"):
        candidates.append(event.source_url)
    index_url = (
        f"https://www.sec.gov/Archives/edgar/data/"
        f"{int(event.cik)}/{event.accession.replace('-', '')}/index.json"
    )
    try:
        documents = filing_index_documents(event, user_agent)
        names = [
            str(item.get("name") or "")
            for item in documents
            if str(item.get("name") or "").lower().endswith(".xml")
        ]
        names.sort(key=lambda name: (name.lower() != str(event.primary_document).lower(), len(name)))
        for name in names:
            candidates.append(
                f"https://www.sec.gov/Archives/edgar/data/"
                f"{int(event.cik)}/{event.accession.replace('-', '')}/{name}"
            )
    except Exception as exc:
        print(f"SPUTNIK: Form {event.form} XML index unavailable {event.accession}: {type(exc).__name__}")
    return list(dict.fromkeys(candidates))


def extract_form4_transactions(event: FilingEvent, user_agent: str) -> list[TransactionRecord]:
    if event.form not in {"3", "4", "5"}:
        return []
    import xml.etree.ElementTree as ET
    root = None
    last_error: Exception | None = None
    for url in _form4_xml_urls(event, user_agent):
        try:
            root = ET.fromstring(fetch_public_document(url, user_agent))
            break
        except Exception as exc:
            last_error = exc
    if root is None:
        print(
            f"SPUTNIK: impossibile leggere Form {event.form} "
            f"{event.accession}: {type(last_error).__name__ if last_error else 'XML non trovato'}"
        )
        return []

    owners = []
    for node in root.iter():
        if local_name(str(node.tag)) == "rptOwnerName":
            value = (node.text or "").strip()
            if value:
                owners.append(value)
    owner = owners[0] if owners else ""

    records: list[TransactionRecord] = []
    transaction_nodes = [
        node for node in root.iter()
        if local_name(str(node.tag)) in {"nonDerivativeTransaction", "derivativeTransaction"}
    ]
    for node in transaction_nodes:
        code = xml_text(node, "transactionCode").upper()
        if code not in {"P", "S"}:
            continue
        security = xml_text(node, "securityTitle") or xml_text(node, "underlyingSecurityTitle")
        shares = xml_text(node, "transactionShares") or xml_text(node, "transactionUnits")
        price = xml_text(node, "transactionPricePerShare") or xml_text(node, "transactionPricePerUnit")
        date = xml_text(node, "transactionDate")
        action = "ACQUISTATO" if code == "P" else "VENDUTO"
        records.append(
            TransactionRecord(
                event_id=event.event_id,
                cik=event.cik,
                company=event.company,
                form=event.form,
                action=action,
                security=security or "Titolo non specificato",
                shares=shares,
                price=price,
                transaction_date=date,
                reporting_owner=owner,
                source_url=event.source_url,
                transaction_code=code,
                filing_date=event.filed_at,
                source_kind="FORM4_TRANSACTION",
            )
        )
    return records


def filing_index_documents(event: FilingEvent, user_agent: str) -> list[dict[str, Any]]:
    index_url = (
        f"https://www.sec.gov/Archives/edgar/data/"
        f"{int(event.cik)}/{event.accession.replace('-', '')}/index.json"
    )
    try:
        payload = json.loads(fetch_public_document(index_url, user_agent).decode("utf-8"))
        return list((payload.get("directory") or {}).get("item") or [])
    except Exception as exc:
        print(f"SPUTNIK: SEC index non disponibile {event.accession}: {type(exc).__name__}")
        return []


def extract_13f_positions(event: FilingEvent, user_agent: str) -> list[TransactionRecord]:
    if event.form not in {"13F-HR", "13F-HR/A"}:
        return []

    documents = filing_index_documents(event, user_agent)
    candidates = [
        str(item.get("name") or "")
        for item in documents
        if str(item.get("name") or "").lower().endswith((".xml", ".txt"))
    ]
    candidates.sort(key=lambda name: ("infotable" not in name.lower(), len(name)))

    for name in candidates:
        url = (
            f"https://www.sec.gov/Archives/edgar/data/"
            f"{int(event.cik)}/{event.accession.replace('-', '')}/{name}"
        )
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(fetch_public_document(url, user_agent))
        except Exception:
            continue

        if not any(local_name(str(node.tag)) == "infoTable" for node in root.iter()):
            continue

        records: list[TransactionRecord] = []
        for node in root.iter():
            if local_name(str(node.tag)) != "infoTable":
                continue
            issuer = xml_text(node, "nameOfIssuer")
            class_name = xml_text(node, "titleOfClass")
            cusip = xml_text(node, "cusip")
            value = xml_text(node, "value")
            shares = xml_text(node, "sshPrnamt")
            security = " ".join(x for x in [issuer, class_name] if x).strip()
            if not security:
                continue
            records.append(
                TransactionRecord(
                    event_id=event.event_id,
                    cik=event.cik,
                    company=event.company,
                    form=event.form,
                    action="POSIZIONE_DICHIARATA",
                    security=security,
                    shares=shares,
                    price=value,
                    transaction_date=event.filed_at,
                    reporting_owner=event.company,
                    source_url=url,
                    evidence="PRIMARY_13F_INFORMATION_TABLE",
                    status="CONFIRMED_POSITION",
                    transaction_code="13F",
                    filing_date=event.filed_at,
                    source_kind="13F_POSITION",
                )
            )
        return records

    return []


def extract_transactions(events: list[FilingEvent]) -> list[TransactionRecord]:
    user_agent = os.getenv(
        "SEC_USER_AGENT",
        "SPUTNIK document monitor / contact not configured",
    )
    records: list[TransactionRecord] = []
    for event in events:
        records.extend(extract_form4_transactions(event, user_agent))
        records.extend(extract_13f_positions(event, user_agent))
    return records


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
    def handle_data(self, data: str) -> None:
        text = re.sub(r"\s+", " ", data).strip()
        if text:
            self.parts.append(text)

    def text(self) -> str:
        return " ".join(self.parts)


INTELLIGENCE_SOURCES = {
    "WHITE_HOUSE": "https://www.whitehouse.gov/",
    "TRUTH_ARCHIVE": "https://www.trumpstruth.org/",
    "OGE": "https://www.oge.gov/",
}

ASSET_KEYWORDS = {
    "ENERGY": ["oil", "crude", "brent", "wti", "natural gas", "lng", "energy", "petroleum"],
    "METALS": ["gold", "silver", "copper", "aluminum", "steel", "uranium"],
    "AGRICULTURE": ["corn", "wheat", "soybean", "sugar", "coffee", "cocoa", "cotton"],
    "DEFENSE": ["defense", "drone", "missile", "military", "aerospace", "weapons"],
    "AI_TECH": ["artificial intelligence", "ai", "semiconductor", "chip", "data center", "cloud"],
    "SPACE": ["spacex", "rocket", "satellite", "space"],
    "CRYPTO": ["bitcoin", "ethereum", "crypto", "digital asset", "stablecoin"],
    "MEDIA": ["truth social", "truth", "media", "streaming"],
    "REAL_ESTATE": ["real estate", "property", "hotel", "resort"],
    # Political and macro catalysts need their own labels; otherwise a tariff
    # headline with no commodity keyword is silently discarded.
    "TRADE_POLICY": ["tariff", "tariffs", "trade deal", "trade agreement", "export control", "import duty", "sanction", "sanctions", "dazi", "accordo commerciale"],
    "RATES_MACRO": ["federal reserve", "interest rate", "interest rates", "treasury yield", "inflation", "policy rate", "dollar", "dollaro"],
}

def fetch_public_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": os.getenv("SEC_USER_AGENT", "SPUTNIK/4.0 public-source-monitor"),
            "Accept": "text/html,application/xhtml+xml,text/plain",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        raw = response.read()
    parser = TextExtractor()
    parser.feed(raw.decode("utf-8", errors="replace"))
    return parser.text()

def _domains_for_public_text(text: str) -> list[str]:
    normalized = str(text or "").lower()
    return [
        domain for domain, keywords in ASSET_KEYWORDS.items()
        if any(keyword in normalized for keyword in keywords)
    ]


def fetch_public_feed(url: str) -> bytes:
    """Fetch a public RSS/Atom feed without requiring third-party packages."""
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": os.getenv("SEC_USER_AGENT", "SPUTNIK/4.1 public-feed-monitor"),
            "Accept": "application/rss+xml,application/atom+xml,application/xml,text/xml,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read()


def _configured_rss_feeds() -> list[str]:
    raw = os.getenv("SPUTNIK_RSS_FEEDS", "").strip()
    if raw:
        return list(dict.fromkeys(url.strip() for url in raw.split(";") if url.strip()))
    # Official White House feed: item-level title, date, URL and summary.
    return ["https://www.whitehouse.gov/feed/"]


def intelligence_snapshot(state: dict[str, Any]) -> list[dict[str, Any]]:
    if os.getenv("SPUTNIK_SOCIAL_ENABLED", "1").strip().lower() not in {"1", "true", "yes"}:
        return []

    known = state.setdefault("intelligence", {})
    known_items = state.setdefault("intelligence_items", {})
    findings: list[dict[str, Any]] = []

    # Keep the legacy homepage scan for broad discovery, but do not treat its
    # generic page-wide keywords as an individual news event.
    for source, url in INTELLIGENCE_SOURCES.items():
        try:
            body = fetch_public_text(url)
        except Exception as exc:
            print(f"SPUTNIK: source {source} unavailable: {type(exc).__name__}")
            continue

        digest = hashlib.sha256((source + "|" + body[:200000]).encode("utf-8")).hexdigest()[:24]
        if known.get(source) == digest:
            continue
        known[source] = digest
        domains = _domains_for_public_text(body)
        if not domains:
            continue
        finding = {
            "source": source,
            "url": url,
            "title": "",
            "published": "",
            "domains": domains,
            "text": body[:6000],
            "evidence": "PUBLIC_SOURCE_TEXT_PAGE_LEVEL",
            "status": "POTENTIAL_CORRELATION",
            "detected_at": utc_now().isoformat(),
            "event_id": digest,
        }
        finding["action_reaction"] = build_action_reaction_record(finding, body)
        findings.append(finding)

    # Item-level feed scan: each article is deduplicated independently, so a
    # page-level digest cannot hide a new post added to an otherwise unchanged
    # archive. A feed item is a catalyst candidate, never an automatic trade.
    for feed_url in _configured_rss_feeds():
        source = "WHITE_HOUSE_RSS" if "whitehouse.gov" in feed_url.lower() else "PUBLIC_RSS"
        try:
            rows = parse_public_feed(fetch_public_feed(feed_url), feed_url)
        except Exception as exc:
            print(f"SPUTNIK: RSS feed unavailable {feed_url}: {type(exc).__name__}")
            continue

        for row in rows:
            title = str(row.get("title") or "").strip()
            body = " ".join(part for part in (title, str(row.get("text") or "").strip()) if part)
            domains = _domains_for_public_text(body)
            if not domains:
                continue
            identity = str(row.get("id") or row.get("url") or (title + "|" + str(row.get("published") or "")))
            digest = hashlib.sha256(
                (source + "|" + feed_url + "|" + identity).encode("utf-8")
            ).hexdigest()[:24]
            if digest in known_items:
                continue
            known_items[digest] = utc_now().isoformat()
            finding = {
                "source": source,
                "feed_url": feed_url,
                "url": str(row.get("url") or feed_url),
                "primary_url": str(row.get("primary_url") or ""),
                "title": title[:300],
                "published": str(row.get("published") or "")[:100],
                "domains": domains,
                "text": body[:6000],
                "evidence": "PUBLIC_RSS_ITEM",
                "status": "POTENTIAL_CORRELATION",
                "detected_at": utc_now().isoformat(),
                "event_id": digest,
            }
            finding["action_reaction"] = build_action_reaction_record(finding, body)
            findings.append(finding)

    # Bound per-item deduplication state and history to prevent unbounded growth.
    if len(known_items) > 2000:
        state["intelligence_items"] = dict(
            sorted(known_items.items(), key=lambda item: item[1], reverse=True)[:2000]
        )
    history = state.setdefault("intelligence_history", {})
    for item in findings:
        history[item["event_id"]] = item
    if len(history) > 500:
        keep = sorted(history.items(), key=lambda item: item[1].get("detected_at", ""), reverse=True)[:500]
        state["intelligence_history"] = dict(keep)
    return findings


def forward_findings_to_gagarin(findings: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Optionally send item-level public catalysts to GAGARIN for price confirmation."""
    items = [
        item for item in findings
        if item.get("evidence") == "PUBLIC_RSS_ITEM" and item.get("event_id")
    ]
    if not items:
        return None
    base_url = os.getenv("GAGARIN_CLOUD_API_URL", "").strip().rstrip("/")
    api_key = os.getenv("GAGARIN_CLOUD_API_KEY", "").strip()
    if not base_url or not api_key:
        print("SPUTNIK: GAGARIN handoff disabled; GAGARIN_CLOUD_API_URL/API_KEY not configured.")
        return None

    payload = {
        "events": [
            {
                "event_id": str(item.get("event_id") or ""),
                "title": str(item.get("title") or "")[:300],
                "url": str(item.get("url") or "")[:1000],
                "published": str(item.get("published") or "")[:100],
                "domains": list(item.get("domains") or []),
                "text": str(item.get("text") or "")[:1500],
            }
            for item in items[:20]
        ]
    }
    request = urllib.request.Request(
        base_url + "/api/sputnik/confirm",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-API-Key": api_key,
            "User-Agent": "SPUTNIK/4.1 GAGARIN-catalyst-handoff",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            result = json.loads(response.read().decode("utf-8"))
        print(
            "SPUTNIK: GAGARIN confirmation received for "
            f"{len(result.get('events') or [])} catalyst event(s); no order requested."
        )
        return result if isinstance(result, dict) else None
    except Exception as exc:
        # News collection must continue even if the optional GAGARIN endpoint is down.
        print(f"SPUTNIK: GAGARIN handoff failed: {type(exc).__name__}")
        return None


def gagarin_confirmation_message(result: dict[str, Any]) -> str:
    lines = [
        "🛰️ SPUTNIK → GAGARIN",
        "━━━━━━━━━━━━━━━━━━",
        "📊 Controllo prezzo/setup completato; nessun ordine inviato.",
    ]
    for event in (result.get("events") or [])[:5]:
        lines.append("")
        lines.append(f"📰 {event.get('title') or event.get('event_id') or 'Evento pubblico'}")
        lines.append(f"🎯 Esito: {event.get('status', 'N/D')}")
        matched = event.get("matched_instruments") or []
        if not matched:
            lines.append("⚪ Nessuno strumento corrispondente nell'universo Gagarin.")
        for row in matched[:3]:
            lines.append(
                f"• {row.get('commodity') or row.get('symbol')}: "
                f"{row.get('action', 'WAIT')} | prezzo {row.get('price', 'N/D')} | "
                f"prob. {row.get('probability', 'N/D')}"
            )
    lines.append("ℹ️ L'evento è un contesto; Gagarin mantiene il proprio filtro tecnico.")
    return "\n".join(lines)


def intelligence_message(item: dict[str, Any]) -> str:
    title = str(item.get("title") or "").strip()
    published = str(item.get("published") or "").strip()
    excerpt = re.sub(r"\s+", " ", str(item.get("text") or "")).strip()[:420]
    lines = [
        "🛰️ SPUTNIK — INTELLIGENCE",
        "━━━━━━━━━━━━━━━━━━",
        f"📡 Fonte: {item.get('source', 'N/D')}",
    ]
    if title:
        lines.append(f"📰 Evento: {title}")
    if published:
        lines.append(f"🕒 Pubblicazione: {published}")
    lines.extend([
        f"🧩 Aree citate: {', '.join(item.get('domains') or [])}",
        f"🔎 Evidenza: {item.get('evidence', 'N/D')}",
    ])
    if excerpt and not title:
        lines.append(f"📝 Testo: {excerpt}")
    lines.extend([
        "⚠️ Stato: CATALIZZATORE DA VERIFICARE",
        f"🔗 {item.get('url', '')}",
        "━━━━━━━━━━━━━━━━━━",
        "ℹ️ Il tema non è un segnale LONG/SHORT. Gagarin deve verificare prezzo, volume e struttura.",
    ])
    return "\n".join(lines)

def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def http_get_json(url: str, user_agent: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read()
    return json.loads(raw.decode("utf-8"))


def normalize_cik(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if not digits:
        raise ValueError(f"CIK non valido: {value!r}")
    return digits.zfill(10)


def load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {"events": {}, "updated_at": None}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        # Corrupted state must not crash the whole collector.
        return {"events": {}, "updated_at": None}


def save_state(state: dict[str, Any]) -> None:
    # Persist only when substantive state changed. This avoids a Git commit
    # every 5 minutes just because updated_at changed.
    current: dict[str, Any] = {}
    if STATE_FILE.exists():
        try:
            current = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            current = {}

    def comparable(value: dict[str, Any]) -> dict[str, Any]:
        copy = dict(value)
        copy.pop("updated_at", None)
        return copy

    events = state.get("events", {})
    transactions = state.get("transactions", {})
    if len(transactions) > MAX_STATE_EVENTS:
        keep_transactions = sorted(
            transactions.items(),
            key=lambda item: item[1].get("transaction_date", ""),
            reverse=True,
        )[:MAX_STATE_EVENTS]
        state["transactions"] = dict(keep_transactions)

    if len(events) > MAX_STATE_EVENTS:
        keep = sorted(
            events.items(),
            key=lambda item: item[1].get("filed_at", ""),
            reverse=True,
        )[:MAX_STATE_EVENTS]
        state["events"] = dict(keep)

    if comparable(current) == comparable(state):
        return

    state["updated_at"] = utc_now().isoformat()
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STATE_FILE)


def event_id(cik: str, accession: str, form: str, document: str) -> str:
    raw = "|".join((cik, accession, form, document))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def filing_url(cik: str, accession: str, document: str) -> str:
    accession_compact = accession.replace("-", "")
    return (
        f"https://www.sec.gov/Archives/edgar/data/"
        f"{int(cik)}/{accession_compact}/{document}"
    )


def fetch_sec_events(cik: str, user_agent: str, forms: set[str]) -> list[FilingEvent]:
    data = http_get_json(SEC_SUBMISSIONS.format(cik=cik), user_agent)
    recent = data.get("filings", {}).get("recent", {})

    fields = ["accessionNumber", "filingDate", "form", "primaryDocument"]
    if not all(field in recent for field in fields):
        raise ValueError("Formato SEC submissions inatteso: campi mancanti.")

    company = data.get("name") or f"CIK {cik}"
    events: list[FilingEvent] = []

    for accession, filed, form, document in zip(
        recent["accessionNumber"],
        recent["filingDate"],
        recent["form"],
        recent["primaryDocument"],
    ):
        if form not in forms:
            continue

        eid = event_id(cik, accession, form, document)
        events.append(
            FilingEvent(
                source="SEC_EDGAR",
                cik=cik,
                accession=accession,
                form=form,
                filed_at=filed,
                primary_document=document,
                company=company,
                source_url=filing_url(cik, accession, document),
                event_id=eid,
            )
        )

    return events


def collect() -> list[FilingEvent]:
    raw_ciks = os.getenv("SPUTNIK_CIKS", "").strip()
    if not raw_ciks:
        print("SPUTNIK: nessun CIK configurato. Impostare SPUTNIK_CIKS.")
        return []

    user_agent = os.getenv(
        "SEC_USER_AGENT",
        "SPUTNIK document monitor / contact not configured",
    )
    forms = {
        item.strip()
        for item in os.getenv(
            "SPUTNIK_SEC_FORMS",
            "3,4,5,8-K,13D,13G,13F-HR,13F-HR/A,144",
        ).split(",")
        if item.strip()
    }

    events: list[FilingEvent] = []
    for raw in raw_ciks.split(","):
        cik = normalize_cik(raw)
        try:
            events.extend(fetch_sec_events(cik, user_agent, forms))
            time.sleep(0.2)
        except Exception as exc:
            print(f"SPUTNIK: SEC source error CIK {cik}: {exc}")

    return events


def new_events(events: list[FilingEvent], state: dict[str, Any]) -> list[FilingEvent]:
    known = state.setdefault("events", {})
    fresh = []
    for event in events:
        if event.event_id in known:
            continue
        known[event.event_id] = asdict(event)
        fresh.append(event)
    return fresh



def telegram_morning_message(state: dict[str, Any]) -> str:
    """Concrete morning briefing: documented activity + historical reaction."""
    transactions = [x for x in (state.get("transactions") or {}).values() if x.get("source_kind") == "FORM4_TRANSACTION"]
    transactions.sort(key=lambda x: str(x.get("transaction_date") or ""), reverse=True)
    findings = list((state.get("intelligence_history") or {}).values())
    findings.sort(key=lambda x: str(x.get("detected_at") or ""), reverse=True)
    lines = ["🛰️ SPUTNIK — BRIEF ORE 05:00", "━━━━━━━━━━━━━━━━━━", "🎯 RISULTATO"]
    if transactions:
        lines.append("🟢 OPERAZIONI FORM 4 DOCUMENTATE")
        for tx in transactions[:5]:
            emoji = "🟢" if tx.get("action") == "ACQUISTATO" else "🔴"
            lines.append(f"{emoji} {tx.get('security') or 'Titolo N/D'} — {tx.get('action')} — {tx.get('transaction_date') or 'N/D'}")
            lines.append(f"   Soggetto filing: {tx.get('reporting_owner') or 'N/D'} | Fonte SEC")
    else:
        lines.append("⚪ Nessuna operazione Form 4 documentata nel dataset.")
    directions: dict[str, int] = {}
    latest = None
    for item in findings[:50]:
        ar = item.get("action_reaction") or {}
        for asset, direction in (ar.get("historical_directions") or {}).items():
            key = f"{asset}:{direction}"
            directions[key] = directions.get(key, 0) + 1
        if ar.get("historical_matches") and latest is None:
            latest = ar
    lines.extend(["", "🧠 AZIONE → REAZIONE STORICA"])
    if directions:
        for key, count in sorted(directions.items(), key=lambda x: x[1], reverse=True)[:6]:
            asset, direction = key.split(":", 1)
            lines.append(f"• {asset}: {direction} ({count} analoghi)")
        if latest:
            lines.append(f"• Analogo: {latest['historical_matches'][0]}")
    else:
        lines.append("⚪ Nessun analogo storico sufficientemente documentato.")
    lines.extend(["", "📌 Solo eventi pubblici e reazioni storiche documentate.", "⚠️ Non è una garanzia sul prossimo movimento."])
    return "\n".join(lines)

def telegram_transaction_message(tx: TransactionRecord) -> str:
    emoji = "🟢" if tx.action == "ACQUISTATO" else "🔴"
    return (
        f"{emoji} SPUTNIK — {tx.action} DOCUMENTATO\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🏢 {tx.company}\n"
        f"👤 Soggetto: {tx.reporting_owner or 'N/D'}\n"
        f"📌 Titolo: {tx.security}\n"
        f"📦 Quantità: {tx.shares or 'N/D'}\n"
        f"💵 Prezzo: {tx.price or 'N/D'}\n"
        f"📅 Data operazione: {tx.transaction_date or 'N/D'}\n"
        f"📄 Form: {tx.form}\n"
        "🔎 Evidenza: PRIMARY_DOCUMENT\n"
        f"🔗 {tx.source_url}\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "✅ Operazione documentata pubblicamente.\n"
        "ℹ️ La presenza nel filing non implica che la posizione sia ancora detenuta."
    )


def telegram_transactions_message(state: dict[str, Any]) -> str:
    items = [
        x for x in (state.get("transactions") or {}).values()
        if x.get("source_kind") == "FORM4_TRANSACTION"
    ]
    items.sort(key=lambda x: x.get("transaction_date", ""), reverse=True)
    if not items:
        return (
            "🛰️ SPUTNIK — OPERAZIONI\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "Nessun acquisto/vendita documentato disponibile."
        )
    lines = ["🛰️ SPUTNIK — ACQUISTI / VENDITE DOCUMENTATI", "━━━━━━━━━━━━━━━━━━"]
    for item in items[:10]:
        emoji = "🟢" if item.get("action") == "ACQUISTATO" else "🔴"
        lines.append(
            f"{emoji} {item.get('action', 'N/D')} — {item.get('security', 'N/D')}\n"
            f"🏢 {item.get('company', 'N/D')} | 👤 {item.get('reporting_owner', 'N/D')}\n"
            f"📦 {item.get('shares', 'N/D')} | 💵 {item.get('price', 'N/D')}\n"
            f"📅 {item.get('transaction_date', 'N/D')} | 📄 Form {item.get('form', 'N/D')}\n"
            f"🔗 {item.get('source_url', '')}"
        )
    return "\n━━━━━━━━━━━━━━━━━━\n".join(lines)


def telegram_purchases_message(state: dict[str, Any]) -> str:
    items = [
        x for x in (state.get("transactions") or {}).values()
        if x.get("action") == "ACQUISTATO" and x.get("source_kind") == "FORM4_TRANSACTION"
    ]
    items.sort(key=lambda x: x.get("transaction_date", ""), reverse=True)
    if not items:
        return "🟢 SPUTNIK — ACQUISTI\n━━━━━━━━━━━━━━━━━━\nNessun acquisto documentato disponibile."
    lines = ["🟢 SPUTNIK — COSA È STATO ACQUISTATO", "━━━━━━━━━━━━━━━━━━"]
    for item in items[:10]:
        lines.append(
            f"📌 {item.get('security', 'N/D')}\n"
            f"🏢 {item.get('company', 'N/D')} | 👤 {item.get('reporting_owner', 'N/D')}\n"
            f"📦 Quantità: {item.get('shares', 'N/D')} | 💵 Prezzo: {item.get('price', 'N/D')}\n"
            f"📅 Data operazione: {item.get('transaction_date', 'N/D')}\n"
            f"📄 Form {item.get('form', 'N/D')} | 🔗 {item.get('source_url', '')}"
        )
    return "\n━━━━━━━━━━━━━━━━━━\n".join(lines)



def telegram_positions_message(state: dict[str, Any]) -> str:
    items = [
        x for x in (state.get("transactions") or {}).values()
        if x.get("source_kind") == "13F_POSITION"
    ]
    items.sort(key=lambda x: x.get("transaction_date", ""), reverse=True)
    if not items:
        return "📊 SPUTNIK — POSIZIONI 13F\\n━━━━━━━━━━━━━━━━━━\\nNessuna posizione 13F disponibile."
    lines = ["📊 SPUTNIK — POSIZIONI DICHIARATE", "━━━━━━━━━━━━━━━━━━"]
    for item in items[:10]:
        lines.append(
            f"📌 {item.get('security', 'N/D')}\\n"
            f"📦 Quantità: {item.get('shares', 'N/D')}\\n"
            f"💰 Valore 13F: {item.get('price', 'N/D')}\\n"
            f"📅 Filing: {item.get('filing_date', 'N/D')}\\n"
            f"🔗 {item.get('source_url', '')}"
        )
    return "\\n━━━━━━━━━━━━━━━━━━\\n".join(lines)

def telegram_sales_message(state: dict[str, Any]) -> str:
    items = [
        x for x in (state.get("transactions") or {}).values()
        if x.get("action") == "VENDUTO" and x.get("source_kind") == "FORM4_TRANSACTION"
    ]
    items.sort(key=lambda x: x.get("transaction_date", ""), reverse=True)
    if not items:
        return "🔴 SPUTNIK — VENDITE\n━━━━━━━━━━━━━━━━━━\nNessuna vendita documentata disponibile."
    lines = ["🔴 SPUTNIK — COSA È STATO VENDUTO", "━━━━━━━━━━━━━━━━━━"]
    for item in items[:10]:
        lines.append(
            f"📌 {item.get('security', 'N/D')}\n"
            f"🏢 {item.get('company', 'N/D')} | 👤 {item.get('reporting_owner', 'N/D')}\n"
            f"📦 Quantità: {item.get('shares', 'N/D')} | 💵 Prezzo: {item.get('price', 'N/D')}\n"
            f"📅 Data operazione: {item.get('transaction_date', 'N/D')}\n"
            f"📄 Form {item.get('form', 'N/D')} | 🔗 {item.get('source_url', '')}"
        )
    return "\n━━━━━━━━━━━━━━━━━━\n".join(lines)


def transaction_key(tx: TransactionRecord) -> str:
    raw = "|".join((
        tx.event_id, tx.action, tx.security, tx.shares,
        tx.price, tx.transaction_date, tx.reporting_owner,
    ))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

def telegram_message(event: FilingEvent) -> str:
    return (
        "🛰️ SPUTNIK — NUOVO DOCUMENTO\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🏢 {event.company}\n"
        f"📄 Form: {event.form}\n"
        f"📅 Filing: {event.filed_at}\n"
        f"🧾 Stato: {event.status}\n"
        f"🔎 Evidenza: {event.evidence}\n"
        f"📌 Tipo: {event.transaction_type}\n"
        f"🔗 {event.source_url}\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "ℹ️ Evento documentale pubblico. Nessuna operazione privata viene inferita."
    )


def send_telegram(message: str, chat_id: str | None = None) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = str(chat_id or os.getenv("TELEGRAM_CHAT_ID") or "").strip()
    if not token or not chat_id:
        print("SPUTNIK: Telegram non configurato.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode(
        {"chat_id": chat_id, "text": message, "disable_web_page_preview": "true"}
    ).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    request.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if payload.get("ok") is True:
            return True
        print(f"SPUTNIK: Telegram API error: {payload.get('description', 'unknown error')}")
    except urllib.error.HTTPError as exc:
        print(f"SPUTNIK: Telegram HTTP error {exc.code}.")
        try:
            payload = json.loads(exc.read().decode("utf-8", errors="replace"))
            print(f"SPUTNIK: Telegram API error: {payload.get('description', 'unknown error')}")
        except Exception:
            pass
    except urllib.error.URLError as exc:
        print(f"SPUTNIK: Telegram network error: {exc.reason}")
    except Exception as exc:
        print(f"SPUTNIK: Telegram exception: {type(exc).__name__}")
    return False


def telegram_api(method: str, token: str, params: dict[str, Any] | None = None, http_timeout: float | None = None) -> dict[str, Any]:
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = urllib.parse.urlencode(params or {}).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    request.add_header("Content-Type", "application/x-www-form-urlencoded")
    timeout = TELEGRAM_HTTP_TIMEOUT if http_timeout is None else http_timeout
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def ensure_polling_mode(token: str) -> None:
    """Ensure SPUTNIK uses Telegram long polling rather than a webhook."""
    try:
        info = telegram_api("getWebhookInfo", token)
        result = info.get("result") or {}
        webhook_url = str(result.get("url") or "")
        if webhook_url:
            print("SPUTNIK: Telegram webhook rilevato; lo rimuovo per usare il polling.")
            deleted = telegram_api("deleteWebhook", token, {"drop_pending_updates": "false"})
            if deleted.get("ok"):
                print("SPUTNIK: webhook rimosso; aggiornamenti pendenti conservati.")
            else:
                print(
                    "SPUTNIK: impossibile rimuovere il webhook: "
                    f"{deleted.get('description', 'unknown error')}"
                )
        else:
            print("SPUTNIK: Telegram webhook assente; long polling disponibile.")
    except urllib.error.HTTPError as exc:
        print(f"SPUTNIK: Telegram webhook HTTP error {exc.code}.")
        try:
            payload = json.loads(exc.read().decode("utf-8", errors="replace"))
            print(f"SPUTNIK: Telegram API error: {payload.get('description', 'unknown error')}")
        except Exception:
            pass
    except urllib.error.URLError as exc:
        print(f"SPUTNIK: Telegram webhook network error: {exc.reason}")
    except Exception as exc:
        print(f"SPUTNIK: Telegram webhook check error: {type(exc).__name__}")


def telegram_help_message() -> str:
    return (
        "🛰️ SPUTNIK — COMANDI\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🏠 HOME — dashboard completa\n"
        "🏆 CLASSIFICA — ranking operativo\n"
        "🟢 COSA COMPRARE — migliori candidati\n"
        "🛒 CARRELLO CFD — Entry/SL/TP/Size se verificabili\n"
        "🎯 CATALIZZATORI — eventi e settori da monitorare\n"
        "🏛️ TRUMP / WHITE HOUSE — briefing politico\n"
        "📰 NEWS — ultime correlazioni pubbliche\n"
        "🧾 SEC / OGE — filing e disclosure\n"
        "📊 SETTORI / IMPATTO — esposizioni documentate\n"
        "🔎 ANALISI — incrocio delle evidenze\n"
        "💰 ACQUISTI — acquisti documentati\n"
        "🔄 AGGIORNA — stato dell'ultimo aggiornamento\n"
        "⚙️ STATO — stato Telegram/motore\n"
        "ℹ️ AIUTO — questa lista\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "⌨️ Comandi rapidi:\n"
        "/start — attiva il monitoraggio\n"
        "/stop — ferma il monitoraggio\n"
        "/status — stato del sistema\n"
        "/test — prova Telegram\n"
        "/scan — stato scansione\n"
        "/filings — ultimi filing rilevati\n"
        "/transactions — acquisti e vendite documentati\n"
        "/purchases — cosa è stato acquistato\n"
        "/sales — cosa è stato venduto\n"
        "/news — ultime correlazioni pubbliche\n"
        "/brief — riepilogo intelligence\n"
        "Cosa comprare? / Cosa compro oggi? — classifica SPUTNIK\n"
        "/help — mostra questa lista"
    )


def telegram_filings_message(state: dict[str, Any]) -> str:
    events = list((state.get("events") or {}).values())
    events.sort(key=lambda x: x.get("filed_at", ""), reverse=True)
    if not events:
        return "🛰️ SPUTNIK — FILING\n━━━━━━━━━━━━━━━━━━\nNessun filing disponibile nello stato locale."
    lines = ["🛰️ SPUTNIK — ULTIMI FILING", "━━━━━━━━━━━━━━━━━━"]
    for item in events[:5]:
        lines.append(
            f"📄 {item.get('form', '?')} — {item.get('company', 'N/D')}\n"
            f"📅 {item.get('filed_at', 'N/D')}\n"
            f"🔗 {item.get('source_url', '')}"
        )
    return "\n━━━━━━━━━━━━━━━━━━\n".join(lines)


def telegram_news_message(state: dict[str, Any]) -> str:
    items = list((state.get("intelligence_history") or {}).values())
    items.sort(key=lambda x: x.get("detected_at", ""), reverse=True)
    if not items:
        return "🛰️ SPUTNIK — NEWS\n━━━━━━━━━━━━━━━━━━\nNessuna correlazione pubblica disponibile."
    lines = ["🛰️ SPUTNIK — ULTIME NEWS", "━━━━━━━━━━━━━━━━━━"]
    for item in items[:5]:
        lines.append(
            f"📡 {item.get('source', 'N/D')}\n"
            f"📰 {item.get('title') or 'Pagina generale / titolo non disponibile'}\n"
            f"🕒 {item.get('published') or item.get('detected_at', 'N/D')}\n"
            f"🧩 {', '.join(item.get('domains', [])) or 'Nessuna area'}\n"
            f"🔎 {item.get('evidence', 'N/D')}\n"
            f"🔗 {item.get('url', '')}"
        )
    return "\n━━━━━━━━━━━━━━━━━━\n".join(lines)


def telegram_brief_message(state: dict[str, Any]) -> str:
    events = list((state.get("events") or {}).values())
    items = list((state.get("intelligence_history") or {}).values())
    events.sort(key=lambda x: x.get("filed_at", ""), reverse=True)
    items.sort(key=lambda x: x.get("detected_at", ""), reverse=True)
    forms = {}
    for event in events[:20]:
        forms[event.get("form", "N/D")] = forms.get(event.get("form", "N/D"), 0) + 1
    latest = events[0] if events else None
    latest_news = items[0] if items else None
    return (
        "🛰️ SPUTNIK — BRIEF\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"📡 Stato: {'ATTIVO' if state.get('telegram_active') else 'FERMO'}\n"
        f"📄 Filing archiviati: {len(events)}\n"
        f"💰 Operazioni documentate: {len(state.get('transactions') or {})}\n"
        f"🧩 Correlazioni archiviate: {len(items)}\n"
        f"📊 Form principali: {', '.join(f'{k}={v}' for k, v in list(forms.items())[:5]) or 'N/D'}\n"
        f"📄 Ultimo filing: {(latest or {}).get('company', 'N/D')} {(latest or {}).get('form', '')}\n"
        f"📡 Ultima fonte: {(latest_news or {}).get('source', 'N/D')}\n"
        "⚠️ Le correlazioni non provano investimenti, intenzioni o transazioni private."
    )


def telegram_help_message_with_commands() -> str:
    return telegram_help_message()


def telegram_trump_order_message(state: dict[str, Any]) -> str:
    """Return a ranked, evidence-labeled BUY candidate view for the natural-language command."""
    transactions = [
        x for x in (state.get("transactions") or {}).values()
        if x.get("source_kind") == "FORM4_TRANSACTION"
    ]
    purchases = [x for x in transactions if x.get("action") == "ACQUISTATO"]
    purchases.sort(key=lambda x: x.get("transaction_date", ""), reverse=True)

    asset_map = {
        "ENERGY": ("PETROLIO / ENERGIA", "oil, crude, brent, wti, natural gas, lng, energy"),
        "METALS": ("ORO / METALLI", "gold, silver, copper, metals"),
        "AGRICULTURE": ("AGRICOLTURA", "corn, wheat, soybean, sugar, coffee, cocoa"),
        "DEFENSE": ("DIFESA / AEROSPAZIO", "defense, aerospace, military"),
        "AI_TECH": ("AI / SEMICONDUTTORI", "artificial intelligence, semiconductor, chip"),
        "SPACE": ("SPAZIO", "space, satellite, rocket"),
        "CRYPTO": ("CRYPTO", "bitcoin, ethereum, crypto"),
        "MEDIA": ("MEDIA", "media, social"),
        "REAL_ESTATE": ("REAL ESTATE", "property, real estate, hotel"),
        "TRADE_POLICY": ("DAZI / POLITICA COMMERCIALE", "tariffs, trade deal, sanctions"),
        "RATES_MACRO": ("TASSI / DOLLARO", "interest rates, inflation, treasury yields, dollar"),
    }

    scores: dict[str, dict[str, Any]] = {}
    for item in purchases[:20]:
        security = str(item.get("security") or "")
        company = str(item.get("company") or "")
        label = f"{security} — {company}".strip(" —")
        scores.setdefault(label, {
            "label": label,
            "score": 70,
            "reason": "acquisto documentato in Form 4",
            "evidence": "FORM4_TRANSACTION",
            "date": item.get("transaction_date") or item.get("filing_date") or "N/D",
            "url": item.get("source_url") or "",
        })
        scores[label]["score"] = min(95, scores[label]["score"] + 5)

    # Public-source correlations are weaker than an actual Form 4 transaction.
    for item in sorted(
        (state.get("intelligence_history") or {}).values(),
        key=lambda x: x.get("detected_at", ""),
        reverse=True,
    )[:20]:
        for domain in item.get("domains", []):
            meta = asset_map.get(domain)
            if not meta:
                continue
            label = meta[0]
            entry = scores.setdefault(label, {
                "label": label,
                "score": 55,
                "reason": "correlazione da fonte pubblica",
                "evidence": item.get("evidence", "PUBLIC_SOURCE_TEXT"),
                "date": item.get("detected_at", "N/D"),
                "url": item.get("url", ""),
            })
            entry["score"] = min(69, entry["score"] + 2)

    ranked = sorted(scores.values(), key=lambda x: x["score"], reverse=True)[:5]
    lines = [
        "🛰️ SPUTNIK — TRUMP ORDINA",
        "━━━━━━━━━━━━━━━━━━",
        "🎯 Cosa comprare secondo il motore:",
    ]
    if not ranked:
        lines.extend([
            "⚪ NESSUN BUY — dati insufficienti",
            "",
            "SPUTNIK non ha abbastanza evidenza pubblica per proporre un candidato.",
        ])
    else:
        for idx, item in enumerate(ranked, 1):
            lines.extend([
                f"{idx}. 🟢 BUY CANDIDATO — {item['label']}",
                f"   Score evidenza: {item['score']}/100",
                f"   Motivo: {item['reason']}",
                f"   Evidenza: {item['evidence']}",
                f"   Data: {item['date']}",
                f"   🔗 {item['url']}" if item["url"] else "",
            ])

    lines.extend([
        "",
        "⚠️ BUY CANDIDATO = valutazione analitica SPUTNIK, NON ordine di mercato.",
        "⚠️ Un filing Form 4 documenta un'operazione del soggetto indicato; una correlazione pubblica non prova un acquisto.",
        "ℹ️ SPUTNIK non esegue ordini.",
    ])
    return "\n".join(line for line in lines if line != "")



def poll_telegram_commands(state: dict[str, Any]) -> bool:
    """Process Telegram commands and auto-discover the first private chat."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    configured_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token:
        print("SPUTNIK: Telegram token non configurato.")
        return bool(state.get("telegram_active", False))

    # A previously discovered chat ID takes priority. The repository secret is
    # only a fallback; this lets SPUTNIK discover the chat from /start.
    chat_id = str(state.get("telegram_chat_id") or configured_chat_id).strip()

    offset = int(state.get("telegram_update_offset", 0) or 0)
    try:
        payload = telegram_api(
            "getUpdates",
            token,
            {"offset": offset, "timeout": TELEGRAM_POLL_TIMEOUT, "allowed_updates": '[\"message\"]'},
            http_timeout=max(TELEGRAM_HTTP_TIMEOUT, TELEGRAM_POLL_TIMEOUT + 10),
        )
    except urllib.error.HTTPError as exc:
        print(f"SPUTNIK: Telegram polling HTTP error {exc.code}.")
        try:
            error_payload = json.loads(exc.read().decode("utf-8", errors="replace"))
            print(f"SPUTNIK: Telegram polling API error: {error_payload.get('description', 'unknown error')}")
        except Exception:
            pass
        return bool(state.get("telegram_active", False))
    except urllib.error.URLError as exc:
        print(f"SPUTNIK: Telegram polling network error: {exc.reason}")
        return bool(state.get("telegram_active", False))
    except Exception as exc:
        print(f"SPUTNIK: Telegram polling error: {type(exc).__name__}")
        return bool(state.get("telegram_active", False))

    if not payload.get("ok"):
        print(f"SPUTNIK: Telegram polling API error: {payload.get('description', 'unknown error')}")
        return bool(state.get("telegram_active", False))

    active = bool(state.get("telegram_active", False))
    updates = payload.get("result", [])
    print(f"SPUTNIK: Telegram updates ricevuti: {len(updates)}")
    accepted = 0

    for update in updates:
        update_id = int(update.get("update_id", 0))
        state["telegram_update_offset"] = max(
            int(state.get("telegram_update_offset", 0) or 0),
            update_id + 1,
        )

        message = update.get("message") or {}
        chat = message.get("chat") or {}
        incoming_chat = str(chat.get("id", ""))
        chat_type = str(chat.get("type", ""))
        command = str(message.get("text", "")).strip().lower()
        normalized_command = re.sub(r"\s+", " ", command).strip()

        # /start from a private chat establishes or refreshes the authorized chat.
        # This also repairs a stale TELEGRAM_CHAT_ID secret automatically.
        if chat_type == "private" and command == "/start":
            chat_id = incoming_chat
            state["telegram_chat_id"] = chat_id
            print("SPUTNIK: Chat ID Telegram scoperto/aggiornato automaticamente.")
        elif incoming_chat != chat_id:
            print("SPUTNIK: comando ricevuto da una chat non autorizzata.")
            continue

        accepted += 1

        if normalized_command in {"trump ordina", "trump cosa compro", "trump cosa comprare"}:
            send_telegram(telegram_trump_order_message(state), chat_id=chat_id)
        elif command == "/help":
            send_telegram(telegram_help_message(), chat_id=chat_id)
        elif command == "/filings":
            send_telegram(telegram_filings_message(state), chat_id=chat_id)
        elif command == "/transactions":
            send_telegram(telegram_transactions_message(state), chat_id=chat_id)
        elif command == "/purchases":
            send_telegram(telegram_purchases_message(state), chat_id=chat_id)
        elif command == "/sales":
            send_telegram(telegram_sales_message(state), chat_id=chat_id)
        elif command == "/positions":
            send_telegram(telegram_positions_message(state), chat_id=chat_id)
        elif command == "/news":
            send_telegram(telegram_news_message(state), chat_id=chat_id)
        elif command == "/brief":
            send_telegram(telegram_brief_message(state), chat_id=chat_id)
        elif command == "/scan":
            send_telegram("🛰️ SPUTNIK — SCAN AVVIATA\n━━━━━━━━━━━━━━━━━━\n🔎 Controllo SEC in corso...", chat_id=chat_id)
            scan_events = collect()
            fresh_scan = new_events(scan_events, state)
            scan_transactions = extract_transactions(scan_events)
            stored_transactions = state.setdefault("transactions", {})
            fresh_transactions: list[TransactionRecord] = []
            for tx in scan_transactions:
                key = transaction_key(tx)
                if key not in stored_transactions:
                    stored_transactions[key] = asdict(tx)
                    fresh_transactions.append(tx)
            save_state(state)
            send_telegram(
                f"🛰️ SPUTNIK — SCAN COMPLETATA\n━━━━━━━━━━━━━━━━━━\n📄 Filing trovati: {len(scan_events)}\n🆕 Nuovi filing: {len(fresh_scan)}\n💰 Nuove operazioni documentate: {len(fresh_transactions)}",
                chat_id=chat_id,
            )
            for tx in fresh_transactions:
                send_telegram(telegram_transaction_message(tx), chat_id=chat_id)
            for event in fresh_scan:
                send_telegram(telegram_message(event), chat_id=chat_id)
        elif command == "/start":
            active = True
            send_telegram(
                "🛰️ SPUTNIK ATTIVO\n━━━━━━━━━━━━━━━━━━\n"
                "✅ Monitoraggio attivato.\n"
                "🔐 Chat Telegram riconosciuta automaticamente.\n"
                "📡 Controllo SEC ad ogni esecuzione GitHub Actions.\n"
                "⏱️ Frequenza: ogni 5 minuti.\n"
                "⏱️ Comandi: /status /scan /filings /transactions /purchases /sales /positions /news /brief /help /stop /test",
                chat_id=chat_id,
            )
        elif command == "/stop":
            active = False
            send_telegram(
                "🛰️ SPUTNIK FERMATO\n━━━━━━━━━━━━━━━━━━\n⛔ Monitoraggio sospeso.",
                chat_id=chat_id,
            )
        elif command == "/status":
            status = "ATTIVO" if active else "FERMO"
            send_telegram(
                f"🛰️ SPUTNIK — STATO\n━━━━━━━━━━━━━━━━━━\n"
                f"📡 Monitoraggio: {status}\n"
                "⏱️ Frequenza: ogni 5 minuti\n"
                "🔎 Fonte: SEC EDGAR",
                chat_id=chat_id,
            )
        elif command == "/test":
            send_telegram(telegram_test_message(), chat_id=chat_id)

    print(f"SPUTNIK: Telegram comandi autorizzati: {accepted}")
    state["telegram_active"] = active
    if chat_id:
        state["telegram_chat_id"] = chat_id
    return active

def telegram_test_message() -> str:
    return (
        "🛰️ SPUTNIK — TELEGRAM ONLINE\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "✅ Connessione Telegram verificata.\n"
        "🔐 Token e Chat ID ricevuti da GitHub Secrets.\n"
        "📡 SPUTNIK resta separato da GAGARIN.\n"
        "ℹ️ Messaggio di test: nessuna operazione di mercato."
    )


def main() -> None:
    if os.getenv("SPUTNIK_TELEGRAM_TEST", "").strip().lower() in {"1", "true", "yes"}:
        print("SPUTNIK: esecuzione test Telegram.")
        if not send_telegram(telegram_test_message()):
            raise SystemExit("SPUTNIK: test Telegram fallito.")
        print("SPUTNIK: test Telegram riuscito.")
        return

    state = load_state()
    telegram_polling_enabled = os.getenv("SPUTNIK_TELEGRAM_POLLING", "1").strip().lower() in {"1", "true", "yes"}
    if telegram_polling_enabled:
        ensure_polling_mode(os.getenv("TELEGRAM_BOT_TOKEN", ""))
        active = poll_telegram_commands(state)
        save_state(state)

        # Legacy fallback only. Production Telegram polling is handled by the
        # dedicated persistent listener service when SPUTNIK_TELEGRAM_POLLING=0.
        if active:
            deadline = time.monotonic() + max(0, TELEGRAM_LISTEN_SECONDS)
            while time.monotonic() < deadline:
                previous_active = active
                active = poll_telegram_commands(state)
                save_state(state)
                if not active or not previous_active:
                    break
    else:
        active = bool(state.get("telegram_active", True))
        print("SPUTNIK: Telegram polling GitHub Actions disabilitato; listener dedicato attivo.")

    if not active:
        save_state(state)
        print("SPUTNIK: monitoraggio fermo. Usa /start su Telegram.")
        return

    events = collect()
    fresh = new_events(events, state)
    all_transaction_events = events
    transactions = extract_transactions(all_transaction_events)
    stored_transactions = state.setdefault("transactions", {})
    new_transactions: list[TransactionRecord] = []
    for tx in transactions:
        key = transaction_key(tx)
        if key not in stored_transactions:
            stored_transactions[key] = asdict(tx)
            new_transactions.append(tx)
    intelligence = intelligence_snapshot(state)
    gagarin_confirmation = forward_findings_to_gagarin(intelligence)
    if gagarin_confirmation:
        state["gagarin_confirmations"] = {
            str(item.get("event_id") or index): item
            for index, item in enumerate(gagarin_confirmation.get("events") or [])
        }
    from zoneinfo import ZoneInfo
    local_now = utc_now().astimezone(ZoneInfo("Europe/Rome"))
    morning_hour = int(os.getenv("SPUTNIK_MORNING_HOUR", "5"))
    morning_key = local_now.date().isoformat()
    morning_due = local_now.hour == morning_hour and state.get("morning_brief_date") != morning_key
    if morning_due:
        state["morning_brief_date"] = morning_key
    save_state(state)

    print(f"SPUTNIK: {len(events)} filing trovati, {len(fresh)} nuovi.")
    print(f"SPUTNIK: {len(new_transactions)} nuove operazioni documentate.")
    print(f"SPUTNIK: {len(intelligence)} nuove correlazioni da fonti pubbliche.")

    for event in fresh:
        message = telegram_message(event)
        print(message)
        send_telegram(message, chat_id=str(state.get("telegram_chat_id") or "").strip() or None)

    for tx in new_transactions:
        message = telegram_transaction_message(tx)
        print(message)
        send_telegram(message, chat_id=str(state.get("telegram_chat_id") or "").strip() or None)

    for item in intelligence:
        message = intelligence_message(item)
        print(message)
        send_telegram(message, chat_id=str(state.get("telegram_chat_id") or "").strip() or None)

    if gagarin_confirmation:
        message = gagarin_confirmation_message(gagarin_confirmation)
        print(message)
        send_telegram(message, chat_id=str(state.get("telegram_chat_id") or "").strip() or None)

    if morning_due:
        message = telegram_morning_message(state)
        print(message)
        send_telegram(message, chat_id=str(state.get("telegram_chat_id") or "").strip() or None)


if __name__ == "__main__":
    main()
