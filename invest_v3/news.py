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
TICKER = r"\((?:NASDAQ|NYSE(?: ARCA| AMERICAN)?|AMEX)\s*:\s*([A-Z][A-Z0-9.-]{0,19})\)"
RULES = (
    ("Guidance", "LONG", 4, r"\b(?:raises?|raised|increases?) (?:its )?(?:full[ -]year |annual |quarterly )?(?:(?:revenue|earnings|EPS) )?(?:guidance|outlook)\b"),
    ("Guidance", "SHORT", 4, r"\b(?:cuts?|lowers?|lowered|reduces?|withdraws?) (?:its )?(?:full[ -]year |annual |quarterly )?(?:(?:revenue|earnings|EPS) )?(?:guidance|outlook)\b"),
    ("Trimestrale", "LONG", 3, r"\b(?:earnings|EPS|revenue|sales)\s+(?:beats?|tops?|exceeds?)\s+(?:analyst |Wall Street )?(?:consensus|estimates|expectations)\b"),
    ("Trimestrale", "SHORT", 3, r"\b(?:earnings|EPS|revenue|sales)\s+(?:miss(?:es)?|falls? short of)\s+(?:analyst |Wall Street )?(?:consensus|estimates|expectations)\b"),
    ("Contratto", "LONG", 3, r"\b(?:wins?|secures?|awarded|selected for|signs?)\b.{0,65}?(?:\$[\d,.]+\s*(?:million|billion|[mb]n?)\b|material\b).{0,40}?\b(?:contract|purchase order)\b"),
    ("Contratto", "SHORT", 3, r"\b(?:loses?|lost|terminates?)\b.{0,60}?\b(?:material|major)\b.{0,30}?\bcontract\b"),
    ("Decisione FDA", "LONG", 3, r"\b(?:receives?|grants?|granted|wins?|secures?) (?:U\.S\. )?FDA approval\b|\bFDA approves?\b"),
    ("Decisione FDA", "SHORT", 3, r"\b(?:FDA rejects?|receives? (?:an? )?(?:FDA )?complete response letter)\b"),
    ("Rischio di insolvenza", "SHORT", 5, r"\bfiles? for chapter 11\b"),
)
TOPICS = (
    ("Trimestrale", r"\b(?:financial results|quarterly results|quarter earnings|quarterly earnings)\b"),
    ("Guidance", r"\b(?:guidance|earnings outlook|revenue outlook)\b"),
    ("Contratto", r"\b(?:contract|purchase order|material definitive agreement)\b"),
    ("Acquisizione", r"\b(?:acquisition|acquires?|acquired|merger|takeover|tender offer)\b"),
    ("Decisione FDA", r"\b(?:FDA|complete response letter)\b"),
)
SEC_ITEMS = (
    ("Rischio di insolvenza", r"\bItem 1\.03:"),
    ("Trimestrale", r"\bItem 2\.02:"),
    ("Acquisizione / cessione", r"\bItem 2\.01:"),
    ("Accordo rilevante", r"\bItem 1\.0[12]:"),
    ("Comunicazione SEC", r"\bItem (?:7\.01|8\.01):"),
)
MACRO_SOURCES = {"BLS", "BEA", "Federal Reserve"}


@dataclass(frozen=True)
class Event:
    source: str
    url: str
    title: str
    published: datetime
    detected: datetime
    symbol: str | None
    category: str
    direction: str | None
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


def reviews(data, *, source, now, directory, configured_symbol=None, atom=False):
    for title, url, published, summary in feed_items(data, atom=atom):
        symbol = configured_symbol
        if source == "SEC EDGAR":
            cik = re.search(r"\((\d{10})\)\s*\(Filer\)", title, re.I)
            symbol = directory.get(int(cik[1])) if cik else None
        elif symbol is None and source not in MACRO_SOURCES:
            matches = {match.upper() for match in re.findall(TICKER, title + " " + summary, re.I)}
            symbol = next(iter(matches)) if len(matches) == 1 else None

        category, direction, impact = classify(source, title, summary, symbol)
        event = Event(source, url, title, published, now, symbol, category, direction, impact)
        reason = None
        age = (now - published).total_seconds()
        if age < 0:
            reason = "pubblicazione futura"
        elif age > 3600:
            reason = "pubblicazione oltre 60 minuti"
        elif source in MACRO_SOURCES:
            reason = "comunicato macro, nessuna direzione automatica per titolo"
        elif not category:
            reason = "catalizzatore non riconosciuto"
        elif not symbol:
            reason = "emittente/ticker non univoco o mancante"
        elif not direction:
            reason = "impatto direzionale ambiguo o confronto mancante"
        yield event, reason


def classify(source, title, summary, symbol):
    if source in MACRO_SOURCES:
        return "Macroeconomia USA", None, 0
    if source == "SEC EDGAR":
        for category, pattern in SEC_ITEMS:
            if re.search(pattern, summary, re.I):
                return (category, "SHORT", 5) if category == "Rischio di insolvenza" else (category, None, 0)
        return "Comunicazione SEC", None, 0

    matched = [(category, direction, strength) for category, direction, strength, pattern in RULES
               if re.search(pattern, title, re.I)]
    # Tie a premium to the named target. A generic transaction says little about the buyer.
    target = re.search(TICKER + r"\s+to be acquired\b.*\bat a\s+[\d.]+%\s+premium\b", title, re.I)
    if target and symbol and target[1].upper() == symbol:
        matched.append(("Acquisizione", "LONG", 4))
    if matched:
        if len({direction for _, direction, _ in matched}) > 1:
            return " / ".join(dict.fromkeys(category for category, _, _ in matched)), None, 0
        return max(matched, key=lambda rule: rule[2])
    return next(((category, None, 0) for category, pattern in TOPICS
                 if re.search(pattern, title, re.I)), ("", None, 0))


def events(data, **kwargs):
    return (event for event, reason in reviews(data, **kwargs) if reason is None)
