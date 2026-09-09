import os
import json
import math
import re
from html.parser import HTMLParser
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, parse_qs
from zoneinfo import ZoneInfo

import requests


# ============================================================
# COMMODITY TRADING BOT v3.0
# QUANT MODEL + MULTI-TIMEFRAME + NEWS + USD + SEASONALITY
# + RANKING + POSITION MANAGEMENT
#
# Analitico/simulato: NON esegue ordini reali. v2.5 aggiunge Weather/Disaster Intelligence e un adapter demo disabilitato di default.
# ============================================================

API_KEY = os.getenv("TWELVE_DATA_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "8002086130")

BASE_URL = "https://api.twelvedata.com/time_series"
NEWS_URL = "https://newsapi.org/v2/everything"

POSITION_FILE = "position.json"
DIRECTION_STATE_FILE = "commodities_direction_state.json"
PREDICTION_LOG_FILE = "commodities_prediction_log.json"
DAILY_REPORT_FILE = "commodities_daily_report_state.json"
PREDICTION_HORIZON_HOURS = 24
EOD_REPORT_HOUR = int(os.getenv("EOD_REPORT_HOUR", "23"))

# v3.0 — multi-horizon research and market-structure layer.
# Real/demo order execution remains OFF by default.
BOT_VERSION = "3.0"
PAPER_TRADING_ONLY = os.getenv("PAPER_TRADING_ONLY", "1") == "1"
FUTURES_STRUCTURE_ENABLED = os.getenv("FUTURES_STRUCTURE_ENABLED", "1") == "1"
POLITICAL_IMPACT_ENABLED = os.getenv("POLITICAL_IMPACT_ENABLED", "1") == "1"
EARLY_OPPORTUNITY_ENABLED = os.getenv("EARLY_OPPORTUNITY_ENABLED", "1") == "1"

# Optional explicit front/next futures symbols. Example:
# FUTURES_SYMBOLS_JSON='{"Oro":["GC1!","GC2!"],"Rame":["HG1!","HG2!"]}'
# Leave empty when the data provider does not expose futures symbols.
try:
    FUTURES_SYMBOLS = json.loads(os.getenv("FUTURES_SYMBOLS_JSON", "{}"))
    if not isinstance(FUTURES_SYMBOLS, dict):
        FUTURES_SYMBOLS = {}
except Exception:
    FUTURES_SYMBOLS = {}

FUTURES_CACHE_FILE = "commodities_futures_structure_cache.json"
FUTURES_CACHE_HOURS = int(os.getenv("FUTURES_CACHE_HOURS", "2"))


# v2.7 — 5-minute smart monitoring. The bot is scheduled externally
# (for example by GitHub Actions cron */5); it does not sleep inside a run.
MONITOR_INTERVAL_MINUTES = int(os.getenv("MONITOR_INTERVAL_MINUTES", "5"))
MONITOR_TOP_N = int(os.getenv("MONITOR_TOP_N", "3"))
MONITOR_SEND_FULL = os.getenv("MONITOR_SEND_FULL", "1") == "1"
MONITOR_STATE_FILE = "commodities_monitor_state.json"

# v2.5 GLOBAL COMMODITY INTELLIGENCE
WEATHER_CACHE_FILE = "commodities_weather_cache.json"
WEATHER_CACHE_HOURS = int(os.getenv("WEATHER_CACHE_HOURS", "3"))
WEATHER_TIMEOUT = 12
WEATHER_ENABLED = os.getenv("WEATHER_ENABLED", "1") == "1"
DISASTER_ENABLED = os.getenv("DISASTER_ENABLED", "1") == "1"
# Automatic broker/demo execution is deliberately OFF. Enable only after
# forward/paper validation and a broker-specific adapter is configured.
DEMO_TRADING_ENABLED = (os.getenv("DEMO_TRADING_ENABLED", "0") == "1") and (not PAPER_TRADING_ONLY)
DEMO_ORDERS_FILE = "commodities_demo_orders.json"
WEATHER_IMPACT_CAP = 8.0

KNOWLEDGE_CACHE_FILE = "trading_knowledge_cache.json"
KNOWLEDGE_REFRESH_HOURS = 24
KNOWLEDGE_FETCH_TIMEOUT = 6
KNOWLEDGE_SOURCES = [
    # Worldwide primary / institutional sources verified for availability.
    {"name": "CME Technical Analysis", "url": "https://www.cmegroup.com/education/courses/technical-analysis", "type": "web"},
    {"name": "CME Trading and Analysis", "url": "https://www.cmegroup.com/education/courses/trading-and-analysis", "type": "web"},
    {"name": "CME Technical Patterns Reversals", "url": "https://www.cmegroup.com/education/courses/technical-analysis/technical-patterns-reversals", "type": "web"},
    {"name": "CFTC Commitments of Traders", "url": "https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm", "type": "web"},
    {"name": "CFTC COT Historical", "url": "https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalViewable/index.htm", "type": "web"},
    {"name": "CFTC Trading Risk Advisory", "url": "https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/CustomerAdvisory_SocialMedia_Metals.html", "type": "web"},
    {"name": "ICE Education", "url": "https://www.ice.com/support/education", "type": "web"},
    {"name": "ICE Commodity Technical Analysis", "url": "https://www.ice.com/publicdocs/Charting_and_Technical_Analysis_for_Commodity_Markets.pdf", "type": "web"},
    {"name": "NOAA Climate Data Online", "url": "https://www.ncei.noaa.gov/cdo-web/", "type": "web"},
]

# Additional global institutional sources. Kept separate so the bot can report
# which source family is healthy without depending on fragile regional academy pages.
WORLDWIDE_KNOWLEDGE_SOURCES = [
    {"name": "CME Education", "url": "https://www.cmegroup.com/education.html", "lang": "en", "tier": "exchange"},
    {"name": "CFTC Education", "url": "https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/index.htm", "lang": "en", "tier": "regulator"},
    {"name": "CFTC COT Explanatory Notes", "url": "https://www.cftc.gov/MarketReports/CommitmentsofTraders/DisaggregatedExplanatoryNotes/index.htm", "lang": "en", "tier": "regulator"},
    {"name": "ICE Education", "url": "https://www.ice.com/education", "lang": "en", "tier": "exchange"},
    {"name": "ICE Trading Concepts", "url": "https://www.ice.com/support/education/sample-our-trading-market-education", "lang": "en", "tier": "exchange"},
    {"name": "Eurex Global Derivatives", "url": "https://www.eurex.com/ex-en/", "lang": "en/de", "tier": "exchange"},
    {"name": "NOAA Climate Data Online", "url": "https://www.ncei.noaa.gov/cdo-web/", "lang": "en", "tier": "weather"},
]


YOUTUBE_KNOWLEDGE_URLS = [
    # "https://www.youtube.com/watch?v=VIDEO_ID",
]
KNOWLEDGE_SOURCES.extend(WORLDWIDE_KNOWLEDGE_SOURCES)
# v2.9 — fonti didattiche aggiuntive studiate per il motore Level-to-Level.
# Sono fonti di metodologia/educazione: non vengono trattate come prove di
# redditività. Le regole derivate devono essere validate sullo storico.
KNOWLEDGE_SOURCES.extend([
    {"name": "Capital.com Commodities", "url": "https://capital.com/it-it/markets/commodities", "type": "web"},
    {"name": "Capital.com Trading Academy", "url": "https://capital.com/it-it/learn", "type": "web"},
    {"name": "IG Academy Technical Analysis", "url": "https://www.ig.com/it/scuola-di-trading/ig-academy/basi-analisi-tecnica", "type": "web"},
    {"name": "IG Support Resistance", "url": "https://www.ig.com/it/ig-academy/basi-analisi-tecnica/support-and-resistance", "type": "web"},
    {"name": "IG Breakout Fakeout", "url": "https://www.ig.com/it/ig-academy/basi-analisi-tecnica/breakouts-and-fakeouts", "type": "web"},
    {"name": "Borsa Italiana Commodity", "url": "https://www.borsaitaliana.it/notizie/sotto-la-lente/commodity.htm", "type": "web"},
])
KNOWLEDGE_CONCEPTS = {
    "trend": ["trend", "trending", "trendline", "higher high", "lower low"],
    "reversal": ["reversal", "inversion", "inversione", "turning point"],
    "support_resistance": ["support", "resistance", "supporto", "resistenza"],
    "breakout": ["breakout", "break out", "rottura", "range break"],
    "pullback": ["pullback", "retracement", "ritracciamento", "correction"],
    "momentum": ["momentum", "oscillator", "rsi", "macd", "stochastic"],
    "volatility": ["volatility", "volatilità", "atr", "average true range"],
    "risk": ["risk management", "risk/reward", "stop loss", "take profit", "money management"],
    "fundamental": ["fundamental", "supply", "demand", "inflation", "interest rate", "macro"],
}

HISTORY_SIZE = 4000
HORIZON = 5

STOP_ATR = 1.5
TP1_ATR = 2.0
TP2_ATR = 3.0
TP3_ATR = 4.5

# Limiti di volatilità per evitare SL/TP irrealistici quando l'ATR giornaliero
# viene gonfiato da spike o gap. Il Gold Engine resta invariato nella
# gestione della posizione; qui limitiamo soltanto la distanza iniziale.
LEVEL_PROFILES = {
    "Oro":          {"max_atr_pct": 0.025, "sl_pct": 0.015, "tp1_pct": 0.022, "tp2_pct": 0.038, "tp3_pct": 0.060},
    "Argento":      {"max_atr_pct": 0.045, "sl_pct": 0.022, "tp1_pct": 0.032, "tp2_pct": 0.055, "tp3_pct": 0.085},
    "Petrolio WTI": {"max_atr_pct": 0.060, "sl_pct": 0.020, "tp1_pct": 0.030, "tp2_pct": 0.050, "tp3_pct": 0.075},
    "Petrolio Brent":{"max_atr_pct": 0.060, "sl_pct": 0.020, "tp1_pct": 0.030, "tp2_pct": 0.050, "tp3_pct": 0.075},
    "Gas Naturale": {"max_atr_pct": 0.100, "sl_pct": 0.035, "tp1_pct": 0.050, "tp2_pct": 0.085, "tp3_pct": 0.125},
    "Rame":         {"max_atr_pct": 0.035, "sl_pct": 0.018, "tp1_pct": 0.028, "tp2_pct": 0.045, "tp3_pct": 0.065},
    "Grano":        {"max_atr_pct": 0.050, "sl_pct": 0.025, "tp1_pct": 0.035, "tp2_pct": 0.055, "tp3_pct": 0.080},
    "Mais":         {"max_atr_pct": 0.050, "sl_pct": 0.025, "tp1_pct": 0.035, "tp2_pct": 0.055, "tp3_pct": 0.080},
    "Caffè":        {"max_atr_pct": 0.060, "sl_pct": 0.030, "tp1_pct": 0.045, "tp2_pct": 0.070, "tp3_pct": 0.100},
}

LONG_THRESHOLD = 0.62
SHORT_THRESHOLD = 0.38

MIN_QUALITY = 45
MIN_CONFIDENCE = 58
MIN_SCORE = 65
MIN_RANK_MARGIN = 5

# ============================================================
# v7.0 GLOBAL / SESSION / RISK ENGINE
# ============================================================
SESSION_BANDS = {
    "NOTTE": (0, 7),
    "EUROPA": (7, 13),
    "USA_OVERLAP": (13, 18),
    "SERA": (18, 24),
}

# Quota iniziale del budget di rischio giornaliero. Il motore la ricalcola
# usando i dati storici intraday della singola commodity. Non rappresenta
# una percentuale da investire automaticamente sul capitale totale.
MAX_RISK_PER_TRADE_PCT = 0.50
MAX_DAILY_RISK_PCT = 1.00
MAX_COMMODITY_RISK_PCT = 0.75

# Weather regions are chosen around the main production/consumption hubs for
# each commodity. Coordinates can be overridden with environment variables later.
WEATHER_REGIONS = {
    "Gas Naturale": [("US South/Central", 31.0, -97.0), ("US Northeast", 41.0, -74.0)],
    "Grano": [("US Plains", 39.0, -98.0), ("Black Sea", 47.0, 35.0), ("EU", 50.0, 10.0)],
    "Mais": [("US Corn Belt", 41.0, -93.0), ("Brazil", -15.0, -52.0)],
    "Caffè": [("Brazil", -20.0, -47.0), ("Vietnam", 12.0, 108.0)],
    "Petrolio WTI": [("US Gulf", 29.0, -95.0)],
    "Petrolio Brent": [("North Sea", 57.0, 2.0), ("US Gulf", 29.0, -95.0)],
    "Oro": [("Global", 0.0, 0.0)],
    "Argento": [("Mexico/US", 25.0, -105.0)],
    "Rame": [("Chile/Peru", -20.0, -70.0), ("China", 30.0, 105.0)],
}

# Weather variables most relevant to commodity demand/supply.
WEATHER_VARIABLES = [
    "temperature_2m", "precipitation", "windspeed_10m",
]

# Simple causal priors. They are deliberately capped and can only nudge the
# main model until historical validation proves they deserve more weight.
WEATHER_PRIORS = {
    "Gas Naturale": {"hot": 1.0, "cold": 1.0, "wet": 0.0, "wind": 0.3},
    "Grano": {"hot": -0.8, "cold": -0.5, "wet": -0.8, "wind": -0.2},
    "Mais": {"hot": -0.8, "cold": -0.4, "wet": -0.6, "wind": -0.2},
    "Caffè": {"hot": -0.6, "cold": -0.9, "wet": 0.4, "wind": -0.2},
    "Petrolio WTI": {"hot": 0.1, "cold": 0.1, "wet": 0.0, "wind": -0.1},
    "Petrolio Brent": {"hot": 0.1, "cold": 0.1, "wet": 0.0, "wind": -0.1},
    "Oro": {"hot": 0.0, "cold": 0.0, "wet": 0.0, "wind": 0.0},
    "Argento": {"hot": 0.0, "cold": 0.0, "wet": 0.0, "wind": 0.0},
    "Rame": {"hot": -0.2, "cold": -0.1, "wet": -0.1, "wind": -0.1},
}

DISASTER_QUERIES = {
    "Gas Naturale": ["hurricane Gulf Mexico oil gas", "wildfire pipeline gas", "flood gas infrastructure"],
    "Petrolio WTI": ["hurricane Gulf Mexico oil production", "refinery outage hurricane", "pipeline disruption oil"],
    "Petrolio Brent": ["North Sea storm oil production", "Middle East storm shipping oil", "flood oil refinery"],
    "Grano": ["drought wheat crop", "frost wheat crop", "flood wheat harvest"],
    "Mais": ["drought corn crop", "frost corn crop", "flood corn harvest"],
    "Caffè": ["Brazil frost coffee crop", "Brazil drought coffee crop", "Vietnam flood coffee crop"],
    "Rame": ["Chile Peru earthquake mine copper", "flood copper mine", "wildfire mining copper"],
    "Oro": ["earthquake mine disruption gold", "flood gold mine", "wildfire mine disruption"],
    "Argento": ["Mexico mine disruption silver", "earthquake silver mine", "flood silver mine"],
}

GLOBAL_NEWS_QUERIES = [
    # Macro / rates / FX
    "global markets stocks bonds dollar Fed ECB BoE BoJ PBoC inflation recession",
    "US jobs payrolls Fed interest rates Treasury yields dollar commodities",
    "ECB rates euro inflation energy prices commodities",
    "China economy stimulus tariffs PMI property demand commodities",
    # Geopolitics / trade
    "geopolitics war sanctions tariffs trade conflict markets commodities",
    "Trump tariffs sanctions trade policy oil gold copper markets",
    "Ukraine Russia war sanctions oil gas wheat commodities",
    "Middle East Iran Israel US war shipping Hormuz oil gas gold",
    # Energy
    "OPEC OPEC+ oil supply production quotas Brent WTI",
    "Strait Hormuz tanker shipping disruption crude oil LNG",
    "IEA EIA oil inventories refinery outages diesel fuel oil",
    "natural gas LNG Europe Asia storage weather supply disruption",
    # Metals
    "gold silver precious metals central banks safe haven dollar rates",
    "copper China demand mine supply smelter inventories LME COMEX",
    # Agriculture / weather
    "wheat corn grain USDA crop drought frost flood Ukraine Russia",
    "coffee Brazil Vietnam crop frost drought exports arabica robusta",
    "agriculture commodities weather El Nino La Nina drought harvest",
    # Global risk / disasters / logistics
    "earthquake hurricane flood wildfire drought volcano commodities supply chain",
    "ports shipping freight Panama Suez Red Sea Hormuz supply chain commodities",
]

# Fonti/aree estere da interrogare tramite Google News RSS. Il risultato viene
# poi deduplicato per evitare che la stessa notizia pesi molte volte.
GLOBAL_NEWS_LOCALes = [
    ("en-US", "US:en"), ("en-GB", "GB:en"), ("en-AU", "AU:en"),
    ("en-IN", "IN:en"), ("zh-CN", "CN:zh-Hans"), ("ja-JP", "JP:ja"),
    ("de-DE", "DE:de"), ("fr-FR", "FR:fr"), ("es-ES", "ES:es"),
    ("it-IT", "IT:it"), ("pt-BR", "BR:pt-BR"), ("ru-RU", "RU:ru"),
]

# Query mirate a testate internazionali: Google News RSS permette di pescare
# articoli anche quando una singola API non espone direttamente quella fonte.
GLOBAL_SOURCE_QUERIES = [
    "site:reuters.com commodities oil gold copper markets",
    "site:ft.com commodities oil gold copper markets",
    "site:wsj.com markets commodities oil gold copper",
    "site:cnbc.com commodities oil gold copper markets",
    "site:bloomberg.com commodities oil gold copper markets",
    "site:bbc.com business oil gold commodities geopolitics",
    "site:aljazeera.com economy oil commodities geopolitics",
    "site:scmp.com China economy commodities copper oil",
    "site:nikkei.com markets commodities China oil metals",
    "site:theguardian.com business oil commodities markets",
    "site:dw.com economy oil commodities markets",
    "site:timesofindia.indiatimes.com commodities gold oil markets",
    "site:business-standard.com commodities oil gold copper",
    "site:theedgemalaysia.com commodities oil copper China",
]


SHOCK_TERMS = {
    "war", "attack", "missile", "invasion", "airstrike", "sanctions",
    "earthquake", "hurricane", "tsunami", "flood", "wildfire",
    "default", "bank collapse", "emergency", "halted production",
    "supply disruption", "strait closed", "hormuz closed",
    "opec emergency", "market crash", "circuit breaker",
}

GLOBAL_BULLISH_TERMS = {
    "risk-off", "safe haven", "supply disruption", "shortage", "sanctions",
    "war", "attack", "production cut", "stimulus", "rate cuts",
    "weaker dollar", "dollar falls",
}
GLOBAL_BEARISH_TERMS = {
    "risk-on", "ceasefire", "peace", "oversupply", "surplus",
    "production increase", "demand slowdown", "recession", "strong dollar",
}

COMMODITIES = {
    # Precious metals
    "Oro": "XAU/USD",
    "Argento": "XAG/USD",
    "Platino": "XPT/USD",
    "Palladio": "XPD/USD",
    # Energy
    "Petrolio WTI": "WTI/USD",
    "Petrolio Brent": "BRN/USD",
    "Gas Naturale": "NG/USD",
    "Benzina RBOB": "RB/USD",
    "Heating Oil": "HO/USD",
    # Industrial metals
    "Rame": "COPPER/USD",
    "Alluminio": "ALUMINUM/USD",
    "Nichel": "NICKEL/USD",
    "Zinco": "ZINC/USD",
    "Piombo": "LEAD/USD",
    # Grains / oilseeds
    "Grano": "WHEAT/USD",
    "Mais": "CORN/USD",
    "Soia": "SOYBEAN/USD",
    "Farina di soia": "SOYBEAN_MEAL/USD",
    "Olio di soia": "SOYBEAN_OIL/USD",
    "Avena": "OATS/USD",
    "Riso": "RICE/USD",
    # Soft commodities
    "Caffè": "COFFEE/USD",
    "Cacao": "COCOA/USD",
    "Zucchero": "SUGAR/USD",
    "Cotone": "COTTON/USD",
    "Succo d'arancia": "ORANGE_JUICE/USD",
    # Livestock
    "Bovini vivi": "LIVE_CATTLE/USD",
    "Maiali magri": "LEAN_HOGS/USD",
    "Feeder Cattle": "FEEDER_CATTLE/USD",
}

NEWS_TERMS = {
    "Oro": "gold OR bullion OR XAU", "Argento": "silver OR XAG",
    "Platino": "platinum OR XPT", "Palladio": "palladium OR XPD",
    "Petrolio WTI": "oil OR crude OR WTI", "Petrolio Brent": "oil OR crude OR Brent",
    "Gas Naturale": "natural gas", "Benzina RBOB": "gasoline OR RBOB",
    "Heating Oil": "heating oil OR diesel", "Rame": "copper",
    "Alluminio": "aluminum OR aluminium", "Nichel": "nickel", "Zinco": "zinc",
    "Piombo": "lead metal", "Grano": "wheat OR grain", "Mais": "corn OR maize",
    "Soia": "soybean OR soybeans", "Farina di soia": "soybean meal",
    "Olio di soia": "soybean oil", "Avena": "oats", "Riso": "rice",
    "Caffè": "coffee", "Cacao": "cocoa", "Zucchero": "sugar", "Cotone": "cotton",
    "Succo d'arancia": "orange juice", "Bovini vivi": "live cattle",
    "Maiali magri": "lean hogs OR hogs", "Feeder Cattle": "feeder cattle",
}

FEATURE_NAMES = [
    "ret_1", "ret_5", "ret_20", "ret_60",
    "trend", "rsi", "macd", "atr_pct",
    "volatility", "pressure", "breakout",
    "seasonality",
]


# ============================================================
# UTILITY
# ============================================================

def safe_float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def mean(values):
    values = [x for x in values if x is not None and math.isfinite(x)]
    return sum(values) / len(values) if values else 0.0


def std(values):
    values = [x for x in values if x is not None and math.isfinite(x)]
    if len(values) < 2:
        return 1.0
    m = mean(values)
    variance = sum((x - m) ** 2 for x in values) / (len(values) - 1)
    return max(math.sqrt(variance), 1e-8)


def sigmoid(x):
    x = max(-30, min(30, x))
    return 1 / (1 + math.exp(-x))


def clamp(value, low, high):
    return max(low, min(high, value))


def pct(value):
    return f"{value * 100:.1f}%"




# ============================================================
# v2.0 WEB / VIDEO KNOWLEDGE INGESTION
# ============================================================
class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self.skip += 1
    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style", "noscript", "svg"} and self.skip:
            self.skip -= 1
    def handle_data(self, data):
        if not self.skip:
            t = re.sub(r"\s+", " ", data).strip()
            if t:
                self.parts.append(t)

def _knowledge_cache_load():
    try:
        with open(KNOWLEDGE_CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}

def _knowledge_cache_save(cache):
    try:
        with open(KNOWLEDGE_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except Exception as exc:
        print(f"⚠️ Knowledge cache: {exc}")

def _youtube_video_id(url):
    parsed = urlparse(url)
    if parsed.hostname in {"youtu.be"}:
        return parsed.path.strip("/").split("/")[0]
    if parsed.hostname and "youtube.com" in parsed.hostname:
        q = parse_qs(parsed.query).get("v")
        if q:
            return q[0]
        m = re.search(r"/(?:shorts|embed)/([^/?]+)", parsed.path)
        if m:
            return m.group(1)
    return None

def fetch_knowledge_text(source):
    url = source.get("url", "")
    if not url:
        return ""
    # Optional YouTube transcript support.
    if source.get("type") == "youtube":
        video_id = _youtube_video_id(url)
        if not video_id:
            return ""
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            api = YouTubeTranscriptApi()
            transcript = api.fetch(video_id)
            return " ".join(getattr(x, "text", str(x)) for x in transcript)
        except Exception as exc:
            print(f"⚠️ Transcript YouTube non disponibile ({video_id}): {exc}")
            return ""

    try:
        # Keep the cycle responsive: unavailable educational pages must not block market analysis.
        r = requests.get(url, timeout=6, headers={"User-Agent": "CommoditiesBot/2.2"})
        r.raise_for_status()
        parser = _TextExtractor()
        parser.feed(r.text)
        return " ".join(parser.parts)
    except Exception as exc:
        print(f"⚠️ Fonte knowledge non disponibile: {url} | {exc}")
        return ""

def extract_knowledge_profile(text):
    text = (text or "").lower()
    counts = {}
    total = 0
    for concept, terms in KNOWLEDGE_CONCEPTS.items():
        count = sum(text.count(term.lower()) for term in terms)
        counts[concept] = count
        total += count
    return counts, total

def refresh_trading_knowledge():
    """Reads public educational pages/transcripts and stores only derived concept counts."""
    sources = list(KNOWLEDGE_SOURCES)
    for url in YOUTUBE_KNOWLEDGE_URLS:
        sources.append({"name": "YouTube", "url": url, "type": "youtube"})
    env_urls = os.getenv("TRADING_KNOWLEDGE_URLS", "")
    for url in [x.strip() for x in env_urls.split(",") if x.strip()]:
        sources.append({"name": "Custom", "url": url, "type": "youtube" if "youtube.com" in url or "youtu.be" in url else "web"})

    cache = _knowledge_cache_load()
    now = datetime.now(timezone.utc)
    profile = {k: 0 for k in KNOWLEDGE_CONCEPTS}
    usable = 0
    for source in sources:
        key = source["url"]
        cached = cache.get(key, {})
        age_hours = 999999
        try:
            age_hours = (now - datetime.fromisoformat(cached["updated_at"])).total_seconds() / 3600
        except Exception:
            pass
        counts = cached.get("counts") if age_hours < KNOWLEDGE_REFRESH_HOURS else None
        if counts is None:
            text = fetch_knowledge_text(source)
            counts, total = extract_knowledge_profile(text)
            cache[key] = {
                "name": source["name"],
                "updated_at": now.isoformat(),
                "counts": counts,
                "total": total,
                "status": "OK" if text else "NO_TEXT",
            }
        for k, v in counts.items():
            profile[k] += int(v or 0)
        if sum(counts.values()) > 0:
            usable += 1

    _knowledge_cache_save(cache)
    return {
        "sources": len(sources),
        "usable": usable,
        "profile": profile,
        "updated_at": now.isoformat(),
    }

def knowledge_bias_for_setup(knowledge, direction, analysis):
    """Small, capped educational prior. Market data always dominates."""
    profile = (knowledge or {}).get("profile", {})
    if not profile:
        return 0.0
    total = max(1, sum(profile.values()))
    # Knowledge increases validation quality rather than inventing a direction.
    emphasis = sum(profile.get(k, 0) for k in ("trend", "structure", "breakout", "pullback", "risk"))
    density = clamp(emphasis / total, 0, 1)
    base = 2.5 * density
    # Strong MTF alignment earns the full prior; weak alignment gets almost none.
    alignment = abs(safe_float(analysis.get("mtf_bias")))
    return base * clamp(alignment / 0.75, 0, 1)

# ============================================================
# v2.0 TRADING KNOWLEDGE ENGINE
# ============================================================
# Educational principles distilled from freely available trading
# material (trend, price action, support/resistance, breakout,
# pullback, momentum, volatility and risk management).
# The bot uses them as quantitative checks; it does NOT copy ebook
# text and it does not treat any source as a profit guarantee.
KNOWLEDGE_WEIGHTS = {
    "trend": 0.24,
    "structure": 0.20,
    "momentum": 0.16,
    "breakout_pullback": 0.16,
    "volatility": 0.08,
    "multi_timeframe": 0.10,
    "risk_reward": 0.06,
}

def trading_knowledge_engine(analysis):
    """Converts core trading-school principles into a 0-100 quality score."""
    tfs = analysis.get("timeframes", {})
    direction = analysis.get("setup_direction") or analysis.get("signal")
    if direction not in ("LONG", "SHORT"):
        return {"score": 0.0, "label": "NEUTRALE", "checks": []}

    vals = [tfs.get(tf, {}).get("direction", "NONE")
            for tf in ("4H", "1H", "15m", "5m", "1m")]
    same = sum(v == direction for v in vals)
    structural_same = sum(tfs.get(tf, {}).get("direction") == direction
                          for tf in ("4H", "1H", "15m"))
    fast_same = sum(tfs.get(tf, {}).get("direction") == direction
                    for tf in ("5m", "1m"))
    opposite = sum(v not in ("NONE", direction) for v in vals)

    trend = clamp(50 + (structural_same / 3.0) * 50 - opposite * 6, 0, 100)
    structure = clamp(
        50 + analysis.get("structural_same", 0) * 18
        - analysis.get("structural_opposite", 0) * 20, 0, 100
    )
    momentum = clamp(50 + analysis.get("mtf_bias", 0) * 50, 0, 100)
    breakout_pullback = 70 if analysis.get("entry_method") else 50
    volatility = 65 if analysis.get("atr") else 45
    mtf = clamp(50 + same * 10 - opposite * 8, 0, 100)

    entry = analysis.get("entry")
    stop = analysis.get("stop")
    tp3 = analysis.get("tp3")
    rr = 0.0
    if entry and stop and tp3:
        risk = abs(entry - stop)
        reward = abs(tp3 - entry)
        rr = reward / risk if risk else 0.0
    risk_reward = clamp(rr / 3.0 * 100, 0, 100)

    components = {
        "trend": trend,
        "structure": structure,
        "momentum": momentum,
        "breakout_pullback": breakout_pullback,
        "volatility": volatility,
        "multi_timeframe": mtf,
        "risk_reward": risk_reward,
    }
    score = sum(components[k] * KNOWLEDGE_WEIGHTS[k] for k in components)
    if score >= 75:
        label = "FORTE"
    elif score >= 60:
        label = "BUONA"
    elif score >= 45:
        label = "MISTA"
    else:
        label = "DEBOLE"

    return {
        "score": round(score, 1),
        "label": label,
        "components": {k: round(v, 1) for k, v in components.items()},
        "checks": [
            f"Trend strutturale {structural_same}/3",
            f"Conferme rapide {fast_same}/2",
            f"Conflitti MTF {opposite}",
            f"R/R TP3 {rr:.2f}",
        ],
    }


# ============================================================
# v2.0 RETRACEMENT vs REVERSAL ENGINE
# ============================================================
def load_direction_state():
    if not os.path.exists(DIRECTION_STATE_FILE):
        return {}
    try:
        with open(DIRECTION_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}

def save_direction_state(state):
    with open(DIRECTION_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def _direction_score_from_analysis(a):
    direction = a.get("setup_direction") or a.get("signal")
    if direction == "LONG":
        return float(a.get("score", 0))
    if direction == "SHORT":
        return -float(a.get("score", 0))
    return 0.0

def reversal_engine(name, analysis, previous=None):
    """
    Distinguishes a normal pullback from a genuine reversal.
    4H/1H/15m define the structural trend; 5m/1m are timing signals.
    """
    tfs = analysis.get("timeframes", {})
    current = analysis.get("setup_direction") or analysis.get("signal")
    score = _direction_score_from_analysis(analysis)
    prev_score = float((previous or {}).get("score", score))
    prev_dir = (previous or {}).get("direction", current)

    structural = [tfs.get(tf, {}).get("direction", "NONE")
                  for tf in ("4H", "1H", "15m")]
    fast = [tfs.get(tf, {}).get("direction", "NONE")
            for tf in ("5m", "1m")]

    # Structural trend remains intact -> retracement, not reversal.
    if prev_dir in ("LONG", "SHORT"):
        opposite = "SHORT" if prev_dir == "LONG" else "LONG"
        structural_opposite = sum(x == opposite for x in structural)
        fast_opposite = sum(x == opposite for x in fast)
        score_flip = (prev_score > 0 and score < -10) or (prev_score < 0 and score > 10)
        rapid_move = abs(score - prev_score) >= 28

        if structural_opposite == 0 and fast_opposite >= 1:
            stage = "RETRACEMENT"
            label = "🟡 RITRACCIAMENTO"
        elif structural_opposite <= 1 and not score_flip:
            stage = "RETRACEMENT"
            label = "🟡 RITRACCIAMENTO"
        elif structural_opposite >= 2 and fast_opposite >= 1 and (score_flip or rapid_move):
            stage = "CONFIRMED"
            label = "🔴 INVERSIONE CONFERMATA"
        elif structural_opposite >= 1 and (score_flip or rapid_move):
            stage = "POSSIBLE"
            label = "🟠 POSSIBILE INVERSIONE"
        elif rapid_move and fast_opposite >= 1:
            stage = "POSSIBLE"
            label = "🟠 POSSIBILE INVERSIONE"
        else:
            stage = "NORMAL"
            label = "🟢 TREND INTACT"
    else:
        stage = "NORMAL"
        label = "🟢 TREND IN FORMAZIONE"

    # A sudden move against an open position gets its own alert flag.
    sudden = False
    if prev_dir in ("LONG", "SHORT") and current in ("LONG", "SHORT"):
        if current != prev_dir and abs(score - prev_score) >= 35:
            sudden = True
    if abs(score - prev_score) >= 45:
        sudden = True

    return {
        "stage": stage,
        "label": label,
        "sudden": sudden,
        "direction": current,
        "previous_direction": prev_dir,
        "score_change": round(score - prev_score, 1),
        "previous_score": round(prev_score, 1),
        "current_score": round(score, 1),
    }


# ============================================================
# POSITION MEMORY
# ============================================================

def load_position():
    if not os.path.exists(POSITION_FILE):
        return None
    try:
        with open(POSITION_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data or None
    except Exception as error:
        print(f"⚠️ Impossibile leggere {POSITION_FILE}: {error}")
        return None


def save_position(position):
    with open(POSITION_FILE, "w", encoding="utf-8") as file:
        json.dump(position, file, indent=2, ensure_ascii=False)


def clear_position():
    if os.path.exists(POSITION_FILE):
        os.remove(POSITION_FILE)


# ============================================================
# TWELVE DATA
# ============================================================

COMMODITY_REFERENCE_CACHE = None

# ============================================================
# MULTI-SOURCE MARKET DATA
# Yahoo Finance = fonte gratuita principale (futures)
# Twelve Data   = fonte di confronto/fallback
# ============================================================
YAHOO_BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"
YAHOO_TICKERS = {
    "Oro": "GC=F", "Argento": "SI=F", "Platino": "PL=F", "Palladio": "PA=F",
    "Petrolio WTI": "CL=F", "Petrolio Brent": "BZ=F", "Gas Naturale": "NG=F",
    "Benzina RBOB": "RB=F", "Heating Oil": "HO=F",
    "Rame": "HG=F", "Alluminio": "ALI=F", "Nichel": "NICKEL=F", "Zinco": "ZNC=F",
    "Piombo": "LEAD=F",
    "Grano": "ZW=F", "Mais": "ZC=F", "Soia": "ZS=F", "Farina di soia": "ZM=F",
    "Olio di soia": "ZL=F", "Avena": "ZO=F", "Riso": "ZR=F",
    "Caffè": "KC=F", "Cacao": "CC=F", "Zucchero": "SB=F", "Cotone": "CT=F",
    "Succo d'arancia": "OJ=F", "Bovini vivi": "LE=F", "Maiali magri": "HE=F",
    "Feeder Cattle": "GF=F",
}
YAHOO_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"}
DATA_SOURCE_STATS = {}



def resolve_commodity_symbols():
    """Resolve the configured commodities against Twelve Data's live /commodities reference list."""
    global COMMODITY_REFERENCE_CACHE
    if COMMODITY_REFERENCE_CACHE is not None:
        return COMMODITY_REFERENCE_CACHE

    resolved = {}
    aliases = {
        "Oro": ["gold spot", "gold"], "Argento": ["silver spot", "silver"],
        "Platino": ["platinum spot", "platinum"], "Palladio": ["palladium spot", "palladium"],
        "Petrolio WTI": ["crude oil wti", "wti"], "Petrolio Brent": ["brent spot", "brent", "crude oil brent"],
        "Gas Naturale": ["natural gas", "natural gas spot"], "Benzina RBOB": ["rbob", "gasoline"],
        "Heating Oil": ["heating oil", "ultra low sulfur diesel", "ulsd"], "Rame": ["copper spot", "copper"],
        "Alluminio": ["aluminum", "aluminium"], "Nichel": ["nickel"], "Zinco": ["zinc"], "Piombo": ["lead"],
        "Grano": ["wheat", "wheat spot"], "Mais": ["corn", "corn spot", "maize"],
        "Soia": ["soybean", "soybeans"], "Farina di soia": ["soybean meal"], "Olio di soia": ["soybean oil"],
        "Avena": ["oats"], "Riso": ["rough rice", "rice"], "Caffè": ["coffee", "coffee spot"],
        "Cacao": ["cocoa"], "Zucchero": ["sugar", "sugar no. 11"], "Cotone": ["cotton"],
        "Succo d'arancia": ["orange juice", "frozen concentrated orange juice", "fcoj"],
        "Bovini vivi": ["live cattle"], "Maiali magri": ["lean hogs", "lean hog"], "Feeder Cattle": ["feeder cattle"],
    }
    try:
        response = requests.get(
            "https://api.twelvedata.com/commodities",
            params={"apikey": API_KEY, "format": "JSON"},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        items = data.get("data", data if isinstance(data, list) else [])
        if not isinstance(items, list):
            items = []

        normalized = []
        for item in items:
            if not isinstance(item, dict):
                continue
            symbol = str(item.get("symbol", "")).strip()
            text = " ".join(str(item.get(k, "")) for k in ("name", "description", "category")).lower()
            normalized.append((symbol, text))

        for name, configured in COMMODITIES.items():
            wanted = [x.lower() for x in aliases.get(name, [name])]
            match = None
            # Prefer exact configured symbol first if it is present in reference data.
            for symbol, text in normalized:
                if symbol.upper() == configured.upper():
                    match = symbol
                    break
            # Then match aliases against name/description/category.
            if match is None:
                for alias in wanted:
                    for symbol, text in normalized:
                        if alias in text:
                            match = symbol
                            break
                    if match:
                        break
            resolved[name] = match or configured

        COMMODITY_REFERENCE_CACHE = resolved
        print("📚 Simboli commodity risolti:")
        for name, symbol in resolved.items():
            print(f"   {name}: {symbol}")
        return resolved
    except Exception as error:
        print(f"⚠️ Reference /commodities non disponibile: {error}")
        COMMODITY_REFERENCE_CACHE = dict(COMMODITIES)
        return COMMODITY_REFERENCE_CACHE


def _normalize_yahoo_interval(interval):
    mapping = {"1day": "1d", "1day": "1d", "1h": "1h", "15min": "15m", "5min": "5m", "1min": "1m"}
    return mapping.get(interval, interval)


def _yahoo_range(interval):
    # Yahoo limita la profondità degli intervalli intraday.
    if interval == "1m":
        return "7d"
    if interval == "5m":
        return "60d"
    if interval == "15m":
        return "60d"
    if interval == "1h":
        return "730d"
    return "max"


def get_data_yahoo(name, interval="1day", outputsize=4000):
    ticker = YAHOO_TICKERS.get(name, name)
    yahoo_interval = _normalize_yahoo_interval(interval)
    params = {
        "range": _yahoo_range(yahoo_interval),
        "interval": yahoo_interval,
        "includePrePost": "false",
        "events": "div,splits",
    }
    response = requests.get(
        f"{YAHOO_BASE_URL}/{ticker}",
        params=params,
        headers=YAHOO_HEADERS,
        timeout=25,
    )
    response.raise_for_status()
    payload = response.json()
    result = (payload.get("chart") or {}).get("result")
    if not result:
        error = (payload.get("chart") or {}).get("error")
        raise RuntimeError(f"Yahoo {ticker}: {error or 'nessun risultato'}")

    result = result[0]
    timestamps = result.get("timestamp") or []
    quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
    opens = quote.get("open") or []
    highs = quote.get("high") or []
    lows = quote.get("low") or []
    closes = quote.get("close") or []
    volumes = quote.get("volume") or []

    candles = []
    for i, ts in enumerate(timestamps):
        close = safe_float(closes[i] if i < len(closes) else None)
        if close is None:
            continue
        dt = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        candles.append({
            "datetime": dt,
            "open": safe_float(opens[i] if i < len(opens) else None),
            "high": safe_float(highs[i] if i < len(highs) else None),
            "low": safe_float(lows[i] if i < len(lows) else None),
            "close": close,
            "volume": safe_float(volumes[i] if i < len(volumes) else None),
        })

    candles.sort(key=lambda x: x["datetime"] or "")
    if len(candles) > outputsize:
        candles = candles[-outputsize:]
    return candles


def _resample_4h(candles):
    if not candles:
        return []
    buckets = {}
    for candle in candles:
        try:
            dt = datetime.fromisoformat(candle["datetime"].replace("Z", "+00:00"))
        except Exception:
            continue
        hour = (dt.hour // 4) * 4
        key = dt.replace(hour=hour, minute=0, second=0, microsecond=0)
        buckets.setdefault(key, []).append(candle)

    result = []
    for key in sorted(buckets):
        rows = buckets[key]
        valid = [r for r in rows if r.get("close") is not None]
        if not valid:
            continue
        result.append({
            "datetime": key.isoformat(),
            "open": valid[0].get("open"),
            "high": max((r.get("high") for r in valid if r.get("high") is not None), default=valid[0]["close"]),
            "low": min((r.get("low") for r in valid if r.get("low") is not None), default=valid[0]["close"]),
            "close": valid[-1]["close"],
            "volume": sum((r.get("volume") or 0) for r in valid),
        })
    return result


def get_data_twelvedata(symbol, interval="1day", outputsize=4000):
    if not API_KEY:
        raise RuntimeError("TWELVE_DATA_API_KEY non configurata")
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "apikey": API_KEY,
        "order": "ASC",
    }
    response = requests.get(BASE_URL, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    if data.get("status") == "error":
        raise RuntimeError(data.get("message", "Errore Twelve Data"))
    candles = []
    for item in data.get("values", []):
        close = safe_float(item.get("close"))
        if close is None:
            continue
        candles.append({
            "datetime": item.get("datetime"),
            "open": safe_float(item.get("open")),
            "high": safe_float(item.get("high")),
            "low": safe_float(item.get("low")),
            "close": close,
            "volume": safe_float(item.get("volume")),
        })
    candles.sort(key=lambda x: x["datetime"] or "")
    return candles


def get_data(symbol, interval="1day", outputsize=4000):
    """Multi-source: Yahoo gratuito prima, Twelve Data come confronto/fallback."""
    # Recuperiamo il nome della commodity dal simbolo configurato/risolto.
    name = next((n for n, s in COMMODITIES.items() if s.upper() == str(symbol).upper()), None)
    if name is None:
        name = next((n for n, s in resolve_commodity_symbols().items() if s.upper() == str(symbol).upper()), None)
    if name is None:
        name = str(symbol)

    yahoo_error = None
    try:
        raw_interval = interval
        if interval == "4h":
            hourly = get_data_yahoo(name, "1h", max(outputsize * 4, 800))
            candles = _resample_4h(hourly)[-outputsize:]
        else:
            candles = get_data_yahoo(name, interval, outputsize)
        if len(candles) >= 10:
            DATA_SOURCE_STATS.setdefault(name, {})[interval] = "YAHOO"
            return candles
    except Exception as exc:
        yahoo_error = str(exc)

    # Fallback Twelve Data se Yahoo non risponde.
    try:
        candles = get_data_twelvedata(symbol, interval, outputsize)
        if len(candles) >= 10:
            DATA_SOURCE_STATS.setdefault(name, {})[interval] = "TWELVE DATA"
            if yahoo_error:
                print(f"   🔁 {name} {interval}: Yahoo KO → Twelve Data OK")
            return candles
    except Exception as td_error:
        if yahoo_error:
            raise RuntimeError(f"Yahoo: {yahoo_error} | Twelve Data: {td_error}")
        raise

    raise RuntimeError(f"Nessun provider dati disponibile per {name} {interval}")


def get_daily_data(symbol):
    return get_data(symbol, "1day", HISTORY_SIZE)


def compare_sources(name, symbol, candles):
    """Confronto provider senza trattare futures Yahoo e spot Twelve Data come prezzi identici."""
    result = {"sources": [], "status": "N/D", "difference_pct": None}
    yahoo_price = candles[-1]["close"] if candles else None
    if yahoo_price is not None:
        result["sources"].append({"name": "Yahoo Finance", "price": yahoo_price})

    if not API_KEY:
        result["status"] = "YAHOO ONLY"
        return result

    try:
        td = get_data_twelvedata(symbol, "1day", 5)
        if not td:
            result["status"] = "YAHOO ONLY (Twelve Data nessun dato)"
            return result
        td_price = td[-1]["close"]
        result["sources"].append({"name": "Twelve Data", "price": td_price})

        # Futures e spot possono avere livelli assoluti diversi. Confrontiamo
        # soprattutto la direzione dell'ultima variazione, non il prezzo assoluto.
        def ret(rows):
            if len(rows) < 2 or not rows[-2].get("close"):
                return None
            return rows[-1]["close"] / rows[-2]["close"] - 1.0

        y_ret = ret(candles)
        t_ret = ret(td)
        if y_ret is not None and t_ret is not None:
            result["difference_pct"] = abs(y_ret - t_ret) * 100.0
            same_direction = (y_ret == 0 and t_ret == 0) or (y_ret >= 0 and t_ret >= 0) or (y_ret < 0 and t_ret < 0)
            result["status"] = "CONFERMATO" if same_direction else "DISCREPANZA DIREZIONALE"
            return result

        result["status"] = "CONFRONTO PARZIALE"
        return result
    except Exception as exc:
        # Non mostriamo URL/query interne nel messaggio operativo.
        msg = str(exc).lower()
        if "404" in msg or "not found" in msg:
            result["status"] = "YAHOO ONLY (Twelve Data simbolo non disponibile)"
        elif "401" in msg or "403" in msg or "api key" in msg:
            result["status"] = "YAHOO ONLY (Twelve Data API key non valida)"
        else:
            result["status"] = "YAHOO ONLY (Twelve Data non disponibile)"
        return result


# ============================================================
# INDICATORS
# ============================================================

def sma(values, period):
    if len(values) < period:
        return None
    return mean(values[-period:])


def ema(values, period):
    if len(values) < period:
        return None

    multiplier = 2 / (period + 1)
    result = mean(values[:period])

    for value in values[period:]:
        result = (value - result) * multiplier + result

    return result


def rsi(values, period=14):
    if len(values) < period + 1:
        return 50.0

    gains = []
    losses = []

    for i in range(1, len(values)):
        change = values[i] - values[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    avg_gain = mean(gains[-period:])
    avg_loss = mean(losses[-period:])

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def atr(candles, period=14):
    if len(candles) < period + 1:
        return None

    ranges = []

    for i in range(1, len(candles)):
        high = candles[i]["high"]
        low = candles[i]["low"]
        previous = candles[i - 1]["close"]

        if high is None or low is None:
            continue

        ranges.append(max(
            high - low,
            abs(high - previous),
            abs(low - previous),
        ))

    return mean(ranges[-period:]) if len(ranges) >= period else None


def macd(values):
    if len(values) < 35:
        return 0.0

    fast = ema(values, 12)
    slow = ema(values, 26)

    if fast is None or slow is None:
        return 0.0

    return fast - slow


def return_pct(values, period):
    if len(values) <= period:
        return 0.0

    old = values[-period - 1]
    current = values[-1]

    if old == 0:
        return 0.0

    return current / old - 1


def volatility(values, period=20):
    if len(values) < period + 1:
        return 0.0

    returns = []
    start = len(values) - period

    for i in range(start, len(values)):
        previous = values[i - 1]
        if previous:
            returns.append(values[i] / previous - 1)

    return std(returns)


def pressure(candles, period=10):
    scores = []

    for candle in candles[-period:]:
        high = candle["high"]
        low = candle["low"]
        close = candle["close"]
        open_price = candle["open"]

        if None in (high, low, close, open_price) or high == low:
            continue

        scores.append((close - open_price) / (high - low))

    return mean(scores)


def breakout(values, period=20):
    if len(values) < period + 1:
        return 0.0

    current = values[-1]
    previous = values[-period - 1:-1]
    highest = max(previous)
    lowest = min(previous)
    distance = highest - lowest

    if distance == 0:
        return 0.0

    return ((current - lowest) / distance) * 2 - 1


# ============================================================
# STAGIONALITÀ / RIPETIZIONE NEGLI ANNI
# ============================================================

def historical_repetition(candles):
    """
    Cerca la ricorrenza del movimento a 5 giorni nello stesso
    periodo dell'anno. Usa tutta la storia disponibile.
    Restituisce direzione, frequenza, rendimento medio e campioni.
    """
    if len(candles) < 120:
        return {
            "score": 0.0,
            "frequency": 0.0,
            "avg_return": 0.0,
            "samples": 0,
            "years": 0,
            "direction": "NEUTRALE",
        }

    try:
        current_date = datetime.fromisoformat(
            candles[-1]["datetime"].replace("Z", "+00:00")
        )
    except Exception:
        return {
            "score": 0.0,
            "frequency": 0.0,
            "avg_return": 0.0,
            "samples": 0,
            "years": 0,
            "direction": "NEUTRALE",
        }

    # Finestra di circa 45 giorni attorno alla data corrente,
    # così confrontiamo un periodo stagionale e non solo il mese.
    target_day = current_date.timetuple().tm_yday
    samples = []

    for i in range(100, len(candles) - HORIZON):
        try:
            d = datetime.fromisoformat(
                candles[i]["datetime"].replace("Z", "+00:00")
            )
            day = d.timetuple().tm_yday
        except Exception:
            continue

        distance = abs(day - target_day)
        distance = min(distance, 366 - distance)

        if distance <= 22:
            current = candles[i]["close"]
            future = candles[i + HORIZON]["close"]

            if current:
                samples.append((future / current) - 1)

    if len(samples) < 5:
        return {
            "score": 0.0,
            "frequency": 0.0,
            "avg_return": 0.0,
            "samples": len(samples),
            "years": 0,
            "direction": "NEUTRALE",
        }

    positive = sum(1 for x in samples if x > 0)
    negative = sum(1 for x in samples if x < 0)
    frequency = max(positive, negative) / len(samples)
    avg_return = mean(samples)

    if positive > negative:
        direction = "LONG"
        raw_score = frequency
    elif negative > positive:
        direction = "SHORT"
        raw_score = -frequency
    else:
        direction = "NEUTRALE"
        raw_score = 0.0

    # Più la media storica è consistente, più il punteggio pesa.
    magnitude_factor = clamp(abs(avg_return) / 0.01, 0.0, 1.0)
    score = raw_score * magnitude_factor

    years = len({
        candles[i]["datetime"][:4]
        for i in range(100, len(candles) - HORIZON)
        if candles[i]["datetime"]
    })

    return {
        "score": score,
        "frequency": frequency,
        "avg_return": avg_return,
        "samples": len(samples),
        "years": years,
        "direction": direction,
    }


def seasonality(candles):
    return historical_repetition(candles)["score"]


# ============================================================
# FEATURES
# ============================================================

def build_features(candles):
    closes = [c["close"] for c in candles]

    if len(closes) < 60:
        return None

    current = closes[-1]

    sma20 = sma(closes, 20) or current
    sma50 = sma(closes, 50) or current

    trend = (sma20 / sma50 - 1) if sma50 else 0.0

    current_atr = atr(candles, 14)
    atr_pct = current_atr / current if current_atr and current else 0.0

    current_macd = macd(closes)
    macd_normalized = current_macd / current if current else 0.0

    return [
        return_pct(closes, 1),
        return_pct(closes, 5),
        return_pct(closes, 20),
        return_pct(closes, 60),
        trend,
        (rsi(closes, 14) - 50) / 50,
        macd_normalized,
        atr_pct,
        volatility(closes, 20),
        pressure(candles, 10),
        breakout(closes, 20),
        seasonality(candles),
    ]


# ============================================================
# DATASET
# ============================================================

def build_dataset(candles):
    dataset = []
    minimum_history = 60

    for i in range(minimum_history, len(candles) - HORIZON):
        history = candles[:i + 1]
        features = build_features(history)

        if features is None:
            continue

        current = candles[i]["close"]
        future = candles[i + HORIZON]["close"]

        if not current:
            continue

        future_return = future / current - 1

        if abs(future_return) < 0.002:
            continue

        dataset.append({
            "x": features,
            "y": 1 if future_return > 0 else 0,
            "return": future_return,
        })

    return dataset


# ============================================================
# STANDARDIZATION
# ============================================================

def standardize(train_x, other_x):
    if not train_x:
        return [], [], [], []

    count = len(train_x[0])
    means = []
    deviations = []

    for j in range(count):
        values = [row[j] for row in train_x]
        means.append(mean(values))
        deviations.append(std(values))

    def transform(row):
        return [
            (row[j] - means[j]) / deviations[j]
            for j in range(count)
        ]

    return (
        [transform(row) for row in train_x],
        [transform(row) for row in other_x],
        means,
        deviations,
    )


# ============================================================
# LOGISTIC MODEL
# ============================================================

def fit_model(X, y, epochs=700, learning_rate=0.035, regularization=0.08):
    if not X:
        return [], 0.0

    feature_count = len(X[0])
    weights = [0.0] * feature_count
    bias = 0.0
    n = len(X)

    for _ in range(epochs):
        gradients = [0.0] * feature_count
        bias_gradient = 0.0

        for row, target in zip(X, y):
            z = bias + sum(weights[j] * row[j] for j in range(feature_count))
            prediction = sigmoid(z)
            error = prediction - target

            bias_gradient += error

            for j in range(feature_count):
                gradients[j] += error * row[j]

        bias -= learning_rate * bias_gradient / n

        for j in range(feature_count):
            gradient = gradients[j] / n
            gradient += regularization * weights[j]
            weights[j] -= learning_rate * gradient

    return weights, bias


def predict(row, weights, bias):
    return sigmoid(
        bias + sum(weights[i] * row[i] for i in range(len(weights)))
    )


# ============================================================
# WALK-FORWARD BACKTEST
# ============================================================

def backtest(dataset):
    if len(dataset) < 80:
        return {
            "accuracy": 0,
            "win_rate": 0,
            "profit_factor": 0,
            "drawdown": 0,
            "trades": 0,
        }

    split = int(len(dataset) * 0.70)
    test = dataset[split:]
    predictions = []

    train_size = 1000
    step = 20

    for start in range(0, len(test), step):
        end = split + start
        training_start = max(0, end - train_size)

        training = dataset[training_start:end]
        testing = test[start:start + step]

        if len(training) < 300:
            continue

        X_train = [x["x"] for x in training]
        y_train = [x["y"] for x in training]
        X_test = [x["x"] for x in testing]

        X_train_scaled, X_test_scaled, _, _ = standardize(
            X_train, X_test
        )

        weights, bias = fit_model(X_train_scaled, y_train)

        for item, row in zip(testing, X_test_scaled):
            predictions.append({
                "probability": predict(row, weights, bias),
                "return": item["return"],
                "actual": item["y"],
            })

    if not predictions:
        return {
            "accuracy": 0,
            "win_rate": 0,
            "profit_factor": 0,
            "drawdown": 0,
            "trades": 0,
        }

    correct = 0
    trades = []
    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0

    for item in predictions:
        p = item["probability"]

        predicted = 1 if p >= 0.50 else 0
        if predicted == item["actual"]:
            correct += 1

        if p >= LONG_THRESHOLD:
            trade_return = item["return"]
        elif p <= SHORT_THRESHOLD:
            trade_return = -item["return"]
        else:
            continue

        trades.append(trade_return)
        equity *= 1 + trade_return
        peak = max(peak, equity)

        drawdown = equity / peak - 1
        max_drawdown = min(max_drawdown, drawdown)

    accuracy = correct / len(predictions)

    if trades:
        winners = [x for x in trades if x > 0]
        losers = [x for x in trades if x < 0]

        win_rate = len(winners) / len(trades)

        gross_profit = sum(winners)
        gross_loss = abs(sum(losers))

        profit_factor = (
            gross_profit / gross_loss
            if gross_loss > 0
            else 99
        )
    else:
        win_rate = 0
        profit_factor = 0

    return {
        "accuracy": accuracy,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "drawdown": max_drawdown,
        "trades": len(trades),
    }


# ============================================================
# FINAL MODEL
# ============================================================

def train_final(dataset):
    if len(dataset) < 40:
        return None

    X = [item["x"] for item in dataset]
    y = [item["y"] for item in dataset]

    X_scaled, _, means, deviations = standardize(X, X[-1:])

    weights, bias = fit_model(
        X_scaled,
        y,
        epochs=900,
        learning_rate=0.03,
        regularization=0.10,
    )

    return {
        "weights": weights,
        "bias": bias,
        "means": means,
        "deviations": deviations,
    }


def scale_current(features, model):
    result = []

    for i, value in enumerate(features):
        deviation = model["deviations"][i] or 1
        result.append((value - model["means"][i]) / deviation)

    return result


# ============================================================
# MODEL QUALITY
# ============================================================

def quality_score(bt):
    score = 50

    score += (bt["accuracy"] - 0.50) * 100
    score += (bt["win_rate"] - 0.50) * 70

    if bt["profit_factor"] > 1:
        score += (bt["profit_factor"] - 1) * 12

    score -= abs(bt["drawdown"]) * 40

    return clamp(score, 0, 100)


# ============================================================
# MULTI-TIMEFRAME
# ============================================================

def timeframe_direction(candles):
    if not candles or len(candles) < 60:
        return "NONE", 0

    closes = [c["close"] for c in candles]
    fast = ema(closes, 20)
    slow = ema(closes, 50)
    current = closes[-1]
    current_rsi = rsi(closes, 14)

    score = 0

    if fast and slow:
        if fast > slow:
            score += 2
        elif fast < slow:
            score -= 2

    if current > (fast or current):
        score += 1
    elif current < (fast or current):
        score -= 1

    if current_rsi > 55:
        score += 1
    elif current_rsi < 45:
        score -= 1

    if score >= 2:
        return "LONG", score
    if score <= -2:
        return "SHORT", score
    return "NONE", score


def get_multitimeframe(symbol):
    intervals = {
        "4H": "4h",
        "1H": "1h",
        "15m": "15min",
        "5m": "5min",
        "1m": "1min",
    }

    result = {}

    for name, interval in intervals.items():
        try:
            candles = get_data(symbol, interval, 120)
            direction, score = timeframe_direction(candles)
            result[name] = {
                "direction": direction,
                "score": score,
            }
        except Exception as error:
            print(f"   ⚠️ {name}: {error}")
            result[name] = {
                "direction": "NONE",
                "score": 0,
            }

    return result


# ============================================================
# USD / UUP
# ============================================================

def analyze_usd():
    try:
        candles = get_data("UUP:NYSE", "1day", 120)
        direction, score = timeframe_direction(candles)

        # Per commodities quotate in USD:
        # USD forte tende generalmente a essere un vento contrario.
        if direction == "LONG":
            impact = -1
            label = "FORTE / SFAVOREVOLE"
        elif direction == "SHORT":
            impact = 1
            label = "DEBOLE / FAVOREVOLE"
        else:
            impact = 0
            label = "NEUTRO"

        return {
            "direction": direction,
            "score": score,
            "impact": impact,
            "label": label,
        }
    except Exception as error:
        print(f"⚠️ UUP non disponibile: {error}")
        return {
            "direction": "NONE",
            "score": 0,
            "impact": 0,
            "label": "NON DISPONIBILE",
        }


# ============================================================
# NEWS
# ============================================================

def analyze_news(name):
    """News robusta: NewsAPI -> Google News RSS. Non nasconde l'errore."""
    import urllib.parse
    import xml.etree.ElementTree as ET

    query = NEWS_TERMS.get(name, name)
    errors = []
    articles = []
    source = "NONE"

    if NEWS_API_KEY:
        try:
            response = requests.get(
                NEWS_URL,
                params={
                    "q": query,
                    "apiKey": NEWS_API_KEY,
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": 20,
                },
                timeout=20,
            )
            data = response.json()
            if response.ok and data.get("status") == "ok":
                articles = data.get("articles", []) or []
                source = "NEWSAPI"
            else:
                errors.append(f"NewsAPI {response.status_code}: {data.get('code', data.get('message', 'errore'))}")
        except Exception as error:
            errors.append(f"NewsAPI: {error}")
    else:
        errors.append("NEWS_API_KEY assente")

    if not articles:
        try:
            url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({
                "q": query,
                "hl": "en-US",
                "gl": "US",
                "ceid": "US:en",
            })
            response = requests.get(
                url,
                timeout=15,
                headers={"User-Agent": "Mozilla/5.0 (compatible; CommoditiesBot/7.2)"},
            )
            response.raise_for_status()
            root = ET.fromstring(response.text)
            for item in root.findall(".//item")[:20]:
                articles.append({
                    "title": item.findtext("title", ""),
                    "description": item.findtext("description", ""),
                })
            if articles:
                source = "GOOGLE RSS"
        except Exception as error:
            errors.append(f"Google RSS: {error}")

    if not articles:
        return {
            "score": 0.0,
            "label": "NON DISPONIBILI",
            "count": 0,
            "status": " | ".join(errors)[:220],
            "source": "NONE",
        }

    positive_words = {
        "rise", "rises", "rising", "gain", "gains", "bullish", "surge",
        "strong", "higher", "increase", "increases", "shortage", "demand",
        "support", "cuts", "disruption", "disruptions",
    }
    negative_words = {
        "fall", "falls", "falling", "drop", "drops", "bearish", "weak",
        "lower", "decrease", "decreases", "oversupply", "collapse", "concern",
        "recession", "surplus", "peace", "ceasefire",
    }

    total = 0
    for article in articles:
        text = f"{article.get('title', '')} {article.get('description', '')}".lower()
        words = set(text.replace("/", " ").replace("-", " ").split())
        pos = len(words & positive_words)
        neg = len(words & negative_words)
        if pos > neg:
            total += 1
        elif neg > pos:
            total -= 1

    normalized = clamp(total / max(len(articles), 1), -1, 1)
    label = "POSITIVE" if normalized >= 0.20 else "NEGATIVE" if normalized <= -0.20 else "NEUTRALI"

    return {
        "score": normalized,
        "label": label,
        "count": len(articles),
        "status": "OK",
        "source": source,
    }


# ============================================================
# POLITICAL / GEOPOLITICAL IMPACT
# ============================================================

def political_impact(name):
    """Impatto politico/geopolitico specifico, con fallback Google RSS."""
    import urllib.parse
    import xml.etree.ElementTree as ET

    queries = {
        "Oro": "gold Trump tariffs Fed geopolitics sanctions war",
        "Argento": "silver Trump tariffs industrial demand geopolitics",
        "Petrolio WTI": "oil WTI OPEC Trump sanctions war tariffs",
        "Petrolio Brent": "Brent oil OPEC Trump sanctions war tariffs",
        "Gas Naturale": "natural gas geopolitics LNG sanctions Europe Trump",
        "Rame": "copper Trump tariffs China geopolitics mining",
        "Grano": "wheat grain Trump tariffs Russia Ukraine geopolitics",
        "Mais": "corn maize Trump tariffs agriculture geopolitics",
        "Caffè": "coffee Brazil tariffs Trump trade weather geopolitics",
    }
    query = queries.get(name, name)
    positive = {"tariff", "tariffs", "sanction", "sanctions", "war", "conflict", "attack", "shortage", "disruption", "embargo", "opec cut", "cut production", "trade war", "escalation"}
    negative = {"ceasefire", "peace", "de-escalation", "oversupply", "surplus", "production increase", "supply increase", "opec increase", "truce"}

    articles = []
    source = "NONE"
    error = None

    if NEWS_API_KEY:
        try:
            response = requests.get(
                NEWS_URL,
                params={"q": query, "apiKey": NEWS_API_KEY, "language": "en", "sortBy": "publishedAt", "pageSize": 20},
                timeout=20,
            )
            data = response.json()
            if response.ok and data.get("status") == "ok":
                articles = data.get("articles", []) or []
                source = "NEWSAPI"
            else:
                error = f"NewsAPI {response.status_code}"
        except Exception as exc:
            error = str(exc)

    if not articles:
        try:
            url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"})
            response = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (compatible; CommoditiesBot/7.2)"})
            response.raise_for_status()
            root = ET.fromstring(response.text)
            for item in root.findall(".//item")[:20]:
                articles.append({"title": item.findtext("title", ""), "description": item.findtext("description", "")})
            if articles:
                source = "GOOGLE RSS"
        except Exception as exc:
            error = f"{error or ''} Google RSS: {exc}".strip()

    if not articles:
        return {"score": 0.0, "direction": "NEUTRALE", "count": 0, "source": "NONE", "status": error or "NESSUNA FONTE"}

    total = 0
    for article in articles:
        text = f"{article.get('title', '')} {article.get('description', '')}".lower()
        pos = sum(1 for w in positive if w in text)
        neg = sum(1 for w in negative if w in text)
        total += 1 if pos > neg else -1 if neg > pos else 0

    normalized = clamp(total / max(len(articles), 1), -1, 1)
    direction = "FAVOREVOLE" if normalized >= 0.20 else "SFAVOREVOLE" if normalized <= -0.20 else "NEUTRALE"
    return {"score": normalized, "direction": direction, "count": len(articles), "source": source, "status": "OK"}


# ============================================================
# GLOBAL MARKET INTELLIGENCE ENGINE
# ============================================================

def _fetch_rss_articles(query, limit=20, hl="en-US", ceid="US:en"):
    import urllib.parse
    import xml.etree.ElementTree as ET
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({
        "q": query,
        "hl": hl,
        "gl": ceid.split(":")[0],
        "ceid": ceid,
    })
    response = requests.get(
        url,
        timeout=15,
        headers={"User-Agent": "Mozilla/5.0 (compatible; CommoditiesBot/7.2)"},
    )
    response.raise_for_status()
    root = ET.fromstring(response.text)
    articles = []
    for item in root.findall(".//item")[:limit]:
        title = item.findtext("title", "")
        desc = item.findtext("description", "")
        link = item.findtext("link", "")
        pub = item.findtext("pubDate", "")
        source_node = item.find("source")
        source_name = source_node.text.strip() if source_node is not None and source_node.text else "Google News"
        articles.append({
            "title": title,
            "description": desc,
            "published": pub,
            "url": link,
            "source": {"name": source_name, "url": link},
            "provider": "GOOGLE RSS",
            "locale": hl,
        })
    return articles


def _article_source_name(article):
    src = article.get("source", "")
    if isinstance(src, dict):
        return str(src.get("name", "Google News"))
    return str(src or "Google News")


def _article_key(article):
    title = str(article.get("title", "")).strip().lower()
    # Normalizziamo titoli per ridurre duplicati cross-lingua/provider.
    return " ".join(title.split())


def global_market_intelligence():
    """Global multi-source intelligence: macro, geopolitica, energia, metalli,
    agricoltura, disastri e supply-chain, con fonti/lingue multiple e consenso
    prima di classificare un evento come SHOCK.
    """
    articles = []
    sources = []
    errors = []

    # 1) NewsAPI: utile se l'utente ha configurato una chiave.
    if NEWS_API_KEY:
        for query in GLOBAL_NEWS_QUERIES:
            try:
                response = requests.get(
                    NEWS_URL,
                    params={
                        "q": query,
                        "apiKey": NEWS_API_KEY,
                        "language": "en",
                        "sortBy": "publishedAt",
                        "pageSize": 50,
                    },
                    timeout=20,
                )
                data = response.json()
                if response.ok and data.get("status") == "ok":
                    for a in data.get("articles", []) or []:
                        a["provider"] = "NEWSAPI"
                    articles.extend(data.get("articles", []) or [])
                    sources.append("NEWSAPI")
                else:
                    errors.append(f"NewsAPI {response.status_code}")
            except Exception as exc:
                errors.append(f"NewsAPI: {exc}")

    # 2) Google News RSS: 12 aree linguistiche/geografiche.
    #    Non usiamo una sola query/locale: questo amplia molto la copertura.
    for query in GLOBAL_NEWS_QUERIES:
        for hl, ceid in GLOBAL_NEWS_LOCALes:
            try:
                articles.extend(_fetch_rss_articles(query, 8, hl, ceid))
                sources.append(f"RSS:{hl}")
            except Exception as exc:
                errors.append(f"RSS {hl}: {exc}")

    # 3) Query specifiche per testata internazionale, con meno peso individuale.
    for query in GLOBAL_SOURCE_QUERIES:
        try:
            articles.extend(_fetch_rss_articles(query, 10, "en-US", "US:en"))
            sources.append("RSS:SOURCES")
        except Exception as exc:
            errors.append(f"RSS sources: {exc}")

    # Deduplica aggressiva: una notizia ripresa da 10 feed vale come una notizia,
    # mentre il numero di fonti viene conservato separatamente.
    unique = []
    seen = set()
    for article in articles:
        title = str(article.get("title", "")).strip()
        key = _article_key(article)
        if title and key and key not in seen:
            seen.add(key)
            unique.append(article)

    unique = unique[:300]

    # Analisi globale con distinzione tra eventi confermati e semplici keyword hit.
    total = 0.0
    shock_candidates = []
    domain_counts = {}
    confirmed_shock_sources = {}

    for article in unique:
        text = f"{article.get('title', '')} {article.get('description', '')}".lower()
        source_name = _article_source_name(article)
        domain_counts[source_name] = domain_counts.get(source_name, 0) + 1

        pos = sum(1 for w in GLOBAL_BULLISH_TERMS if w in text)
        neg = sum(1 for w in GLOBAL_BEARISH_TERMS if w in text)
        if pos > neg:
            total += 1
        elif neg > pos:
            total -= 1

        hits = [term for term in SHOCK_TERMS if term in text]
        if hits:
            shock_candidates.append({
                "title": article.get("title", ""),
                "terms": hits[:4],
                "source": source_name,
                "provider": article.get("provider", "RSS"),
            })
            # Raggruppamento approssimato dell'evento per parole chiave comuni.
            event_key = next((t for t in hits if t in {
                "war", "attack", "missile", "airstrike", "invasion",
                "strait closed", "hormuz closed", "supply disruption",
                "earthquake", "hurricane", "flood", "wildfire",
                "opec emergency", "market crash", "bank collapse",
            }), hits[0])
            confirmed_shock_sources.setdefault(event_key, set()).add(source_name)

    denominator = max(min(len(unique), 300), 1)
    score = clamp(total / denominator, -1, 1)

    # SHOCK richiede consenso: almeno 3 articoli distinti e 2 fonti/editori
    # per uno stesso evento, oppure una fonte primaria/ufficiale molto forte.
    strong_events = []
    for event_key, srcs in confirmed_shock_sources.items():
        candidate_count = sum(1 for x in shock_candidates if event_key in x["terms"])
        if candidate_count >= 3 and len(srcs) >= 2:
            strong_events.append({"event": event_key, "articles": candidate_count, "sources": len(srcs)})

    shock_count = len(strong_events)
    raw_shock_hits = len(shock_candidates)
    shock_intensity = clamp((0.60 * min(shock_count / 3.0, 1.0)) + (0.40 * min(raw_shock_hits / 15.0, 1.0)), 0, 1)

    if shock_count >= 2:
        mode = "SHOCK"
    elif shock_count >= 1 or raw_shock_hits >= 6:
        mode = "ALERT"
    else:
        mode = "NORMAL"

    return {
        "score": score,
        "articles": unique,
        "count": len(unique),
        "shock_count": shock_count,
        "raw_shock_hits": raw_shock_hits,
        "shock_intensity": shock_intensity,
        "mode": mode,
        "top_shocks": shock_candidates[:8],
        "confirmed_events": strong_events[:8],
        "source": "+".join(sorted(set(sources))) if sources else "NONE",
        "source_count": len(domain_counts),
        "source_names": sorted(domain_counts, key=domain_counts.get, reverse=True)[:15],
        "status": "OK" if unique else (" | ".join(errors)[:220] or "NESSUNA FONTE"),
    }


def commodity_global_impact(name, global_intel):
    """Impatto globale specifico per commodity.
    Uno shock generale non blocca automaticamente tutte le materie prime:
    l'evento deve essere rilevante per lo strumento e sufficientemente confermato.
    """
    base = safe_float(global_intel.get("score")) or 0.0
    articles = global_intel.get("articles", []) or []

    profiles = {
        "Oro": {"keys": {"gold", "safe haven", "war", "attack", "sanctions", "risk-off", "rate cuts", "weaker dollar", "central bank"},
                "shock": {"war", "attack", "missile", "invasion", "sanctions", "bank collapse", "market crash"}},
        "Argento": {"keys": {"silver", "industrial demand", "stimulus", "weaker dollar", "rate cuts", "risk-off"},
                    "shock": {"war", "attack", "supply disruption", "market crash"}},
        "Petrolio WTI": {"keys": {"opec", "oil", "crude", "hormuz", "supply disruption", "sanctions", "attack", "brent"},
                         "shock": {"hormuz closed", "strait closed", "supply disruption", "opec emergency", "attack", "missile", "war"}},
        "Petrolio Brent": {"keys": {"opec", "oil", "crude", "hormuz", "supply disruption", "sanctions", "attack", "brent"},
                           "shock": {"hormuz closed", "strait closed", "supply disruption", "opec emergency", "attack", "missile", "war"}},
        "Gas Naturale": {"keys": {"lng", "natural gas", "gas", "cold", "heat", "supply disruption", "sanctions"},
                          "shock": {"supply disruption", "lng disruption", "pipeline", "explosion", "war"}},
        "Rame": {"keys": {"copper", "china", "stimulus", "industrial demand", "supply disruption", "mine"},
                 "shock": {"mine", "mine strike", "supply disruption", "earthquake", "flood", "war"}},
        "Grano": {"keys": {"wheat", "grain", "drought", "flood", "ukraine", "russia", "supply disruption"},
                  "shock": {"drought", "flood", "crop failure", "supply disruption", "war"}},
        "Mais": {"keys": {"corn", "maize", "drought", "flood", "crop", "supply disruption"},
                 "shock": {"drought", "flood", "crop failure", "supply disruption"}},
        "Caffè": {"keys": {"coffee", "brazil", "drought", "frost", "crop", "supply disruption"},
                  "shock": {"drought", "frost", "crop failure", "supply disruption"}},
    }
    prof=profiles.get(name, {"keys":set(), "shock":set()})
    relevant=[]
    relevant_shocks=[]
    for a in articles[:120]:
        text=(str(a.get("title", ""))+" "+str(a.get("description", ""))).lower()
        if any(k in text for k in prof["keys"]):
            relevant.append(a)
            hits=[k for k in prof["shock"] if k in text]
            if hits:
                relevant_shocks.append((a,hits))

    # Un evento viene considerato specifico solo se compare in almeno 3 articoli
    # distinti provenienti da almeno 2 fonti/editori. Keyword isolate = ALERT, non SHOCK.
    groups={}
    for a,hits in relevant_shocks:
        key=hits[0]
        src=_article_source_name(a)
        groups.setdefault(key, {"articles":0,"sources":set()})
        groups[key]["articles"] += 1
        groups[key]["sources"].add(src)
    confirmed=[]
    for key,g in groups.items():
        real_sources={x for x in g["sources"] if x and x.upper() not in {"NONE","UNKNOWN","N/D"}}
        if g["articles"] >= 3 and len(real_sources) >= 2:
            confirmed.append({"event":key,"articles":g["articles"],"sources":len(real_sources)})

    # Direzione specifica: solo gli articoli rilevanti pesano fortemente.
    pos_terms = {
        "Oro":{"safe haven","war","attack","sanctions","risk-off","rate cuts","weaker dollar"},
        "Argento":{"industrial demand","stimulus","weaker dollar","rate cuts","risk-off"},
        "Petrolio WTI":{"opec","supply disruption","hormuz","oil","crude","sanctions","attack"},
        "Petrolio Brent":{"opec","supply disruption","hormuz","oil","crude","sanctions","attack"},
        "Gas Naturale":{"lng","gas","cold","heat","supply disruption","sanctions"},
        "Rame":{"china","stimulus","industrial demand","supply disruption","mine"},
        "Grano":{"wheat","grain","drought","flood","ukraine","russia","supply disruption"},
        "Mais":{"corn","maize","drought","flood","crop","supply disruption"},
        "Caffè":{"coffee","brazil","drought","frost","crop","supply disruption"},
    }
    neg_terms = {
        "Oro":{"risk-on","peace","ceasefire","strong dollar"},
        "Argento":{"strong dollar","recession","industrial slowdown"},
        "Petrolio WTI":{"ceasefire","oversupply","demand slowdown","recession"},
        "Petrolio Brent":{"ceasefire","oversupply","demand slowdown","recession"},
        "Gas Naturale":{"oversupply","warm weather","demand slowdown"},
        "Rame":{"china slowdown","recession","industrial slowdown","strong dollar"},
        "Grano":{"harvest increase","oversupply","strong dollar"},
        "Mais":{"crop increase","oversupply","strong dollar"},
        "Caffè":{"harvest increase","oversupply","strong dollar"},
    }
    rel_text=" ".join(str(a.get("title",""))+" "+str(a.get("description","")) for a in relevant).lower()
    pos=sum(1 for t in pos_terms.get(name,set()) if t in rel_text)
    neg=sum(1 for t in neg_terms.get(name,set()) if t in rel_text)
    event_bias=clamp((pos-neg)/6.0,-1,1)
    score=clamp(0.25*base+0.75*event_bias,-1,1)
    if len(confirmed)>=1:
        mode="ALERT"
    elif relevant_shocks and len(relevant_shocks)>=3:
        mode="ALERT"
    else:
        mode="NORMAL"
    if len(confirmed)>=2:
        mode="SHOCK"
    intensity=clamp(0.65*min(len(confirmed)/2.0,1.0)+0.35*min(len(relevant_shocks)/8.0,1.0),0,1)
    direction="FAVOREVOLE" if score>=0.20 else "SFAVOREVOLE" if score<=-0.20 else "NEUTRALE"
    return {"score":score,"direction":direction,"mode":mode,"shock_intensity":intensity,
            "count":len(relevant),"relevant_articles":len(relevant),"shock_count":len(confirmed),
            "confirmed_events":confirmed[:6]}


# ============================================================
# SESSION / HISTORICAL INTRADAY ENGINE
# ============================================================

def session_engine(name, symbol, current_direction="NONE"):
    """Four intraday windows; weights come from historical 1h returns, not fixed guesses."""
    try:
        hourly = get_data(symbol, "1h", 4000)
    except Exception as exc:
        return {
            "bands": {}, "best_band": "N/D", "current_band": "N/D",
            "quality": 50.0, "allocation_pct": 0.25,
            "status": f"NON DISPONIBILE: {str(exc)[:120]}"
        }

    rows = {k: [] for k in SESSION_BANDS}
    now_utc = datetime.now(timezone.utc)
    # Current hour converted to the same UTC bucket. User-facing label is Italian time;
    # using UTC internally avoids DST errors. The four windows are applied to local Italy.
    try:
        from zoneinfo import ZoneInfo
        local_now = now_utc.astimezone(ZoneInfo("Europe/Rome"))
        current_hour = local_now.hour
        current_band = next((b for b, (start, end) in SESSION_BANDS.items() if start <= current_hour < end), "SERA")
    except Exception:
        current_hour = now_utc.hour
        current_band = next((b for b, (start, end) in SESSION_BANDS.items() if start <= current_hour < end), "SERA")

    for i in range(len(hourly) - 3):
        c = hourly[i]
        n = hourly[i + 3]
        try:
            dt = datetime.fromisoformat(c["datetime"].replace("Z", "+00:00"))
            from zoneinfo import ZoneInfo
            hour_local = dt.astimezone(ZoneInfo("Europe/Rome")).hour
        except Exception:
            continue
        band = next((b for b, (start, end) in SESSION_BANDS.items() if start <= hour_local < end), "SERA")
        close = c.get("close")
        future = n.get("close")
        if close:
            rows[band].append((future / close) - 1)

    bands = {}
    for band, values in rows.items():
        if len(values) < 20:
            bands[band] = {"samples": len(values), "win_rate": 0.50, "avg_return": 0.0, "quality": 50.0, "allocation": 0.25}
            continue
        if current_direction == "SHORT":
            directional = [-x for x in values]
        else:
            directional = values
        win_rate = sum(1 for x in directional if x > 0) / len(directional)
        avg_return = mean(directional)
        vol = std(values)
        edge = clamp((win_rate - 0.50) * 2, -1, 1)
        reward_risk = clamp(abs(avg_return) / max(vol, 1e-8), 0, 1)
        quality = clamp(50 + edge * 35 + reward_risk * 15, 0, 100)
        bands[band] = {
            "samples": len(values), "win_rate": win_rate,
            "avg_return": avg_return, "quality": quality,
            "allocation": 0.25,
        }

    qualities = {b: v["quality"] for b, v in bands.items()}
    total_quality = sum(max(q, 1) for q in qualities.values()) or 1
    for band in bands:
        bands[band]["allocation"] = qualities[band] / total_quality

    best_band = max(bands, key=lambda b: bands[b]["quality"])
    worst_band = min(bands, key=lambda b: bands[b]["quality"])
    current_quality = bands[current_band]["quality"]
    # Allocation is a share of the daily risk budget, capped for safety.
    raw_alloc = bands[current_band]["allocation"] * 100
    allocation_pct = clamp(raw_alloc * (current_quality / 100), 5, 50)

    return {
        "bands": bands,
        "best_band": best_band,
        "worst_band": worst_band,
        "exit_band": worst_band,
        "current_band": current_band,
        "quality": current_quality,
        "allocation_pct": allocation_pct,
        "status": "OK",
        "sample_hours": len(hourly),
    }


# ============================================================
# CYCLICAL MARKET ENGINE
# ============================================================

def cyclical_market_engine(candles, direction="NONE"):
    """Misura cicli intraday, settimanali, mensili e stagionali.
    Usa solo osservazioni passate rispetto all'ultima candela disponibile.
    Se il campione è insufficiente, riduce il peso invece di inventare un edge.
    """
    if len(candles) < 120:
        return {"score": 0.0, "direction": "NEUTRALE", "confidence": 0.0,
                "intraday": {}, "weekly": {}, "monthly": {}, "seasonal": {},
                "samples": 0, "status": "CAMPIONE INSUFFICIENTE"}

    def parse_dt(row):
        try:
            return datetime.fromisoformat(str(row["datetime"]).replace("Z", "+00:00"))
        except Exception:
            return None

    current_dt = parse_dt(candles[-1])
    if current_dt is None:
        return {"score": 0.0, "direction": "NEUTRALE", "confidence": 0.0,
                "intraday": {}, "weekly": {}, "monthly": {}, "seasonal": {},
                "samples": 0, "status": "DATE NON DISPONIBILE"}

    # Il ciclo intraday viene stimato su rendimenti a 3 ore, raggruppati per ora locale.
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("Europe/Rome")
    except Exception:
        tz = timezone.utc

    horizons = []
    for i in range(len(candles) - 3):
        d = parse_dt(candles[i])
        c = safe_float(candles[i].get("close"))
        f = safe_float(candles[i + 3].get("close"))
        if d is None or not c or f is None:
            continue
        horizons.append((d, f / c - 1.0))

    current_local = current_dt.astimezone(tz)
    current_hour = current_local.hour
    hour_rows = []
    for d, r in horizons:
        if d.astimezone(tz).hour == current_hour:
            hour_rows.append(r)
    if direction == "SHORT":
        hour_rows = [-r for r in hour_rows]

    # Weekly cycle: same weekday, forward 1 trading day.
    weekly_rows = []
    for i in range(len(candles) - 24):
        d = parse_dt(candles[i])
        if d is None or d.astimezone(tz).weekday() != current_local.weekday():
            continue
        c = safe_float(candles[i].get("close")); f = safe_float(candles[i + 24].get("close"))
        if c and f:
            weekly_rows.append(f / c - 1.0)
    if direction == "SHORT":
        weekly_rows = [-r for r in weekly_rows]

    # Monthly cycle: same month/day bucket (±7 days), 5-day forward return.
    seasonal_rows = []
    target_doy = current_local.timetuple().tm_yday
    for i in range(20, len(candles) - 5):
        d = parse_dt(candles[i])
        if d is None:
            continue
        local = d.astimezone(tz)
        doy = local.timetuple().tm_yday
        dist = abs(doy - target_doy)
        dist = min(dist, 366 - dist)
        if dist <= 7:
            c = safe_float(candles[i].get("close")); f = safe_float(candles[i + 5].get("close"))
            if c and f:
                seasonal_rows.append(f / c - 1.0)
    if direction == "SHORT":
        seasonal_rows = [-r for r in seasonal_rows]

    monthly_rows = []
    for i in range(len(candles) - 5):
        d = parse_dt(candles[i])
        if d is None or d.astimezone(tz).day != current_local.day:
            continue
        c = safe_float(candles[i].get("close")); f = safe_float(candles[i + 5].get("close"))
        if c and f:
            monthly_rows.append(f / c - 1.0)
    if direction == "SHORT":
        monthly_rows = [-r for r in monthly_rows]

    def summarize(rows):
        if len(rows) < 10:
            return {"samples": len(rows), "win_rate": 0.50, "avg_return": 0.0, "quality": 50.0}
        win = sum(1 for x in rows if x > 0) / len(rows)
        avg = mean(rows)
        vol = std(rows)
        edge = clamp((win - 0.50) * 2.0, -1, 1)
        rr = clamp(abs(avg) / max(vol, 1e-8), 0, 1)
        quality = clamp(50 + edge * 35 + rr * 15, 0, 100)
        return {"samples": len(rows), "win_rate": win, "avg_return": avg, "quality": quality}

    intraday = summarize(hour_rows)
    weekly = summarize(weekly_rows)
    monthly = summarize(monthly_rows)
    seasonal = summarize(seasonal_rows)

    parts = [
        (intraday, 0.35), (weekly, 0.20), (monthly, 0.15), (seasonal, 0.30)
    ]
    valid = [(x, w) for x, w in parts if x["samples"] >= 10]
    if not valid:
        return {"score": 0.0, "direction": "NEUTRALE", "confidence": 0.0,
                "intraday": intraday, "weekly": weekly, "monthly": monthly,
                "seasonal": seasonal, "samples": 0, "status": "CAMPIONE INSUFFICIENTE"}

    total_w = sum(w for _, w in valid)
    quality = sum(x["quality"] * w for x, w in valid) / total_w
    signed_edges = []
    for x, w in valid:
        signed_edges.append(((x["win_rate"] - 0.50) * 2.0, w))
    edge = sum(e * w for e, w in signed_edges) / total_w
    score = clamp(edge, -1, 1)
    cyc_direction = "LONG" if score >= 0.10 else "SHORT" if score <= -0.10 else "NEUTRALE"
    confidence = clamp(abs(score) * 100 * min(1.0, len(valid) / 4), 0, 100)

    return {
        "score": score,
        "direction": cyc_direction,
        "confidence": confidence,
        "quality": quality,
        "intraday": intraday,
        "weekly": weekly,
        "monthly": monthly,
        "seasonal": seasonal,
        "samples": sum(x["samples"] for x, _ in valid),
        "status": "OK",
    }



# ============================================================
# V8 ENTRY / CANDLE / TIMING / LOCAL BACKTEST ENGINE
# ============================================================

def _price_round(value):
    value = safe_float(value)
    if value is None:
        return 0.0
    if abs(value) >= 1000:
        return round(value, 2)
    if abs(value) >= 100:
        return round(value, 3)
    if abs(value) >= 10:
        return round(value, 3)
    return round(value, 4)


def _candle_metrics(c):
    o, h, l, cl = [safe_float(c.get(k)) for k in ('open','high','low','close')]
    if None in (o,h,l,cl) or h <= l:
        return None
    rng = h-l
    body = abs(cl-o)
    upper = h-max(o,cl)
    lower = min(o,cl)-l
    close_pos = (cl-l)/rng
    return {'open':o,'high':h,'low':l,'close':cl,'range':rng,'body':body,
            'upper':upper,'lower':lower,'close_pos':close_pos,
            'bull':cl>o,'bear':cl<o}


def candle_engine(candles, direction):
    """Riconosce pattern semplici e robusti; non pretende di predire il mercato."""
    if direction not in ('LONG','SHORT') or len(candles) < 3:
        return {'patterns': [], 'score': 0.0, 'label': 'N/D'}
    a=_candle_metrics(candles[-1]); p=_candle_metrics(candles[-2]); pp=_candle_metrics(candles[-3])
    if not a or not p or not pp:
        return {'patterns': [], 'score': 0.0, 'label': 'N/D'}
    patterns=[]; score=0.0
    # engulfing
    if a['bull'] and p['bear'] and a['open'] <= p['close'] and a['close'] >= p['open']:
        patterns.append('BULLISH ENGULFING'); score += 2.0 if direction=='LONG' else -1.0
    if a['bear'] and p['bull'] and a['open'] >= p['close'] and a['close'] <= p['open']:
        patterns.append('BEARISH ENGULFING'); score += 2.0 if direction=='SHORT' else -1.0
    # hammer / shooting star
    if a['lower'] >= max(a['body']*2, a['range']*0.45) and a['upper'] <= a['range']*0.25:
        patterns.append('HAMMER'); score += 1.5 if direction=='LONG' else -0.8
    if a['upper'] >= max(a['body']*2, a['range']*0.45) and a['lower'] <= a['range']*0.25:
        patterns.append('SHOOTING STAR'); score += 1.5 if direction=='SHORT' else -0.8
    # doji
    if a['body'] <= a['range']*0.12:
        patterns.append('DOJI'); score -= 0.5
    # inside bar
    if a['high'] <= p['high'] and a['low'] >= p['low']:
        patterns.append('INSIDE BAR'); score += 0.5
    # short 3-candle momentum
    if direction=='LONG' and a['close']>p['close']>pp['close']:
        patterns.append('MOMENTO RIALZISTA'); score += 1.0
    if direction=='SHORT' and a['close']<p['close']<pp['close']:
        patterns.append('MOMENTO RIBASSISTA'); score += 1.0
    score=clamp(score,-3,4)
    label=' + '.join(patterns[:2]) if patterns else 'NESSUN PATTERN FORTE'
    return {'patterns':patterns,'score':score,'label':label}


def _recent_levels(candles, lookback=80):
    rows=candles[-lookback:]
    highs=[safe_float(x.get('high')) for x in rows if safe_float(x.get('high')) is not None]
    lows=[safe_float(x.get('low')) for x in rows if safe_float(x.get('low')) is not None]
    closes=[safe_float(x.get('close')) for x in rows if safe_float(x.get('close')) is not None]
    return (max(highs) if highs else None, min(lows) if lows else None, closes)



# WORLD_PATTERN_ENGINE_V82
# Pattern library: Japanese candlesticks + common price-action structures.
def world_pattern_engine(candles, direction):
    """Detect a broad, conservative library of widely used candle/price patterns.
    Returns names and a compact directional quality score. It is an analytical filter,
    not a guarantee of future price movement.
    """
    if not candles or len(candles) < 5 or direction not in ("LONG", "SHORT"):
        return {"patterns": [], "score": 0.0, "bias": "NONE"}
    def cm(c):
        o,h,l,cl=float(c['open']),float(c['high']),float(c['low']),float(c['close'])
        r=max(h-l,1e-12); b=abs(cl-o)
        return o,h,l,cl,r,b,(h-max(o,cl))/r,(min(o,cl)-l)/r,(cl-l)/r
    x=[cm(c) for c in candles[-60:]]
    names=[]; score=0.0
    a=x[-1]; prev=x[-2]
    o,h,l,c,r,b,uw,lw,cp=a; po,ph,pl,pc,pr,pb,pu,plw,pcp=prev
    bull=c>o; pbull=pc>po
    # Single-candle patterns
    if b/r < .10: names.append('DOJI')
    if lw >= max(uw*1.8, b*1.2) and cp > .55: names.append('HAMMER')
    if uw >= max(lw*1.8, b*1.2) and cp < .45: names.append('SHOOTING STAR')
    # Engulfing
    if bull and not pbull and c>=po and o<=pc: names.append('BULLISH ENGULFING')
    if not bull and pbull and o>=pc and c<=po: names.append('BEARISH ENGULFING')
    # Harami / inside bar
    if max(o,c) < max(po,pc) and min(o,c) > min(po,pc): names.append('INSIDE BAR / HARAMI')
    # Three-candle patterns
    if len(x)>=3:
        q=x[-3]
        qo,qh,ql,qc,qr,qb,qu,qlw,qcp=q
        if (not (qc>qo)) and abs(pc-po) < pr*.35 and c>o and c > (qo+qc)/2: names.append('MORNING STAR')
        if (qc>qo) and abs(pc-po) < pr*.35 and c<o and c < (qo+qc)/2: names.append('EVENING STAR')
    # Range/structure patterns from recent 20 bars
    highs=[z[1] for z in x[:-1]]; lows=[z[2] for z in x[:-1]]
    rh=max(highs[-20:]); rl=min(lows[-20:])
    near_high=abs(c-rh)/max(c,1e-12) < .0025
    near_low=abs(c-rl)/max(c,1e-12) < .0025
    if near_high and bull: names.append('RESISTANCE BREAKOUT')
    if near_low and not bull: names.append('SUPPORT BREAKDOWN')
    # Momentum / trend structure
    closes=[z[3] for z in x]
    if len(closes)>=10:
        fast=sum(closes[-5:])/5; slow=sum(closes[-10:])/10
        if fast>slow and c>fast: names.append('MOMENTO RIALZISTA')
        if fast<slow and c<fast: names.append('MOMENTO RIBASSISTA')
    # Directional scoring; only count patterns that agree with requested direction.
    bullish={'HAMMER','BULLISH ENGULFING','MORNING STAR','RESISTANCE BREAKOUT','MOMENTO RIALZISTA'}
    bearish={'SHOOTING STAR','BEARISH ENGULFING','EVENING STAR','SUPPORT BREAKDOWN','MOMENTO RIBASSISTA'}
    for n in names:
        if n in bullish: score += 1
        elif n in bearish: score -= 1
    if direction=='SHORT': score=-score
    return {'patterns':names[-4:], 'score':score, 'bias':('LONG' if score>0 else 'SHORT' if score<0 else 'NONE')}


def classify_entry_type(price, entry, candles, direction):
    """Classify the calculated entry as PULLBACK, BREAKOUT or RETEST."""
    if not candles or entry is None: return 'PULLBACK'
    highs=[float(c['high']) for c in candles[-30:]]; lows=[float(c['low']) for c in candles[-30:]]
    rh=max(highs[:-2]) if len(highs)>2 else max(highs); rl=min(lows[:-2]) if len(lows)>2 else min(lows)
    tol=max(price*0.002, (max(highs)-min(lows))*0.03)
    if direction=='LONG':
        if abs(entry-rh)<tol and entry>=price*0.997: return 'BREAKOUT + CONFERMA'
        if entry<price: return 'PULLBACK'
        return 'RETEST'
    else:
        if abs(entry-rl)<tol and entry<=price*1.003: return 'BREAKDOWN + CONFERMA'
        if entry>price: return 'PULLBACK'
        return 'RETEST'

def calculate_entry_price(candles, direction, atr_value=None):
    """Entry singola: combina pullback, S/R locale, ATR e candela recente."""
    if direction not in ('LONG','SHORT') or len(candles)<20:
        return None, 'N/D'
    price=safe_float(candles[-1].get('close'))
    if price is None: return None, 'N/D'
    a=_candle_metrics(candles[-1]); prev=candles[-min(2,len(candles))]
    atr_value=safe_float(atr_value) or atr(candles,14) or price*0.01
    hi,lo,closes=_recent_levels(candles,80)
    recent=candles[-20:]
    rh=max((safe_float(x.get('high')) for x in recent if safe_float(x.get('high')) is not None), default=price)
    rl=min((safe_float(x.get('low')) for x in recent if safe_float(x.get('low')) is not None), default=price)
    pattern=candle_engine(candles,direction)
    # Support/resistance candidates near price.
    if direction=='LONG':
        supports=[x for x in (lo,rl,price-0.35*atr_value) if x is not None and x<=price]
        base=max(supports) if supports else price-0.25*atr_value
        if pattern['score']>0 and a:
            entry=price-0.12*atr_value
            method='CONFERMA CANDELA + PULLBACK'
        else:
            entry=base+0.18*atr_value
            method='PULLBACK SU SUPPORTO'
        entry=min(entry,price+0.10*atr_value)
        entry=max(entry,price-0.55*atr_value)
    else:
        resistances=[x for x in (hi,rh,price+0.35*atr_value) if x is not None and x>=price]
        base=min(resistances) if resistances else price+0.25*atr_value
        if pattern['score']>0 and a:
            entry=price+0.12*atr_value
            method='CONFERMA CANDELA + PULLBACK'
        else:
            entry=base-0.18*atr_value
            method='PULLBACK SU RESISTENZA'
        entry=max(entry,price-0.10*atr_value)
        entry=min(entry,price+0.55*atr_value)
    return _price_round(entry), method


def local_setup_backtest(candles, direction, lookback=240):
    """Mini-backtest dei pattern/setup: misura se il contesto storico ha seguito la direzione."""
    if direction not in ('LONG','SHORT') or len(candles)<80:
        return {'samples':0,'win_rate':0.0,'avg_return':0.0,'quality':0.0}
    rows=candles[-min(len(candles),lookback):]
    wins=0; returns=[]; samples=0
    step=3
    for i in range(20,len(rows)-5,step):
        c=rows[i]
        cm=_candle_metrics(c)
        if not cm: continue
        prev=_candle_metrics(rows[i-1]); nxt=rows[i+3]
        if not prev: continue
        bullish=(cm['bull'] and cm['close']>prev['close'])
        bearish=(cm['bear'] and cm['close']<prev['close'])
        if (direction=='LONG' and not bullish) or (direction=='SHORT' and not bearish):
            continue
        entry=cm['close']; future=safe_float(nxt.get('close'))
        if not future or not entry: continue
        r=(future-entry)/entry if direction=='LONG' else (entry-future)/entry
        returns.append(r); samples+=1
        if r>0: wins+=1
    if not samples: return {'samples':0,'win_rate':0.0,'avg_return':0.0,'quality':0.0}
    wr=wins/samples; avg=sum(returns)/len(returns)
    quality=clamp(wr*70+clamp(avg/0.01,-1,1)*30,0,100)
    return {'samples':samples,'win_rate':wr,'avg_return':avg,'quality':quality}


def precise_timing_engine(candles, direction):
    """Trova l'ora locale europea con migliore rendimento storico per la direzione."""
    if direction not in ('LONG','SHORT') or len(candles)<80:
        return {'best_time':'N/D','window':'N/D','hour_score':0.0,'samples':0}
    try:
        from zoneinfo import ZoneInfo
        zone=ZoneInfo('Europe/Rome')
    except Exception:
        zone=timezone.utc
    buckets={h:[] for h in range(24)}
    for i in range(0,len(candles)-3):
        c=candles[i]; n=candles[i+3]
        cm=_candle_metrics(c); entry=safe_float(c.get('close')); future=safe_float(n.get('close'))
        if not cm or not entry or not future: continue
        try: dt=datetime.fromisoformat(str(c.get('datetime')).replace('Z','+00:00'))
        except Exception: continue
        if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
        hour=dt.astimezone(zone).hour
        # usa solo barre coerenti con la direzione del contesto
        move=(future-entry)/entry if direction=='LONG' else (entry-future)/entry
        buckets[hour].append(move)
    scored=[]
    for h,vals in buckets.items():
        if len(vals)<5: continue
        wr=sum(1 for x in vals if x>0)/len(vals); avg=sum(vals)/len(vals)
        score=wr*70+clamp(avg/0.005,-1,1)*30
        scored.append((score,h,len(vals)))
    if not scored: return {'best_time':'N/D','window':'N/D','hour_score':0.0,'samples':0}
    score,h,n=max(scored)
    minute=30
    best=f'{h:02d}:{minute:02d}'
    # Finestra stretta attorno all'orario scelto.
    h1=(h*60+25)%1440; h2=(h*60+40)%1440
    window=f'{h1//60:02d}:{h1%60:02d}–{h2//60:02d}:{h2%60:02d}'
    return {'best_time':best,'window':window,'hour_score':score,'samples':n}




def pattern_signature_engine(candles, direction, index=None):
    """Classifica un setup storico usando una libreria ampia di candele + price action."""
    if not candles or direction not in ("LONG", "SHORT"):
        return {"patterns": [], "score": 0.0, "setup": "N/D"}
    end = len(candles) if index is None else min(index + 1, len(candles))
    if end < 5:
        return {"patterns": [], "score": 0.0, "setup": "N/D"}
    rows = candles[:end]
    wp = world_pattern_engine(rows, direction)
    names = list(wp.get("patterns", []))
    score = float(wp.get("score", 0.0) or 0.0)
    a = _candle_metrics(rows[-1]); p = _candle_metrics(rows[-2]); pp = _candle_metrics(rows[-3])
    if not a or not p or not pp:
        return {"patterns": names[-5:], "score": score, "setup": "N/D"}
    price = a["close"]
    hi20 = max(safe_float(x.get("high")) for x in rows[-21:-1] if safe_float(x.get("high")) is not None) if len(rows) >= 22 else price
    lo20 = min(safe_float(x.get("low")) for x in rows[-21:-1] if safe_float(x.get("low")) is not None) if len(rows) >= 22 else price
    atrv = atr(rows, 14) or price * .01
    # Price-action states are mutually informative, not mutually exclusive.
    if direction == "LONG":
        if lo20 < price and abs(price-lo20) <= max(.35*atrv, price*.004):
            names.append("PULLBACK")
        if hi20 and price > hi20:
            names.append("BREAKOUT")
        if hi20 and abs(price-hi20) <= max(.25*atrv, price*.003):
            names.append("RETEST RESISTENZA")
    else:
        if hi20 > price and abs(hi20-price) <= max(.35*atrv, price*.004):
            names.append("PULLBACK")
        if lo20 and price < lo20:
            names.append("BREAKDOWN")
        if lo20 and abs(price-lo20) <= max(.25*atrv, price*.003):
            names.append("RETEST SUPPORTO")
    # Penalize indecision when it is the only information.
    if "DOJI" in names and len(names) <= 1:
        score -= .5
    return {"patterns": list(dict.fromkeys(names))[-6:], "score": clamp(score, -6, 6),
            "setup": " + ".join(list(dict.fromkeys(names))[-3:]) or "NESSUN SETUP FORTE"}


def pattern_combo_backtest(candles, direction, lookback=500, forward=4):
    """Backtest locale di combinazioni candlestick/price-action sulla stessa commodity."""
    if direction not in ("LONG", "SHORT") or len(candles) < 100:
        return {"samples": 0, "win_rate": 0.0, "avg_return": 0.0, "quality": 0.0,
                "top_patterns": []}
    rows = candles[-min(len(candles), lookback):]
    wins = 0; returns = []; counts = {}; wins_by = {}
    # Skip one bar between samples to reduce dependence between adjacent candles.
    for i in range(25, len(rows)-forward, 3):
        sig = pattern_signature_engine(rows, direction, i)
        pats = sig["patterns"]
        directional = sig["score"]
        if not pats or directional <= 0:
            continue
        entry = safe_float(rows[i].get("close")); future = safe_float(rows[i+forward].get("close"))
        if not entry or not future: continue
        r = (future-entry)/entry if direction == "LONG" else (entry-future)/entry
        returns.append(r)
        if r > 0: wins += 1
        for pat in pats:
            counts[pat] = counts.get(pat, 0) + 1
            if r > 0: wins_by[pat] = wins_by.get(pat, 0) + 1
    n=len(returns)
    if not n:
        return {"samples":0,"win_rate":0.0,"avg_return":0.0,"quality":0.0,"top_patterns":[]}
    wr=wins/n; avg=sum(returns)/n
    # Require both sample size and payoff; avoid letting tiny samples dominate.
    sample_factor=clamp(n/40, .35, 1.0)
    quality=clamp((wr*65 + clamp(avg/.008,-1,1)*35)*sample_factor,0,100)
    ranked=[]
    for pat,cnt in counts.items():
        if cnt < 3: continue
        pwr=wins_by.get(pat,0)/cnt
        ranked.append((pwr*100,cnt,pat))
    ranked.sort(reverse=True)
    return {"samples":n,"win_rate":wr,"avg_return":avg,"quality":quality,
            "top_patterns":[{"pattern":p,"samples":c,"win_rate":w} for w,c,p in ranked[:5]]}


def choose_entry_setup(candles, direction, atr_value, world_patterns):
    """Sceglie un solo prezzo di ingresso e il tipo di setup più coerente."""
    if not candles or direction not in ("LONG","SHORT"): return None, "N/D"
    price=safe_float(candles[-1].get("close"));
    if not price: return None,"N/D"
    atrv=safe_float(atr_value) or atr(candles,14) or price*.01
    look=candles[-40:-1] if len(candles)>2 else candles
    highs=[safe_float(x.get('high')) for x in look if safe_float(x.get('high')) is not None]
    lows=[safe_float(x.get('low')) for x in look if safe_float(x.get('low')) is not None]
    rh=max(highs) if highs else price; rl=min(lows) if lows else price
    tol=max(.22*atrv, price*.0015)
    pats=set(world_patterns.get('patterns',[]))
    if direction=='LONG':
        if 'BREAKOUT' in pats or 'RESISTANCE BREAKOUT' in pats:
            entry=max(price, rh + .05*atrv)
            return _price_round(entry), 'BREAKOUT + CONFERMA'
        if 'RETEST RESISTENZA' in pats:
            entry=max(rl, rh - .10*atrv)
            return _price_round(min(entry, price+.10*atrv)), 'RETEST'
        # Prefer support pullback; if price is already very close, use shallow pullback.
        support=max([x for x in (rl, price-.35*atrv, price-.15*atrv) if x <= price] or [price-.20*atrv])
        entry=min(price-.08*atrv, support+.12*atrv)
        entry=max(entry, price-.50*atrv)
        return _price_round(entry), 'PULLBACK'
    else:
        if 'BREAKDOWN' in pats or 'SUPPORT BREAKDOWN' in pats:
            entry=min(price, rl - .05*atrv)
            return _price_round(entry), 'BREAKDOWN + CONFERMA'
        if 'RETEST SUPPORTO' in pats:
            entry=min(rh, rl + .10*atrv)
            return _price_round(max(entry, price-.10*atrv)), 'RETEST'
        resistance=min([x for x in (rh, price+.35*atrv, price+.15*atrv) if x >= price] or [price+.20*atrv])
        entry=max(price+.08*atrv, resistance-.12*atrv)
        entry=min(entry, price+.50*atrv)
        return _price_round(entry), 'PULLBACK'


def v83_setup_engine(analysis, intraday_candles=None, commodity_name=None, pattern_timeframes=None):
    direction=analysis.get('setup_direction') or analysis.get('model_signal')
    if direction not in ('LONG','SHORT'):
        analysis['action_label']='NON ENTRARE'
        return analysis
    candles=intraday_candles if intraday_candles and len(intraday_candles)>=30 else analysis.get('_candles',[])
    if not candles: return analysis
    atr_value=analysis.get('atr') or atr(candles,14)
    world=pattern_signature_engine(candles,direction)
    combo=pattern_combo_backtest(candles,direction)
    entry,method=choose_entry_setup(candles,direction,atr_value,world)
    # Multi-timeframe pattern confluence: structural TFs carry more weight.
    tf_results=[]
    for tf,tf_candles in (pattern_timeframes or {}).items():
        if not tf_candles or len(tf_candles)<10: continue
        sig=pattern_signature_engine(tf_candles,direction)
        tf_results.append((tf,sig))
    tf_weight={'4H':.30,'1H':.28,'15m':.22,'5m':.14,'1m':.06}
    mtf_pattern_score=0.0; mtf_names=[]
    for tf,sig in tf_results:
        norm=clamp(sig.get('score',0)/6,-1,1)
        mtf_pattern_score += norm*100*tf_weight.get(tf,.10)
        if sig.get('patterns'):
            mtf_names.append(f"{tf}: " + ' + '.join(sig['patterns'][:2]))
    # Quality combines current pattern, historical combo and MTF agreement.
    pattern_now=clamp((world.get('score',0)+3)/6*100,0,100)
    combo_q=combo.get('quality',0)
    entry_quality=clamp(
        analysis.get('confidence',0)*.25 + analysis.get('quality',0)*.15 +
        pattern_now*.20 + combo_q*.25 + clamp(50+mtf_pattern_score/2,0,100)*.15,0,100)
    timing=precise_timing_engine(candles,direction)
    timing['composite_score']=clamp(timing.get('hour_score',0)*.45 + combo_q*.30 +
                                    clamp(50+mtf_pattern_score/2,0,100)*.25,0,100)
    if entry:
        profile=LEVEL_PROFILES.get(commodity_name or '',{})
        p=entry; sl_pct=profile.get('sl_pct',min(atr_value/max(p,1e-8)*STOP_ATR,.025))
        tp1_pct=profile.get('tp1_pct',min(atr_value/max(p,1e-8)*TP1_ATR,.035))
        tp2_pct=profile.get('tp2_pct',min(atr_value/max(p,1e-8)*TP2_ATR,.055))
        tp3_pct=profile.get('tp3_pct',min(atr_value/max(p,1e-8)*TP3_ATR,.080))
        if direction=='LONG': stop=p*(1-sl_pct); tp1=p*(1+tp1_pct); tp2=p*(1+tp2_pct); tp3=p*(1+tp3_pct)
        else: stop=p*(1+sl_pct); tp1=p*(1-tp1_pct); tp2=p*(1-tp2_pct); tp3=p*(1-tp3_pct)
        analysis.update({'entry':_price_round(p),'stop':_price_round(stop),'tp1':_price_round(tp1),
                         'tp2':_price_round(tp2),'tp3':_price_round(tp3)})
    # Decide only after confluence. A good pattern alone is not enough.
    action='ATTENDERE'
    risk_mode=analysis.get('risk',{}).get('mode','NORMAL')
    if risk_mode=='SHOCK': action='NON ENTRARE'
    elif analysis.get('signal') in ('LONG','SHORT') and entry_quality>=72 and combo.get('samples',0)>=15 and world.get('score',0)>0:
        action='ENTRARE'
    elif analysis.get('signal') not in ('LONG','SHORT'):
        action='ATTENDERE'
    analysis.update({
        'entry_method':method,
        'candle_pattern':world.get('setup','NESSUN SETUP FORTE'),
        'candle_patterns':world.get('patterns',[]),
        'candle_score':world.get('score',0),
        'pattern_mtf':mtf_names,
        'pattern_mtf_score':mtf_pattern_score,
        'pattern_backtest':combo,
        'local_backtest':combo,
        'timing':timing,
        'entry_quality':entry_quality,
        'action_label':action,
    })
    return analysis

def v8_setup_engine(analysis, intraday_candles=None, commodity_name=None):
    direction=analysis.get('setup_direction') or analysis.get('model_signal')
    if direction not in ('LONG','SHORT'):
        return analysis
    candles=intraday_candles if intraday_candles and len(intraday_candles)>=20 else []
    if not candles:
        candles=analysis.get('_candles',[])
    if not candles: return analysis
    atr_value=analysis.get('atr') or atr(candles,14)
    entry,method=calculate_entry_price(candles,direction,atr_value)
    pattern=candle_engine(candles,direction)
    bt=local_setup_backtest(candles,direction)
    timing=precise_timing_engine(candles,direction)
    # Timing composito: storico orario + pattern + ricorrenza del setup.
    timing['composite_score']=clamp(
        timing.get('hour_score',0)*0.55 + bt.get('quality',0)*0.25 +
        max(0.0, pattern.get('score',0))/4.0*100*0.20, 0, 100)
    if entry:
        price=entry
        profile=LEVEL_PROFILES.get(commodity_name or '',{})
        sl_pct=profile.get('sl_pct',min((atr_value/max(price,1e-8))*STOP_ATR,0.025))
        tp1_pct=profile.get('tp1_pct',min((atr_value/max(price,1e-8))*TP1_ATR,0.035))
        tp2_pct=profile.get('tp2_pct',min((atr_value/max(price,1e-8))*TP2_ATR,0.055))
        tp3_pct=profile.get('tp3_pct',min((atr_value/max(price,1e-8))*TP3_ATR,0.080))
        if direction=='LONG':
            stop=price*(1-sl_pct); tp1=price*(1+tp1_pct); tp2=price*(1+tp2_pct); tp3=price*(1+tp3_pct)
        else:
            stop=price*(1+sl_pct); tp1=price*(1-tp1_pct); tp2=price*(1-tp2_pct); tp3=price*(1-tp3_pct)
        analysis.update({'entry':_price_round(price),'stop':_price_round(stop),'tp1':_price_round(tp1),'tp2':_price_round(tp2),'tp3':_price_round(tp3)})
    entry_quality=clamp(
        analysis.get('confidence',0)*0.30 + analysis.get('quality',0)*0.20 +
        pattern['score']/4*15 + bt['quality']*0.20 + timing.get('composite_score', timing.get('hour_score',0))*0.15,0,100)
    analysis.update({'entry_method':method,'candle_pattern':pattern['label'],'candle_score':pattern['score'],
                     'local_backtest':bt,'timing':timing,'entry_quality':entry_quality})
    # Decisione chiara per l'utente; shock blocca sempre l'ingresso.
    shock_mode=analysis.get('risk',{}).get('mode')
    if shock_mode=='SHOCK':
        analysis['signal']='WAIT'; analysis['action_label']='NON ENTRARE'
    elif analysis.get('signal') in ('LONG','SHORT') and entry_quality>=68:
        analysis['action_label']='ENTRARE'
    elif direction in ('LONG','SHORT'):
        analysis['action_label']='ATTENDERE'
    else:
        analysis['action_label']='NON ENTRARE'
    return analysis


def risk_benefit_engine(analysis, cyclical):
    """Valuta opportunità e rischio. Non usa solo lo score tecnico."""
    direction = analysis.get("signal")
    if direction not in ("LONG", "SHORT"):
        direction = analysis.get("model_signal")
    price = safe_float(analysis.get("entry")) or safe_float(analysis.get("price"))
    stop = safe_float(analysis.get("stop"))
    tp3 = safe_float(analysis.get("tp3"))
    if not price or not stop or not tp3 or direction not in ("LONG", "SHORT"):
        return {"opportunity": 0.0, "risk": 100.0, "reward_risk": 0.0, "score": 0.0, "label": "NON OPERATIVO"}

    risk_dist = abs(price - stop)
    reward_dist = abs(tp3 - price)
    rr = reward_dist / max(risk_dist, 1e-8)
    rr_score = clamp((rr - 1.0) / 3.0, 0, 1) * 100

    pressure = safe_float(analysis.get("pressure_score"))
    if pressure is None:
        # proxy conservativo: la pressione MTF/fast non viene trattata come order book reale
        pressure = clamp(50 + analysis.get("mtf_bias", 0) * 50, 0, 100)
    vol_pct = (safe_float(analysis.get("atr")) or 0) / max(price, 1e-8)
    vol_risk = clamp(vol_pct / 0.06, 0, 1) * 100
    conflict_risk = analysis.get("fast_conflicts", 0) * 15 + analysis.get("structural_opposite", 0) * 20
    news_risk = 35 if abs(safe_float(analysis.get("news", {}).get("score")) or 0) < 0.20 else 0
    shock_risk = (safe_float(analysis.get("global_impact", {}).get("shock_intensity")) or 0) * 100
    risk = clamp(0.45 * vol_risk + 0.20 * conflict_risk + 0.10 * news_risk + 0.25 * shock_risk, 0, 100)

    opportunity = clamp(
        0.30 * analysis.get("score", 0)
        + 0.20 * analysis.get("confidence", 0)
        + 0.15 * analysis.get("quality", 0)
        + 0.15 * pressure
        + 0.10 * rr_score
        + 0.10 * (abs(cyclical.get("score", 0)) * 100),
        0, 100
    )
    final = clamp(0.60 * opportunity + 0.40 * rr_score - 0.35 * risk, 0, 100)
    label = "ECCELLENTE" if final >= 80 else "ALTO" if final >= 65 else "MEDIO" if final >= 50 else "BASSO"
    return {"opportunity": opportunity, "risk": risk, "reward_risk": rr,
            "rr_score": rr_score, "score": final, "label": label}


# ============================================================
# RISK / CONFLUENCE / SHOCK ENGINE
# ============================================================

def risk_engine(analysis, session, global_impact):
    score = analysis.get("score", 0)
    confidence = analysis.get("confidence", 0)
    session_quality = session.get("quality", 50)
    shock = global_impact.get("shock_intensity", 0)
    confluence = 0
    checks = []
    for key, good in [
        ("tecnica", analysis.get("structural_same", 0) >= 2),
        ("modello", (analysis.get("model_signal") or analysis.get("setup_direction")) == (analysis.get("setup_direction") or analysis.get("signal") ) and (analysis.get("setup_direction") or analysis.get("signal")) in ("LONG", "SHORT")),
        ("news", abs(safe_float(analysis.get("news", {}).get("score")) or 0) >= 0.20),
        ("political", abs(safe_float(analysis.get("political", {}).get("score")) or 0) >= 0.20),
        ("sessione", session_quality >= 65),
        ("storico", analysis.get("repetition", {}).get("frequency", 0) >= 0.55),
    ]:
        checks.append((key, good))
        confluence += 1 if good else 0

    market_quality = clamp(
        score * 0.45 + confidence * 0.20 + session_quality * 0.20 + confluence / 6 * 15,
        0, 100
    )
    confirmed_shocks = int(global_impact.get("shock_count", 0) or 0)
    # Uno shock globale non deve bloccare automaticamente TUTTE le commodities.
    # Blocchiamo solo se esiste un impatto avverso esplicito sulla commodity.
    gi_text = str(global_impact.get("summary", "") or "").upper()
    adverse = str(analysis.get("shock_impact", "") or "").upper()
    commodity_specific_shock = any(k in adverse for k in ("STRONG NEGATIVE", "ADVERSE", "BEARISH SHOCK", "NEGATIVE SHOCK"))
    if confirmed_shocks >= 2 and commodity_specific_shock:
        mode = "SHOCK"
        risk_pct = 0.0
    elif confirmed_shocks >= 1:
        mode = "ALERT"
        risk_pct = min(MAX_RISK_PER_TRADE_PCT, 0.25)
    else:
        mode = "NORMAL"
        risk_pct = min(MAX_RISK_PER_TRADE_PCT, session.get("allocation_pct", 25) / 100 * MAX_RISK_PER_TRADE_PCT)
        if market_quality < 60:
            risk_pct *= 0.5

    return {
        "confluence": confluence,
        "confluence_total": 6,
        "market_quality": market_quality,
        "risk_pct": risk_pct,
        "mode": mode,
        "checks": checks,
    }



# ============================================================
# v2.1 LEARNING / RULE VALIDATION ENGINE
# ============================================================
# The engine converts educational concepts into explicit, testable rules.
# It never "learns" a strategy from text and assumes it works: each rule
# is measured on historical candles before it can influence the live signal.

RULE_MEMORY_FILE = "validated_trading_rules.json"
RULE_MIN_SAMPLES = 20
RULE_MIN_WIN_RATE = 0.52
RULE_MAX_DRAWDOWN_PCT = 35.0
RULE_WEIGHT_CAP = 0.18


def _close_series(candles):
    return [safe_float(c.get("close")) for c in candles if safe_float(c.get("close")) is not None]


def _rule_features(candles, i, direction):
    if i < 20 or i >= len(candles):
        return None
    window = candles[:i+1]
    closes = _close_series(window)
    if len(closes) < 20:
        return None
    c = closes[-1]
    e9 = ema(closes, 9)
    e21 = ema(closes, 21)
    r = rsi(closes, 14)
    a = atr(window, 14) or c * 0.01
    recent = window[-20:]
    hi = max(safe_float(x.get("high")) or safe_float(x.get("close")) or c for x in recent[:-1])
    lo = min(safe_float(x.get("low")) or safe_float(x.get("close")) or c for x in recent[:-1])
    slope = closes[-1] - closes[-6]
    trend_ok = (e9 > e21 and slope > 0) if direction == "LONG" else (e9 < e21 and slope < 0)
    momentum_ok = (r >= 52 and r <= 72 and slope > 0) if direction == "LONG" else (r <= 48 and r >= 28 and slope < 0)
    pullback_ok = (c >= e21 - 0.60*a and c <= e9 + 0.20*a) if direction == "LONG" else (c <= e21 + 0.60*a and c >= e9 - 0.20*a)
    breakout_ok = c > hi if direction == "LONG" else c < lo
    vol_pct = a / max(c, 1e-9)
    volatility_ok = 0.001 <= vol_pct <= 0.08
    return {
        "trend": trend_ok,
        "momentum": momentum_ok,
        "pullback": pullback_ok,
        "breakout": breakout_ok,
        "volatility": volatility_ok,
    }


def _future_outcome(candles, i, direction, horizon=5):
    if i + horizon >= len(candles):
        return None
    entry = safe_float(candles[i].get("close"))
    future = [safe_float(candles[j].get("close")) for j in range(i+1, i+horizon+1)]
    future = [x for x in future if x is not None]
    if not entry or not future:
        return None
    final = future[-1]
    return final > entry if direction == "LONG" else final < entry


def _rule_trade_outcome(candles, i, direction, atr_value, horizon=8):
    """Realistic educational rule outcome: 1R stop vs 2R target, first touch wins."""
    entry = safe_float(candles[i].get("close"))
    if not entry or not atr_value or atr_value <= 0:
        return None
    risk = atr_value
    target = 2.0 * risk
    for j in range(i + 1, min(len(candles), i + 1 + horizon)):
        hi = safe_float(candles[j].get("high"), entry)
        lo = safe_float(candles[j].get("low"), entry)
        if direction == "LONG":
            hit_stop = lo <= entry - risk
            hit_target = hi >= entry + target
        else:
            hit_stop = hi >= entry + risk
            hit_target = lo <= entry - target
        # Conservative convention when both are touched in the same candle.
        if hit_stop and hit_target:
            return False
        if hit_target:
            return True
        if hit_stop:
            return False
    return None


def backtest_learning_rules(candles, direction):
    """Walk-forward validation of explicit trading rules.

    The rule is calibrated only on the first historical segment and accepted
    only when it also survives an unseen validation segment. This reduces
    the risk of turning educational ideas into overfit signals.
    """
    rules = {
        "TREND_FOLLOWING": lambda f: f["trend"],
        "MOMENTUM": lambda f: f["momentum"],
        "PULLBACK": lambda f: f["trend"] and f["pullback"],
        "BREAKOUT": lambda f: f["trend"] and f["breakout"],
        "VOLATILITY_FILTER": lambda f: f["volatility"],
        "TREND_MOMENTUM": lambda f: f["trend"] and f["momentum"],
        "PULLBACK_MOMENTUM": lambda f: f["trend"] and f["pullback"] and f["momentum"],
    }
    split = max(40, int(len(candles) * 0.60))
    stats = {}
    for name, predicate in rules.items():
        buckets = {"train": {"wins": 0, "losses": 0}, "test": {"wins": 0, "losses": 0}}
        for i in range(20, len(candles) - HORIZON):
            f = _rule_features(candles, i, direction)
            if f is None or not predicate(f):
                continue
            a = atr(candles[:i+1], 14) or safe_float(candles[i].get("close"), 0) * 0.01
            outcome = _rule_trade_outcome(candles, i, direction, a, HORIZON)
            if outcome is None:
                continue
            bucket = "train" if i < split else "test"
            buckets[bucket]["wins" if outcome else "losses"] += 1

        tr = buckets["train"]; te = buckets["test"]
        train_n = tr["wins"] + tr["losses"]
        test_n = te["wins"] + te["losses"]
        train_wr = tr["wins"] / train_n if train_n else 0.0
        test_wr = te["wins"] / test_n if test_n else 0.0
        # Accept only when unseen performance is at least 52% and does not
        # collapse more than 8 percentage points below the training result.
        validated = (
            train_n >= RULE_MIN_SAMPLES and
            test_n >= max(10, RULE_MIN_SAMPLES // 2) and
            train_wr >= RULE_MIN_WIN_RATE and
            test_wr >= RULE_MIN_WIN_RATE and
            test_wr >= train_wr - 0.08
        )
        stats[name] = {
            "train_samples": train_n,
            "train_win_rate": round(train_wr, 4),
            "test_samples": test_n,
            "test_win_rate": round(test_wr, 4),
            "validated": bool(validated),
            "expectancy_proxy": round((2 * test_wr) - (1 - test_wr), 3) if test_n else 0.0,
        }
    return stats

def learning_rule_snapshot(candles, direction, commodity_name=None):
    """Return current rule state + historical validation, persisted for audit."""
    if direction not in ("LONG", "SHORT") or len(candles) < 50:
        return {"direction": direction, "validated": [], "active": [], "score": 0.0, "samples": 0}
    stats = backtest_learning_rules(candles, direction)
    active = [k for k,v in stats.items() if v.get("validated")]
    current = _rule_features(candles, len(candles)-1, direction) or {}
    current_hits = []
    mapping = {
        "TREND_FOLLOWING": "trend", "MOMENTUM": "momentum", "PULLBACK": "pullback",
        "BREAKOUT": "breakout", "VOLATILITY_FILTER": "volatility",
        "TREND_MOMENTUM": None, "PULLBACK_MOMENTUM": None,
    }
    for rule in active:
        key = mapping.get(rule)
        if key is not None and current.get(key):
            current_hits.append(rule)
        elif rule == "TREND_MOMENTUM" and current.get("trend") and current.get("momentum"):
            current_hits.append(rule)
        elif rule == "PULLBACK_MOMENTUM" and current.get("trend") and current.get("pullback") and current.get("momentum"):
            current_hits.append(rule)
    score = clamp(len(current_hits) / max(len(active), 1) * 100, 0, 100) if active else 0.0
    snapshot = {
        "commodity": commodity_name or "N/D",
        "direction": direction,
        "validated": stats,
        "active": active,
        "current_hits": current_hits,
        "score": round(score, 1),
        "samples": sum(v.get("test_samples",0) for v in stats.values()),
        "validation_method": "60/40 walk-forward, 1R stop / 2R target, first-touch conservative",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        memory = {}
        if os.path.exists(RULE_MEMORY_FILE):
            with open(RULE_MEMORY_FILE, "r", encoding="utf-8") as f:
                memory = json.load(f) or {}
        memory[f"{commodity_name or 'UNKNOWN'}:{direction}"] = snapshot
        with open(RULE_MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        snapshot["memory_error"] = str(exc)
    return snapshot


def apply_learning_rules(analysis, learning):
    """Use validated rules only as a capped confirmation bonus/penalty."""
    if not learning:
        return analysis
    base_score = safe_float(analysis.get("score")) or 0.0
    score = base_score
    hits = len(learning.get("current_hits", []))
    active = len(learning.get("active", []))
    bonus = 0.0
    if active:
        bonus = clamp((hits / active) * 8.0, 0, 8)
        score = clamp(score + bonus, 0, 100)
    analysis["learning_rules"] = learning
    analysis["score"] = score
    analysis["learning_bonus"] = round(bonus, 2)
    return analysis


# ============================================================
# SIGNAL
# ============================================================

def analyze(candles, dataset, model, bt, usd, news, timeframes, political=None, commodity_name=None, global_impact=None, session=None, intraday_candles=None, pattern_timeframes=None, trading_knowledge=None):
    """Gold Engine instrument-agnostic: modello + MTF + contesto."""
    features = build_features(candles)
    political = political or {"score": 0.0, "direction": "NEUTRALE", "count": 0}
    global_impact = global_impact or {"score": 0.0, "direction": "NEUTRALE", "mode": "NORMAL", "shock_intensity": 0.0, "count": 0}
    session = session or {"quality": 50.0, "allocation_pct": 25.0, "current_band": "N/D", "best_band": "N/D", "bands": {}}
    news = news or {"score": 0.0, "label": "NON DISPONIBILI", "count": 0, "status": "N/D", "source": "NONE"}
    pattern_timeframes = pattern_timeframes or {}

    if features is None or model is None:
        return None

    scaled = scale_current(features, model)
    probability = predict(scaled, model["weights"], model["bias"])
    quality = quality_score(bt)

    # --------------------------------------------------------
    # 1) MODELLO QUANTITATIVO
    # --------------------------------------------------------
    model_direction = "LONG" if probability >= 0.50 else "SHORT"
    model_strength = abs(probability - 0.50) * 2.0

    # --------------------------------------------------------
    # 2) MULTI-TIMEFRAME: struttura > velocità
    # --------------------------------------------------------
    weights = {"4H": 0.30, "1H": 0.25, "15m": 0.20, "5m": 0.15, "1m": 0.10}
    mtf_bias = 0.0
    for tf, weight in weights.items():
        direction = timeframes.get(tf, {}).get("direction", "NONE")
        if direction == "LONG":
            mtf_bias += weight
        elif direction == "SHORT":
            mtf_bias -= weight

    mtf_probability = clamp(0.50 + mtf_bias, 0.01, 0.99)

    # Il modello resta importante, ma il consenso MTF può rafforzarlo.
    combined_long = clamp(0.45 * probability + 0.55 * mtf_probability, 0.01, 0.99)
    combined_short = 1.0 - combined_long

    if combined_long >= 0.62:
        main_direction = "LONG"
    elif combined_short >= 0.62:
        main_direction = "SHORT"
    else:
        main_direction = model_direction if model_strength >= 0.20 else "NONE"

    # --------------------------------------------------------
    # 3) CONSENSO STRUTTURALE E CONFERMA VELOCE
    # --------------------------------------------------------
    structural = [timeframes.get(tf, {}).get("direction", "NONE") for tf in ("4H", "1H", "15m")]
    fast = [timeframes.get(tf, {}).get("direction", "NONE") for tf in ("5m", "1m")]

    structural_same = sum(1 for d in structural if d == main_direction)
    structural_opposite = sum(1 for d in structural if d not in ("NONE", main_direction))
    fast_same = sum(1 for d in fast if d == main_direction)
    fast_opposite = sum(1 for d in fast if d not in ("NONE", main_direction))

    # 4H + 1H + 15m hanno priorità. Un solo 1m contrario non annulla il setup.
    structural_score = structural_same * 2 - structural_opposite * 2

    repetition = historical_repetition(candles)
    cyclical = cyclical_market_engine(candles, main_direction)
    repetition_impact = 0.0
    if repetition["direction"] == main_direction:
        repetition_impact = repetition["frequency"] * 6
    elif repetition["direction"] not in ("NEUTRALE", main_direction):
        repetition_impact = -repetition["frequency"] * 6

    cyclical_impact = 0.0
    if cyclical["direction"] == main_direction:
        cyclical_impact = abs(cyclical["score"]) * 7
    elif cyclical["direction"] not in ("NEUTRALE", main_direction):
        cyclical_impact = -abs(cyclical["score"]) * 7

    # --------------------------------------------------------
    # 4) CONFIDENCE E SCORE DEL SETUP
    # --------------------------------------------------------
    confidence = clamp(
        model_strength * 100 * 0.45
        + (abs(mtf_bias) * 100) * 0.35
        + (structural_same / 3.0) * 20 * 0.20,
        0,
        100,
    )

    direction_score = abs(combined_long - 0.50) * 200
    news_impact = safe_float(news.get("score")) or 0.0
    usd_impact = safe_float(usd.get("impact")) or 0.0
    political_score = safe_float(political.get("score")) or 0.0

    context = 0.0
    if main_direction == "LONG":
        context += news_impact * 5 + usd_impact * 3 + political_score * 4
    elif main_direction == "SHORT":
        context -= news_impact * 5 + usd_impact * 3 + political_score * 4

    global_score = safe_float(global_impact.get("score")) or 0.0
    if main_direction == "SHORT":
        global_score = -global_score
    context += global_score * 5

    score = clamp(
        direction_score * 0.40
        + quality * 0.17
        + confidence * 0.15
        + structural_score * 4
        + fast_same * 3
        - fast_opposite * 2
        + repetition_impact
        + cyclical_impact
        + context,
        0,
        100,
    )

    # --------------------------------------------------------
    # 5) DECISIONE OPERATIVA
    # --------------------------------------------------------
    operational_signal = main_direction

    # Se la struttura è 3/3 contro, niente ingresso.
    if structural_opposite >= 2 and structural_same == 0:
        operational_signal = "WAIT"

    # Il solo 1m contrario è un conflitto veloce, non un annullamento.
    # Due conflitti veloci richiedono attesa.
    if fast_opposite >= 2:
        operational_signal = "WAIT"

    if operational_signal in ("LONG", "SHORT"):
        if score < MIN_SCORE or confidence < MIN_CONFIDENCE:
            operational_signal = "WAIT"

    # --------------------------------------------------------
    # 6) GRADE
    # --------------------------------------------------------
    if operational_signal in ("LONG", "SHORT"):
        if score >= 80 and confidence >= 72 and structural_same >= 2:
            grade = "FORTE"
        elif score >= 65 and confidence >= 58 and structural_same >= 2:
            grade = "IN FORMAZIONE"
        else:
            grade = "DEBOLE"
    elif main_direction in ("LONG", "SHORT"):
        grade = "CONFLITTO" if fast_opposite else "ATTENDERE"
    else:
        grade = "NEUTRALE"

    price = candles[-1]["close"]
    raw_atr = atr(candles, 14) or price * 0.01
    profile = LEVEL_PROFILES.get(commodity_name or "", {})
    max_atr_pct = profile.get("max_atr_pct", 0.05)
    current_atr = min(raw_atr, price * max_atr_pct)

    # I livelli iniziali sono calibrati per strumento. La gestione Gold Engine
    # (BE dopo TP1, stop a TP1 dopo TP2, chiusura a TP3) non cambia.
    # IMPORTANTISSIMO: i livelli vengono calcolati anche in WAIT, usando la
    # direzione del setup (main_direction). In questo modo Telegram mostra
    # sempre numeri operativi provvisori anche quando l'ingresso è bloccato,
    # in formazione o in attesa di conferma.
    setup_direction = operational_signal if operational_signal in ("LONG", "SHORT") else main_direction
    if setup_direction in ("LONG", "SHORT"):
        sl_pct = profile.get("sl_pct", min((current_atr / price) * STOP_ATR, 0.025))
        tp1_pct = profile.get("tp1_pct", min((current_atr / price) * TP1_ATR, 0.035))
        tp2_pct = profile.get("tp2_pct", min((current_atr / price) * TP2_ATR, 0.055))
        tp3_pct = profile.get("tp3_pct", min((current_atr / price) * TP3_ATR, 0.080))
        if setup_direction == "LONG":
            stop = price * (1 - sl_pct)
            tp1 = price * (1 + tp1_pct)
            tp2 = price * (1 + tp2_pct)
            tp3 = price * (1 + tp3_pct)
        else:
            stop = price * (1 + sl_pct)
            tp1 = price * (1 - tp1_pct)
            tp2 = price * (1 - tp2_pct)
            tp3 = price * (1 - tp3_pct)
    else:
        stop = tp1 = tp2 = tp3 = None

    knowledge_bias = knowledge_bias_for_setup(trading_knowledge, setup_direction, {"mtf_bias": mtf_bias})
    score = clamp(score + knowledge_bias, 0, 100)

    strong_confirmation = (
        operational_signal in ("LONG", "SHORT")
        and score >= 75
        and confidence >= 68
        and structural_same >= 2
        and fast_opposite == 0
    )

    risk = risk_engine(
        {
            "score": score, "confidence": confidence, "structural_same": structural_same,
            "model_signal": model_direction, "signal": operational_signal,
            "news": news, "political": political, "repetition": repetition,
        }, session, global_impact
    )
    if risk["mode"] == "SHOCK":
        strong_confirmation = False
        if operational_signal in ("LONG", "SHORT"):
            operational_signal = "WAIT"

    risk_benefit = risk_benefit_engine(
        {
            "signal": operational_signal, "model_signal": model_direction,
            "entry": price, "price": price, "stop": stop, "tp3": tp3, "score": score,
            "confidence": confidence, "quality": quality, "mtf_bias": mtf_bias,
            "atr": current_atr, "fast_conflicts": fast_opposite,
            "structural_opposite": structural_opposite, "news": news,
            "global_impact": global_impact,
        }, cyclical
    )

    result = {
        "signal": operational_signal,
        "model_signal": model_direction,
        "setup_direction": setup_direction,
        "grade": grade,
        "probability": probability,
        "long_probability": combined_long,
        "short_probability": combined_short,
        "mtf_bias": mtf_bias,
        "confidence": confidence,
        "quality": quality,
        "score": score,
        "price": price,
        "atr": current_atr,
        "stop": stop,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "strong_confirmation": strong_confirmation,
        "timeframes": timeframes,
        "usd": usd,
        "news": news,
        "political": political,
        "repetition": repetition,
        "structural_same": structural_same,
        "structural_opposite": structural_opposite,
        "fast_confirmations": fast_same,
        "fast_conflicts": fast_opposite,
        "global_impact": global_impact,
        "session": session,
        "risk": risk,
        "cyclical": cyclical,
        "risk_benefit": risk_benefit,
        "knowledge_bias": knowledge_bias,
        "trading_knowledge": trading_knowledge or {},
        "pattern_timeframes": pattern_timeframes or {},
        "source_check": {},
    }
    result["_candles"] = candles
    result = v83_setup_engine(result, intraday_candles=intraday_candles, commodity_name=commodity_name, pattern_timeframes=pattern_timeframes)
    # Ricalcola R/B con l'entry effettiva trovata dal motore V8.
    result["risk_benefit"] = risk_benefit_engine(result, cyclical)

    # v2.0 knowledge layer
    result["trading_knowledge"] = trading_knowledge or {}
    result["trading_knowledge"] = trading_knowledge_engine(result)

    # v2.1: validate explicit trading rules on historical candles.
    learning = learning_rule_snapshot(candles, result.get("setup_direction"), commodity_name)
    before_learning_score = result.get("score", 0.0)
    result = apply_learning_rules(result, learning)
    result["learning_score"] = learning.get("score", 0.0)
    result["learning_validated_rules"] = learning.get("active", [])
    result["learning_current_hits"] = learning.get("current_hits", [])
    result["learning_score_delta"] = round(result.get("score", 0.0) - before_learning_score, 2)

    # Compare with the previous run for this commodity.
    direction_state = load_direction_state()
    previous = direction_state.get(commodity_name or "")
    result["reversal"] = reversal_engine(commodity_name or "", result, previous)

    # Store the current state for the next polling cycle.
    direction_state[commodity_name or "UNKNOWN"] = {
        "direction": result.get("setup_direction") or result.get("signal"),
        "score": _direction_score_from_analysis(result),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    save_direction_state(direction_state)

    # A confirmed reversal is stronger than the generic "strong confirmation".
    if result["reversal"]["stage"] == "CONFIRMED":
        result["strong_confirmation"] = True

    return {k:v for k,v in result.items() if k != "_candles"} | {"_candles": candles}


# ============================================================
# v2.4 INSTITUTIONAL-STYLE ENSEMBLE LAYER
# Inspired by robust ideas found in commodity research/platforms:
# multi-horizon ensemble, cross-sectional ranking, flow/volume proxy,
# regime detection and explicit execution-quality gating.
# This layer is deliberately transparent and testable; it is NOT a claim
# of access to proprietary institutional order-flow feeds.
# ============================================================

def _pct_change_at(closes, bars):
    if not closes or len(closes) <= bars:
        return 0.0
    base = closes[-bars-1]
    return (closes[-1] / base - 1.0) if base else 0.0


def _zscore(values, value):
    vals = [safe_float(v) for v in values if safe_float(v) is not None]
    if len(vals) < 3 or value is None:
        return 0.0
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / max(len(vals) - 1, 1)
    sd = math.sqrt(var)
    return (value - mean) / sd if sd > 1e-12 else 0.0


def institutional_style_features(candles):
    """Transparent proxies for ideas commonly used by systematic desks.

    Uses only data already available to the bot: OHLCV. No look-ahead.
    """
    if not candles or len(candles) < 80:
        return {
            "direction": "NONE", "score": 0.0, "regime": "UNKNOWN",
            "momentum_ensemble": 0.0, "volume_confirmation": 0.0,
            "trend_consistency": 0.0, "range_efficiency": 0.0,
            "volatility_percentile": 0.0,
        }

    closes = [safe_float(c.get("close")) for c in candles]
    closes = [x for x in closes if x is not None]
    if len(closes) < 80:
        return {"direction": "NONE", "score": 0.0, "regime": "UNKNOWN"}

    # Ensemble across short / medium / long horizons.
    r1 = _pct_change_at(closes, 1)
    r5 = _pct_change_at(closes, 5)
    r20 = _pct_change_at(closes, 20)
    r60 = _pct_change_at(closes, 60)
    momentum = 0.15*r1 + 0.25*r5 + 0.30*r20 + 0.30*r60

    # Trend consistency: share of positive daily returns in the last 20 bars,
    # converted to a signed measure.
    daily = []
    for i in range(max(1, len(closes)-20), len(closes)):
        if closes[i-1]:
            daily.append(closes[i] / closes[i-1] - 1.0)
    pos = sum(1 for x in daily if x > 0)
    neg = sum(1 for x in daily if x < 0)
    consistency = (pos - neg) / max(len(daily), 1)

    # Range efficiency: net displacement / total absolute movement.
    moves = [abs(closes[i]/closes[i-1]-1.0) for i in range(max(1,len(closes)-20), len(closes)) if closes[i-1]]
    efficiency = abs(_pct_change_at(closes, 20)) / max(sum(moves), 1e-9)
    efficiency = clamp(efficiency, 0.0, 1.0)

    # Volume confirmation proxy. A true institutional flow feed is not assumed.
    vols = [safe_float(c.get("volume")) for c in candles]
    vols = [v for v in vols if v is not None and v > 0]
    volume_confirmation = 0.0
    if len(vols) >= 21:
        vz = _zscore(vols[-21:-1], vols[-1])
        last_return = r1
        volume_confirmation = clamp((vz / 2.5) * (1 if last_return > 0 else -1 if last_return < 0 else 0), -1, 1)

    # Volatility regime relative to the recent history.
    returns = [closes[i]/closes[i-1]-1.0 for i in range(1, len(closes)) if closes[i-1]]
    recent_vol = math.sqrt(sum(x*x for x in returns[-20:]) / max(len(returns[-20:]),1)) if returns else 0
    hist_vols=[]
    for end in range(40, len(returns)+1, 5):
        chunk=returns[max(0,end-20):end]
        if chunk:
            hist_vols.append(math.sqrt(sum(x*x for x in chunk)/len(chunk)))
    vol_pct = 0.5
    if hist_vols:
        vol_pct = sum(1 for v in hist_vols if v <= recent_vol) / len(hist_vols)

    if vol_pct >= 0.80:
        regime = "HIGH_VOL"
    elif vol_pct <= 0.20:
        regime = "LOW_VOL"
    else:
        regime = "NORMAL"

    direction_value = momentum * 0.50 + consistency * 0.30 + (1 if momentum != 0 else 0) * volume_confirmation * 0.20
    direction = "LONG" if direction_value > 0.001 else "SHORT" if direction_value < -0.001 else "NONE"
    score = clamp(abs(direction_value) * 5000 * (0.70 + 0.30*efficiency), 0, 100)

    return {
        "direction": direction,
        "score": score,
        "regime": regime,
        "momentum_ensemble": momentum,
        "momentum_1d": r1,
        "momentum_5d": r5,
        "momentum_20d": r20,
        "momentum_60d": r60,
        "volume_confirmation": volume_confirmation,
        "trend_consistency": consistency,
        "range_efficiency": efficiency,
        "volatility_percentile": vol_pct,
    }


def apply_cross_sectional_ensemble(results):
    """Rank commodities against each other, not only against fixed thresholds.

    This implements a key research idea: cross-sectional commodity ranking
    combined with multi-horizon signals. The adjustment is capped so the
    ensemble cannot override the core risk gates by itself.
    """
    available = [x for x in results if x.get("available") and x.get("candles")]
    if len(available) < 2:
        return

    feature_rows=[]
    for item in available:
        f = institutional_style_features(item.get("candles", []))
        item["analysis"]["institutional"] = f
        feature_rows.append((item, f))

    def percentile(values, value):
        ordered=sorted(values)
        if not ordered:
            return 0.5
        rank=sum(1 for v in ordered if v <= value)
        return rank/len(ordered)

    mom20=[f.get("momentum_20d",0) for _,f in feature_rows]
    mom60=[f.get("momentum_60d",0) for _,f in feature_rows]
    eff=[f.get("range_efficiency",0) for _,f in feature_rows]
    volc=[f.get("volume_confirmation",0) for _,f in feature_rows]

    for item,f in feature_rows:
        a=item["analysis"]
        d=f.get("direction","NONE")
        if d == "NONE":
            a["cross_sectional_score"] = 50.0
            a["ensemble_alignment"] = "NEUTRALE"
            continue

        p20=percentile(mom20, f.get("momentum_20d",0))
        p60=percentile(mom60, f.get("momentum_60d",0))
        pe=percentile(eff, f.get("range_efficiency",0))
        pv=percentile(volc, f.get("volume_confirmation",0))
        raw=100*(0.35*p20 + 0.35*p60 + 0.15*pe + 0.15*pv)
        if d == "SHORT":
            # Percentile direction must be inverted for bearish momentum.
            raw=100*(0.35*(1-p20) + 0.35*(1-p60) + 0.15*pe + 0.15*(1-pv))

        a["cross_sectional_score"] = round(raw, 1)
        a["ensemble_alignment"] = d
        a["ensemble_rank"] = 1 + sum(1 for _,other in feature_rows if other.get("score",0) > f.get("score",0))

        # Only a bounded nudge: this is a confluence layer, not a replacement model.
        nudge = (raw - 50.0) * 0.12
        if d == a.get("setup_direction"):
            a["score"] = clamp(a.get("score",0) + nudge, 0, 100)
            a["confidence"] = clamp(a.get("confidence",0) + max(0, abs(nudge))*0.35, 0, 100)
        elif a.get("setup_direction") in ("LONG","SHORT"):
            a["score"] = clamp(a.get("score",0) - max(0, abs(nudge))*0.25, 0, 100)

        # High-volatility regimes require stronger confirmation rather than
        # automatically generating a signal.
        if f.get("regime") == "HIGH_VOL":
            a["high_volatility_guard"] = True
            if a.get("signal") in ("LONG","SHORT") and a.get("confidence",0) < 72:
                a["signal"] = "WAIT"
                a["action_label"] = "ATTENDERE"
        else:
            a["high_volatility_guard"] = False


def ensemble_trade_gate(analysis):
    """Final transparent gate inspired by execution-quality/risk systems."""
    inst=analysis.get("institutional",{})
    d=analysis.get("setup_direction")
    if d not in ("LONG","SHORT"):
        return True, "N/D"
    if inst.get("direction") not in (d, "NONE"):
        return False, "MOMENTUM MULTI-HORIZON CONTRARIO"
    if inst.get("regime") == "HIGH_VOL" and analysis.get("confidence",0) < 72:
        return False, "VOLATILITÀ ELEVATA — CONFERMA RICHIESTA"
    if analysis.get("cross_sectional_score",50) < 25:
        return False, "RANKING CROSS-SECTIONALE DEBOLE"
    return True, "OK"



# ============================================================
# v2.6 SCORE CONSISTENCY + SMART ENTRY ENGINE
# ============================================================
def normalize_analysis_metrics(analysis):
    """Unifica i valori finali usati da dettaglio, ranking e trade gate.

    Nelle versioni precedenti 'quality' e 'risk.market_quality' potevano
    divergere dopo i vari layer. Qui definiamo una singola metrica finale,
    senza sovrascrivere la qualità grezza utile alla ricerca.
    """
    if not isinstance(analysis, dict):
        return analysis
    raw_q = safe_float(analysis.get("quality"), 0.0) or 0.0
    market_q = safe_float(analysis.get("risk", {}).get("market_quality"), 0.0) or 0.0
    entry_q = safe_float(analysis.get("entry_quality"), 0.0) or 0.0
    conf = safe_float(analysis.get("confidence"), 0.0) or 0.0
    score = safe_float(analysis.get("score"), 0.0) or 0.0

    # La qualità finale pesa struttura, mercato e qualità dell'ingresso.
    final_q = clamp(raw_q * 0.45 + market_q * 0.30 + entry_q * 0.25, 0, 100)
    # Se alcuni layer non sono ancora disponibili, non penalizziamo due volte.
    if raw_q <= 0 and market_q > 0:
        final_q = clamp(market_q * 0.70 + entry_q * 0.30, 0, 100)
    if entry_q <= 0:
        final_q = clamp(raw_q * 0.60 + market_q * 0.40, 0, 100)

    analysis["quality_raw"] = round(raw_q, 2)
    analysis["market_quality"] = round(market_q, 2)
    analysis["quality"] = round(final_q, 2)
    analysis["confidence"] = round(clamp(conf, 0, 100), 2)
    analysis["score"] = round(clamp(score, 0, 100), 2)
    analysis.setdefault("entry_state", "N/D")
    return analysis


def entry_trigger_engine(analysis):
    """Persistent entry trigger engine v2.7.

    Non guarda soltanto l'ultima candela: cerca un breakout/retest o una
    ripartenza nelle ultime barre. Questo evita di perdere un LONG iniziato
    poche ore prima solo perché l'ultima candela non è essa stessa il trigger.

    Priorità: 5m/1m. Se i rapidi non sono disponibili, usa 15m/1H come
    fallback dichiarato ("EARLY ENTRY"), senza fingere una precisione da 1m.
    """
    d = analysis.get("setup_direction") or analysis.get("model_signal")
    pts = analysis.get("pattern_timeframes", {}) or {}
    tfs = analysis.get("timeframes", {}) or {}
    if d not in ("LONG", "SHORT"):
        return {"confirmed": False, "kind": "NONE", "score": 0.0,
                "reasons": ["NESSUNA DIREZIONE"], "available": False}

    details=[]
    candidates=[]
    tf_plan=(("5m", 12, False), ("1m", 20, False), ("15m", 8, True), ("1H", 5, True))
    for tf, lookback, fallback in tf_plan:
        rows=pts.get(tf)
        if not rows or len(rows)<25:
            continue
        closes=[safe_float(x.get("close")) for x in rows if safe_float(x.get("close")) is not None]
        highs=[safe_float(x.get("high")) for x in rows if safe_float(x.get("high")) is not None]
        lows=[safe_float(x.get("low")) for x in rows if safe_float(x.get("low")) is not None]
        if len(closes)<25 or len(highs)<25 or len(lows)<25:
            continue
        a=atr(rows,14) or closes[-1]*0.005
        e9=ema(closes,9); e21=ema(closes,21)
        start=max(21, len(rows)-lookback)
        best=None
        for i in range(start, len(rows)):
            cm=_candle_metrics(rows[i])
            if not cm:
                continue
            c=cm["close"]
            prior_hi=max(highs[max(0,i-21):i]) if i>=1 else None
            prior_lo=min(lows[max(0,i-21):i]) if i>=1 else None
            if prior_hi is None or prior_lo is None:
                continue
            body=abs(cm["close"]-cm["open"])
            range_=max(cm["high"]-cm["low"],1e-12)
            body_ratio=body/range_
            bullish=cm["close"]>cm["open"]
            bearish=cm["close"]<cm["open"]
            bo=((c>prior_hi) and bullish and body_ratio>=0.38) if d=="LONG" else ((c<prior_lo) and bearish and body_ratio>=0.38)
            # Retest/ripartenza: una delle barre recenti interagisce con EMA21,
            # poi una successiva chiude di nuovo dalla parte della direzione.
            recent_from=max(0,i-3)
            interacted=False
            for j in range(recent_from,i):
                cj=closes[j]
                if abs(cj-e21) <= max(0.65*a, c*0.0025):
                    interacted=True
                    break
            pb=(interacted and c>e9 and c>e21 and bullish) if d=="LONG" else (interacted and c<e9 and c<e21 and bearish)
            mom=((c-e9)/max(a,1e-12)>0.05) if d=="LONG" else ((e9-c)/max(a,1e-12)>0.05)
            score=0
            kind="NONE"
            if bo:
                score+=58; kind="BREAKOUT"
            elif pb:
                score+=58; kind="PULLBACK + RIPARTENZA"
            if mom: score+=20
            if tfs.get(tf,{}).get("direction")==d: score+=15
            # Un trigger recente vale più di uno vecchio.
            age=(len(rows)-1-i)
            score-=min(age*2.0,16)
            score=clamp(score,0,100)
            if kind!="NONE" or mom:
                cand=(score,tf,kind,bo,pb,mom,age,c)
                if best is None or cand[0]>best[0]: best=cand
        if best:
            candidates.append(best)

    if not candidates:
        return {"confirmed": False, "kind": "NONE", "score": 0.0,
                "reasons": ["TRIGGER RAPIDO NON DISPONIBILE"], "available": False}

    # Prefer rapid timeframes whenever their score is reasonably close.
    rapid=[x for x in candidates if x[1] in ("5m","1m")]
    pool=rapid if rapid else candidates
    pool.sort(key=lambda x:x[0], reverse=True)
    best_score,tf,kind,bo,pb,mom,age,trigger_price=pool[0]
    confirmations=sum(1 for x in candidates if x[3] or x[4])
    confirmed=bool(kind!="NONE" and best_score>=60 and (bo or pb) and (mom or best_score>=75))
    reasons=[]
    if bo: reasons.append(f"BREAKOUT {tf}")
    if pb: reasons.append(f"PULLBACK + RIPARTENZA {tf}")
    if mom: reasons.append("MOMENTUM CONFERMATO")
    if age>0: reasons.append(f"TRIGGER {age} BARRE FA")
    if tf in ("15m","1H"): reasons.append("FALLBACK TIMEFRAME")
    if not reasons: reasons.append("NESSUN TRIGGER")
    return {"confirmed": confirmed, "kind": kind, "score": round(best_score,1),
            "timeframe": tf, "age_bars": age, "trigger_price": trigger_price,
            "reasons": reasons, "available": True,
            "candidates": [{"tf":x[1],"kind":x[2],"score":round(x[0],1),"age_bars":x[6]} for x in candidates]}


def smart_entry_engine(analysis):
    """Trade gate v2.7: direzione e trigger di ingresso sono separati."""
    d = analysis.get("setup_direction") or analysis.get("model_signal")
    if d not in ("LONG", "SHORT"):
        analysis.update({"entry_state":"NO_SETUP", "action_label":"NON ENTRARE",
                         "signal":"WAIT", "strong_confirmation":False})
        return analysis

    tfs = analysis.get("timeframes", {}) or {}
    structural = [tfs.get(tf, {}).get("direction", "NONE") for tf in ("4H", "1H", "15m")]
    fast = [tfs.get(tf, {}).get("direction", "NONE") for tf in ("5m", "1m")]
    structural_same = sum(x == d for x in structural)
    fast_opp = sum(x == ("SHORT" if d=="LONG" else "LONG") for x in fast)
    fast_same = sum(x == d for x in fast)
    rev = analysis.get("reversal", {}) or {}
    risk = analysis.get("risk", {}) or {}
    ensemble_ok = bool(analysis.get("ensemble_gate", True))
    score = safe_float(analysis.get("score"), 0) or 0
    quality = safe_float(analysis.get("quality"), 0) or 0
    conf = safe_float(analysis.get("confidence"), 0) or 0
    entry_q = safe_float(analysis.get("entry_quality"), 0) or 0
    rb = safe_float(analysis.get("risk_benefit", {}).get("score"), 0) or 0
    prob = safe_float(analysis.get("long_probability" if d=="LONG" else "short_probability"), 0) or 0
    prob *= 100 if prob <= 1 else 1
    source_status = str(analysis.get("source_check",{}).get("status", ""))
    source_discrepancy = "DISCREPANZA" in source_status.upper()
    trigger = entry_trigger_engine(analysis)
    l2l = analysis.get("level_to_level", {}) or {}
    l2l_gate = bool(l2l.get("gate", True))

    blockers=[]
    if risk.get("mode") == "SHOCK": blockers.append("SHOCK")
    if not ensemble_ok: blockers.append(analysis.get("ensemble_gate_reason", "ENSEMBLE"))
    if rev.get("stage") == "CONFIRMED": blockers.append("INVERSIONE CONFERMATA")
    if fast_opp > 0: blockers.append("CONFLITTO 1m/5m")
    if structural_same < 2: blockers.append("MTF STRUTTURALE")
    if source_discrepancy: blockers.append("DISCREPANZA FONTI")
    if not l2l_gate: blockers.append("LEVEL-TO-LEVEL")

    hard = (
        score >= 62 and quality >= 45 and conf >= 52 and prob >= 55
        and structural_same >= 2 and fast_opp == 0 and ensemble_ok
        and risk.get("mode") in ("NORMAL", "ALERT")
        and safe_float(risk.get("market_quality"),0) >= 50
        and (entry_q >= 55 or trigger.get("confirmed",False))
        and safe_float(risk.get("risk_pct"),0) > 0
        and rev.get("stage") != "CONFIRMED"
        and not source_discrepancy
        and l2l_gate
        and trigger.get("confirmed",False)
        and (rb >= 40 or trigger.get("score",0) >= 65)
    )

    near = (
        score >= 50 and quality >= 38 and conf >= 45 and prob >= 51
        and structural_same >= 2 and fast_opp <= 1
    )

    if risk.get("mode") == "SHOCK" or rev.get("stage") == "CONFIRMED":
        state, action = "NON_ENTRARE", "NON ENTRARE"
    elif hard:
        state, action = "ENTRY_CONFIRMED", ("COMPRA ORA" if d == "LONG" else "VENDI ORA")
    elif near and (trigger.get("kind") != "NONE" or fast_same >= 1):
        state, action = "PREPARAZIONE", "ATTENDERE"
    elif near:
        state, action = "CONFERMA_RICHIESTA", "ATTENDERE"
    else:
        state, action = "WEAK_SETUP", "NON ENTRARE"

    analysis["entry_trigger"] = trigger
    analysis["entry_state"] = state
    analysis["entry_blockers"] = blockers[:6]
    analysis["action_label"] = action
    # CRITICO: signal è operativo. La previsione resta in setup_direction.
    analysis["signal"] = d if state == "ENTRY_CONFIRMED" else "WAIT"
    analysis["strong_confirmation"] = bool(state == "ENTRY_CONFIRMED")
    analysis["entry_probability"] = round(prob,2)
    return analysis


# ============================================================
# v2.9 LEVEL-TO-LEVEL ENGINE
# Trend -> Level -> Behaviour -> Confirmation -> Risk/Reward
# Derived from the studied educational material (L2L / IG / Capital.com /
# Borsa Italiana). The engine is deliberately quantitative and bounded:
# it nudges the model and can block weak entries, but never claims prediction.
# ============================================================
def _l2l_pivots(candles, atr_value):
    """Find clustered swing levels without future-looking beyond the candle window."""
    if not candles or len(candles) < 20:
        return [], []
    c = safe_float(candles[-1].get("close")) or 0.0
    atrv = safe_float(atr_value) or (c * 0.01 if c else 1.0)
    left_right = 2
    highs, lows = [], []
    for i in range(left_right, len(candles) - left_right):
        h = safe_float(candles[i].get("high")); lo = safe_float(candles[i].get("low"))
        if h is None or lo is None:
            continue
        local_h = [safe_float(candles[j].get("high")) for j in range(i-left_right, i+left_right+1)]
        local_l = [safe_float(candles[j].get("low")) for j in range(i-left_right, i+left_right+1)]
        if all(v is not None for v in local_h) and h >= max(local_h):
            highs.append((h, i))
        if all(v is not None for v in local_l) and lo <= min(local_l):
            lows.append((lo, i))

    tol = max(0.22 * atrv, c * 0.0012 if c else 0.0)
    def cluster(points):
        clusters = []
        for value, idx in sorted(points, key=lambda x: x[0]):
            hit = None
            for cl in clusters:
                if abs(value - cl["level"]) <= tol:
                    hit = cl; break
            if hit is None:
                clusters.append({"level": value, "tests": 1, "last_idx": idx, "values": [value]})
            else:
                hit["values"].append(value)
                hit["tests"] += 1
                hit["last_idx"] = max(hit["last_idx"], idx)
                hit["level"] = sum(hit["values"]) / len(hit["values"])
        for cl in clusters:
            recency = 1.0 - max(0, len(candles) - 1 - cl["last_idx"]) / max(len(candles), 1)
            cl["strength"] = round(clamp(cl["tests"] * 18 + recency * 28, 0, 100), 1)
        return clusters
    return cluster(lows), cluster(highs)


def level_to_level_engine(analysis, commodity_name=None, candles=None, pattern_timeframes=None):
    """Quantify the Level-to-Level sequence for a commodity.

    The engine looks for:
      1) structural trend,
      2) objective support/resistance zones,
      3) approach strength/weakness,
      4) breakout/retest/fakeout or reaction,
      5) a confirmation gate and R/R feasibility.

    It does not invent order-book data or volume if the source does not provide it.
    """
    d = analysis.get("setup_direction") or analysis.get("model_signal")
    if d not in ("LONG", "SHORT"):
        analysis["level_to_level"] = {"available": False, "state": "NO_SETUP", "score": 50.0, "gate": True}
        return analysis
    candles = candles or analysis.get("_candles") or []
    if len(candles) < 30:
        analysis["level_to_level"] = {"available": False, "state": "DATI INSUFFICIENTI", "score": 50.0, "gate": True}
        return analysis

    price = safe_float(candles[-1].get("close")) or safe_float(analysis.get("price"))
    atrv = safe_float(analysis.get("atr")) or atr(candles, 14) or (price * 0.01 if price else 1.0)
    supports, resistances = _l2l_pivots(candles[-160:], atrv)
    supports = [x for x in supports if x["level"] <= price * 1.002]
    resistances = [x for x in resistances if x["level"] >= price * 0.998]
    support = max(supports, key=lambda x: x["level"], default=None)
    resistance = min(resistances, key=lambda x: x["level"], default=None)
    zone = max(0.22 * atrv, price * 0.0015 if price else 0.0)

    # Structural trend from recent swing sequence / moving averages.
    closes = [safe_float(x.get("close")) for x in candles[-40:]]
    closes = [x for x in closes if x is not None]
    trend_score = 50.0
    trend = "RANGE"
    if len(closes) >= 20:
        ma_fast = sum(closes[-10:]) / 10
        ma_slow = sum(closes[-20:]) / 20
        slope = (closes[-1] - closes[-10]) / max(atrv, 1e-12)
        if ma_fast > ma_slow and slope > 0.35:
            trend, trend_score = "LONG", 92.0
        elif ma_fast < ma_slow and slope < -0.35:
            trend, trend_score = "SHORT", 92.0
        elif ma_fast > ma_slow:
            trend, trend_score = "LONG", 68.0
        elif ma_fast < ma_slow:
            trend, trend_score = "SHORT", 68.0

    # Approach: strong directional candle vs quiet/weak approach into a level.
    recent = candles[-6:]
    body_ratios = []
    for row in recent:
        o = safe_float(row.get("open")); h = safe_float(row.get("high")); lo = safe_float(row.get("low")); c = safe_float(row.get("close"))
        if None in (o, h, lo, c) or h <= lo:
            continue
        body_ratios.append(abs(c-o) / max(h-lo, 1e-12))
    body = sum(body_ratios) / len(body_ratios) if body_ratios else 0.5
    recent_move = ((closes[-1] - closes[-6]) / max(atrv, 1e-12)) if len(closes) >= 6 else 0.0
    approach = "FORTE" if abs(recent_move) >= 1.0 and body >= 0.55 else ("DEBOLE" if abs(recent_move) <= 0.35 else "NORMALE")

    # Detect current interaction with the nearest relevant level.
    near_support = bool(support and abs(price - support["level"]) <= 1.35 * zone)
    near_resistance = bool(resistance and abs(price - resistance["level"]) <= 1.35 * zone)
    prev = candles[-2] if len(candles) >= 2 else candles[-1]
    prev_close = safe_float(prev.get("close")) or price
    current_high = safe_float(candles[-1].get("high")) or price
    current_low = safe_float(candles[-1].get("low")) or price

    breakout = False; retest = False; fakeout = False; reaction = False
    trigger_level = None; behaviour = "NESSUNA"
    if resistance and d == "LONG":
        lvl = resistance["level"]
        breakout = price > lvl + 0.12 * zone and prev_close > lvl
        retest = breakout and current_low <= lvl + 0.35 * zone and price > lvl
        fakeout = current_high > lvl + 0.10 * zone and price < lvl - 0.05 * zone
        reaction = near_resistance and price > prev_close and current_low <= lvl + zone
        trigger_level = lvl
    elif support and d == "SHORT":
        lvl = support["level"]
        breakout = price < lvl - 0.12 * zone and prev_close < lvl
        retest = breakout and current_high >= lvl - 0.35 * zone and price < lvl
        fakeout = current_low < lvl - 0.10 * zone and price > lvl + 0.05 * zone
        reaction = near_support and price < prev_close and current_high >= lvl - zone
        trigger_level = lvl
    elif d == "LONG" and near_support:
        reaction = price > prev_close and current_low <= support["level"] + zone
        trigger_level = support["level"]
    elif d == "SHORT" and near_resistance:
        reaction = price < prev_close and current_high >= resistance["level"] - zone
        trigger_level = resistance["level"]

    if retest:
        behaviour = "BREAKOUT_RETEST"
    elif breakout:
        behaviour = "BREAKOUT"
    elif fakeout:
        behaviour = "FAKEOUT"
    elif reaction:
        behaviour = "REACTION"
    elif near_support or near_resistance:
        behaviour = "APPROCCIO_AL_LIVELLO"

    trend_component = trend_score if trend == d else (35.0 if trend == "RANGE" else 20.0)
    level_component = 70.0
    if d == "LONG" and support:
        level_component = 55.0 + support["strength"] * 0.35 if near_support else 50.0
    if d == "SHORT" and resistance:
        level_component = 55.0 + resistance["strength"] * 0.35 if near_resistance else 50.0
    if trigger_level is not None:
        level_component = max(level_component, 62.0)

    behaviour_component = {
        "BREAKOUT_RETEST": 95.0, "BREAKOUT": 82.0, "REACTION": 76.0,
        "APPROCCIO_AL_LIVELLO": 58.0, "FAKEOUT": 18.0, "NESSUNA": 42.0,
    }.get(behaviour, 42.0)
    approach_component = 82.0 if approach == "DEBOLE" and (near_support or near_resistance) else (72.0 if approach == "NORMALE" else 58.0)
    if approach == "FORTE" and behaviour in ("BREAKOUT", "BREAKOUT_RETEST"):
        approach_component = 92.0
    if approach == "FORTE" and behaviour == "APPROCCIO_AL_LIVELLO":
        approach_component = 48.0  # aggressive approach into resistance/support without confirmation

    # Risk/reward feasibility uses the existing risk engine outputs where available.
    rb = safe_float(analysis.get("risk_benefit", {}).get("score"), 0) or 0
    rr_component = clamp(rb + 20.0, 0, 100)
    l2l_score = clamp(
        trend_component * 0.25 + level_component * 0.20 + behaviour_component * 0.30
        + approach_component * 0.15 + rr_component * 0.10, 0, 100
    )

    confirmations = 0
    if trend == d: confirmations += 1
    if behaviour in ("BREAKOUT", "BREAKOUT_RETEST", "REACTION"): confirmations += 1
    if (d == "LONG" and (near_support or breakout or retest)) or (d == "SHORT" and (near_resistance or breakout or retest)):
        confirmations += 1
    if analysis.get("fast_conflicts", 0) == 0: confirmations += 1

    gate = bool(
        not fakeout and l2l_score >= 58 and confirmations >= 2
        and behaviour not in ("NESSUNA", "APPROCCIO_AL_LIVELLO") or
        (not fakeout and behaviour == "BREAKOUT_RETEST" and l2l_score >= 52)
    )
    if behaviour == "APPROCCIO_AL_LIVELLO" and approach == "FORTE":
        gate = False

    # Bounded score contribution: L2L can help/hurt but cannot dominate the model.
    signed_bonus = clamp((l2l_score - 50.0) * 0.20, -10.0, 10.0)
    if trend not in (d, "RANGE"):
        signed_bonus = min(signed_bonus, -4.0)
    analysis["score"] = clamp((safe_float(analysis.get("score"), 0) or 0) + signed_bonus, 0, 100)
    analysis["level_to_level"] = {
        "available": True,
        "state": "CONFERMATO" if gate else ("IN FORMAZIONE" if l2l_score >= 50 else "DEBOLE"),
        "score": round(l2l_score, 1),
        "trend": trend,
        "trend_score": round(trend_component, 1),
        "support": round(support["level"], 6) if support else None,
        "support_strength": round(support["strength"], 1) if support else 0.0,
        "resistance": round(resistance["level"], 6) if resistance else None,
        "resistance_strength": round(resistance["strength"], 1) if resistance else 0.0,
        "level": round(trigger_level, 6) if trigger_level is not None else None,
        "approach": approach,
        "behaviour": behaviour,
        "breakout": bool(breakout),
        "retest": bool(retest),
        "fakeout": bool(fakeout),
        "reaction": bool(reaction),
        "confirmations": confirmations,
        "rr_component": round(rr_component, 1),
        "bonus": round(signed_bonus, 2),
        "gate": gate,
        "source_logic": "L2L + IG + Capital.com + Borsa Italiana",
    }
    return analysis

def finalize_v26_analysis(analysis):
    normalize_analysis_metrics(analysis)
    # Ricalcolo del rischio DOPO tutti i layer che possono aver modificato score
    # e contesto. Per la qualità del rischio usiamo la direzione del setup, non
    # il signal operativo WAIT/ENTRARE.
    d = analysis.get("setup_direction") or analysis.get("model_signal")
    if d in ("LONG", "SHORT"):
        risk_input = dict(analysis)
        risk_input["signal"] = d
        try:
            analysis["risk"] = risk_engine(
                risk_input,
                analysis.get("session", {}) or {},
                analysis.get("global_impact", {}) or {}
            )
            analysis["risk_benefit"] = risk_benefit_engine(analysis, analysis.get("cyclical", {}) or {})
        except Exception as exc:
            print(f"⚠️ Ricalcolo rischio v2.7: {exc}")
    smart_entry_engine(analysis)
    return analysis

# ============================================================
# v2.3 PREDICTION JOURNAL + END-OF-DAY TEST
# ============================================================

def _json_load(path, default):
    try:
        if not os.path.exists(path):
            return default
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:
        print(f"⚠️ Impossibile leggere {path}: {exc}")
        return default


def _json_save(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def _prediction_direction(item):
    a = item.get("analysis", {})
    direction = a.get("setup_direction") or a.get("model_signal") or a.get("signal")
    return direction if direction in ("LONG", "SHORT") else "WAIT"


def record_predictions(results):
    """Record auditable forecasts without looking at future candles."""
    log = _json_load(PREDICTION_LOG_FILE, [])
    if not isinstance(log, list):
        log = []
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=45)
    new_items = 0
    for item in results:
        if not item.get("available"):
            continue
        a = item.get("analysis", {})
        price = safe_float(a.get("price"))
        if price is None:
            continue
        direction = _prediction_direction(item)
        rec = {
            "id": f"{item['name']}|{now.strftime('%Y-%m-%dT%H:%M:%SZ')}|{direction}|{price:.8f}",
            "created_at": now.isoformat(), "name": item["name"], "symbol": item["symbol"],
            "direction": direction, "action": a.get("action_label", "ATTENDERE"), "price": price,
            "entry": safe_float(a.get("entry")), "stop": safe_float(a.get("stop")),
            "tp1": safe_float(a.get("tp1")), "tp2": safe_float(a.get("tp2")), "tp3": safe_float(a.get("tp3")),
            "atr": safe_float(a.get("atr")) or 0.0, "score": safe_float(a.get("score")) or 0.0,
            "confidence": safe_float(a.get("confidence")) or 0.0, "quality": safe_float(a.get("quality")) or 0.0,
            "setup": a.get("entry_method", "N/D"),
            "l2l": a.get("level_to_level", {}),
            "validated_rules": list(a.get("learning_current_hits", [])) if isinstance(a.get("learning_current_hits", []), list) else [],
            "status": "PENDING"
        }
        if not any(x.get("id") == rec["id"] for x in log):
            log.append(rec); new_items += 1
    log = [x for x in log if x.get("created_at", "") >= cutoff.isoformat()]
    _json_save(PREDICTION_LOG_FILE, log)
    return new_items, log


def _future_candles_for_prediction(prediction):
    created = datetime.fromisoformat(prediction["created_at"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) < created + timedelta(hours=PREDICTION_HORIZON_HOURS):
        return []
    try:
        rows = get_data(prediction["symbol"], "1h", 1200)
    except Exception:
        return []
    end = created + timedelta(hours=PREDICTION_HORIZON_HOURS)
    out = []
    for row in rows:
        try:
            dt = datetime.fromisoformat(str(row["datetime"]).replace("Z", "+00:00"))
        except Exception:
            continue
        if created < dt <= end:
            out.append(row)
    return out


def evaluate_prediction(prediction, future):
    if not future:
        return None
    p = safe_float(prediction.get("price"))
    if p is None:
        return None
    direction = prediction.get("direction", "WAIT")
    sl, tp1 = safe_float(prediction.get("stop")), safe_float(prediction.get("tp1"))
    close_end = safe_float(future[-1].get("close"))
    if close_end is None:
        return None
    first_hit = "NONE"
    if direction in ("LONG", "SHORT"):
        for c in future:
            hi, lo = safe_float(c.get("high")), safe_float(c.get("low"))
            if hi is None or lo is None:
                continue
            hit_tp = (tp1 is not None and (hi >= tp1 if direction == "LONG" else lo <= tp1))
            hit_sl = (sl is not None and (lo <= sl if direction == "LONG" else hi >= sl))
            if hit_tp and hit_sl: first_hit = "AMBIGUO"; break
            if hit_tp: first_hit = "TP1"; break
            if hit_sl: first_hit = "SL"; break
        close_correct = close_end > p if direction == "LONG" else close_end < p
        verdict = "CORRETTA" if first_hit == "TP1" or (first_hit == "NONE" and close_correct) else "ERRATA"
        if first_hit == "AMBIGUO": verdict = "AMBIGUA"
    else:
        atr = safe_float(prediction.get("atr")) or 0.0
        band = max(abs(p) * 0.003, atr * 0.75)
        max_high = max((safe_float(c.get("high")) or p) for c in future)
        min_low = min((safe_float(c.get("low")) or p) for c in future)
        verdict = "CORRETTA" if max_high <= p + band and min_low >= p - band else "ERRATA"
        first_hit = "NEUTRALE" if verdict == "CORRETTA" else "MOVIMENTO"
    return {"verdict": verdict, "first_hit": first_hit, "close_end": close_end, "move_pct": (close_end / p - 1.0) * 100.0, "evaluated_at": datetime.now(timezone.utc).isoformat()}


def run_end_of_day_test(force=False):
    log = _json_load(PREDICTION_LOG_FILE, [])
    if not isinstance(log, list) or not log:
        return None
    local_now = datetime.now(ZoneInfo("Europe/Rome"))
    if not force and local_now.hour < EOD_REPORT_HOUR:
        return None
    changed = False
    for pred in log:
        if pred.get("status") != "PENDING":
            continue
        result = evaluate_prediction(pred, _future_candles_for_prediction(pred))
        if result:
            pred.update(result); pred["status"] = "EVALUATED"; changed = True
    if changed: _json_save(PREDICTION_LOG_FILE, log)
    today = local_now.date().isoformat()
    evaluated = []
    for pred in log:
        try: d = datetime.fromisoformat(pred.get("created_at", "").replace("Z", "+00:00")).astimezone(ZoneInfo("Europe/Rome")).date().isoformat()
        except Exception: continue
        if d == today and pred.get("status") == "EVALUATED": evaluated.append(pred)
    if not evaluated:
        return None
    correct = sum(p.get("verdict") == "CORRETTA" for p in evaluated)
    wrong = sum(p.get("verdict") == "ERRATA" for p in evaluated)
    ambiguous = sum(p.get("verdict") == "AMBIGUA" for p in evaluated)
    accuracy = correct / (correct + wrong) * 100.0 if correct + wrong else 0.0
    lines = ["📊 COMMODITIES BOT v2.4 — TEST FINE GIORNATA", "", f"📅 {local_now.strftime('%d/%m/%Y')}", "━━━━━━━━━━━━━━━━━━━━", "🎯 ACCURATEZZA PREVISIONI", f"Previsioni valutate: {len(evaluated)}", f"✅ Corrette: {correct}", f"❌ Errate: {wrong}", f"⚪ Ambigue: {ambiguous}", f"🎯 Accuratezza: {accuracy:.1f}%", "", "🧭 PER DIREZIONE"]
    for direction, icon in (("LONG", "🟢"), ("SHORT", "🔴"), ("WAIT", "🟡")):
        rows = [p for p in evaluated if p.get("direction") == direction]
        d = sum(x.get("verdict") == "CORRETTA" for x in rows); w = sum(x.get("verdict") == "ERRATA" for x in rows)
        acc = d / (d + w) * 100.0 if d + w else 0.0
        lines.append(f"{icon} {direction}: {len(rows)} | {acc:.1f}%")
    by_name = {}
    for pred in evaluated: by_name.setdefault(pred["name"], []).append(pred)
    ranking = []
    for name, rows in by_name.items():
        d = sum(x.get("verdict") == "CORRETTA" for x in rows); w = sum(x.get("verdict") == "ERRATA" for x in rows)
        if d + w: ranking.append((d / (d + w) * 100.0, name, len(rows)))
    ranking.sort(reverse=True)
    lines += ["", "🏆 MIGLIORI COMMODITY"]
    for i, (acc, name, n) in enumerate(ranking[:3]): lines.append(f"{('🥇','🥈','🥉')[i]} {name}: {acc:.1f}% ({n})")
    lines += ["", "🔒 STATO: PAPER TRADING", "🚫 ORDINI REALI: DISATTIVATI"]
    state = _json_load(DAILY_REPORT_FILE, {})
    if state.get("last_report_date") == today and not force: return None
    state.update({"last_report_date": today, "accuracy": accuracy, "evaluated": len(evaluated)})
    _json_save(DAILY_REPORT_FILE, state)
    return "\n".join(lines)

# ============================================================
# POSITION MANAGEMENT
# ============================================================

def manage_position(position, current_analysis, current_price):
    """Gestione posizione allineata al GOLD BOT v15.1."""
    direction = position["direction"]
    entry = position["entry"]
    stop = position["stop"]
    tp1 = position["tp1"]
    tp2 = position["tp2"]
    tp3 = position["tp3"]
    break_even = position.get("break_even", False)
    tp2_reached = position.get("tp2_reached", False)

    strong_opposite = (
        current_analysis.get("reversal", {}).get("stage") == "CONFIRMED"
        and current_analysis.get("signal") == ("SHORT" if direction == "LONG" else "LONG")
    )

    if direction == "LONG":
        if current_price <= stop:
            return {"action": "EXIT", "reason": "STOP LOSS", "new_stop": stop}
        if current_price >= tp3:
            return {"action": "EXIT", "reason": "TP3 RAGGIUNTO — INCASSARE", "new_stop": stop}
        if current_price >= tp2 and not tp2_reached:
            return {"action": "MOVE_STOP", "reason": "TP2 RAGGIUNTO — STOP A TP1", "new_stop": max(stop, tp1), "tp2_reached": True}
        if current_price >= tp1 and not break_even:
            return {"action": "MOVE_STOP", "reason": "TP1 RAGGIUNTO — STOP A BREAK-EVEN", "new_stop": max(stop, entry), "break_even": True}
        if strong_opposite:
            return {"action": "EXIT", "reason": "SEGNALE OPPOSTO CONFERMATO", "new_stop": stop}
        return {"action": "HOLD", "reason": "LONG — TENERE", "new_stop": stop}

    if direction == "SHORT":
        if current_price >= stop:
            return {"action": "EXIT", "reason": "STOP LOSS", "new_stop": stop}
        if current_price <= tp3:
            return {"action": "EXIT", "reason": "TP3 RAGGIUNTO — INCASSARE", "new_stop": stop}
        if current_price <= tp2 and not tp2_reached:
            return {"action": "MOVE_STOP", "reason": "TP2 RAGGIUNTO — STOP A TP1", "new_stop": min(stop, tp1), "tp2_reached": True}
        if current_price <= tp1 and not break_even:
            return {"action": "MOVE_STOP", "reason": "TP1 RAGGIUNTO — STOP A BREAK-EVEN", "new_stop": min(stop, entry), "break_even": True}
        if strong_opposite:
            return {"action": "EXIT", "reason": "SEGNALE OPPOSTO CONFERMATO", "new_stop": stop}
        return {"action": "HOLD", "reason": "SHORT — TENERE", "new_stop": stop}

    return {"action": "EXIT", "reason": "DIREZIONE NON RICONOSCIUTA", "new_stop": stop}


# ============================================================
# v2.5 WEATHER + NATURAL DISASTER INTELLIGENCE
# ============================================================

def _cache_get(path, max_age_hours):
    try:
        obj = _json_load(path, {})
        ts = datetime.fromisoformat(obj.get("timestamp", "").replace("Z", "+00:00"))
        if datetime.now(timezone.utc) - ts <= timedelta(hours=max_age_hours):
            return obj.get("data")
    except Exception:
        pass
    return None


def _cache_put(path, data):
    try:
        _json_save(path, {"timestamp": datetime.now(timezone.utc).isoformat(), "data": data})
    except Exception:
        pass


def _weather_json(url, params):
    r = requests.get(url, params=params, timeout=WEATHER_TIMEOUT)
    r.raise_for_status()
    return r.json()


def _weather_region_snapshot(name, lat, lon):
    """Free forecast + recent observations from Open-Meteo.

    This is an intelligence layer, not a direct trading signal. We keep source,
    timestamps and raw metrics so later backtests can audit the decision.
    """
    forecast = _weather_json(
        "https://api.open-meteo.com/v1/forecast",
        {"latitude": lat, "longitude": lon,
         "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
         "forecast_days": 10, "timezone": "UTC"}
    )
    # Recent history is used for anomaly context. Open-Meteo archive is a
    # climate-history source; the model treats it as context, not as a future leak.
    end = (datetime.now(timezone.utc) - timedelta(days=2)).date().isoformat()
    start = (datetime.now(timezone.utc) - timedelta(days=32)).date().isoformat()
    history = _weather_json(
        "https://archive-api.open-meteo.com/v1/archive",
        {"latitude": lat, "longitude": lon, "start_date": start, "end_date": end,
         "daily": "temperature_2m_mean,precipitation_sum,wind_speed_10m_max",
         "timezone": "UTC"}
    )
    fd=forecast.get("daily", {})
    hd=history.get("daily", {})
    temps=[x for x in (fd.get("temperature_2m_max") or []) if isinstance(x,(int,float))]
    mins=[x for x in (fd.get("temperature_2m_min") or []) if isinstance(x,(int,float))]
    rain=[x for x in (fd.get("precipitation_sum") or []) if isinstance(x,(int,float))]
    winds=[x for x in (fd.get("wind_speed_10m_max") or []) if isinstance(x,(int,float))]
    htemps=[x for x in (hd.get("temperature_2m_mean") or []) if isinstance(x,(int,float))]
    hrain=[x for x in (hd.get("precipitation_sum") or []) if isinstance(x,(int,float))]
    hwinds=[x for x in (hd.get("wind_speed_10m_max") or []) if isinstance(x,(int,float))]
    return {
        "region": name, "lat": lat, "lon": lon, "source": "Open-Meteo",
        "forecast_days": len(temps),
        "forecast_max_mean": sum(temps)/len(temps) if temps else None,
        "forecast_min_mean": sum(mins)/len(mins) if mins else None,
        "forecast_rain_total": sum(rain),
        "forecast_wind_max": max(winds) if winds else None,
        "recent_temp_mean": sum(htemps)/len(htemps) if htemps else None,
        "recent_rain_total": sum(hrain),
        "recent_wind_max": max(hwinds) if hwinds else None,
        "raw_forecast_dates": fd.get("time", []),
    }


def weather_intelligence(commodity):
    if not WEATHER_ENABLED or commodity not in WEATHER_REGIONS:
        return {"enabled": False, "score": 0.0, "label": "N/D", "confidence": 0.0, "regions": []}
    cached = _cache_get(WEATHER_CACHE_FILE, WEATHER_CACHE_HOURS)
    if isinstance(cached, dict) and commodity in cached:
        return cached[commodity]
    regions=[]
    for label,lat,lon in WEATHER_REGIONS.get(commodity, []):
        try:
            regions.append(_weather_region_snapshot(label,lat,lon))
        except Exception as e:
            regions.append({"region":label,"error":str(e),"source":"Open-Meteo"})
    valid=[r for r in regions if not r.get("error")]
    if not valid:
        return {"enabled": True, "score": 0.0, "label": "DATI METEO NON DISPONIBILI", "confidence": 0.0, "regions": regions}
    p=WEATHER_PRIORS.get(commodity,{})
    raw=0.0
    anomaly=[]
    for r in valid:
        # Recent-vs-forecast change is a "surprise" proxy. It is not a climate
        # normal; this deliberately avoids pretending 30 days of history is a 30-year climatology.
        if r.get("forecast_max_mean") is not None and r.get("recent_temp_mean") is not None:
            dt=r["forecast_max_mean"]-r["recent_temp_mean"]
            raw += max(-3,min(3,dt/5.0))*p.get("hot",0)
            anomaly.append(dt)
        if r.get("forecast_rain_total") is not None:
            raw += max(-2,min(2,(r["forecast_rain_total"]-r.get("recent_rain_total",0))/100.0))*p.get("wet",0)
        if r.get("forecast_wind_max") is not None:
            raw += max(-1.5,min(1.5,(r["forecast_wind_max"]-r.get("recent_wind_max",0))/20.0))*p.get("wind",0)
    score=max(-100,min(100,raw*25))
    if score >= 15: label="BULLISH"
    elif score <= -15: label="BEARISH"
    else: label="NEUTRALE"
    confidence=min(95,40+len(valid)*12)
    out={"enabled":True,"score":round(score,1),"label":label,"confidence":round(confidence,1),"regions":regions,
         "temperature_change_mean":round(sum(anomaly)/len(anomaly),2) if anomaly else None,
         "historical_context":"recent 30-day observations + 10-day forecast"}
    cache = _cache_get(WEATHER_CACHE_FILE, WEATHER_CACHE_HOURS) or {}
    cache[commodity]=out
    _cache_put(WEATHER_CACHE_FILE,cache)
    return out


def natural_disaster_intelligence(commodity):
    if not DISASTER_ENABLED:
        return {"enabled":False,"score":0.0,"count":0,"events":[]}
    events=[]
    # Global news engine is already configured for disasters. We use RSS search
    # only as an extra event layer, not as a replacement for official feeds.
    for q in DISASTER_QUERIES.get(commodity,[]):
        try:
            url="https://news.google.com/rss/search"
            r=requests.get(url,params={"q":q,"hl":"en-US","gl":"US","ceid":"US:en"},timeout=8)
            r.raise_for_status()
            parser=RSSParser()
            parser.feed(r.text)
            for item in parser.items[:3]:
                events.append({"query":q,"title":item.get("title",""),"source":item.get("source","Google News RSS")})
        except Exception:
            continue
    # Keep only a bounded event score; relevance is further checked by the model.
    count=len(events)
    score=max(-20.0,min(20.0,count*1.5)) if count else 0.0
    return {"enabled":True,"score":score,"count":count,"events":events[:12]}


def apply_weather_and_disaster_layers(analysis, weather, disasters):
    """Bounded fundamental nudge. No weather/disaster layer can override risk gates."""
    analysis["weather"] = weather
    analysis["natural_disasters"] = disasters
    w=float(weather.get("score",0) or 0)
    # Disaster events are risk/context first. They only become directional if
    # weather/fundamental direction agrees with the current setup.
    dscore=float(disasters.get("score",0) or 0)
    direction=analysis.get("setup_direction")
    if direction == "LONG":
        nudge=(w+dscore)*0.08
    elif direction == "SHORT":
        nudge=(-w+dscore)*0.08
    else:
        nudge=0.0
    nudge=max(-WEATHER_IMPACT_CAP,min(WEATHER_IMPACT_CAP,nudge))
    analysis["weather_disaster_nudge"] = round(nudge,2)
    analysis["score"] = clamp(analysis.get("score",0)+nudge,0,100)
    if abs(w) >= 20 and analysis.get("confidence",0) < 70 and direction in ("LONG","SHORT"):
        analysis["weather_confirmation"]="DEBOLE — conferma meteo insufficiente"
    else:
        analysis["weather_confirmation"]="OK"


def demo_execution_adapter(results, position):
    """Paper/demo execution adapter. No real broker API is called here.

    It writes a proposed order only when DEMO_TRADING_ENABLED=1 and the normal
    trade gates say the best setup is executable. A future Pepperstone/MT5
    adapter can consume this exact order schema without changing the model.
    """
    if not DEMO_TRADING_ENABLED:
        return {"enabled":False,"executed":False,"reason":"DEMO_TRADING_ENABLED=0"}
    candidates=[x for x in results if x.get("available") and x.get("analysis",{}).get("signal") in ("LONG","SHORT")]
    if not candidates:
        return {"enabled":True,"executed":False,"reason":"NESSUN SEGNALE ESEGUIBILE"}
    best=max(candidates,key=lambda x:x.get("ranking_score",-1))
    a=best["analysis"]
    if not a.get("ensemble_gate",False):
        return {"enabled":True,"executed":False,"reason":"ENSEMBLE GATE BLOCCATO"}
    order={"timestamp":datetime.now(timezone.utc).isoformat(),"commodity":best["name"],"symbol":best["symbol"],
           "side":a["signal"],"price":a.get("price"),"entry":a.get("entry"),"stop":a.get("stop"),
           "tp1":a.get("tp1"),"tp2":a.get("tp2"),"tp3":a.get("tp3"),"mode":"DEMO/PAPER"}
    orders=_json_load(DEMO_ORDERS_FILE,[])
    orders.append(order); _json_save(DEMO_ORDERS_FILE,orders[-500:])
    return {"enabled":True,"executed":True,"order":order}


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram non configurato.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
    }

    try:
        response = requests.post(url, json=payload, timeout=20)
        response.raise_for_status()
    except Exception as error:
        print(f"⚠️ Errore Telegram: {error}")


def icon_for_signal(signal):
    return {
        "LONG": "🟢",
        "SHORT": "🔴",
        "WAIT": "🟡",
        "NO TRADE": "⚪",
    }.get(signal, "⚪")


def compact_tf(timeframes):
    return " | ".join(
        f"{tf} {timeframes[tf]['direction']}"
        for tf in ("4H", "1H", "15m", "5m", "1m")
    )


def confirmation_text(analysis):
    signal = analysis["signal"] if analysis["signal"] in ("LONG", "SHORT") else analysis["model_signal"]
    tfs = analysis["timeframes"]

    if signal not in ("LONG", "SHORT"):
        return "👉 Nessun setup principale sufficientemente forte."

    opposite = "SHORT" if signal == "LONG" else "LONG"

    if (
        tfs["5m"]["direction"] == signal
        and tfs["1m"]["direction"] == signal
    ):
        return f"👉 ✅ 5m + 1m CONFERMANO {signal}"

    if (
        tfs["5m"]["direction"] == opposite
        or tfs["1m"]["direction"] == opposite
    ):
        return f"👉 ⚠️ CONFLITTO CONTRO {signal}"

    if tfs["5m"]["direction"] == signal:
        return f"👉 ⏳ ATTENDERE CONFERMA 1m {signal}"

    if tfs["1m"]["direction"] == signal:
        return f"👉 ⏳ ATTENDERE CONFERMA 5m {signal}"

    return f"👉 ⏳ ATTENDERE CONFERMA {signal}"



def enrich_v82_setup(item):
    """Attach global pattern library classification to an already-built setup."""
    a=item.get('analysis',{})
    candles=a.get('candles') or item.get('candles')
    direction=a.get('setup_direction') or a.get('main_direction') or a.get('direction')
    if candles and direction in ('LONG','SHORT'):
        pe=world_pattern_engine(candles,direction)
        a['pattern_library']=pe
        entry=a.get('entry')
        price=a.get('price')
        a['entry_type']=classify_entry_type(price,entry,candles,direction)
        if pe.get('patterns'):
            a['pattern_display']=' + '.join(pe['patterns'])
    return item


def build_reversal_alert(position, analysis):
    """Builds a concise Telegram alert only for an existing position."""
    if not position or not analysis:
        return None
    rev = analysis.get("reversal", {})
    if not rev.get("sudden") and rev.get("stage") not in ("POSSIBLE", "CONFIRMED"):
        return None

    name = position.get("name", "Commodity")
    old_dir = position.get("direction", "N/D")
    new_dir = rev.get("direction", "N/D")
    stage = rev.get("stage")

    if stage == "CONFIRMED":
        headline = "🔴 INVERSIONE CONFERMATA"
        action = "🚨 VALUTARE USCITA / NUOVO SHORT"
    elif rev.get("sudden"):
        headline = "🚨 CAMBIO DIREZIONE REPENTINO"
        action = "⚠️ PROTEGGERE LA POSIZIONE E ATTENDERE CONFERMA"
    else:
        headline = "🟠 POSSIBILE INVERSIONE"
        action = "⚠️ NON CONFONDERE CON UN NORMALE RITRACCIAMENTO"

    return "\n".join([
        "🚨 COMMODITIES ALERT",
        "",
        f"{headline}",
        f"📌 {name}",
        f"🟢 Posizione: {old_dir}",
        f"🧭 Direzione rilevata: {new_dir}",
        f"📊 Score: {rev.get('previous_score', 0):.0f} → {rev.get('current_score', 0):.0f}",
        f"📈 Variazione: {rev.get('score_change', 0):+.0f}",
        f"🧠 Stato: {rev.get('label', 'N/D')}",
        "",
        action,
    ])


def _historical_forward_stats(rows, horizons=(3, 7, 14, 30)):
    """Anti-lookahead forward-return statistics on a historical series."""
    if not rows or len(rows) < 40:
        return {}
    closes = [safe_float(x.get("close")) for x in rows]
    out = {}
    for h in horizons:
        samples = []
        for i in range(20, len(rows) - h):
            p0, pf = closes[i], closes[i + h]
            if p0 in (None, 0) or pf is None:
                continue
            samples.append(pf / p0 - 1.0)
        if samples:
            out[str(h)] = {
                "samples": len(samples),
                "up_rate": sum(r > 0 for r in samples) / len(samples),
                "down_rate": sum(r < 0 for r in samples) / len(samples),
                "avg_return": sum(samples) / len(samples),
            }
    return out


def _historical_regime_stats(rows):
    """Finds past configurations resembling today's 3/7/14-period regime."""
    if not rows or len(rows) < 60:
        return {"similar": 0, "up_rate_7": 0.5, "avg_7": 0.0}

    c = [safe_float(x.get("close")) for x in rows]
    c = [x for x in c if x is not None]
    if len(c) < 60:
        return {"similar": 0, "up_rate_7": 0.5, "avg_7": 0.0}

    def mom(i, n):
        return c[i] / c[i-n] - 1 if c[i-n] else 0.0

    i = len(c) - 1
    now = (mom(i, 3), mom(i, 7), mom(i, 14))
    lo, hi = min(c[-60:]), max(c[-60:])
    now_pos = (c[-1] - lo) / (hi - lo) if hi > lo else 0.5

    candidates = []
    for j in range(20, len(c) - 7):
        vals = (mom(j, 3), mom(j, 7), mom(j, 14))
        lo_j, hi_j = min(c[max(0, j-59):j+1]), max(c[max(0, j-59):j+1])
        pos_j = (c[j] - lo_j) / (hi_j - lo_j) if hi_j > lo_j else 0.5
        dist = (
            abs(vals[0]-now[0])/0.03 +
            abs(vals[1]-now[1])/0.05 +
            abs(vals[2]-now[2])/0.08 +
            abs(pos_j-now_pos)
        )
        if dist <= 3.0:
            candidates.append(c[j+7] / c[j] - 1 if c[j] else 0.0)

    if not candidates:
        return {"similar": 0, "up_rate_7": 0.5, "avg_7": 0.0}
    return {
        "similar": len(candidates),
        "up_rate_7": sum(r > 0 for r in candidates) / len(candidates),
        "avg_7": sum(candidates) / len(candidates),
    }


def _seasonality_stats(rows):
    """Historical month-of-year tendency."""
    if not rows:
        return {"samples": 0, "up_rate": 0.5, "avg_return": 0.0}
    try:
        current_month = datetime.fromtimestamp(
            int(rows[-1].get("timestamp", 0)), tz=timezone.utc
        ).month
    except Exception:
        current_month = datetime.now(timezone.utc).month

    vals = []
    for i in range(1, len(rows)):
        try:
            month = datetime.fromtimestamp(
                int(rows[i].get("timestamp", 0)), tz=timezone.utc
            ).month
        except Exception:
            continue
        if month != current_month:
            continue
        p0, p1 = safe_float(rows[i-1].get("close")), safe_float(rows[i].get("close"))
        if p0 not in (None, 0) and p1 is not None:
            vals.append(p1 / p0 - 1.0)

    if not vals:
        return {"samples": 0, "up_rate": 0.5, "avg_return": 0.0}
    return {
        "samples": len(vals),
        "up_rate": sum(r > 0 for r in vals) / len(vals),
        "avg_return": sum(vals) / len(vals),
    }


def _early_context_bias(analysis):
    """Bounded live-context contribution; it cannot force an entry."""
    vals = []
    for key in ("political", "global_impact", "usd", "weather", "news"):
        obj = analysis.get(key, {}) or {}
        d = obj.get("direction")
        if d == "LONG":
            vals.append(1.0)
        elif d == "SHORT":
            vals.append(-1.0)
        else:
            sc = safe_float(obj.get("score"), None)
            if sc is not None:
                vals.append(clamp(sc / 100.0, -1, 1))
    return clamp(sum(vals) / len(vals), -1, 1) if vals else 0.0


def early_opportunity_engine(name, history_rows, analysis):
    """
    Long-horizon intelligence. It never changes signal/action and never opens
    a trade. Historical tests use only information available before each
    historical forward window, avoiding look-ahead leakage.
    """
    result = {
        "state": "NO_EARLY_EDGE",
        "direction": "NONE",
        "score": 0.0,
        "probability": 50.0,
        "horizon": "3-14 giorni",
        "history_years_target": EARLY_HISTORY_YEARS_TARGET,
        "history_observations": len(history_rows or []),
        "forward": {},
        "regime": {},
        "seasonality": {},
        "context_bias": 0.0,
        "reasons": [],
    }
    if not history_rows or len(history_rows) < EARLY_HISTORY_MIN_MONTHS:
        result["risk"] = "INSUFFICIENT_HISTORY"
        return result

    forward = _historical_forward_stats(history_rows, EARLY_TARGET_DAYS)
    regime = _historical_regime_stats(history_rows)
    season = _seasonality_stats(history_rows)
    ctx = _early_context_bias(analysis)

    biases = []
    for h in ("3", "7", "14", "30"):
        x = forward.get(h)
        if x and x["samples"] >= 20:
            biases.append((x["up_rate"] - 0.5) * 2)
    hist_bias = sum(biases) / len(biases) if biases else 0.0
    regime_bias = clamp((regime.get("up_rate_7", 0.5)-0.5)*2, -1, 1)
    season_bias = clamp((season.get("up_rate", 0.5)-0.5)*2, -1, 1)

    combined = clamp(
        0.50*hist_bias + 0.25*regime_bias + 0.10*season_bias + 0.15*ctx,
        -1, 1
    )
    direction = "LONG" if combined > 0.12 else "SHORT" if combined < -0.12 else "NONE"

    score = clamp(50 + abs(combined)*50, 0, 100)
    score += min(20, max(0, regime.get("similar", 0)-5)*0.5)
    score = clamp(score, 0, 100)
    probability = clamp(50 + combined*35, 5, 95)

    if direction != "NONE" and score >= 70:
        state = "OPPORTUNITA_ANTICIPATA"
    elif direction != "NONE" and score >= 58:
        state = "MONITOR"
    else:
        state = "NO_EARLY_EDGE"

    best_h = max(
        (h for h, x in forward.items() if x.get("samples", 0) >= 20),
        key=lambda h: abs(forward[h].get("up_rate", 0.5)-0.5),
        default="7"
    )

    reasons = []
    if abs(hist_bias) >= 0.15:
        reasons.append("storico forward favorevole " + ("LONG" if hist_bias > 0 else "SHORT"))
    if regime.get("similar", 0) >= 5:
        reasons.append(f"{regime['similar']} configurazioni storiche simili")
    if abs(season_bias) >= 0.15:
        reasons.append("stagionalità " + ("LONG" if season_bias > 0 else "SHORT"))
    if abs(ctx) >= 0.15:
        reasons.append("contesto live " + ("LONG" if ctx > 0 else "SHORT"))

    result.update({
        "state": state,
        "direction": direction,
        "score": score,
        "probability": probability,
        "horizon": f"{best_h} periodi",
        "forward": forward,
        "regime": regime,
        "seasonality": season,
        "context_bias": ctx,
        "reasons": reasons[:4],
        "risk": "NORMAL",
    })
    return result


def apply_early_opportunity(results):
    """Adds long-horizon intelligence without changing operational signals."""
    for item in results:
        if not item.get("available"):
            continue
        a = item.get("analysis", {})
        history = []
        try:
            # Monthly Yahoo history is requested with range=max, giving the
            # engine the longest series the provider makes available.
            history = get_data(item["symbol"], EARLY_HISTORY_INTERVAL, 1000)
        except Exception as exc:
            print(f"   ⚠️ Early history {item['name']}: {exc}")
        if len(history) < EARLY_HISTORY_MIN_MONTHS:
            history = item.get("candles") or []

        early = early_opportunity_engine(item["name"], history, a)
        a["early_opportunity"] = early

        setup = a.get("setup_direction") or a.get("model_signal")
        if early.get("direction") in ("LONG", "SHORT") and early.get("direction") == setup:
            a["early_alignment_bonus"] = min(8.0, max(0.0, (early["score"]-50)*0.16))
        else:
            a["early_alignment_bonus"] = 0.0


def build_early_telegram(ranked):
    available = [
        x for x in ranked
        if x.get("available") and x.get("analysis", {}).get("early_opportunity")
    ]
    available.sort(
        key=lambda x: safe_float(
            x["analysis"]["early_opportunity"].get("score"), 0
        ) or 0,
        reverse=True
    )
    available = available[:EARLY_TOP_N]
    lines = ["🔭 OPPORTUNITÀ IN ANTICIPO", "━━━━━━━━━━━━━━━━━━━━"]
    medals = ["🥇", "🥈", "🥉"]

    for i, item in enumerate(available):
        e = item["analysis"]["early_opportunity"]
        d = e.get("direction", "NONE")
        icon = "🟠" if e.get("state") == "OPPORTUNITA_ANTICIPATA" else "🟡" if e.get("state") == "MONITOR" else "⚪"
        h7 = e.get("forward", {}).get("7", {})
        hist = (
            f"Storico 7p: {h7.get('up_rate', 0.5)*100:.0f}% LONG"
            if h7.get("samples", 0) >= 20 else "Storico: campione limitato"
        )
        lines += [
            "",
            f"{medals[i]} {item['name']}",
            f"{icon} {e.get('state','N/D')} | {d}",
            f"🔭 Early Score: {e.get('score',0):.0f}/100 | Prob. {e.get('probability',50):.0f}%",
            f"📚 {hist}",
            f"⏳ Orizzonte: {e.get('horizon','N/D')}",
        ]
        if e.get("reasons"):
            lines.append("🧠 " + " | ".join(e["reasons"][:3]))
        lines.append("⚠️ Anticipazione: NON è un ingresso automatico.")
    return "\n".join(lines)


def _monitor_context_line(a):
    """Compact context: fundamentals/global factors inform, but do not decide entry."""
    weather = a.get("weather", {}) or {}
    political = a.get("political", {}) or {}
    global_impact = a.get("global_impact", {}) or {}
    usd = a.get("usd", {}) or {}
    return (
        f"🌦️ Meteo {weather.get('direction', 'N/D')} | "
        f"🌍 Geo {global_impact.get('direction', 'N/D')} | "
        f"🇺🇸 Politica {political.get('direction', 'N/D')} | "
        f"💵 USD {usd.get('direction', 'N/D')}"
    )

def build_telegram_5m(ranked, best, position_message=None, position=None):
    """v2.7: concise operational monitor intended for a 5-minute schedule."""
    available = [x for x in ranked if x.get("available")][:MONITOR_TOP_N]
    early_block = build_early_telegram(ranked)
    lines = [
        "🌍 COMMODITIES BOT v2.9",
        f"⏱️ MONITORAGGIO OGNI {MONITOR_INTERVAL_MINUTES} MINUTI",
        "",
        early_block,
        "",
        "⚡ TRADING OGGI",
        "━━━━━━━━━━━━━━━━━━━━",
    ]
    medals = ["🥇", "🥈", "🥉"]
    for i, item in enumerate(available):
        a = item["analysis"]
        action = a.get("action_label", "ATTENDERE")
        direction = a.get("setup_direction") or a.get("model_signal") or "N/D"
        icon = "🟢" if action == "COMPRA ORA" else "🔴" if action == "VENDI ORA" else "🟡" if direction in ("LONG", "SHORT") else "⚪"
        trig = a.get("entry_trigger", {}) or {}
        prob = a.get("entry_probability", a.get("probability", 0) * 100)
        lines += [
            "",
            f"{medals[i]} {item['name']}",
            f"{icon} {action} | {direction}",
            f"📊 Score {a.get('score',0):.0f} | Prob {prob:.1f}% | Q {a.get('quality',0):.0f}",
            f"📚 L2L: {(a.get('level_to_level',{}) or {}).get('state','N/D')} | {(a.get('level_to_level',{}) or {}).get('behaviour','N/D')} | {(a.get('level_to_level',{}) or {}).get('score',50):.0f}/100",
            f"⚡ Trigger: {trig.get('kind','N/D')} {trig.get('timeframe','')}".strip(),
            f"🧭 1H {a.get('timeframes',{}).get('1H',{}).get('direction','N/D')} | 15m {a.get('timeframes',{}).get('15m',{}).get('direction','N/D')} | 5m {a.get('timeframes',{}).get('5m',{}).get('direction','N/D')} | 1m {a.get('timeframes',{}).get('1m',{}).get('direction','N/D')}",
            _monitor_context_line(a),
        ]
        if action in ("COMPRA ORA", "VENDI ORA"):
            if a.get("price") is not None:
                lines.append(f"💰 Prezzo {a['price']:.4f}")
            if a.get("entry") is not None:
                lines.append(f"📥 Entry {a['entry']:.4f}")
            if a.get("stop") is not None:
                lines.append(f"🛑 SL {a['stop']:.4f}")
            lines.append(
                f"🎯 TP1 {a.get('tp1',0):.4f} | TP2 {a.get('tp2',0):.4f} | TP3 {a.get('tp3',0):.4f}"
            )
        else:
            blockers = a.get("entry_blockers", []) or []
            if blockers:
                lines.append("⛔ " + " | ".join(blockers[:3]))
            if a.get("price") is not None:
                lines.append(f"💰 Prezzo {a['price']:.4f}")

    gm = best.get("analysis", {}).get("global_impact", {}) or {}
    if gm.get("mode") == "SHOCK":
        lines += ["", "🚨 GLOBAL SHOCK — nuove entrate solo con conferma completa."]
    elif gm.get("mode") == "ALERT":
        lines += ["", "⚠️ GLOBAL ALERT — contesto volatile."]

    if position_message:
        lines += ["", "━━━━━━━━━━━━━━━━━━━━", "📌 POSIZIONE", position_message]

    lines += ["", f"🔄 Prossimo controllo: ~{MONITOR_INTERVAL_MINUTES} minuti"]
    return "\n".join(lines)

def save_monitor_state(ranked, best, position):
    """Persist the latest monitor snapshot when the runner persists workspace files."""
    try:
        a = best.get("analysis", {}) or {}
        t = a.get("entry_trigger", {}) or {}
        _json_save(MONITOR_STATE_FILE, {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "best": best.get("name"),
            "direction": a.get("setup_direction") or a.get("model_signal"),
            "action": a.get("action_label"),
            "entry_state": a.get("entry_state"),
            "trigger": t.get("kind"),
            "trigger_tf": t.get("timeframe"),
            "position": (position or {}).get("name"),
            "position_direction": (position or {}).get("direction"),
        })
    except Exception as exc:
        print(f"⚠️ Monitor state non salvato: {exc}")

def build_telegram(ranked, best, position_message=None, position=None):
    """Telegram operativo V8: niente dettagli tecnici interni."""
    available=[x for x in ranked if x.get('available')][:3]
    lines=['🌍 COMMODITIES BOT v3.0','', '🏆 CLASSIFICA']
    medals=['🥇','🥈','🥉']
    for i,item in enumerate(available):
        a=item['analysis']; action=a.get('action_label')
        if action=='ENTRARE': icon='🟢'
        elif action=='NON ENTRARE': icon='🔴'
        else: icon='🟡'
        lines += ['',f"{medals[i]} {item['name']}",f"{icon} {action} | {a.get('setup_direction','N/D')}"]
    global_mode=best.get('analysis',{}).get('global_impact',{}).get('mode','NORMAL')
    confirmed_global=int(best.get('analysis',{}).get('global_impact',{}).get('shock_count',0) or 0)
    if global_mode=='SHOCK' and confirmed_global>=2:
        lines += ['', '🚨 MERCATO BLOCCATO','NUOVE ENTRATE BLOCCATE','📌 Posizioni esistenti: SOLO GESTIONE / PROTEZIONE']
    elif global_mode=='ALERT':
        lines += ['', '⚠️ MERCATO IN ALLERTA','Entrare solo con conferma completa']
    for i,item in enumerate(available):
        a=item['analysis']; medal=medals[i]; direction=a.get('setup_direction') or a.get('signal')
        price=a.get('price'); entry=a.get('entry'); stop=a.get('stop'); tp1=a.get('tp1'); tp2=a.get('tp2'); tp3=a.get('tp3')
        timing=a.get('timing',{}); pattern=a.get('candle_pattern','N/D')
        action=a.get('action_label','ATTENDERE')
        lines += ['', '━━━━━━━━━━━━━━━━━━━━', f'{medal} {item["name"]}', '━━━━━━━━━━━━━━━━━━━━',
                  f'🎯 AZIONE: {action}', f'🧭 DIREZIONE: {direction}', f'🧩 STATO ENTRY: {a.get("entry_state","N/D")}', f'📊 SCORE/QUALITÀ/CONF: {a.get("score",0):.0f}/{a.get("quality",0):.0f}/{a.get("confidence",0):.0f}',
                  f'💰 PREZZO ATTUALE: {price:.4f}' if price is not None else '💰 PREZZO ATTUALE: N/D',
                  f'📥 ENTRATA: {entry:.4f}' if entry is not None else '📥 ENTRATA: N/D', f'📌 SETUP: {a.get("entry_method","N/D")}', f'⚡ TRIGGER: {a.get("entry_trigger",{}).get("kind","N/D")} {a.get("entry_trigger",{}).get("timeframe","")}'.strip(), f'🕯️ PATTERN: {pattern}', f'📚 STORICO SETUP: {a.get("pattern_backtest",{}).get("win_rate",0)*100:.0f}% successo' if a.get("pattern_backtest",{}).get("samples",0)>=5 else '📚 STORICO SETUP: dati insufficienti',
                  f'🧠 ENSEMBLE: {a.get("ensemble_alignment","N/D")} | RANK {a.get("ensemble_rank","N/D")} | {a.get("cross_sectional_score",50):.0f}/100',
                  f'🧭 V3: EARLY {a.get("early_opportunity",{}).get("state","N/D")} {a.get("early_opportunity",{}).get("direction","N/D")} | POL {a.get("political",{}).get("direction","N/D")} | CURVE {a.get("futures_structure",{}).get("state","N/D")}',
                  f'🔄 REVERSAL: {a.get("reversal",{}).get("label","N/D")}',
                  f'🌡️ REGIME: {a.get("institutional",{}).get("regime","N/D")} | VOLUME/FLOW PROXY: {a.get("institutional",{}).get("volume_confirmation",0):+.2f}']
        item_mode=a.get('risk',{}).get('mode', global_mode)
        if item_mode=='SHOCK':
            lines.append('🚨 ENTRATA BLOCCATA — SHOCK MODE')
        elif item_mode=='ALERT':
            lines.append('⚠️ ENTRATA SOLO CON CONFERMA COMPLETA')
        lines += [
            f'🛑 STOP LOSS: {stop:.4f}' if stop is not None else '🛑 STOP LOSS: N/D',
            f'🎯 TP1: {tp1:.4f}' if tp1 is not None else '🎯 TP1: N/D',
            f'🎯 TP2: {tp2:.4f}' if tp2 is not None else '🎯 TP2: N/D',
            f'🎯 TP3: {tp3:.4f}' if tp3 is not None else '🎯 TP3: N/D',
            f'⏰ ORARIO MIGLIORE: {timing.get("best_time","N/D")}',
            f'⏳ FINESTRA: {timing.get("window","N/D")}',
        ]
        if action=='ENTRARE': lines.append('👉 Entrare solo se il prezzo conferma l\'area di ingresso.')
        elif action=='ATTENDERE': lines.append(f'👉 Attendere conferma {direction}.')
        else: lines.append('👉 Nessuna nuova entrata.')
        lines += ['', '📌 GESTIONE','TP1 → STOP A BREAK-EVEN','TP2 → STOP A TP1','TP3 → CHIUDERE','STOP LOSS → CHIUDERE','SEGNALE OPPOSTO CONFERMATO → CHIUDERE']
    if position_message:
        lines += ['', '━━━━━━━━━━━━━━━━━━━━','📌 POSIZIONE',position_message]
        if position and best.get("name") == position.get("name"):
            rev = best.get("analysis", {}).get("reversal", {})
            if rev.get("stage") == "RETRACEMENT":
                lines.append("🟡 RITRACCIAMENTO — trend principale ancora valido")
            elif rev.get("stage") == "POSSIBLE":
                lines.append("🟠 POSSIBILE INVERSIONE — attendere conferma")
            elif rev.get("stage") == "CONFIRMED":
                lines.append("🔴 INVERSIONE CONFERMATA — proteggere/valutare uscita")
    return '\n'.join(lines)

def analysis_direction_hint(timeframes):
    vals = [timeframes.get(tf, {}).get("direction", "NONE") for tf in ("4H", "1H", "15m")]
    if vals.count("LONG") >= 2:
        return "LONG"
    if vals.count("SHORT") >= 2:
        return "SHORT"
    return "NONE"


# ============================================================
# v3.0 FUTURES STRUCTURE / CONTANGO-BACKWARDATION ENGINE
# ============================================================

def futures_structure_engine(name):
    """Optional front-vs-next futures curve signal.

    The engine is intentionally conservative: without explicit provider symbols
    it returns N/D rather than inventing a curve. When symbols are supplied,
    it computes the annualized-ish front/next slope proxy from the latest closes.
    """
    base = {"enabled": FUTURES_STRUCTURE_ENABLED, "status": "N/D", "state": "N/D",
            "score": 0.0, "front": None, "next": None, "spread_pct": None,
            "symbol_front": None, "symbol_next": None}
    if not FUTURES_STRUCTURE_ENABLED:
        base["status"] = "DISABLED"
        return base
    syms = FUTURES_SYMBOLS.get(name)
    if not isinstance(syms, (list, tuple)) or len(syms) < 2:
        base["status"] = "SYMBOLS_NOT_CONFIGURED"
        return base
    try:
        front_sym, next_sym = str(syms[0]), str(syms[1])
        front = get_data(front_sym, "1day", 30)
        nxt = get_data(next_sym, "1day", 30)
        if not front or not nxt:
            base["status"] = "DATA_UNAVAILABLE"
            return base
        f = safe_float(front[-1].get("close"), None)
        n = safe_float(nxt[-1].get("close"), None)
        if f is None or n is None or f <= 0:
            base["status"] = "DATA_INVALID"
            return base
        spread_pct = (n / f - 1.0) * 100.0
        # Positive next>front = contango; negative = backwardation.
        if spread_pct > 0.35:
            state, score = "CONTANGO", -min(8.0, spread_pct * 2.0)
        elif spread_pct < -0.35:
            state, score = "BACKWARDATION", min(8.0, abs(spread_pct) * 2.0)
        else:
            state, score = "FLAT", 0.0
        return {**base, "status": "OK", "state": state, "score": round(score,2),
                "front": f, "next": n, "spread_pct": round(spread_pct,3),
                "symbol_front": front_sym, "symbol_next": next_sym}
    except Exception as exc:
        base["status"] = f"ERROR: {exc}"
        return base


def apply_futures_structure(analysis, structure):
    analysis["futures_structure"] = structure or {}
    if not structure or structure.get("status") != "OK":
        return
    # Curve information is a bounded context adjustment, never a standalone trade.
    delta = float(structure.get("score", 0.0) or 0.0)
    direction = analysis.get("setup_direction") or analysis.get("model_signal")
    if direction == "SHORT":
        delta = -delta
    analysis["score"] = clamp(float(analysis.get("score", 0.0)) + delta, 0, 100)
    analysis["futures_structure_delta"] = round(delta, 2)


# ============================================================
# v3.0 POLITICAL EVENT -> MECHANISM -> COMMODITY -> HORIZON
# ============================================================

POLITICAL_RULES = {
    "tariff": {"mechanism": "trade_flow", "horizon": "1-14d"},
    "tariffs": {"mechanism": "trade_flow", "horizon": "1-14d"},
    "sanction": {"mechanism": "supply_disruption", "horizon": "1-30d"},
    "sanctions": {"mechanism": "supply_disruption", "horizon": "1-30d"},
    "export ban": {"mechanism": "supply_disruption", "horizon": "1-30d"},
    "trade war": {"mechanism": "trade_flow", "horizon": "3-30d"},
    "opec": {"mechanism": "energy_supply", "horizon": "1-14d"},
    "ceasefire": {"mechanism": "risk_premium", "horizon": "1-14d"},
    "war": {"mechanism": "risk_premium", "horizon": "1-30d"},
    "conflict": {"mechanism": "risk_premium", "horizon": "1-30d"},
    "fed": {"mechanism": "rates_usd", "horizon": "1-14d"},
}

POLITICAL_COMMODITY_MAP = {
    "Oro": ["tariff", "sanction", "war", "conflict", "fed", "rates", "dollar", "geopolit"],
    "Argento": ["tariff", "trade", "china", "industrial", "war", "sanction"],
    "Rame": ["tariff", "china", "trade", "sanction", "mine", "export", "critical mineral"],
    "Petrolio WTI": ["opec", "sanction", "iran", "russia", "war", "tariff", "export"],
    "Petrolio Brent": ["opec", "sanction", "iran", "russia", "war", "tariff", "export"],
    "Gas Naturale": ["lng", "russia", "ukraine", "sanction", "pipeline", "war", "europe"],
    "Grano": ["ukraine", "russia", "black sea", "tariff", "export", "sanction", "war"],
    "Mais": ["tariff", "china", "trade", "export", "agriculture"],
    "Caffè": ["tariff", "brazil", "vietnam", "export", "trade"],
}


def political_impact_v3(name, base=None):
    """Turn political headlines into bounded, explainable event context."""
    if not POLITICAL_IMPACT_ENABLED:
        return base or {"direction":"NEUTRALE", "score":0.0, "count":0, "status":"DISABLED"}
    base = dict(base or political_impact(name) or {})
    try:
        query_terms = POLITICAL_COMMODITY_MAP.get(name, [name])
        query = "(" + " OR ".join(query_terms[:8]) + ") (Trump OR tariff OR sanctions OR geopolitics OR OPEC OR Fed)"
        articles = _fetch_rss_articles(query, limit=30)
    except Exception:
        articles = []
    if not articles:
        base.update({"v3_status":"NO_EVENT_FEED", "mechanism":"N/D", "horizon":"N/D"})
        return base
    weights = []
    mechanisms = {}
    for a in articles:
        text = f"{a.get('title','')} {a.get('description','')}".lower()
        matched = [k for k in POLITICAL_RULES if k in text]
        if not matched:
            continue
        sign = 0
        # Conservative polarity: supply shock/risk escalation positive for oil/gold,
        # while tariffs are not automatically bullish/bearish across commodities.
        if any(k in text for k in ("escalation", "sanction", "sanctions", "attack", "war", "conflict", "export ban", "opec cut")):
            sign = 1
        if any(k in text for k in ("ceasefire", "peace", "de-escalation", "supply increase", "opec increase")):
            sign = -1
        for k in matched:
            rule = POLITICAL_RULES[k]
            mechanisms[rule["mechanism"]] = mechanisms.get(rule["mechanism"], 0) + 1
        weights.append(sign)
    if weights:
        raw = sum(weights) / len(weights)
    else:
        raw = float(base.get("score", 0.0) or 0.0)
    raw = clamp(raw, -1, 1)
    # Keep political influence bounded; it cannot override the price engine.
    if abs(raw) < 0.20:
        direction = "NEUTRALE"
    elif raw > 0:
        direction = "FAVOREVOLE"
    else:
        direction = "SFAVOREVOLE"
    mechanism = max(mechanisms, key=mechanisms.get) if mechanisms else "N/D"
    horizon = "1-3d" if len(articles) < 8 else "1-14d" if len(articles) < 18 else "1-30d"
    out = dict(base)
    out.update({"score": round(raw,3), "direction": direction, "count": len(articles),
                "v3_status":"OK", "mechanism":mechanism, "horizon":horizon,
                "event_count":len(weights)})
    return out


def v3_context_summary(analysis):
    early = analysis.get("early_opportunity", {}) or {}
    political = analysis.get("political", {}) or {}
    fs = analysis.get("futures_structure", {}) or {}
    rev = analysis.get("reversal", {}) or {}
    return {
        "early": early.get("state", "N/D"),
        "early_direction": early.get("direction", "N/D"),
        "political": political.get("direction", "N/D"),
        "political_mechanism": political.get("mechanism", "N/D"),
        "political_horizon": political.get("horizon", "N/D"),
        "curve": fs.get("state", "N/D"),
        "reversal": rev.get("label", "N/D"),
    }


def build_v3_header():
    return [
        "🌍 COMMODITIES BOT v3.0",
        "🧪 PAPER / ANALISI — ORDINI REALI DISABILITATI",
        "━━━━━━━━━━━━━━━━━━━━",
        "🔭 EARLY OPPORTUNITY | ⚡ TRADING OGGI | 🧠 POLITICAL IMPACT | 📈 FUTURES CURVE",
    ]


# ============================================================
# MAIN
# ============================================================

def main():
    print()
    print("=" * 70)
    print("🌍 COMMODITIES BOT v3.0")
    print("5-MIN SMART MONITOR + EARLY OPPORTUNITY + POLITICAL IMPACT + FUTURES STRUCTURE + PAPER GATE")
    print("=" * 70)
    print()

    position = load_position()
    print("🧠 Aggiornamento Trading Knowledge Engine...")
    trading_knowledge = refresh_trading_knowledge()
    print(f"   📚 Fonti: {trading_knowledge['sources']} | utilizzabili: {trading_knowledge['usable']}")
    usd = analyze_usd()
    print("🌍 Avvio Global Market Intelligence...")
    global_intel = global_market_intelligence()
    print(f"   📰 Global news: {global_intel['count']} | fonti {global_intel.get('source_count', 0)} | mode {global_intel['mode']} | shock {global_intel['shock_intensity']:.2f}")

    results = []
    resolved_symbols = resolve_commodity_symbols()

    # Analizza SEMPRE tutte le commodity configurate. Un errore su una non
    # deve interrompere né nascondere le altre.
    for name in COMMODITIES:
        symbol = resolved_symbols.get(name, COMMODITIES[name])
        print(f"🔎 Analizzo {name} [{symbol}]...")

        try:
            candles = get_daily_data(symbol)
            print(f"   📥 Dati giornalieri: {len(candles)}")

            if len(candles) < 120:
                raise RuntimeError(f"Dati giornalieri insufficienti ({len(candles)}/120)")

            source_check = compare_sources(name, symbol, candles)
            dataset = build_dataset(candles)
            print(f"   🧮 Dataset: {len(dataset)} | Fonte: {DATA_SOURCE_STATS.get(name, {}).get("1day", "N/D")}")

            if len(dataset) < 80:
                raise RuntimeError(f"Dataset insufficiente ({len(dataset)}/80)")

            bt = backtest(dataset)
            model = train_final(dataset)
            if model is None:
                raise RuntimeError("Modello non disponibile")

            timeframes = get_multitimeframe(symbol)
            news = analyze_news(name)
            political = political_impact_v3(name, political_impact(name))
            global_impact = commodity_global_impact(name, global_intel)
            session = session_engine(name, symbol, "LONG" if analysis_direction_hint(timeframes) == "LONG" else "SHORT" if analysis_direction_hint(timeframes) == "SHORT" else "NONE")

            # Dati 1H dedicati a candlestick, entry e timing storico.
            intraday_candles = get_data(symbol, "1h", 1200)
            if len(intraday_candles) < 80:
                raise RuntimeError(f"Storico 1H insufficiente per Entry/Timing ({len(intraday_candles)}/80)")

            # Libreria pattern multi-timeframe: 4H, 1H, 15m, 5m e 1m.
            # Se un timeframe non è disponibile, gli altri continuano a pesare.
            pattern_timeframes = {"1H": intraday_candles}
            for _tf, _interval, _size in (("4H", "4h", 500), ("15m", "15min", 500), ("5m", "5min", 500), ("1m", "1min", 500)):
                try:
                    _c = get_data(symbol, _interval, _size)
                    if len(_c) >= 30:
                        pattern_timeframes[_tf] = _c
                except Exception as _e:
                    print(f"   ⚠️ Pattern {_tf}: {_e}")

            analysis = analyze(
                candles, dataset, model, bt, usd, news, timeframes, political, commodity_name=name,
                global_impact=global_impact, session=session, intraday_candles=intraday_candles, pattern_timeframes=pattern_timeframes,
                trading_knowledge=trading_knowledge
            )
            if analysis is None:
                raise RuntimeError("Analisi Gold Engine non disponibile")

            analysis["pattern_timeframes"] = pattern_timeframes or {}
            analysis["source_check"] = source_check or {}

            weather = weather_intelligence(name)
            disasters = natural_disaster_intelligence(name)
            apply_weather_and_disaster_layers(analysis, weather, disasters)

            # v2.9: Level-to-Level technical structure after all current context layers.
            level_to_level_engine(
                analysis, commodity_name=name, candles=candles,
                pattern_timeframes=pattern_timeframes
            )

            # v3.0: optional futures curve context. No data -> no invented signal.
            _curve = futures_structure_engine(name)
            apply_futures_structure(analysis, _curve)
            analysis["v3_context"] = v3_context_summary(analysis)

            results.append({
                "name": name,
                "symbol": symbol,
                "candles": candles,
                "analysis": analysis,
                "backtest": bt,
                "available": True,
                "source_check": source_check,
            })

            print(
                f"   ✅ ANALIZZATA | MODELLO {analysis['model_signal']} | "
                f"OPERATIVO {analysis['signal']} | SCORE {analysis['score']:.0f} | "
                f"QUALITÀ {analysis['risk']['market_quality']:.0f} | "
                f"SESSIONE {analysis['session']['current_band']}"
            )

        except Exception as error:
            # La commodity resta nel ranking come NON DISPONIBILE, così il
            # report dimostra esplicitamente che è stata controllata.
            print(f"   ❌ NON DISPONIBILE: {error}")
            results.append({
                "name": name,
                "symbol": symbol,
                "candles": [],
                "analysis": {
                    "signal": "NONE",
                    "grade": "DATI NON DISPONIBILI",
                    "score": -1,
                    "price": None,
                    "long_probability": 0.5,
                    "short_probability": 0.5,
                    "confidence": 0,
                    "quality": 0,
                    "model_signal": "NONE",
                    "timeframes": {},
                    "news": {"label": "N/D", "count": 0, "source": "NONE", "status": str(error)},
                    "political": {"direction": "N/D", "score": 0, "count": 0},
                    "usd": usd,
                    "repetition": {"direction": "N/D", "frequency": 0, "samples": 0},
                    "fast_conflicts": 0,
                    "fast_confirmations": 0,
                    "structural_same": 0,
                    "strong_confirmation": False,
                    "global_impact": global_impact,
                    "session": {"current_band": "N/D", "best_band": "N/D", "worst_band": "N/D", "exit_band": "N/D", "quality": 0, "allocation_pct": 0, "bands": {}},
                    "risk": {"confluence": 0, "confluence_total": 6, "market_quality": 0, "risk_pct": 0, "mode": "ERROR", "checks": []},
                    "cyclical": {"direction": "N/D", "quality": 0, "score": 0},
                    "risk_benefit": {"score": 0, "risk": 100, "reward_risk": 0, "label": "N/D"},
                },
                "backtest": {},
                "available": False,
                "error": str(error),
            })

    if not results:
        raise RuntimeError("Nessuna materia prima analizzata.")

    # v2.4: cross-sectional multi-horizon ensemble + volatility/flow proxies.
    apply_cross_sectional_ensemble(results)
    for _item in results:
        if _item.get("available"):
            _ok, _reason = ensemble_trade_gate(_item["analysis"])
            _item["analysis"]["ensemble_gate"] = _ok
            _item["analysis"]["ensemble_gate_reason"] = _reason
            if not _ok and _item["analysis"].get("signal") in ("LONG", "SHORT"):
                _item["analysis"]["signal"] = "WAIT"
                _item["analysis"]["action_label"] = "ATTENDERE"
                _item["analysis"]["strong_confirmation"] = False

    # v2.6: finalizzazione unica dopo TUTTI i layer.
    for _item in results:
        if _item.get("available"):
            finalize_v26_analysis(_item["analysis"])

    # v2.7: diagnostica trasparente dei blocchi di ingresso per le migliori 5.
    _diag = [x for x in results if x.get("available") and x.get("analysis",{}).get("setup_direction") in ("LONG","SHORT")]
    _diag.sort(key=lambda x: safe_float(x.get("analysis",{}).get("score"),0) or 0, reverse=True)
    print("\n🔬 DIAGNOSTICA ENTRY v2.7")
    for _it in _diag[:5]:
        _a=_it["analysis"]; _t=_a.get("entry_trigger",{}) or {}; _r=_a.get("risk",{}) or {}; _l=_a.get("level_to_level",{}) or {}
        print(f"   {_it['name']}: {_a.get('setup_direction')} | score={_a.get('score',0):.1f} q={_a.get('quality',0):.1f} conf={_a.get('confidence',0):.1f} prob={_a.get('entry_probability',0):.1f}% | L2L={_l.get('score',0):.1f} {_l.get('behaviour','-')} gate={_l.get('gate')} | MTF={_a.get('structural_same',0)} | fast_opp={_a.get('fast_conflicts',0)} | risk={_r.get('mode')} mq={_r.get('market_quality',0):.1f} rb={safe_float(_a.get('risk_benefit',{}).get('score'),0) or 0:.1f} | trigger={_t.get('kind')} {_t.get('timeframe','-')} {_t.get('score',0):.1f} confirmed={_t.get('confirmed')} | state={_a.get('entry_state')} | blockers={','.join(_a.get('entry_blockers',[])) or 'NESSUNO'}")

    new_predictions, _prediction_log = record_predictions(results)
    print(f"📝 Prediction Journal: {new_predictions} nuove previsioni registrate")

    print("\n🧠 V3 CONTEXT")
    for _it in sorted([x for x in results if x.get("available")], key=lambda x: safe_float(x.get("analysis",{}).get("score"),0) or 0, reverse=True)[:5]:
        _a=_it["analysis"]; _v=_a.get("v3_context",{}) or {}; _p=_a.get("political",{}) or {}; _f=_a.get("futures_structure",{}) or {}
        print(f"   {_it['name']}: EARLY={_v.get('early')} {_v.get('early_direction')} | POL={_p.get('direction')} { _p.get('mechanism','N/D')} { _p.get('horizon','N/D')} | CURVE={_f.get('state')} | REV={_v.get('reversal')}")

    print("\n🔭 EARLY OPPORTUNITY ENGINE v3.0")
    for _it in sorted(
        [x for x in results if x.get("available")],
        key=lambda x: safe_float(x.get("analysis",{}).get("early_opportunity",{}).get("score"),0) or 0,
        reverse=True
    )[:5]:
        _e = _it["analysis"].get("early_opportunity", {})
        print(
            f"   {_it['name']}: {_e.get('state')} | {_e.get('direction')} | "
            f"score={_e.get('score',0):.1f} prob={_e.get('probability',50):.1f}% | "
            f"simili={_e.get('regime',{}).get('similar',0)}"
        )

    # ========================================================
    # RANKING
    # ========================================================

    # Ranking finale: non basta il segnale; privilegiamo opportunità, rischio e R/R.
    for item in results:
        if item.get("available"):
            rb = item["analysis"].get("risk_benefit", {})
            base_rb = safe_float(rb.get("score"), item["analysis"].get("score", 0)) or 0
            q = safe_float(item["analysis"].get("quality"), 0) or 0
            conf = safe_float(item["analysis"].get("confidence"), 0) or 0
            # Ranking coerente: opportunità + qualità + confidenza, senza
            # permettere a una sola metrica di dominare.
            item["ranking_score"] = clamp(base_rb * 0.60 + q * 0.25 + conf * 0.15 + safe_float(item["analysis"].get("early_alignment_bonus"), 0), 0, 100)
        else:
            item["ranking_score"] = -1

    ranked = sorted(results, key=lambda x: x.get("ranking_score", -1), reverse=True)
    available_ranked = [x for x in ranked if x.get("available") and x["analysis"]["score"] >= 0]
    if not available_ranked:
        raise RuntimeError("Nessuna commodity dispone di dati sufficienti per il Gold Engine. Controllare simboli/API quota.")
    best = available_ranked[0]

    demo_execution = demo_execution_adapter(results, position)
    print(f"🤖 Demo adapter: {demo_execution.get('reason', 'ordine registrato')}" if not demo_execution.get('executed') else f"🤖 DEMO ORDER: {demo_execution['order']['commodity']} {demo_execution['order']['side']}")

    # ========================================================
    # GESTIONE POSIZIONE ESISTENTE
    # ========================================================

    position_message = None

    if position:
        matching = [
            x for x in results
            if x["name"] == position["name"]
        ]

        if matching:
            current = matching[0]
            current_price = current["analysis"]["price"]

            management = manage_position(
                position,
                current["analysis"],
                current_price,
            )

            if management["action"] == "EXIT":
                position_message = (
                    f"🚨 POSIZIONE {position['direction']} — USCITA\n"
                    f"Motivo: {management['reason']}"
                )
                clear_position()
                position = None

            else:
                if management.get("new_stop") != position["stop"]:
                    position["stop"] = management["new_stop"]
                if management.get("break_even"):
                    position["break_even"] = True
                if management.get("tp2_reached"):
                    position["tp2_reached"] = True
                save_position(position)

                icon = "🟡" if management["action"] == "MOVE_STOP" else "🟢"
                position_message = (
                    f"{icon} POSIZIONE {position['direction']} — "
                    f"{management['reason']}\n"
                    f"STOP ATTUALE: {position['stop']:.4f}"
                )

    # ========================================================
    # NUOVA POSIZIONE
    # ========================================================

    if not position and best["analysis"]["signal"] in ("LONG", "SHORT"):
        second_score = available_ranked[1].get("ranking_score", available_ranked[1]["analysis"]["score"]) if len(available_ranked) > 1 else 0
        a = best["analysis"]

        # Apertura solo se:
        # - score alto
        # - qualità/confidenza sufficienti
        # - margine sul secondo setup
        # - nessun conflitto rapido
        if (
            a["score"] >= MIN_SCORE
            and a["quality"] >= MIN_QUALITY
            and a["confidence"] >= MIN_CONFIDENCE
            and a.get("risk_benefit", {}).get("score", a["score"]) - second_score >= MIN_RANK_MARGIN
            and a["fast_conflicts"] == 0
            and a["strong_confirmation"]
            and a.get("risk", {}).get("mode") == "NORMAL"
            and a.get("risk", {}).get("market_quality", 0) >= 60
            and a.get("risk", {}).get("risk_pct", 0) > 0
            and a.get("reversal", {}).get("stage") != "CONFIRMED"
        ):
            position = {
                "name": best["name"],
                "symbol": best["symbol"],
                "direction": a["signal"],
                "entry": a.get("entry") or a["price"],
                "stop": a["stop"],
                "tp1": a["tp1"],
                "tp2": a["tp2"],
                "tp3": a["tp3"],
                "risk_pct": a.get("risk", {}).get("risk_pct", 0.0),
                "break_even": False,
                "tp2_reached": False,
                "opened_at": datetime.now(timezone.utc).isoformat(),
            }

            save_position(position)

            position_message = (
                f"🚨 NUOVA POSIZIONE {a['signal']}\n"
                f"Entry {a.get('entry') or a['price']:.4f} | "
                f"SL {a['stop']:.4f} | "
                f"TP1 {a['tp1']:.4f} | "
                f"TP2 {a['tp2']:.4f}"
            )
        else:
            position_message = (
                "🟡 NESSUNA APERTURA AUTOMATICA — "
                "setup non abbastanza selettivo."
            )
    elif not position:
        position_message = "🟡 NESSUNA ENTRATA."

    # ========================================================
    # OUTPUT
    # ========================================================

    print()
    print("=" * 70)
    print("🏆 MIGLIORE OPPORTUNITÀ")
    print("=" * 70)

    a = best["analysis"]

    print(f"Materia prima: {best['name']}")
    print(f"Segnale modello: {a['model_signal']}")
    print(f"Segnale operativo: {a['signal']}")
    print(f"Score: {a['score']:.1f}/100")
    print(f"Probabilità: {a['probability'] * 100:.1f}%")
    print(f"Confidenza: {a['confidence']:.1f}/100")
    print(f"Qualità: {a['quality']:.1f}/100")
    print(f"Knowledge Engine: {a.get('trading_knowledge', {}).get('usable', 0)} fonti | bias {a.get('knowledge_bias', 0):+.1f}")
    print(f"Learning Engine: {len(a.get('learning_validated_rules', []))} regole validate | attive {', '.join(a.get('learning_current_hits', [])) or 'nessuna'} | score {a.get('learning_score', 0):.1f}")
    _l2l = a.get("level_to_level", {}) or {}
    print(f"Level-to-Level: {_l2l.get('state','N/D')} | score {_l2l.get('score',50):.1f} | trend {_l2l.get('trend','N/D')} | {_l2l.get('behaviour','N/D')} | gate {_l2l.get('gate')}")
    print(
        f"Ricorrenza storica: "
        f"{a['repetition']['direction']} | "
        f"{a['repetition']['frequency'] * 100:.1f}%"
    )

    print()
    print("=" * 70)
    print("📊 RANKING")
    print("=" * 70)

    for i, item in enumerate(ranked, 1):
        x = item["analysis"]
        if not item.get("available"):
            print(f"{i}. ⚪ {item['name']} | DATI NON DISPONIBILI | {item.get('error', '')}")
            continue
        print(
            f"{i}. {icon_for_signal(x['signal'])} "
            f"{item['name']} | "
            f"{x['signal']} | "
            f"R/B {item.get('ranking_score', x['score']):.0f}/100 | "
            f"SHORT {x['short_probability'] * 100:.1f}% | "
            f"storico {x['repetition']['direction']} | fonte {item.get('source_check', {}).get('status', 'N/D')}"
        )

    # v2.7: messaggio Telegram compatto e operativo ad ogni esecuzione.
    # Il job esterno deve essere schedulato ogni 5 minuti.
    monitor_message = build_telegram_5m(ranked, best, position_message, position)
    if MONITOR_SEND_FULL:
        send_telegram(monitor_message)
    else:
        print(monitor_message)
    save_monitor_state(ranked, best, position)

    # Fine giornata: valuta le previsioni maturate e invia il report una sola volta.
    eod_report = run_end_of_day_test()
    if eod_report:
        send_telegram(eod_report)
        print(eod_report)

    # Separate alert: only for the commodity currently held.
    if position:
        held = next((x for x in results if x.get("name") == position.get("name") and x.get("available")), None)
        if held:
            alert = build_reversal_alert(position, held.get("analysis", {}))
            if alert:
                send_telegram(alert)

    print()
    print("=" * 70)
    print("⚠️ v3.0: analisi quantitativa, non garanzia di profitto. PAPER ONLY.")
    print("=" * 70)


if __name__ == "__main__":
    main() 
