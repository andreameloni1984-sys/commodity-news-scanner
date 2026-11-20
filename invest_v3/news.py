"""Timestamped RSS/Atom intake and conservative catalyst classification."""
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from html import unescape
import json
import re
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

from invest_v2.sec_ticker import SEC_TICKERS_URL

SEC = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&owner=exclude&count=40&output=atom"
FEEDS = {
    "SEC EDGAR": SEC,
    "Federal Reserve": "https://www.federalreserve.gov/feeds/press_all.xml",
    "BLS": "https://www.bls.gov/feed/bls_latest.rss",
    "BEA": "https://www.bea.gov/rss/rss.xml",
    "FDA": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml",
    "GlobeNewswire": "https://www.globenewswire.com/RssFeed/subjectcode/01-Earnings%20Releases/feedTitle/Earnings%20Releases",
    "PR Newswire": "https://www.prnewswire.com/rss/news-releases-list.rss",
}
PRIMARY = {"SEC EDGAR", "Federal Reserve", "BLS", "BEA", "Treasury", "Casa Bianca", "FDA"}
RULES = (
    ("Guidance rialzata", "LONG", 4, r"\b(?:raises?|raised|increases?) (?:its |full.year )?(?:guidance|(?:revenue|earnings) outlook)\b"),
    ("Guidance ridotta", "SHORT", 4, r"\b(?:cuts?|lowers?|lowered|reduces?) (?:its |full.year )?(?:guidance|(?:revenue|earnings) outlook)\b"),
    ("Decisione regolatoria positiva", "LONG", 3, r"\b(?:receives? FDA approval|FDA approves?)\b"),
    ("Decisione regolatoria negativa", "SHORT", 3, r"\b(?:FDA rejects?|receives? (?:an? )?(?:FDA )?complete response letter)\b"),
    ("Rischio di insolvenza", "SHORT", 5, r"\bfiles? for chapter 11\b"),
)


@dataclass(frozen=True)
class Event:
    source: str
    url: str
    title: str
    published: datetime
    detected: datetime
    symbol: str
    category: str
    direction: str
    impact: int


def fetch(url, user_agent):
    if urlsplit(url).scheme != "https":
        raise ValueError("Feed HTTPS richiesto")
    with urlopen(Request(url, headers={"User-Agent": user_agent}), timeout=10) as response:
        data = response.read(4_000_001)
    if len(data) > 4_000_000:
        raise ValueError("Feed troppo grande")
    return data


def sec_directory(user_agent):
    grouped = {}
    for row in json.loads(fetch(SEC_TICKERS_URL, user_agent)).values():
        grouped.setdefault(int(row["cik_str"]), set()).add(row["ticker"])
    return {cik: next(iter(symbols)) for cik, symbols in grouped.items() if len(symbols) == 1}


def feed_items(data, *, atom=False):
    root = ET.fromstring(data)
    for node in root.findall(".//{*}entry" if atom else ".//{*}item"):
        title = (node.findtext("{*}title") or "").strip()
        stamp = node.findtext("{*}published") or node.findtext("{*}pubDate")
        # EDGAR Current Filings uses updated for acceptance time.
        if atom and not stamp:
            stamp = node.findtext("{*}updated")
        link = node.find("{*}link")
        url = (link.get("href") or link.text or "").strip() if link is not None else ""
        if url.startswith("http://www.fda.gov/"):
            url = "https" + url[4:]
        try:
            published = datetime.fromisoformat(stamp) if atom else parsedate_to_datetime(stamp)
            if published.utcoffset() is None or not title or urlsplit(url).scheme != "https" or not urlsplit(url).hostname:
                continue
        except (TypeError, ValueError):
            continue
        summary = node.findtext("{*}summary") or node.findtext("{*}description") or ""
        yield title, url, published, re.sub(r"<[^>]+>", " ", unescape(summary))


def events(data, *, source, now, directory, configured_symbol=None, atom=False):
    for title, url, published, summary in feed_items(data, atom=atom):
        if not 0 <= (now - published).total_seconds() <= 3600:
            continue
        symbol = configured_symbol
        if source == "SEC EDGAR":
            cik = re.search(r"\((\d{10})\)\s*\(Filer\)", title, re.I)
            symbol = directory.get(int(cik[1])) if cik else None
        elif symbol is None:
            matches = set(re.findall(r"\((?:NASDAQ|NYSE|AMEX|NYSE ARCA)\s*:\s*([A-Z][A-Z0-9.-]{0,19})\)", title + " " + summary))
            symbol = next(iter(matches)) if len(matches) == 1 else None
        if not symbol:
            continue
        # Headlines supply polarity. Generic results and ambiguous headlines abstain.
        matched = [(category, direction, impact) for category, direction, impact, pattern in RULES
                   if re.search(pattern, title, re.I)]
        if source == "SEC EDGAR" and re.search(r"\bItem 1\.03: Bankruptcy or Receivership\b", summary):
            matched = [("Rischio di insolvenza", "SHORT", 5)]
        if len(matched) == 1:
            yield Event(source, url, title, published, now, symbol, *matched[0])
