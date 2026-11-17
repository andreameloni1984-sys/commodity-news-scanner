"""Dated primary-source articles; social rumours and index pages cannot trigger.

Primary provenance is checked, not factual truth or causality. The event rule
only chooses articles for technical confirmation; it is not an NLP prediction.
"""
import os
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse
from .data import get_bytes
from .feed_parser import parse_public_feed, clean_public_text

DEFAULT_FEEDS = (
    "https://www.whitehouse.gov/news/",
    "https://nvidianews.nvidia.com/releases.xml",
    "https://www.federalreserve.gov/feeds/press_all.xml",
)
PRIMARY_HOSTS = frozenset({
    "www.whitehouse.gov", "www.federalreserve.gov", "www.sec.gov",
    "nvidianews.nvidia.com", "investor.nvidia.com", "news.microsoft.com",
    "www.apple.com", "ir.amd.com", "ir.aboutamazon.com", "investor.tesla.com",
    "www.commerce.gov", "www.defense.gov",
})
EVENT = re.compile(r"\b(awarded|wins? (?:a |the )?contract|approved|approval|raises? (?:its )?(?:guidance|outlook)|record (?:revenue|sales)|raises? dividend|share repurchase|buyback)\b", re.I)
CAUTION = re.compile(r"\b(not|no|denied|denies|rumou?r|reportedly|unconfirmed|may|might|could|alleged|false|revoked|cancelled|canceled|cuts?|rejected|investigation|lawsuit|layoffs?|fired|sanctions?)\b", re.I)


def timestamp(value):
    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError, AttributeError):
        try:
            date = parsedate_to_datetime(value)
        except (ValueError, TypeError, AttributeError):
            return None
    return date.astimezone(timezone.utc) if date.tzinfo else None


def article_evidence(item, instrument, now, fetch=get_bytes):
    parsed = urlparse(item.get("url", ""))
    feed = urlparse(item.get("feed_url", ""))
    path = parsed.path.strip("/")
    if parsed.scheme != "https" or parsed.hostname not in PRIMARY_HOSTS or feed.hostname not in PRIMARY_HOSTS:
        return None
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        return None
    if parsed.hostname != feed.hostname or len(path.split("/")) < 2 or parsed.path == feed.path:
        return None
    date = timestamp(item.get("published"))
    if date is None or not 0 <= (now - date).total_seconds() <= 24 * 3600:
        return None
    summary = item.get("title", "") + ". " + item.get("text", "")
    aliases = [re.compile(r"(?<!\w)" + re.escape(a) + r"(?!\w)", re.I) for a in instrument.aliases]
    sentences = re.split(r"(?<=[.!?])\s+|\n+", summary)
    relevant = [s for s in sentences if any(a.search(s) for a in aliases)]
    if any(CAUTION.search(s) for s in relevant):
        return None
    positive = next((s for s in relevant if EVENT.search(s)), None)
    if positive is None:
        return None
    # Fetch individual article and require its company/event sentence to be
    # present in the body, not just the RSS snippet or a redirect destination.
    try:
        body = clean_public_text(fetch(item["url"]).decode("utf-8", errors="replace"))
    except Exception:
        return None
    normalize = lambda s: re.sub(r"\W+", " ", s).strip().casefold()
    if normalize(positive) not in normalize(body):
        return None
    return {
        "title": item["title"], "url": item["url"], "published": date.isoformat(),
        "source": parsed.hostname, "excerpt": positive[:240],
        "verification": "FONTE_PRIMARIA_E_TESTO_RISCONTRATI",
        "interpretation": "Evento potenzialmente favorevole; impatto economico non verificato automaticamente.",
    }


def collect_news(instruments, now):
    feeds = tuple(filter(None, os.getenv("INVEST_NEWS_FEEDS", ";".join(DEFAULT_FEEDS)).split(";")))
    evidence = {i.symbol: [] for i in instruments}
    diagnostics = []
    fetched = {}
    def cached(url):
        if url not in fetched:
            fetched[url] = get_bytes(url)
        return fetched[url]
    for feed in feeds:
        if urlparse(feed).scheme != "https" or urlparse(feed).hostname not in PRIMARY_HOSTS:
            diagnostics.append("Fonte non primaria esclusa")
            continue
        try:
            if feed == "https://www.whitehouse.gov/news/":
                from .whitehouse import items
                rows = items(cached(feed), feed, cached)
            else:
                rows = parse_public_feed(cached(feed), feed)[:40]
        except Exception as exc:
            diagnostics.append(f"Fonte {urlparse(feed).hostname} non disponibile: {type(exc).__name__}")
            continue
        diagnostics.append(f"Fonte {urlparse(feed).hostname}: {len(rows)} articoli esaminati")
        for item in rows:
            for instrument in instruments:
                if len(evidence[instrument.symbol]) >= 2:
                    continue
                match = article_evidence(item, instrument, now, fetch=cached)
                if match and not any(e["url"] == match["url"] for e in evidence[instrument.symbol]):
                    evidence[instrument.symbol].append(match)
    return evidence, diagnostics
