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
DAILY_TOP5_FILE = "commodities_daily_top5.json"
PREDICTION_HORIZON_HOURS = int(os.getenv("PREDICTION_HORIZON_HOURS", "6"))
INTRADAY_ALERT_MIN_SCORE = float(os.getenv("INTRADAY_ALERT_MIN_SCORE", "70"))
PERFORMANCE_RETENTION_DAYS = int(os.getenv("PERFORMANCE_RETENTION_DAYS", "90"))
REGIME_ENABLED = os.getenv("REGIME_ENABLED", "1") == "1"
PRICE_ACTION_ENABLED = os.getenv("PRICE_ACTION_ENABLED", "1") == "1"
CANDLE_ENGINE_ENABLED = os.getenv("CANDLE_ENGINE_ENABLED", "1") == "1"
ADAPTIVE_RISK_ENABLED = os.getenv("ADAPTIVE_RISK_ENABLED", "1") == "1"
EXIT_ENGINE_ENABLED = os.getenv("EXIT_ENGINE_ENABLED", "1") == "1"
EOD_REPORT_HOUR = int(os.getenv("EOD_REPORT_HOUR", "21"))

# v3.0 — multi-horizon research and market-structure layer.
# Real/demo order execution remains OFF by default.
BOT_VERSION = "6.1"
PAPER_TRADING_ONLY = os.getenv("PAPER_TRADING_ONLY", "1") == "1"
FUTURES_STRUCTURE_ENABLED = os.getenv("FUTURES_STRUCTURE_ENABLED", "1") == "1"
POLITICAL_IMPACT_ENABLED = os.getenv("POLITICAL_IMPACT_ENABLED", "1") == "1"
EARLY_OPPORTUNITY_ENABLED = os.getenv("EARLY_OPPORTUNITY_ENABLED", "1") == "1"

# v3.0 — Early Opportunity Engine configuration.
# These defaults restore the v2.8/v2.9 research horizon settings.
EARLY_HISTORY_INTERVAL = "1day"
EARLY_HISTORY_MIN_MONTHS = int(os.getenv("EARLY_HISTORY_MIN_MONTHS", "180"))
EARLY_TARGET_DAYS = (3, 7, 14, 30)
EARLY_REFRESH_MINUTES = int(os.getenv("EARLY_REFRESH_MINUTES", "15"))
EARLY_TOP_N = int(os.getenv("EARLY_TOP_N", "3"))
EARLY_HISTORY_YEARS_TARGET = int(os.getenv("EARLY_HISTORY_YEARS_TARGET", "30"))

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


# v3.3 — 15-minute smart monitoring. The bot is scheduled externally
# (for example by GitHub Actions cron */15); it does not sleep inside a run.
MONITOR_INTERVAL_MINUTES = int(os.getenv("MONITOR_INTERVAL_MINUTES", "15"))
MONITOR_TOP_N = int(os.getenv("MONITOR_TOP_N", "3"))
MONITOR_SEND_FULL = os.getenv("MONITOR_SEND_FULL", "0") == "1"

# v3.6 — Morning / USA / Event Driven communication. Internal analysis can run often,
# but Telegram is intentionally quiet except for scheduled decision points,
# material scenario changes, and the daily statistical report.
COMMUNICATION_MODE = os.getenv("COMMUNICATION_MODE", "MORNING_USA_EVENT")
MORNING_REPORT_HOUR = int(os.getenv("MORNING_REPORT_HOUR", "8"))
MORNING_REPORT_MINUTE = int(os.getenv("MORNING_REPORT_MINUTE", "0"))
USA_REPORT_HOUR = int(os.getenv("USA_REPORT_HOUR", "14"))
USA_REPORT_MINUTE = int(os.getenv("USA_REPORT_MINUTE", "30"))
EOD_REPORT_HOUR = int(os.getenv("EOD_REPORT_HOUR", "21"))
EVENT_ALERTS_ENABLED = os.getenv("EVENT_ALERTS_ENABLED", "0") == "1"
SILENT_INTERNAL_ANALYSIS = os.getenv("SILENT_INTERNAL_ANALYSIS", "1") == "1"
MONITOR_STATE_FILE = "commodities_monitor_state.json"
MIN_ENTRY_PROBABILITY = float(os.getenv("MIN_ENTRY_PROBABILITY", "62"))
MIN_ENTRY_QUALITY = float(os.getenv("MIN_ENTRY_QUALITY", "55"))
MIN_ENTRY_CONFIDENCE = float(os.getenv("MIN_ENTRY_CONFIDENCE", "60"))
MIN_ENTRY_RR = float(os.getenv("MIN_ENTRY_RR", "2.5"))
MIN_ENTRY_RR_TP1 = float(os.getenv("MIN_ENTRY_RR_TP1", "1.5"))
MIN_ENTRY_RR_TP2 = float(os.getenv("MIN_ENTRY_RR_TP2", "2.0"))
MAX_ENTRY_STOP_ATR = float(os.getenv("MAX_ENTRY_STOP_ATR", "2.5"))

# v4.3 — Intelligence fusion + long-term forecast journal.
ELECTION_IMPACT_ENABLED = os.getenv("ELECTION_IMPACT_ENABLED", "1") == "1"
ELECTION_LOOKBACK_DAYS = int(os.getenv("ELECTION_LOOKBACK_DAYS", "21"))
ELECTION_CACHE_FILE = "commodities_election_cache.json"
ELECTION_CACHE_HOURS = int(os.getenv("ELECTION_CACHE_HOURS", "3"))
LONG_TERM_ENABLED = os.getenv("LONG_TERM_ENABLED", "1") == "1"
LONG_TERM_FORECAST_FILE = "commodities_long_term_forecasts.json"
LONG_TERM_RETENTION_DAYS = int(os.getenv("LONG_TERM_RETENTION_DAYS", "450"))
LONG_TERM_HORIZONS_DAYS = (30, 90, 180, 365)
INTRADAY_JOURNAL_ALL = os.getenv("INTRADAY_JOURNAL_ALL", "1") == "1"
INTRADAY_JOURNAL_RETENTION_DAYS = int(os.getenv("INTRADAY_JOURNAL_RETENTION_DAYS", "120"))
INTRADAY_EVAL_HOURS = int(os.getenv("INTRADAY_EVAL_HOURS", "6"))

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
    {"name": "TradingView Futures", "url": "https://www.tradingview.com/markets/futures/", "type": "web"},
    {"name": "Trading Economics Commodities", "url": "https://tradingeconomics.com/commodity", "type": "web"},
    {"name": "Trading Economics Calendar", "url": "https://tradingeconomics.com/calendar", "type": "web"},
    {"name": "Investing Commodities", "url": "https://www.investing.com/commodities/", "type": "web"},
    {"name": "Borsa Italiana ETC/ETN", "url": "https://www.borsaitaliana.it/etc-etn/etc-etn/home.htm", "type": "web"},
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
    {"name": "Unger Academy - Metodo e Sistema", "url": "https://ungeracademy.com/it/blog/metodo-o-sistema", "type": "web"},
    {"name": "Unger Academy - Backtest Strategia", "url": "https://ungeracademy.com/it/blog/backtest-strategia-trading", "type": "web"},
    {"name": "Unger Academy - Stop Loss", "url": "https://ungeracademy.com/it/blog/come-impostare-lo-stop-loss-nei-trading-system", "type": "web"},
    {"name": "Unger Academy - Trailing Stop", "url": "https://ungeracademy.com/it/blog/trailing-stop-loss-e-trading-systems-come-si-usa-e-funziona-davvero", "type": "web"},
    {"name": "GOAT Money - Orso Giordi Locatelli", "url": "https://goatmoney.it/workshop-3giorni", "type": "web"},
    {"name": "GOAT Money - Preparazione del Trade", "url": "https://www.linkedin.com/pulse/come-preparo-un-trade-dalla-lavagna-al-mercato-goat-money-xcbpf", "type": "web"},
    {"name": "Alfio Bardolla - Commodity Spread Trading", "url": "https://www.alfiobardolla.com/corsi-premium/corso-online-in-commodity-spread-trading/", "type": "web"},
    {"name": "Capital.com Commodities", "url": "https://capital.com/it-it/markets/commodities", "type": "web"},
    {"name": "Capital.com Trading Academy", "url": "https://capital.com/it-it/learn", "type": "web"},
    {"name": "IG Academy Technical Analysis", "url": "https://www.ig.com/it/scuola-di-trading/ig-academy/basi-analisi-tecnica", "type": "web"},
    {"name": "IG Support Resistance", "url": "https://www.ig.com/it/ig-academy/basi-analisi-tecnica/support-and-resistance", "type": "web"},
    {"name": "IG Breakout Fakeout", "url": "https://www.ig.com/it/ig-academy/basi-analisi-tecnica/breakouts-and-fakeouts", "type": "web"},
    {"name": "Borsa Italiana Commodity", "url": "https://www.borsaitaliana.it/notizie/sotto-la-lente/commodity.htm", "type": "web"},
])
# v5.0 — Research sources and methodology map. These sources inform concepts only;
# no source is treated as proof of profitability. Every derived rule is validated on market data.
KNOWLEDGE_SOURCES.extend([
    {"name": "Gianluca Defendi - Trading con i volumi", "url": "https://www.hoeplieditore.it/hoepli-editore/articolo/trading-con-i-volumi-gianluca-defendi/9788836020317/3261", "type": "web"},
    {"name": "Andrea Salari - Trading Intraday", "url": "https://www.andreasalari.it/", "type": "web"},
    {"name": "PoliTO - Commodities + AI", "url": "https://webthesis.biblio.polito.it/20297/", "type": "web"},
    {"name": "PoliTO - Trading System e Reti Neurali", "url": "https://webthesis.biblio.polito.it/17701/", "type": "web"},
    {"name": "PoliTO - AI e Deep Learning nel mercato finanziario", "url": "https://webthesis.biblio.polito.it/25393/", "type": "web"},
    {"name": "PoliTO - Intraday classification + pattern recognition", "url": "https://webthesis.biblio.polito.it/7654/", "type": "web"},
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
    "candlestick": ["candlestick", "candle", "doji", "hammer", "engulfing", "morning star", "evening star", "shooting star", "japanese"],
    "levels": ["level to level", "key level", "support", "resistance", "livelli chiave"],
    "entry_exit": ["entry", "entrata", "exit", "uscita", "trigger", "breakout", "retest"],
    "retracement": ["retracement", "pullback", "ritracciamento", "fibonacci"],
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

# ============================================================
# v6.1 — DATA RESCUE + INTELLIGENCE FUSION
# Multiple providers, retries, cache, timeframe reconstruction,
# regime detection, cross-market context and feedback journal.
# ============================================================
DATA_CACHE = {}
DATA_CACHE_TTL_MINUTES = int(os.getenv("DATA_CACHE_TTL_MINUTES", "60"))
DATA_INTRADAY_CACHE_TTL_MINUTES = int(os.getenv("DATA_INTRADAY_CACHE_TTL_MINUTES", "15"))
DATA_RETRY_COUNT = int(os.getenv("DATA_RETRY_COUNT", "2"))
DATA_RETRY_BACKOFF = float(os.getenv("DATA_RETRY_BACKOFF", "1.2"))
INTELLIGENCE_JOURNAL_FILE = "commodities_intelligence_journal.json"

# Provider-specific Twelve Data aliases. We never assume that a Yahoo
# futures ticker is also a valid Twelve Data symbol.
TD_SYMBOL_ALIASES = {
    "Oro": ["XAU/USD", "GOLD"], "Argento": ["XAG/USD", "SILVER"],
    "Platino": ["XPT/USD", "PLATINUM"], "Palladio": ["XPD/USD", "PALLADIUM"],
    "Petrolio WTI": ["WTI/USD", "WTI", "CRUDE OIL"],
    "Petrolio Brent": ["XBR/USD", "BRENT", "BRENT CRUDE"],
    "Gas Naturale": ["NG/USD", "NATURAL GAS"], "Benzina RBOB": ["RB/USD", "RBOB", "GASOLINE"],
    "Heating Oil": ["HO/USD", "HEATING OIL"], "Rame": ["HG1", "COPPER", "XCU/USD"],
    "Alluminio": ["ALI", "ALUMINUM"], "Nichel": ["NICKEL"], "Zinco": ["ZINC"], "Piombo": ["LEAD"],
}

# Informational sources: used as contextual/validation sources, never as a
# replacement for executable market data unless an API is explicitly available.
INTELLIGENCE_SOURCE_REGISTRY = [
    {"name":"TradingView Futures", "url":"https://www.tradingview.com/markets/futures/", "role":"market_structure"},
    {"name":"Trading Economics Commodities", "url":"https://tradingeconomics.com/commodity", "role":"macro_commodities"},
    {"name":"Trading Economics Calendar", "url":"https://tradingeconomics.com/calendar", "role":"events"},
    {"name":"Investing Commodities", "url":"https://www.investing.com/commodities/", "role":"market_news"},
    {"name":"Borsa Italiana ETC/ETN", "url":"https://www.borsaitaliana.it/etc-etn/etc-etn/home.htm", "role":"investment_reference"},
]



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


def _provider_cache_get(name, interval):
    key = (name, interval)
    item = DATA_CACHE.get(key)
    if not item:
        return None
    age_min = (datetime.now(timezone.utc) - item["saved_at"]).total_seconds() / 60.0
    ttl = DATA_INTRADAY_CACHE_TTL_MINUTES if interval not in ("1day", "1d") else DATA_CACHE_TTL_MINUTES
    if age_min <= ttl:
        return item["candles"], age_min
    return None


def _provider_cache_put(name, interval, candles, provider):
    DATA_CACHE[(name, interval)] = {
        "saved_at": datetime.now(timezone.utc),
        "candles": candles,
        "provider": provider,
    }


def _retry_call(fn, label):
    last = None
    for attempt in range(max(1, DATA_RETRY_COUNT + 1)):
        try:
            return fn()
        except Exception as exc:
            last = exc
            if attempt < DATA_RETRY_COUNT:
                import time
                time.sleep(DATA_RETRY_BACKOFF * (2 ** attempt))
    raise RuntimeError(f"{label}: {last}")


def _resample_minutes(candles, minutes):
    if not candles:
        return []
    buckets = {}
    for candle in candles:
        try:
            dt = datetime.fromisoformat(str(candle["datetime"]).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        total = dt.hour * 60 + dt.minute
        bucket_total = (total // minutes) * minutes
        key = dt.replace(hour=bucket_total // 60, minute=bucket_total % 60, second=0, microsecond=0)
        buckets.setdefault(key, []).append(candle)
    out = []
    for key in sorted(buckets):
        rows = [r for r in buckets[key] if r.get("close") is not None]
        if not rows:
            continue
        highs = [r.get("high") for r in rows if r.get("high") is not None]
        lows = [r.get("low") for r in rows if r.get("low") is not None]
        out.append({
            "datetime": key.isoformat(),
            "open": rows[0].get("open"),
            "high": max(highs) if highs else rows[0]["close"],
            "low": min(lows) if lows else rows[0]["close"],
            "close": rows[-1]["close"],
            "volume": sum((r.get("volume") or 0) for r in rows),
        })
    return out


def _td_candidates(name, symbol):
    vals = []
    if symbol:
        vals.append(str(symbol))
    vals.extend(TD_SYMBOL_ALIASES.get(name, []))
    resolved = resolve_commodity_symbols().get(name) if name else None
    if resolved:
        vals.insert(0, resolved)
    seen = set(); out = []
    for x in vals:
        if x and x.upper() not in seen:
            seen.add(x.upper()); out.append(x)
    return out


def get_data(symbol, interval="1day", outputsize=4000):
    """v6.1 DATA RESCUE: provider-specific symbols + retry + cache + timeframe reconstruction."""
    name = next((n for n, s in COMMODITIES.items() if s.upper() == str(symbol).upper()), None)
    if name is None:
        name = next((n for n, s in resolve_commodity_symbols().items() if s.upper() == str(symbol).upper()), None)
    if name is None:
        name = str(symbol)

    errors = []
    # 1) Fast cache rescue.
    cached = _provider_cache_get(name, interval)
    if cached:
        candles, age = cached
        DATA_SOURCE_STATS.setdefault(name, {})[interval] = f"CACHE ({age:.0f}m)"
        print(f"   🗃️ {name} {interval}: cache {age:.0f}m")
        return candles[-outputsize:]

    # 2) Native Yahoo.
    try:
        if interval == "4h":
            hourly = _retry_call(lambda: get_data_yahoo(name, "1h", max(outputsize * 4, 800)), f"Yahoo {name} 1h")
            candles = _resample_4h(hourly)[-outputsize:]
        else:
            candles = _retry_call(lambda: get_data_yahoo(name, interval, outputsize), f"Yahoo {name} {interval}")
        if len(candles) >= 10:
            _provider_cache_put(name, interval, candles, "YAHOO")
            DATA_SOURCE_STATS.setdefault(name, {})[interval] = "YAHOO"
            return candles
        errors.append(f"Yahoo insufficienti {len(candles)}")
    except Exception as exc:
        errors.append(f"Yahoo: {exc}")

    # 3) Twelve Data with multiple provider-specific symbols.
    for td_symbol in _td_candidates(name, symbol):
        try:
            candles = _retry_call(lambda td_symbol=td_symbol: get_data_twelvedata(td_symbol, interval, outputsize), f"Twelve Data {td_symbol} {interval}")
            if len(candles) >= 10:
                _provider_cache_put(name, interval, candles, f"TWELVE DATA:{td_symbol}")
                DATA_SOURCE_STATS.setdefault(name, {})[interval] = f"TWELVE DATA ({td_symbol})"
                print(f"   🔁 {name} {interval}: fallback Twelve Data {td_symbol} OK")
                return candles
            errors.append(f"TD {td_symbol} insufficienti {len(candles)}")
        except Exception as exc:
            errors.append(f"TD {td_symbol}: {exc}")

    # 4) Reconstruct missing intraday timeframes from a finer timeframe.
    fallbacks = {"4h": ("1h", 4, _resample_4h), "15min": ("5min", 3, lambda c: _resample_minutes(c, 15)), "5min": ("1min", 5, lambda c: _resample_minutes(c, 5))}
    if interval in fallbacks:
        finer, factor, builder = fallbacks[interval]
        try:
            fine = get_data(name if name else symbol, finer, max(outputsize * factor, 500))
            candles = builder(fine)[-outputsize:]
            if len(candles) >= 10:
                DATA_SOURCE_STATS.setdefault(name, {})[interval] = f"RECONSTRUCTED FROM {finer}"
                _provider_cache_put(name, interval, candles, f"RECONSTRUCTED:{finer}")
                print(f"   🧩 {name} {interval}: ricostruito da {finer}")
                return candles
        except Exception as exc:
            errors.append(f"reconstruction {finer}: {exc}")

    # 5) Stale cache is preferable to deleting the analysis, but mark it stale.
    stale = DATA_CACHE.get((name, interval))
    if stale and stale.get("candles"):
        age = (datetime.now(timezone.utc) - stale["saved_at"]).total_seconds() / 60.0
        DATA_SOURCE_STATS.setdefault(name, {})[interval] = f"STALE CACHE ({age:.0f}m)"
        print(f"   ⚠️ {name} {interval}: uso cache vecchia {age:.0f}m")
        return stale["candles"][-outputsize:]

    raise RuntimeError(f"DATA RESCUE FALLITO {name} {interval}: " + " | ".join(errors[-6:]))


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
        "Oro": "gold White House tariffs Fed geopolitics sanctions war",
        "Argento": "silver White House tariffs industrial demand geopolitics",
        "Petrolio WTI": "oil WTI OPEC White House sanctions war tariffs",
        "Petrolio Brent": "Brent oil OPEC White House sanctions war tariffs",
        "Gas Naturale": "natural gas geopolitics LNG sanctions Europe White House",
        "Rame": "copper White House tariffs China geopolitics mining",
        "Grano": "wheat grain White House tariffs Russia Ukraine geopolitics",
        "Mais": "corn maize White House tariffs agriculture geopolitics",
        "Caffè": "coffee Brazil tariffs White House trade weather geopolitics",
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

    # v2.0 knowledge layer: merge source metadata with quantitative checks.
    # Previously the second assignment erased sources/usable/profile, making
    # Telegram report "0 fonti" even when the refresh had usable sources.
    source_knowledge = dict(trading_knowledge or {})
    quantitative_knowledge = trading_knowledge_engine(result)
    source_knowledge.update(quantitative_knowledge)
    result["trading_knowledge"] = source_knowledge

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


def market_regime_engine(analysis):
    """Classify the current market regime using only data already in analysis.

    This is a descriptive regime classifier, not a predictive guarantee.
    It deliberately stays simple so each regime can later be validated
    independently in the Daily Performance Engine.
    """
    if not REGIME_ENABLED:
        return {"state": "N/D", "score": 0.0, "strategy_bias": "N/D", "reason": "DISATTIVATO"}
    tfs = analysis.get("timeframes", {}) or {}
    rev = analysis.get("reversal", {}) or {}
    risk = analysis.get("risk", {}) or {}
    if risk.get("mode") == "SHOCK":
        return {"state":"SHOCK", "score":100.0, "strategy_bias":"BLOCK", "reason":"SHOCK GLOBALE"}
    if rev.get("stage") == "CONFIRMED":
        return {"state":"REVERSAL", "score":90.0, "strategy_bias":"WAIT/REVERSAL", "reason":"INVERSIONE CONFERMATA"}
    dirs=[tfs.get(tf,{}).get("direction") for tf in ("4H","1H","15m") if tfs.get(tf,{}).get("direction") in ("LONG","SHORT")]
    long_n=dirs.count("LONG"); short_n=dirs.count("SHORT")
    mq=safe_float(risk.get("market_quality"),50) or 50
    atr=safe_float(analysis.get("atr"),0) or 0
    price=safe_float(analysis.get("price"),0) or 0
    vol_pct=(atr/price*100) if atr>0 and price>0 else 0.0
    if len(dirs)>=2 and long_n==len(dirs) and len(dirs)>=2:
        state="TREND UP"; bias="BREAKOUT/PULLBACK LONG"; score=70+10*long_n
    elif len(dirs)>=2 and short_n==len(dirs) and len(dirs)>=2:
        state="TREND DOWN"; bias="BREAKOUT/PULLBACK SHORT"; score=70+10*short_n
    elif mq < 45 or vol_pct >= 4.0:
        state="HIGH VOLATILITY"; bias="CONFIRMATION FORTE"; score=65
    elif len(dirs)>=2 and long_n==short_n:
        state="RANGE"; bias="MEAN REVERSION / LEVELS"; score=60
    else:
        state="TRANSITION"; bias="SELECTIVE"; score=55
    return {"state":state,"score":round(clamp(score,0,100),1),"strategy_bias":bias,
            "reason":f"MTF {long_n}L/{short_n}S | MQ {mq:.0f} | ATR% {vol_pct:.2f}"}



# ============================================================
# v3.5 PRICE ACTION / LEVEL / RETRACEMENT / BREAKOUT ENGINE
# ============================================================

def _directional_candle_score(candles, direction):
    if direction not in ("LONG", "SHORT") or not candles or len(candles) < 3:
        return {"score": 0.0, "patterns": [], "label": "N/D"}
    ce = candle_engine(candles, direction)
    wp = world_pattern_engine(candles, direction)
    # Candlestick score is deliberately bounded: it confirms price action,
    # but never creates a trade by itself.
    raw = safe_float(ce.get("score"), 0) or 0
    world = safe_float(wp.get("score"), 0) or 0
    score = clamp(50 + raw * 10 + world * 8, 0, 100)
    return {
        "score": round(score, 1),
        "patterns": list(dict.fromkeys((ce.get("patterns") or []) + (wp.get("patterns") or [])))[:8],
        "label": ce.get("label") if ce.get("label") not in (None, "NESSUN PATTERN FORTE") else (" + ".join((wp.get("patterns") or [])[:2]) or "NESSUN PATTERN FORTE"),
        "raw_score": round(raw, 2),
        "world_score": round(world, 2),
    }


def retracement_engine(candles, direction):
    """Classifies pullback depth without assuming that every pullback is a reversal."""
    if direction not in ("LONG", "SHORT") or not candles or len(candles) < 30:
        return {"state": "N/D", "score": 50.0, "depth": None, "level": None, "reason": "DATI INSUFFICIENTI"}
    closes = [safe_float(c.get("close")) for c in candles if safe_float(c.get("close")) is not None]
    price = closes[-1]
    e9, e21, e50 = ema(closes, 9), ema(closes, 21), ema(closes, 50)
    e9 = e9 if e9 is not None else price
    e21 = e21 if e21 is not None else price
    e50 = e50 if e50 is not None else e21
    a = atr(candles, 14) or price * 0.01
    window = candles[-40:]
    hi = max((safe_float(c.get("high")) for c in window if safe_float(c.get("high")) is not None), default=price)
    lo = min((safe_float(c.get("low")) for c in window if safe_float(c.get("low")) is not None), default=price)
    span = max(hi-lo, a)
    if direction == "LONG":
        depth = (hi-price)/span
        aligned = e9 >= e21 >= e50
        zone = e21
        # Healthy pullback: price returns toward EMA21 but remains above the
        # broader structure. Deep penetration becomes a warning, not an auto-block.
        near = abs(price-e21) <= 0.75*a
        deep = price < e21 - 1.25*a
        state = "PULLBACK FORTE" if near and aligned else "PULLBACK PROFONDO" if deep else "PULLBACK LEGGERO" if depth < .35 else "NESSUN PULLBACK"
        score = 78 if near and aligned else 62 if aligned and not deep else 45 if deep else 52
    else:
        depth = (price-lo)/span
        aligned = e9 <= e21 <= e50
        zone = e21
        near = abs(price-e21) <= 0.75*a
        deep = price > e21 + 1.25*a
        state = "PULLBACK FORTE" if near and aligned else "PULLBACK PROFONDO" if deep else "PULLBACK LEGGERO" if depth < .35 else "NESSUN PULLBACK"
        score = 78 if near and aligned else 62 if aligned and not deep else 45 if deep else 52
    return {"state": state, "score": float(score), "depth": round(depth, 3), "level": round(zone, 6),
            "ema9": round(e9, 6), "ema21": round(e21, 6), "ema50": round(e50, 6),
            "atr": round(a, 6), "reason": "EMA21 + struttura swing"}


def breakout_retest_engine(candles, direction):
    """Detects a recent breakout and whether price is successfully retesting it."""
    if direction not in ("LONG", "SHORT") or not candles or len(candles) < 30:
        return {"state": "N/D", "score": 50.0, "breakout": False, "retest": False, "level": None}
    rows = candles[-35:]
    highs = [safe_float(c.get("high")) for c in rows]
    lows = [safe_float(c.get("low")) for c in rows]
    closes = [safe_float(c.get("close")) for c in rows]
    a = atr(rows, 14) or closes[-1]*0.01
    look = 20
    level = max(x for x in highs[-look-1:-1] if x is not None) if direction == "LONG" else min(x for x in lows[-look-1:-1] if x is not None)
    recent = rows[-5:]
    breakout = False
    retest = False
    for c in recent:
        cm = _candle_metrics(c)
        if not cm: continue
        if direction == "LONG" and cm["close"] > level and cm["bull"] and cm["body"] >= cm["range"]*0.35:
            breakout = True
        if direction == "SHORT" and cm["close"] < level and cm["bear"] and cm["body"] >= cm["range"]*0.35:
            breakout = True
    if breakout:
        last = _candle_metrics(rows[-1])
        if last:
            if direction == "LONG":
                retest = last["low"] <= level + 0.45*a and last["close"] >= level
            else:
                retest = last["high"] >= level - 0.45*a and last["close"] <= level
    state = "BREAKOUT + RETEST" if breakout and retest else "BREAKOUT" if breakout else "NESSUN BREAKOUT"
    score = 88 if breakout and retest else 76 if breakout else 50
    return {"state": state, "score": float(score), "breakout": breakout, "retest": retest,
            "level": round(level, 6), "atr": round(a, 6)}


def price_action_context_engine(analysis):
    """Combines candles, levels, retracement and breakout/retest into one bounded confirmation layer."""
    if not PRICE_ACTION_ENABLED:
        return {"enabled": False, "score": 50.0, "direction": "NONE", "patterns": []}
    d = analysis.get("setup_direction") or analysis.get("model_signal")
    if d not in ("LONG", "SHORT"):
        return {"enabled": True, "score": 50.0, "direction": "NONE", "patterns": []}
    pts = analysis.get("pattern_timeframes", {}) or {}
    tf_scores=[]; patterns=[]
    for tf in ("4H","1H","15m","5m","1m"):
        rows=pts.get(tf)
        if rows and len(rows)>=5:
            c=_directional_candle_score(rows,d)
            tf_scores.append((tf,c["score"]))
            patterns.extend([f"{tf}:{x}" for x in c["patterns"][:3]])
    base_candle=mean([x[1] for x in tf_scores]) if tf_scores else 50.0
    rows15=pts.get("15m") or pts.get("1H") or []
    ret=retracement_engine(rows15,d) if rows15 else {"score":50,"state":"N/D"}
    br=breakout_retest_engine(rows15,d) if rows15 else {"score":50,"state":"N/D"}
    l2l=analysis.get("level_to_level",{}) or {}
    l2l_score=safe_float(l2l.get("score"),50) or 50
    # Location is more important than the candle name: a candle at a key level
    # gets more weight than the same candle in the middle of a range.
    location = clamp(l2l_score, 0, 100)
    combo = clamp(base_candle*0.30 + ret.get("score",50)*0.20 + br.get("score",50)*0.25 + location*0.25,0,100)
    return {"enabled": True, "score": round(combo,1), "direction": d,
            "candle_score": round(base_candle,1), "retracement": ret,
            "breakout_retest": br, "patterns": patterns[:10],
            "level_score": round(location,1)}


def adaptive_risk_levels(analysis, candles, direction):
    """Adaptive SL/TP: structure first, ATR second, percentage profile as fallback."""
    if not ADAPTIVE_RISK_ENABLED or direction not in ("LONG","SHORT") or not candles:
        return {"available": False}
    price=safe_float(analysis.get("price"))
    if not price: return {"available": False}
    a=atr(candles,14) or price*0.01
    l2l=analysis.get("level_to_level",{}) or {}
    support=safe_float(l2l.get("support")); resistance=safe_float(l2l.get("resistance"))
    lows=[safe_float(x.get("low")) for x in candles[-30:] if safe_float(x.get("low")) is not None]
    highs=[safe_float(x.get("high")) for x in candles[-30:] if safe_float(x.get("high")) is not None]
    swing_low=min(lows) if lows else None; swing_high=max(highs) if highs else None
    profile=LEVEL_PROFILES.get(analysis.get("commodity_name") or "", {})
    sl_pct=profile.get("sl_pct", min(STOP_ATR*a/max(price,1e-9),0.025))
    tp1_pct=profile.get("tp1_pct", min(TP1_ATR*a/max(price,1e-9),0.035))
    tp2_pct=profile.get("tp2_pct", min(TP2_ATR*a/max(price,1e-9),0.055))
    tp3_pct=profile.get("tp3_pct", min(TP3_ATR*a/max(price,1e-9),0.08))
    if direction=="LONG":
        candidates=[x for x in (support,swing_low,price-sl_pct*price) if x is not None and x < price]
        stop=max(candidates) if candidates else price-sl_pct*price
        stop=min(stop, price-0.55*a)
        risk=max(price-stop,0.35*a)
        tps=[price+max(tp1_pct*price,1.35*risk), price+max(tp2_pct*price,2.0*risk), price+max(tp3_pct*price,2.7*risk)]
    else:
        candidates=[x for x in (resistance,swing_high,price+sl_pct*price) if x is not None and x > price]
        stop=min(candidates) if candidates else price+sl_pct*price
        stop=max(stop, price+0.55*a)
        risk=max(stop-price,0.35*a)
        tps=[price-max(tp1_pct*price,1.35*risk), price-max(tp2_pct*price,2.0*risk), price-max(tp3_pct*price,2.7*risk)]
    return {"available": True, "atr": round(a,6), "stop": _price_round(stop), "tp1": _price_round(tps[0]), "tp2": _price_round(tps[1]), "tp3": _price_round(tps[2]),
            "risk_distance": round(risk,6), "method": "STRUCTURA + ATR + PROFILE FALLBACK"}


def exit_engine(position, analysis, current_price):
    """Early exit logic based on structure/reversal/price action; targets and SL remain primary."""
    if not EXIT_ENGINE_ENABLED or not position:
        return {"action":"HOLD","score":0.0,"reason":"DISATTIVATO"}
    d=position.get("direction")
    opposite="SHORT" if d=="LONG" else "LONG"
    rev=analysis.get("reversal",{}) or {}
    if rev.get("stage")=="CONFIRMED" and (analysis.get("signal")==opposite or analysis.get("setup_direction")==opposite):
        return {"action":"EXIT","score":100.0,"reason":"INVERSIONE CONFERMATA"}
    pa=analysis.get("price_action",{}) or {}
    patterns=[]
    for p in pa.get("patterns",[]): patterns.append(str(p).upper())
    adverse_names=("BEARISH ENGULFING","SHOOTING STAR","EVENING STAR","SUPPORT BREAKDOWN") if d=="LONG" else ("BULLISH ENGULFING","HAMMER","MORNING STAR","RESISTANCE BREAKOUT")
    adverse=sum(1 for p in patterns if any(x in p for x in adverse_names))
    tfs=analysis.get("timeframes",{}) or {}
    structural_opposite=sum(1 for tf in ("4H","1H","15m") if tfs.get(tf,{}).get("direction")==opposite)
    score=adverse*28 + structural_opposite*18
    if pa.get("breakout_retest",{}).get("state") in ("BREAKOUT", "BREAKOUT + RETEST") and d==opposite:
        score+=20
    score=clamp(score,0,100)
    if score>=70:
        return {"action":"EXIT","score":round(score,1),"reason":"PRICE ACTION CONTRARIA + STRUTTURA"}
    return {"action":"HOLD","score":round(score,1),"reason":"NESSUN SEGNALE DI USCITA FORTE"}


def smart_entry_engine(analysis):
    """v3.3: permissive intraday decision engine.

    Core signal = trend + momentum + price/structure. Secondary filters add
    or subtract points instead of becoming hard blockers. Only confirmed
    reversal and material shock remain safety blocks. This prevents a valid
    LONG/SHORT from disappearing simply because one fast timeframe disagrees.
    """
    d = analysis.get("setup_direction") or analysis.get("model_signal")
    if d not in ("LONG", "SHORT"):
        analysis.update({"entry_state":"NO_SETUP", "action_label":"NON ENTRARE",
                         "signal":"WAIT", "strong_confirmation":False,
                         "intraday_score":0.0})
        return analysis

    tfs = analysis.get("timeframes", {}) or {}
    structural = [tfs.get(tf, {}).get("direction", "NONE") for tf in ("4H", "1H", "15m")]
    fast = [tfs.get(tf, {}).get("direction", "NONE") for tf in ("5m", "1m")]
    structural_same = sum(x == d for x in structural)
    fast_same = sum(x == d for x in fast)
    fast_opp = sum(x == ("SHORT" if d == "LONG" else "LONG") for x in fast)
    rev = analysis.get("reversal", {}) or {}
    risk = analysis.get("risk", {}) or {}
    score = safe_float(analysis.get("score"), 0) or 0
    quality = safe_float(analysis.get("quality"), 0) or 0
    conf = safe_float(analysis.get("confidence"), 0) or 0
    entry_q = safe_float(analysis.get("entry_quality"), 0) or 0
    rb = safe_float(analysis.get("risk_benefit", {}).get("score"), 0) or 0
    prob = safe_float(analysis.get("long_probability" if d == "LONG" else "short_probability"), 0) or 0
    prob *= 100 if prob <= 1 else 1
    market_q = safe_float(risk.get("market_quality"), 50) or 50
    trigger = entry_trigger_engine(analysis)
    l2l = analysis.get("level_to_level", {}) or {}
    l2l_score = safe_float(l2l.get("score"), 50) or 50
    price_action = price_action_context_engine(analysis)
    pa_score = safe_float(price_action.get("score"), 50) or 50
    ensemble_ok = bool(analysis.get("ensemble_gate", True))
    source_status = str(analysis.get("source_check", {}).get("status", ""))
    source_discrepancy = "DISCREPANZA" in source_status.upper()

    # Secondary filters are scoring components, not hard gates.
    intraday = score
    intraday += clamp((quality - 50) * 0.12, -6, 6)
    intraday += clamp((conf - 55) * 0.10, -5, 5)
    intraday += clamp((prob - 55) * 0.16, -7, 7)
    intraday += 4 if structural_same >= 2 else 2 if structural_same == 1 else -2
    intraday += 4 if fast_same >= 2 else 2 if fast_same == 1 else 0
    intraday -= min(6, fast_opp * 3)
    intraday += clamp((l2l_score - 50) * 0.10, -5, 5)
    intraday += clamp((pa_score - 50) * 0.16, -8, 8)
    intraday += 4 if trigger.get("confirmed") else 2 if trigger.get("kind") not in (None, "NONE") else 0
    intraday += 2 if ensemble_ok else -2
    intraday += clamp((market_q - 55) * 0.08, -4, 4)
    if source_discrepancy:
        intraday -= 4
    if risk.get("mode") == "ALERT":
        intraday -= 3
    intraday = clamp(intraday, 0, 100)

    blockers=[]
    warnings=[]
    if risk.get("mode") == "SHOCK": blockers.append("SHOCK")
    if rev.get("stage") == "CONFIRMED": blockers.append("INVERSIONE CONFERMATA")
    if fast_opp > 0: blockers.append("CONFLITTO RAPIDO")
    if structural_same < 2: blockers.append("MTF PARZIALE")
    if source_discrepancy: blockers.append("DISCREPANZA FONTI")
    if not l2l.get("gate", True): warnings.append("L2L CONTRARIO")

    # v3.8: strict confluence gate. Telegram may say COMPRA/VENDI ORA
    # only when ALL critical conditions are satisfied.
    entry_price = safe_float(analysis.get("entry"), safe_float(analysis.get("price"), 0)) or 0
    stop_price = safe_float(analysis.get("stop"), 0) or 0
    tp1_price = safe_float(analysis.get("tp1"), 0) or 0
    tp2_price = safe_float(analysis.get("tp2"), 0) or 0
    tp3_price = safe_float(analysis.get("tp3"), 0) or 0
    risk_distance = abs(entry_price-stop_price) if entry_price and stop_price else 0
    rr1 = abs(tp1_price-entry_price) / risk_distance if risk_distance else 0
    rr2 = abs(tp2_price-entry_price) / risk_distance if risk_distance else 0
    rr3 = abs(tp3_price-entry_price) / risk_distance if risk_distance else 0
    atr_value = safe_float(analysis.get("atr"), 0) or 0
    stop_atr = risk_distance / atr_value if atr_value > 0 else 999.0
    rr1_ok = rr1 >= MIN_ENTRY_RR_TP1
    rr2_ok = rr2 >= MIN_ENTRY_RR_TP2
    rr3_ok = rr3 >= MIN_ENTRY_RR
    stop_ok = stop_atr <= MAX_ENTRY_STOP_ATR
    l2l_ok = bool(l2l.get("gate", False))
    structural_ok = structural_same >= 2
    fast_ok = fast_opp == 0
    prob_ok = prob >= MIN_ENTRY_PROBABILITY
    quality_ok = quality >= MIN_ENTRY_QUALITY
    confidence_ok = conf >= MIN_ENTRY_CONFIDENCE
    trigger_ok = bool(trigger.get("confirmed"))
    safety_block = (risk.get("mode") in ("SHOCK", "ALERT") or
                    rev.get("stage") == "CONFIRMED")
    confluence_ok = (structural_ok and fast_ok and l2l_ok and trigger_ok and
                     rr1_ok and rr2_ok and rr3_ok and stop_ok and
                     prob_ok and quality_ok and confidence_ok and not safety_block)
    if safety_block:
        state, action, signal = "SAFETY_BLOCK", "NON ENTRARE", "WAIT"
    elif intraday >= 80 and confluence_ok:
        state, action, signal = "ENTRY_CONFIRMED", ("COMPRA ORA" if d == "LONG" else "VENDI ORA"), d
    elif intraday >= 65 and not safety_block:
        state, action, signal = "ACTIVE_SETUP", ("LONG — ASPETTARE CONFERMA" if d == "LONG" else "SHORT — ASPETTARE CONFERMA"), "WAIT"
    else:
        state, action, signal = "WATCH", "ATTENDERE", "WAIT"
    if not confluence_ok:
        missing=[]
        if not structural_ok: missing.append("MTF")
        if not fast_ok: missing.append("5m/1m")
        if not l2l_ok: missing.append("L2L")
        if not trigger_ok: missing.append("TRIGGER")
        if not rr1_ok: missing.append("RR TP1")
        if not rr2_ok: missing.append("RR TP2")
        if not rr3_ok: missing.append("RR TP3")
        if not stop_ok: missing.append("STOP/ATR")
        if not prob_ok: missing.append("PROB")
        if not quality_ok: missing.append("QUALITÀ")
        if not confidence_ok: missing.append("CONFIDENZA")
        if missing: blockers.append("CONFLUENZA INCOMPLETA: " + ",".join(missing))

    analysis["price_action"] = price_action
    analysis["entry_trigger"] = trigger
    analysis["entry_state"] = state
    analysis["entry_blockers"] = blockers[:6]
    analysis["entry_warnings"] = warnings[:6]
    analysis["action_label"] = action
    analysis["signal"] = signal
    analysis["strong_confirmation"] = bool(state == "ENTRY_CONFIRMED")
    analysis["entry_probability"] = round(prob, 2)
    analysis["intraday_score"] = round(intraday, 1)
    analysis["intraday_core"] = {
        "trend": d,
        "structural_same": structural_same,
        "fast_same": fast_same,
        "fast_opposite": fast_opp,
        "trigger": trigger.get("kind", "NONE"),
        "l2l_score": round(l2l_score, 1),
        "price_action_score": round(pa_score, 1),
        "rr_tp1": round(rr1, 2),
        "rr_tp2": round(rr2, 2),
        "rr_tp3": round(rr3, 2),
        "stop_atr": round(stop_atr, 2),
        "confluence_ok": confluence_ok,
    }
    return analysis

# ============================================================
# v4.3 LONG-TERM FORECAST ENGINE + JOURNAL
# ============================================================
def _daily_momentum(rows, bars):
    closes=[safe_float(x.get("close")) for x in rows or []]; closes=[x for x in closes if x is not None]
    if len(closes)<=bars or closes[-bars-1]==0: return 0.0
    return closes[-1]/closes[-bars-1]-1.0

def long_term_forecast(name, candles, analysis):
    """Create frozen 30/90/180/365-day directional forecasts from current data.
    This is a research forecast, not a promise or price target.
    """
    if not LONG_TERM_ENABLED or len(candles or [])<120:
        return {"enabled":False,"status":"INSUFFICIENT_DATA"}
    closes=[safe_float(x.get("close")) for x in candles if safe_float(x.get("close")) is not None]
    if len(closes)<120: return {"enabled":False,"status":"INSUFFICIENT_DATA"}
    m20=_daily_momentum(candles,20); m60=_daily_momentum(candles,60); m120=_daily_momentum(candles,120)
    base=0.50
    model_dir=analysis.get("setup_direction") or analysis.get("model_signal")
    model_prob=safe_float(analysis.get("long_probability"),0.5) or 0.5
    if model_dir=="LONG": base += (model_prob-0.5)*0.22
    elif model_dir=="SHORT": base -= (0.5-(1-model_prob))*0.22
    trend=0.40*math.tanh(m20*18)+0.35*math.tanh(m60*10)+0.25*math.tanh(m120*7)
    structural=0.0
    reg=(analysis.get("market_regime",{}) or {}).get("state","")
    if "UP" in reg.upper(): structural=0.08
    elif "DOWN" in reg.upper(): structural=-0.08
    fs=(analysis.get("futures_structure",{}) or {}).get("score",0) or 0
    cyc=(analysis.get("cyclical",{}) or {}).get("score",0) or 0
    political=(analysis.get("political",{}) or {}).get("score",0) or 0
    election=(analysis.get("elections",{}) or {}).get("score",0) or 0
    weather=(analysis.get("weather",{}) or {}).get("score",0) or 0
    # Context is capped so long-term direction cannot be hijacked by one news feed.
    context=clamp((fs*0.012)+(cyc*0.06)+(political*0.012)+(election*0.006)+(weather*0.003),-0.15,0.15)
    signal=clamp((base-0.5)*0.55 + trend*0.30 + structural*0.10 + context*0.05,-0.45,0.45)
    out={}
    for d in LONG_TERM_HORIZONS_DAYS:
        horizon_weight=1.0 if d<=30 else 0.85 if d<=90 else 0.70 if d<=180 else 0.55
        p_long=clamp(0.50+signal*horizon_weight,0.05,0.95)
        p_short=1-p_long
        direction="LONG" if p_long>=0.56 else "SHORT" if p_short>=0.56 else "NEUTRALE"
        confidence=clamp(abs(p_long-0.5)*200,0,100)
        out[str(d)]={"direction":direction,"long_probability":round(p_long*100,1),"short_probability":round(p_short*100,1),"confidence":round(confidence,1)}
    return {"enabled":True,"status":"OK","price":safe_float(analysis.get("price")),"generated_at":datetime.now(timezone.utc).isoformat(),"horizons":out,
            "drivers":{"momentum20":round(m20*100,2),"momentum60":round(m60*100,2),"momentum120":round(m120*100,2),"regime":reg,"futures":fs,"cyclical":cyc,"political":political,"elections":election,"weather":weather}}

def record_long_term_forecasts(results):
    if not LONG_TERM_ENABLED: return 0
    log=_json_load(LONG_TERM_FORECAST_FILE,[])
    if not isinstance(log,list): log=[]
    now=datetime.now(timezone.utc); today=now.date().isoformat(); new=0
    cutoff=now-timedelta(days=LONG_TERM_RETENTION_DAYS)
    for item in results:
        if not item.get("available"): continue
        a=item.get("analysis",{}); f=a.get("long_term") or long_term_forecast(item["name"],item.get("candles",[]),a)
        a["long_term"]=f
        if not f.get("enabled"): continue
        # Exactly one frozen forecast per commodity/day.
        if any(x.get("name")==item["name"] and x.get("forecast_date")==today for x in log): continue
        log.append({"id":f'{item["name"]}|{today}',"name":item["name"],"symbol":item["symbol"],"forecast_date":today,
                    "created_at":now.isoformat(),"price":f.get("price"),"horizons":f.get("horizons",{}),"drivers":f.get("drivers",{}),"status":"OPEN"})
        new+=1
    kept=[]
    for x in log:
        try:
            dt=datetime.fromisoformat(str(x.get("created_at")).replace("Z","+00:00"))
            if dt>=cutoff: kept.append(x)
        except Exception: kept.append(x)
    _json_save(LONG_TERM_FORECAST_FILE,kept)
    return new

def _evaluate_long_term_entry(rec, horizon_days):
    created=datetime.fromisoformat(str(rec["created_at"]).replace("Z","+00:00")); target=created+timedelta(days=horizon_days)
    if datetime.now(timezone.utc)<target: return None
    try: rows=get_data(rec["symbol"],"1day",500)
    except Exception: return None
    if not rows: return None
    best=None
    for r in rows:
        try: dt=datetime.fromisoformat(str(r["datetime"]).replace("Z","+00:00"))
        except Exception: continue
        if dt.date()>=target.date(): best=r; break
    if best is None: return None
    p=safe_float(rec.get("price")); c=safe_float(best.get("close"))
    if p is None or c is None: return None
    h=rec.get("horizons",{}).get(str(horizon_days),{}); d=h.get("direction")
    move=(c/p-1)*100
    if d=="LONG": verdict="CORRETTA" if move>0 else "ERRATA"
    elif d=="SHORT": verdict="CORRETTA" if move<0 else "ERRATA"
    else: verdict="NEUTRALE"
    return {"verdict":verdict,"target_price":c,"move_pct":round(move,3),"evaluated_at":datetime.now(timezone.utc).isoformat()}

def evaluate_long_term_forecasts():
    log=_json_load(LONG_TERM_FORECAST_FILE,[])
    if not isinstance(log,list): return log,False
    changed=False
    for rec in log:
        ev=rec.setdefault("evaluations",{})
        for d in LONG_TERM_HORIZONS_DAYS:
            k=str(d)
            if k in ev: continue
            result=_evaluate_long_term_entry(rec,d)
            if result: ev[k]=result; changed=True
    if changed: _json_save(LONG_TERM_FORECAST_FILE,log)
    return log,changed

def long_term_report():
    log,_=evaluate_long_term_forecasts()
    if not log: return "🧠 LONG-TERM FORECAST — nessun dato storico disponibile."
    now=datetime.now(ZoneInfo("Europe/Rome")); lines=["🧠 LONG-TERM FORECAST REPORT",f"📅 {now.strftime('%d/%m/%Y')}","━━━━━━━━━━━━━━━━━━━━"]
    for d in LONG_TERM_HORIZONS_DAYS:
        rows=[r for r in log if r.get("evaluations",{}).get(str(d)) and r.get("horizons",{}).get(str(d),{}).get("direction") in ("LONG","SHORT")]
        c=sum(r["evaluations"][str(d)].get("verdict")=="CORRETTA" for r in rows); w=sum(r["evaluations"][str(d)].get("verdict")=="ERRATA" for r in rows); acc=c/(c+w)*100 if c+w else 0
        pending=sum(1 for r in log if str(d) not in r.get("evaluations",{}))
        lines.append(f"⏳ {d} GIORNI: {c} ✅ | {w} ❌ | Accuracy {acc:.1f}% | Aperte {pending}")
    # Current directional outlook for the most recent forecast of each commodity.
    latest={}
    for r in log:
        latest[r.get("name")]=r
    lines += ["","🔮 OUTLOOK ATTUALE"]
    for name,r in sorted(latest.items()):
        h=r.get("horizons",{}); parts=[]
        for d in LONG_TERM_HORIZONS_DAYS:
            x=h.get(str(d),{}); parts.append(f"{d}g {x.get('direction','N/D')} {safe_float(x.get('long_probability'),0) or 0:.0f}%L")
        lines.append(f"• {name}: " + " | ".join(parts))
    lines.append("🔒 Previsioni storiche congelate: non vengono riscritte.")
    return "\n".join(lines)

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
    """Journal every 15-minute commodity reading, while scoring only directional forecasts.
    WAIT/NEUTRAL are retained but are not counted as LONG/SHORT wins/losses.
    """
    log=_json_load(PREDICTION_LOG_FILE,[])
    if not isinstance(log,list): log=[]
    now=datetime.now(timezone.utc); cutoff=now-timedelta(days=INTRADAY_JOURNAL_RETENTION_DAYS); new=0
    cycle=now.replace(minute=(now.minute//15)*15,second=0,microsecond=0).isoformat()
    for item in results:
        if not item.get("available"): continue
        a=item.get("analysis",{}) or {}
        direction=a.get("setup_direction") or a.get("model_signal")
        if direction not in ("LONG","SHORT"): direction="NEUTRALE"
        price=safe_float(a.get("price"));
        if price is None: continue
        rec={"id":f'{item["name"]}|{cycle}',"created_at":now.isoformat(),"cycle":cycle,"name":item["name"],"symbol":item["symbol"],
             "direction":direction,"operational_signal":a.get("signal","WAIT"),"action":a.get("action_label",""),"price":price,
             "entry":safe_float(a.get("entry")),"stop":safe_float(a.get("stop")),"tp1":safe_float(a.get("tp1")),"tp2":safe_float(a.get("tp2")),"tp3":safe_float(a.get("tp3")),
             "score":safe_float(a.get("score"),0) or 0,"probability":safe_float(a.get("entry_probability"),0) or safe_float(a.get("long_probability"),0.5)*100,
             "confidence":safe_float(a.get("confidence"),0) or 0,"quality":safe_float(a.get("quality"),0) or 0,
             "regime":(a.get("market_regime",{}) or {}).get("state","N/D"),"status":"PENDING" if direction in ("LONG","SHORT") else "NEUTRALE"}
        if not any(x.get("id")==rec["id"] for x in log): log.append(rec); new+=1
    log=[x for x in log if x.get("created_at","")>=cutoff.isoformat()]
    _json_save(PREDICTION_LOG_FILE,log)
    return new,log

def _future_candles_for_prediction(prediction):
    """Return the forecast window using 15m candles for more precise TP/SL validation."""
    created=datetime.fromisoformat(prediction["created_at"].replace("Z","+00:00"))
    if datetime.now(timezone.utc) < created+timedelta(hours=INTRADAY_EVAL_HOURS): return []
    end=created+timedelta(hours=INTRADAY_EVAL_HOURS)
    for interval, size in (("15min", 2000), ("1h", 1200)):
        try:
            rows=get_data(prediction["symbol"], interval, size)
            out=[]
            for row in rows:
                try: dt=datetime.fromisoformat(str(row["datetime"]).replace("Z","+00:00"))
                except Exception: continue
                if created < dt <= end: out.append(row)
            if out: return out
        except Exception:
            continue
    return []

def evaluate_prediction(prediction,future):
    """Validate direction plus each frozen TP/SL level from the original forecast."""
    if not future: return None
    p=safe_float(prediction.get("price")); direction=prediction.get("direction","WAIT")
    if p is None or direction not in ("LONG","SHORT"): return None
    entry=safe_float(prediction.get("entry")) or p
    sl=safe_float(prediction.get("stop")); tps=[safe_float(prediction.get(k)) for k in ("tp1","tp2","tp3")]
    close_end=safe_float(future[-1].get("close"))
    if close_end is None: return None
    hits={"tp1":False,"tp2":False,"tp3":False,"sl":False}
    first_event="NONE"; ambiguous=False
    for c in future:
        hi,lo=safe_float(c.get("high")),safe_float(c.get("low"))
        if hi is None or lo is None: continue
        candle_hits=[]
        if tps[0] is not None and (hi>=tps[0] if direction=="LONG" else lo<=tps[0]): candle_hits.append("TP1")
        if tps[1] is not None and (hi>=tps[1] if direction=="LONG" else lo<=tps[1]): candle_hits.append("TP2")
        if tps[2] is not None and (hi>=tps[2] if direction=="LONG" else lo<=tps[2]): candle_hits.append("TP3")
        if sl is not None and (lo<=sl if direction=="LONG" else hi>=sl): candle_hits.append("SL")
        for h in candle_hits: hits[h.lower()]=True
        if first_event=="NONE" and candle_hits: first_event=candle_hits[0]
        if "SL" in candle_hits and any(x.startswith("TP") for x in candle_hits): ambiguous=True
    close_correct=close_end>entry if direction=="LONG" else close_end<entry
    direction_verdict="AMBIGUA" if ambiguous else ("CORRETTA" if close_correct else "ERRATA")
    tp_verdict="TP3" if hits["tp3"] else "TP2" if hits["tp2"] else "TP1" if hits["tp1"] else "NESSUN TP"
    return {"verdict":direction_verdict,"direction_correct":close_correct,"first_hit":first_event,
            "tp1_hit":hits["tp1"],"tp2_hit":hits["tp2"],"tp3_hit":hits["tp3"],"sl_hit":hits["sl"],
            "tp_verdict":tp_verdict,"ambiguous_levels":ambiguous,"close_end":close_end,
            "move_pct":(close_end/entry-1)*100 if entry else 0,"evaluated_at":datetime.now(timezone.utc).isoformat()}

def save_daily_top5_snapshot(ranked, prediction_log):
    """Freeze the first top-5 ranking after the configured morning report time."""
    try:
        now=datetime.now(ZoneInfo("Europe/Rome")); today=now.date().isoformat()
        state=_json_load(DAILY_TOP5_FILE,{}) or {}
        if state.get("date")==today: return False
        minutes=now.hour*60+now.minute; morning=MORNING_REPORT_HOUR*60+MORNING_REPORT_MINUTE; usa=USA_REPORT_HOUR*60+USA_REPORT_MINUTE
        if minutes < morning or minutes >= usa: return False
        available=[x for x in ranked if x.get("available")][:5]
        if len(available)<5: return False
        snapshot=[]
        for item in available:
            a=item.get("analysis",{}) or {}
            candidates=[p for p in prediction_log if p.get("name")==item.get("name")]
            pred=max(candidates,key=lambda x:x.get("created_at","")) if candidates else None
            snapshot.append({"name":item.get("name"),"symbol":item.get("symbol"),"rank":len(snapshot)+1,
                "ranking_score":item.get("ranking_score"),"direction":a.get("setup_direction") or a.get("model_signal"),"signal":a.get("signal"),
                "price":safe_float(a.get("price")),"entry":safe_float(a.get("entry")),"stop":safe_float(a.get("stop")),
                "tp1":safe_float(a.get("tp1")),"tp2":safe_float(a.get("tp2")),"tp3":safe_float(a.get("tp3")),
                "prediction_id":pred.get("id") if pred else None,"created_at":pred.get("created_at") if pred else now.astimezone(timezone.utc).isoformat()})
        _json_save(DAILY_TOP5_FILE,{"date":today,"captured_at":now.isoformat(),"items":snapshot})
        return True
    except Exception as exc:
        print(f"⚠️ Snapshot top 5 non salvato: {exc}")
        return False

def _periodic_intraday_summary(log, start_date, end_date):
    rows=[]
    for p in log:
        try: d=datetime.fromisoformat(str(p.get("created_at")).replace("Z","+00:00")).astimezone(ZoneInfo("Europe/Rome")).date()
        except Exception: continue
        if start_date<=d<=end_date and p.get("status")=="EVALUATED" and p.get("direction") in ("LONG","SHORT"): rows.append(p)
    c=sum(x.get("verdict")=="CORRETTA" for x in rows); w=sum(x.get("verdict")=="ERRATA" for x in rows); a=c/(c+w)*100 if c+w else 0
    return len(rows),c,w,a

def _periodic_long_term_summary(log, start_date, end_date):
    out=[]
    for d in LONG_TERM_HORIZONS_DAYS:
        rows=[]
        for r in log:
            try: fd=datetime.fromisoformat(str(r.get("forecast_date"))).date()
            except Exception: continue
            ev=r.get("evaluations",{}).get(str(d),{}); direction=r.get("horizons",{}).get(str(d),{}).get("direction")
            if start_date<=fd<=end_date and direction in ("LONG","SHORT") and ev: rows.append(ev)
        c=sum(x.get("verdict")=="CORRETTA" for x in rows); w=sum(x.get("verdict")=="ERRATA" for x in rows); a=c/(c+w)*100 if c+w else 0
        out.append((d,c,w,a))
    return out

def periodic_performance_appendix():
    now=datetime.now(ZoneInfo("Europe/Rome")); log=_json_load(PREDICTION_LOG_FILE,[]) or []
    ltlog,_=_evaluate_long_term_placeholder() if False else (None,None)
    lines=[]
    # Weekly report on Friday; month report on the last calendar day.
    if now.weekday()==4:
        start=now.date()-timedelta(days=4); n,c,w,a=_periodic_intraday_summary(log,start,now.date())
        lines += ["","📅 REPORT SETTIMANALE",f"⚡ Intraday: {c} ✅ | {w} ❌ | Accuracy {a:.1f}% ({n} valutate)"]
        ltlog,_=evaluate_long_term_forecasts();
        for d,c,w,a in _periodic_long_term_summary(ltlog,start,now.date()): lines.append(f"🧠 {d}g: {c} ✅ | {w} ❌ | {a:.1f}%")
    tomorrow=now.date()+timedelta(days=1)
    if tomorrow.month!=now.month:
        start=now.date().replace(day=1); n,c,w,a=_periodic_intraday_summary(log,start,now.date())
        lines += ["","📆 REPORT MENSILE",f"⚡ Intraday: {c} ✅ | {w} ❌ | Accuracy {a:.1f}% ({n} valutate)"]
        ltlog,_=evaluate_long_term_forecasts();
        for d,c,w,a in _periodic_long_term_summary(ltlog,start,now.date()): lines.append(f"🧠 {d}g: {c} ✅ | {w} ❌ | {a:.1f}%")
    return lines

def run_end_of_day_test(force=False):
    log=_json_load(PREDICTION_LOG_FILE,[])
    if not isinstance(log,list): log=[]
    local_now=datetime.now(ZoneInfo("Europe/Rome"))
    if not force and not (local_now.hour==EOD_REPORT_HOUR and 0<=local_now.minute<30): return None
    changed=False
    for pred in log:
        if pred.get("status")!="PENDING": continue
        result=evaluate_prediction(pred,_future_candles_for_prediction(pred))
        if result:
            pred.update(result); pred["status"]="EVALUATED"; changed=True
    if changed: _json_save(PREDICTION_LOG_FILE,log)
    today=local_now.date().isoformat(); rows=[]
    for pred in log:
        try: d=datetime.fromisoformat(pred.get("created_at","").replace("Z","+00:00")).astimezone(ZoneInfo("Europe/Rome")).date().isoformat()
        except Exception: continue
        if d==today: rows.append(pred)
    directional=[p for p in rows if p.get("direction") in ("LONG","SHORT") and p.get("status")=="EVALUATED"]
    correct=sum(p.get("verdict")=="CORRETTA" for p in directional); wrong=sum(p.get("verdict")=="ERRATA" for p in directional); amb=sum(p.get("verdict")=="AMBIGUA" for p in directional)
    pending=sum(p.get("status")=="PENDING" for p in rows); neutral=sum(p.get("direction")=="NEUTRALE" for p in rows)
    acc=correct/(correct+wrong)*100 if correct+wrong else 0.0
    lines=[f"🌙 COMMODITIES DAILY REPORT v{BOT_VERSION}",f"📅 {local_now.strftime('%d/%m/%Y')}","━━━━━━━━━━━━━━━━━━━━",
           "⚡ INTRADAY — RILEVAMENTI OGNI 15 MINUTI",f"🔎 Rilevamenti totali: {len(rows)}",f"🎯 Previsioni direzionali valutate: {len(directional)}",
           f"✅ Azzeccate: {correct}",f"❌ Sbagliate: {wrong}",f"⚪ Ambigue: {amb}",f"🟡 Ancora aperte: {pending}",f"⚪ Neutrali/WAIT: {neutral}",f"📈 Accuracy direzionale: {acc:.1f}%"]
    by_name={}
    for p in directional: by_name.setdefault(p["name"],[]).append(p)
    if by_name:
        lines += ["","🏆 ACCURACY PER COMMODITY"]
        vals=[]
        for name,rs in by_name.items():
            c=sum(x.get("verdict")=="CORRETTA" for x in rs); w=sum(x.get("verdict")=="ERRATA" for x in rs); a=c/(c+w)*100 if c+w else 0; vals.append((a,name,len(rs)))
        for a,name,n in sorted(vals,reverse=True): lines.append(f"• {name}: {a:.1f}% ({n})")
    state=_json_load(DAILY_REPORT_FILE,{})
    if state.get("last_report_date")==today and not force: return None
    state.update({"last_report_date":today,"accuracy":acc,"evaluated":len(directional),"total_readings":len(rows),"pending":pending}); _json_save(DAILY_REPORT_FILE,state)
    # Long-term is part of the same evening report.
    # ========================================================
    # SONDAGGIO SERALE — TOP 5 DELLA GIORNATA
    # ========================================================
    top5_state=_json_load(DAILY_TOP5_FILE,{}) or {}
    top5=top5_state.get("items",[]) if top5_state.get("date")==today else []
    if top5:
        lines += ["", "🌙 SONDAGGIO SERALE — TOP 5", "Verifica della previsione congelata al mattino:"]
        survey_direction=survey_tp1=survey_tp2=survey_tp3=survey_sl=0
        for item in top5:
            pred=next((p for p in log if p.get("id")==item.get("prediction_id")),None)
            result=evaluate_prediction(pred,_future_candles_for_prediction(pred)) if pred else None
            if result is None:
                lines.append(f"{item.get('rank')}. {item.get('name')} — 🟡 DA VALUTARE")
                continue
            d="✅" if result.get("direction_correct") else "❌"
            tp1="✅" if result.get("tp1_hit") else "❌"
            tp2="✅" if result.get("tp2_hit") else "❌"
            tp3="✅" if result.get("tp3_hit") else "❌"
            sl="❌ COLPITO" if result.get("sl_hit") else "✅ NON COLPITO"
            lines.append(f"{item.get('rank')}. {item.get('name')} | {item.get('direction','N/D')} | PREVISIONE {d} | TP1 {tp1} | TP2 {tp2} | TP3 {tp3} | SL {sl}")
            lines.append(f"   Entry {_fmt_price(item.get('entry'))} | SL {_fmt_price(item.get('stop'))} | TP1 {_fmt_price(item.get('tp1'))} | TP2 {_fmt_price(item.get('tp2'))} | TP3 {_fmt_price(item.get('tp3'))}")
            survey_direction += int(bool(result.get("direction_correct")))
            survey_tp1 += int(bool(result.get("tp1_hit")))
            survey_tp2 += int(bool(result.get("tp2_hit")))
            survey_tp3 += int(bool(result.get("tp3_hit")))
            survey_sl += int(not result.get("sl_hit"))
        lines.append(f"📊 TOP 5: previsione {survey_direction}/5 | TP1 {survey_tp1}/5 | TP2 {survey_tp2}/5 | TP3 {survey_tp3}/5 | SL rispettato {survey_sl}/5")
    else:
        lines += ["", "🌙 SONDAGGIO SERALE — TOP 5", "🟡 Nessun Top 5 congelato per questa giornata."]

    lines += ["","🧠 LUNGO TERMINE"]
    lt=long_term_report()
    lines.extend(lt.splitlines()[3:] if len(lt.splitlines())>3 else lt.splitlines())
    lines += periodic_performance_appendix()
    lines += ["","🔒 PAPER ONLY — nessun ordine reale"]
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

    exit_signal = exit_engine(position, current_analysis, current_price)
    if exit_signal.get("action") == "EXIT":
        return {"action": "EXIT", "reason": exit_signal.get("reason", "EXIT ENGINE"), "new_stop": stop}

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
        print("⚠️ Telegram non configurato: controlla TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID.")
        return False

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
        "horizon": f"{best_h} giorni",
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
            # The early horizons are expressed in DAYS (3/7/14/30), so the
            # historical sample must also be DAILY. Never mix monthly bars
            # with day horizons.
            history = get_data(item["symbol"], "1day", 4000)
        except Exception as exc:
            print(f"   ⚠️ Early history {item['name']}: {exc}")
        print(f"   📚 Early history {item['name']}: {len(history)} barre DAILY")
        if len(history) < EARLY_HISTORY_MIN_MONTHS:
            # Keep the engine explicit about insufficient history. Do not
            # downgrade to a shorter sample and present it as a long-horizon edge.
            history = []

        early = early_opportunity_engine(item["name"], history, a)
        early["timing"] = early_timing_engine(history, early)
        a["early_opportunity"] = early

        setup = a.get("setup_direction") or a.get("model_signal")
        if early.get("direction") in ("LONG", "SHORT") and early.get("direction") == setup:
            a["early_alignment_bonus"] = min(8.0, max(0.0, (early["score"]-50)*0.16))
        else:
            a["early_alignment_bonus"] = 0.0


def early_timing_engine(history, early):
    """Estimate when a historical move typically starts, without look-ahead.

    For each historical anchor we calculate the first future day on which the
    close reaches a direction-specific ATR-normalised move. Only past candles
    are used to create the anchor; future candles are used strictly as labels.
    """
    rows=[]
    for r in history or []:
        c=safe_float(r.get("close"))
        h=safe_float(r.get("high"))
        l=safe_float(r.get("low"))
        if c is not None: rows.append((c,h,l))
    if len(rows) < 80:
        return {"available":False,"reason":"CAMPIONE STORICO INSUFFICIENTE"}
    closes=[x[0] for x in rows]
    trs=[]
    for i in range(1,len(rows)):
        c,h,l=rows[i]
        pc=closes[i-1]
        if h is None or l is None: trs.append(abs(c-pc)); continue
        trs.append(max(h-l, abs(h-pc), abs(l-pc)))
    atr_window=20
    hits={"LONG":[],"SHORT":[]}
    # 1.25 ATR is a deliberately moderate event threshold; results are
    # descriptive statistics, not a guarantee of a future move.
    for i in range(atr_window, len(rows)-30):
        atr=sum(trs[max(0,i-atr_window):i])/atr_window
        if atr <= 0: continue
        base=closes[i]
        threshold=1.25*atr
        for d in ("LONG","SHORT"):
            first=None
            for k in range(1,31):
                future=closes[i+k]
                move=(future-base) if d=="LONG" else (base-future)
                if move >= threshold:
                    first=k; break
            if first is not None: hits[d].append(first)
    d=early.get("direction")
    if d not in hits or len(hits[d]) < 20:
        return {"available":False,"reason":"CAMPIONE TIMING INSUFFICIENTE","samples":len(hits.get(d,[]))}
    vals=sorted(hits[d])
    def pct(q):
        return vals[min(len(vals)-1, max(0, int(round((len(vals)-1)*q))))]
    q25,q50,q75=pct(.25),pct(.50),pct(.75)
    # Window labels are intentionally broad: historical start-time dispersion
    # is more honest than a single predicted day.
    start=max(1,q25-2); end=min(30,q75+2)
    entry_start=max(1,start-3); entry_end=max(entry_start, q50)
    horizon_start=max(1,q50-2); horizon_end=min(30,q75+3)
    return {
        "available":True,"direction":d,"samples":len(vals),
        "first_move_days_median":q50,"first_move_days_p25":q25,"first_move_days_p75":q75,
        "move_window_start":start,"move_window_end":end,
        "entry_window_start":entry_start,"entry_window_end":entry_end,
        "holding_window_start":horizon_start,"holding_window_end":horizon_end,
        "timing_confidence":round(clamp(50 + min(30,len(vals)-20)*0.8 - max(0,q75-q25)*0.5,0,90),1),
        "threshold_atr":1.25,
    }

def build_forecast_alert(ranked):
    available=[x for x in ranked if x.get("available") and x.get("analysis",{}).get("early_opportunity")]
    available.sort(key=lambda x:safe_float(x["analysis"]["early_opportunity"].get("score"),0) or 0, reverse=True)
    available=available[:EARLY_TOP_N]
    if not available:
        return "🔭 FORECAST\n\n⚪ Nessuna opportunità anticipata affidabile disponibile."
    item=available[0]; a=item["analysis"]; e=a.get("early_opportunity",{}) or {}; d=e.get("direction","NONE")
    icon="🟢" if d=="LONG" else "🔴" if d=="SHORT" else "🟡"
    timing=e.get("timing",{}) or {}
    if timing.get("available"):
        move=f"{timing['move_window_start']}–{timing['move_window_end']} giorni"
        entry=f"{timing['entry_window_start']}–{timing['entry_window_end']} giorni"
        hold=f"{timing['holding_window_start']}–{timing['holding_window_end']} giorni"
        active=timing['entry_window_start'] <= 1 <= timing['entry_window_end']
        status="⚡ FINESTRA ATTIVA" if active else "⏳ PREPARARSI"
    else:
        move=e.get("horizon","N/D"); entry="N/D"; hold="N/D"; status="⏳ MONITORARE"
    return "\n".join([
        "🔭 FORECAST", "", f"🥇 {item['name']}", f"{icon} {d}", "",
        f"📈 Movimento atteso: {move}", f"🎯 Finestra entrata: {entry}",
        f"⏳ Holding indicativo: {hold}", f"📊 Probabilità {e.get('probability',50):.0f}% | Score {e.get('score',0):.0f}/100",
        f"{status}", "", "⚡ L'ingresso viene cercato e confermato dal motore intraday.",
    ])


def build_early_telegram(ranked):
    """Compatibility wrapper: forecast-only, compact Telegram block."""
    return build_forecast_alert(ranked)


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

def _fmt_price(v):
    try:
        return f"{float(v):,.4f}".replace(",","X").replace(".",",").replace("X",".")
    except Exception:
        return "N/D"


def build_intraday_alert(ranked, position_message=None):
    candidates=[x for x in ranked if x.get("available") and x.get("analysis",{}).get("setup_direction") in ("LONG","SHORT")]
    candidates.sort(key=lambda x:safe_float(x["analysis"].get("intraday_score",0),0) or 0, reverse=True)
    if not candidates:
        return "⚡ INTRADAY ALERT\n\n⚪ Nessun setup operativo disponibile."
    item=candidates[0]; a=item["analysis"]; d=a.get("setup_direction"); s=a.get("intraday_score",a.get("score",0)); action=a.get("action_label","ATTENDERE")
    icon="🟢" if d=="LONG" else "🔴"; action_icon="🟢" if "COMPRA" in action or "ENTRATA" in action else "🔴" if "VENDI" in action else "🟡"
    trig=a.get("entry_trigger",{}) or {}; trigger=trig.get("kind","SETUP")
    if action=="NON ENTRARE": status="NON ENTRARE"
    elif action=="ATTENDERE": status="ATTENDERE"
    elif action=="ENTRATA POSSIBILE": status="ENTRATA POSSIBILE"
    else: status="ENTRARE"
    lines=["⚡ INTRADAY ALERT","",f"🥇 {item['name']}",f"{icon} {d} — {action_icon} {status}",""]
    lines.append(f"💰 {_fmt_price(a.get('price'))}")
    if a.get("entry") is not None: lines.append(f"🎯 Entry {_fmt_price(a.get('entry'))}")
    if a.get("stop") is not None: lines.append(f"🛑 SL {_fmt_price(a.get('stop'))}")
    if a.get("tp1") is not None: lines.append(f"🎯 TP1 {_fmt_price(a.get('tp1'))}")
    if a.get("tp2") is not None: lines.append(f"🎯 TP2 {_fmt_price(a.get('tp2'))}")
    pa=a.get("price_action",{}) or {}
    lines += ["",f"📊 Score {s:.0f}/100 | Prob. {a.get('entry_probability',0):.0f}%",f"🔥 {trigger} {trig.get('timeframe','')}"]
    if pa.get("patterns"):
        lines.append("🕯️ " + " + ".join(pa.get("patterns",[])[:2]))
    if pa.get("retracement",{}).get("state") not in (None, "N/D"):
        lines.append("↩️ " + str(pa.get("retracement",{}).get("state")))
    if pa.get("breakout_retest",{}).get("state") not in (None, "N/D", "NESSUN BREAKOUT"):
        lines.append("📍 " + str(pa.get("breakout_retest",{}).get("state")))
    if action in ("ATTENDERE","NON ENTRARE") and a.get("entry_blockers"):
        lines.append("⏳ " + " | ".join(a["entry_blockers"][:2]))
    if a.get("entry_warnings"):
        lines.append("ℹ️ " + " | ".join(a["entry_warnings"][:2]))
    if position_message:
        lines += ["", "📌 POSIZIONE", position_message]
    lines += ["",f"🔄 Aggiornamento ogni {MONITOR_INTERVAL_MINUTES} minuti"]
    return "\n".join(lines)


def build_ranking_alert(ranked):
    lines=["🏆 OPPORTUNITÀ","━━━━━━━━━━━━━━━━━━━━"]
    medals=["🥇","🥈","🥉"]
    shown=0
    ranked=sorted([x for x in ranked if x.get("available")], key=lambda x: safe_float(x.get("analysis",{}).get("intraday_score"),0) or 0, reverse=True)
    for item in ranked:
        if not item.get("available"): continue
        a=item["analysis"]; d=a.get("setup_direction") or a.get("model_signal") or "NONE"; sc=a.get("intraday_score",a.get("score",0));
        state=a.get("action_label","ATTENDERE")
        icon="🟢" if d=="LONG" else "🔴" if d=="SHORT" else "⚪"
        lines.append(f"{medals[shown] if shown<3 else str(shown+1)+'️⃣'} {item['name']}  {icon} {d}  {sc:.0f}")
        shown+=1
        if shown>=5: break
    return "\n".join(lines)


def build_telegram_5m(ranked, best, position_message=None, position=None):
    """Compatibility wrapper for the new compact v3.3 two-alert interface."""
    return "\n\n".join([build_intraday_alert(ranked, position_message), build_forecast_alert(ranked), build_ranking_alert(ranked), "⚠️ PAPER ONLY — nessun ordine reale."])


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
            "ranked": [
                {"name": x.get("name"), "symbol": x.get("symbol"), "analysis": {
                    "signal": (x.get("analysis",{}) or {}).get("signal"),
                    "setup_direction": (x.get("analysis",{}) or {}).get("setup_direction"),
                    "model_signal": (x.get("analysis",{}) or {}).get("model_signal"),
                    "action_label": (x.get("analysis",{}) or {}).get("action_label"),
                    "score": (x.get("analysis",{}) or {}).get("score",0),
                    "entry_probability": (x.get("analysis",{}) or {}).get("entry_probability",0),
                    "probability_validated": (x.get("analysis",{}) or {}).get("probability_validated"),
                    "probability_status": (x.get("analysis",{}) or {}).get("probability_status"),
                    "entry": (x.get("analysis",{}) or {}).get("entry"),
                    "stop": (x.get("analysis",{}) or {}).get("stop"),
                    "tp2": (x.get("analysis",{}) or {}).get("tp2"),
                    "statistical_risk": (x.get("analysis",{}) or {}).get("statistical_risk",{}),
                }} for x in ranked[:5]
            ],
        })
    except Exception as exc:
        print(f"⚠️ Monitor state non salvato: {exc}")

def build_telegram(ranked, best, position_message=None, position=None):
    """Telegram operativo V8: niente dettagli tecnici interni."""
    available=[x for x in ranked if x.get('available')][:3]
    lines=[f'🌍 COMMODITIES BOT v{BOT_VERSION}','', '🏆 CLASSIFICA']
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
                  f'🎯 AZIONE: {action}', f'🧭 DIREZIONE: {direction}', f'🧩 STATO ENTRY: {a.get("entry_state","N/D")}', f'📊 SCORE/QUALITÀ/CONF: {a.get("score",0):.0f}/{a.get("quality",0):.0f}/{a.get("confidence",0):.0f}', f'🧪 PROB. VALIDATA: {a.get("probability_validated"):.1f}%' if isinstance(a.get("probability_validated"),(int,float)) else '🧪 PROB. VALIDATA: non ancora validata',
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
            f'🎯 TP3: {tp3:.4f}' if tp3 is not None else '🎯 TP3: N/D', f'📐 TP/SL STATISTICO: {(a.get("statistical_risk",{}) or {}).get("status","N/D")} | SL {(a.get("statistical_risk",{}) or {}).get("sl_atr","-")} ATR | TP {(a.get("statistical_risk",{}) or {}).get("tp_atr","-")} ATR',
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
# v4.3 GLOBAL ELECTION INTELLIGENCE
# ============================================================
ELECTION_COMMODITY_MAP = {
    "Oro": ["gold", "safe haven", "central bank", "tariff", "sanction", "war", "rates", "dollar"],
    "Argento": ["silver", "industrial demand", "china", "tariff", "trade", "mine"],
    "Rame": ["copper", "china", "infrastructure", "manufacturing", "mine", "export", "tariff"],
    "Petrolio WTI": ["oil", "opec", "energy", "iran", "russia", "sanction", "production", "tariff"],
    "Petrolio Brent": ["oil", "opec", "energy", "iran", "russia", "sanction", "production", "tariff"],
    "Gas Naturale": ["natural gas", "lng", "pipeline", "energy", "russia", "europe", "storage"],
    "Grano": ["wheat", "grain", "ukraine", "russia", "black sea", "export", "tariff", "agriculture"],
    "Mais": ["corn", "maize", "ethanol", "china", "export", "agriculture", "tariff"],
    "Soia": ["soybean", "china", "brazil", "export", "agriculture", "tariff"],
    "Caffè": ["coffee", "brazil", "vietnam", "export", "tariff", "agriculture"],
    "Zucchero": ["sugar", "brazil", "ethanol", "export", "agriculture", "tariff"],
}

ELECTION_EVENT_TERMS = (
    "election", "elections", "presidential election", "general election", "parliamentary election",
    "vote", "voting", "ballot", "poll", "runoff", "referendum", "coalition", "government",
)

def _election_cache():
    return _json_load(ELECTION_CACHE_FILE, {}) or {}

def _save_election_cache(data):
    _json_save(ELECTION_CACHE_FILE, data)

def election_impact(name):
    if not ELECTION_IMPACT_ENABLED:
        return {"enabled": False, "direction": "NEUTRALE", "score": 0.0, "count": 0, "events": []}
    cache=_election_cache(); now=datetime.now(timezone.utc)
    key=name
    old=cache.get(key)
    try:
        if old:
            dt=datetime.fromisoformat(str(old.get("updated_at")).replace("Z","+00:00"))
            if now-dt < timedelta(hours=ELECTION_CACHE_HOURS): return old.get("value", old)
    except Exception: pass
    terms=ELECTION_COMMODITY_MAP.get(name,[name])
    q='("election" OR "elections" OR "vote" OR "runoff" OR "referendum") ('+' OR '.join(terms[:8])+')'
    articles=[]
    try:
        articles=_fetch_rss_articles(q, limit=30)
    except Exception:
        articles=[]
    relevant=[]; raw=0.0
    for a in articles:
        text=(str(a.get("title",''))+' '+str(a.get("description",''))).lower()
        if not any(t in text for t in ELECTION_EVENT_TERMS): continue
        rel=sum(1 for t in terms if t.lower() in text)
        if rel<=0: continue
        # Conservative mechanism-based direction. Elections are not inherently bullish/bearish.
        sign=0.0
        if any(k in text for k in ("sanction","export ban","production cut","infrastructure spending","stimulus","military escalation","war")):
            sign=1.0
        elif any(k in text for k in ("production increase","export increase","ceasefire","de-escalation","fiscal tightening")):
            sign=-1.0
        # Election uncertainty is useful for gold but not automatically for every commodity.
        if name=="Oro" and any(k in text for k in ("uncertainty","tight race","political risk","instability")):
            sign=max(sign,0.6)
        raw += sign * min(2.0, rel*0.35)
        relevant.append({"title":a.get("title",""),"publishedAt":a.get("publishedAt",a.get("published",'')),"url":a.get("url","")})
    score=clamp(raw/max(len(relevant),1)*8.0,-8.0,8.0) if relevant else 0.0
    direction="FAVOREVOLE" if score>=1.0 else "SFAVOREVOLE" if score<=-1.0 else "NEUTRALE"
    value={"enabled":True,"direction":direction,"score":round(score,2),"count":len(relevant),"events":relevant[:8],"updated_at":now.isoformat()}
    cache[key]={"updated_at":now.isoformat(),"value":value}; _save_election_cache(cache)
    return value

def apply_election_layer(analysis, election):
    analysis["elections"]=election or {}
    if not election: return
    direction=analysis.get("setup_direction") or analysis.get("model_signal")
    e=safe_float(election.get("score"),0) or 0
    if direction=="SHORT": e=-e
    # Very small bounded adjustment: election data informs, price engine decides.
    delta=clamp(e*0.45,-3.0,3.0)
    analysis["election_nudge"]=round(delta,2)
    analysis["score"]=clamp(safe_float(analysis.get("score"),0) + delta,0,100)

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
        query = "(" + " OR ".join(query_terms[:8]) + ") (White House OR U.S. president OR US administration OR tariff OR sanctions OR geopolitics OR OPEC OR Fed)"
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
        f"🌍 COMMODITIES BOT v{BOT_VERSION}",
        "🧪 PAPER / ANALISI — ORDINI REALI DISABILITATI",
        "━━━━━━━━━━━━━━━━━━━━",
        "🔭 EARLY OPPORTUNITY | ⚡ TRADING OGGI | 🧠 POLITICAL IMPACT | 📈 FUTURES CURVE",
    ]


# ============================================================
# v2.9 LEVEL-TO-LEVEL ENGINE (restored in v3.3 patch)
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



# ============================================================
# FINALIZATION ENGINE (restored in v3.3 patch)
# ============================================================
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
    analysis["market_regime"] = market_regime_engine(analysis)
    return analysis

# ============================================================
# v2.3 PREDICTION JOURNAL + END-OF-DAY TEST
# ============================================================



# ============================================================
# v3.6 COMMUNICATION ENGINE
# ============================================================
def _communication_state():
    return _json_load("commodities_communication_state.json", {}) or {}

def _save_communication_state(state):
    _json_save("commodities_communication_state.json", state)

def _daily_selection_state():
    return _json_load("commodities_daily_selection.json", {}) or {}

def _save_daily_selection_state(state):
    _json_save("commodities_daily_selection.json", state)

def _selection_for_today(ranked):
    now=datetime.now(ZoneInfo("Europe/Rome")); today=now.date().isoformat(); state=_daily_selection_state()
    if state.get("date")==today and state.get("name"): return state
    if not ranked: return {}
    candidates=[x for x in ranked if x.get("available")]
    if not candidates: return {}
    best=candidates[0]; a=best.get("analysis",{})
    state={"date":today,"name":best.get("name"),"symbol":best.get("symbol"),"direction":a.get("setup_direction") or a.get("model_signal"),"locked_at":datetime.now(timezone.utc).isoformat()}
    _save_daily_selection_state(state); return state

def _find_selected(ranked, selection):
    name=selection.get("name") if selection else None
    return next((x for x in ranked if x.get("name")==name and x.get("available")), None) or (ranked[0] if ranked else {})

def _session_message(label, item, position_message=None):
    a=item.get("analysis",{}) or {}; direction=a.get("setup_direction") or a.get("model_signal") or "NONE"; state=a.get("entry_state","WATCH"); confluence_ok=bool((a.get("intraday_core",{}) or {}).get("confluence_ok",False))
    if state=="ENTRY_CONFIRMED" and confluence_ok and direction in ("LONG","SHORT"):
        action="COMPRA ORA" if direction=="LONG" else "VENDI ORA"; icon="🟢" if direction=="LONG" else "🔴"; display=f"{icon} {direction} — {action}"
    elif direction in ("LONG","SHORT"):
        display=f"🟡 {direction} — ASPETTARE CONFERMA"
    else: display="⚪ NO TRADE"
    lines=[label,"",f"🥇 {item.get('name','N/D')}",display,"",f"💰 Prezzo: {_fmt_price(a.get('price'))}",f"📊 Score: {safe_float(a.get('score'),0) or 0:.0f}/100",f"📈 Probabilità: {safe_float(a.get('entry_probability'),0) or safe_float(a.get('long_probability'),0.5)*100:.1f}%",f"🧠 Confidenza: {safe_float(a.get('confidence'),0) or 0:.1f}/100"]
    for key,lab in (("entry","Entry"),("stop","Stop"),("tp1","TP1"),("tp2","TP2"),("tp3","TP3")):
        if a.get(key) is not None: lines.append(f"{'🎯' if key!='stop' else '🛑'} {lab}: {_fmt_price(a.get(key))}")
    reg=(a.get("market_regime",{}) or {}).get("state");
    if reg: lines.append(f"🌍 Regime: {reg}")
    pa=a.get("price_action",{}) or {}; patterns=pa.get("patterns",[]) or []
    if patterns: lines.append("🕯️ "+" + ".join(patterns[:3]))
    e=a.get("elections",{}) or {}; p=a.get("political",{}) or {}
    lines.append(f"🗳️ Elezioni globali: {e.get('direction','N/D')} ({e.get('count',0)} eventi)")
    lines.append(f"🇺🇸 Presidente degli Stati Uniti: {p.get('direction','N/D')}")
    lt=a.get("long_term",{}).get("horizons",{}) if isinstance(a.get("long_term"),dict) else {}
    if lt:
        lines.append(f"🔮 LT: 30g {lt.get('30',{}).get('direction','N/D')} | 90g {lt.get('90',{}).get('direction','N/D')} | 180g {lt.get('180',{}).get('direction','N/D')}")
    if position_message: lines += ["","📌 POSIZIONE",position_message]
    lines += ["","🧪 PAPER ONLY — nessun ordine reale"]
    return "\n".join(lines)

def maybe_send_session_reports(ranked, best, position_message=None):
    if COMMUNICATION_MODE!="MORNING_USA_EVENT": return
    now=datetime.now(ZoneInfo("Europe/Rome")); today=now.date().isoformat(); state=_communication_state(); sent=state.setdefault("sent",{})
    selection=_selection_for_today(ranked); selected=_find_selected(ranked,selection)
    if now.hour==MORNING_REPORT_HOUR and MORNING_REPORT_MINUTE<=now.minute<MORNING_REPORT_MINUTE+30 and sent.get("morning")!=today and selected:
        send_telegram(_session_message("🌅 COMMODITY DEL GIORNO — INTRADAY",selected,position_message)); sent["morning"]=today
    if now.hour==USA_REPORT_HOUR and USA_REPORT_MINUTE<=now.minute<USA_REPORT_MINUTE+30 and sent.get("usa")!=today and selected:
        send_telegram(_session_message("🇺🇸 USA SESSION UPDATE — RECHECK",selected,position_message)); sent["usa"]=today
    _save_communication_state(state)


# ============================================================
# v5.0 PREDICTIVE VALIDATION / SMART-MONEY PROXY / STATISTICAL RISK
# ============================================================
V5_MIN_CALIBRATION_SAMPLES = int(os.getenv("V5_MIN_CALIBRATION_SAMPLES", "30"))
V5_MIN_RISK_TRADES = int(os.getenv("V5_MIN_RISK_TRADES", "25"))
V5_REQUIRE_VALIDATED_PROB = os.getenv("V5_REQUIRE_VALIDATED_PROB", "0") == "1"
V5_RISK_HORIZON_BARS = int(os.getenv("V5_RISK_HORIZON_BARS", "8"))


def _v5_directional_log():
    log = _json_load(PREDICTION_LOG_FILE, []) or []
    return [x for x in log if x.get("status") == "EVALUATED" and x.get("direction") in ("LONG", "SHORT")]


def v5_probability_calibration(name, direction):
    """Calibrate the model probability using only already evaluated paper predictions.
    Uses empirical-Bayes shrinkage toward 50% so tiny samples cannot create fake certainty.
    """
    rows = [x for x in _v5_directional_log()
            if x.get("name") == name and x.get("direction") == direction]
    wins = sum(x.get("verdict") == "CORRETTA" for x in rows)
    losses = sum(x.get("verdict") == "ERRATA" for x in rows)
    n = wins + losses
    # Twelve neutral pseudo-observations keep early estimates conservative.
    pseudo = 12
    empirical = (wins + pseudo * 0.5) / (n + pseudo) if n + pseudo else 0.5
    status = "VALIDATA" if n >= V5_MIN_CALIBRATION_SAMPLES else "NON_VALIDATA"
    return {
        "samples": n,
        "wins": wins,
        "losses": losses,
        "raw_rate": round(wins / n * 100, 1) if n else None,
        "calibrated_probability": round(empirical * 100, 1),
        "status": status,
        "method": "EMPIRICAL_BAYES_SHRINKAGE_50",
    }


def _v5_obv(candles):
    if not candles:
        return 0.0
    obv = 0.0
    prev = safe_float(candles[0].get("close"))
    for c in candles[1:]:
        close = safe_float(c.get("close")); vol = safe_float(c.get("volume"), 0.0) or 0.0
        if close is None or prev is None:
            continue
        if close > prev: obv += vol
        elif close < prev: obv -= vol
        prev = close
    return obv


def v5_smart_money_proxy(candles, direction):
    """Conservative price/volume proxy inspired by liquidity, pressure and Wyckoff concepts.
    It does not pretend to observe institutional order flow when the provider exposes no order book.
    """
    if not candles or direction not in ("LONG", "SHORT"):
        return {"score": 50.0, "state": "N/D", "available": False}
    rows = candles[-80:]
    closes = [safe_float(x.get("close")) for x in rows]
    vols = [safe_float(x.get("volume"), 0.0) or 0.0 for x in rows]
    closes = [x for x in closes if x is not None]
    if len(closes) < 20:
        return {"score": 50.0, "state": "DATI INSUFFICIENTI", "available": False}
    last = closes[-1]
    e20 = ema(closes, 20) or last
    avg_vol = mean(vols[-20:])
    last_vol = vols[-1] if vols else 0.0
    vol_ratio = last_vol / avg_vol if avg_vol > 0 else 1.0
    recent_ret = (closes[-1] / closes[-6] - 1.0) if len(closes) >= 6 and closes[-6] else 0.0
    obv = _v5_obv(rows)
    obv_prev = _v5_obv(rows[:-10]) if len(rows) > 30 else 0.0
    obv_delta = obv - obv_prev
    direction_sign = 1 if direction == "LONG" else -1
    trend_component = 1 if (last > e20) == (direction == "LONG") else -1
    momentum_component = 1 if recent_ret * direction_sign > 0 else -1
    flow_component = 1 if obv_delta * direction_sign > 0 else -1
    volume_component = 1 if vol_ratio >= 1.15 and momentum_component > 0 else 0
    raw = 50 + 12 * trend_component + 15 * momentum_component + 15 * flow_component + 8 * volume_component
    score = clamp(raw, 0, 100)
    state = "ACCUMULAZIONE/PRESSIONE" if score >= 65 else "DISTRIBUZIONE/CONTROPRESSIONE" if score <= 35 else "MISTA"
    return {"available": True, "score": round(score, 1), "state": state,
            "volume_ratio": round(vol_ratio, 2), "recent_return": round(recent_ret * 100, 3),
            "obv_delta": round(obv_delta, 2), "method": "PRICE_VOLUME_PROXY"}


def v5_statistical_risk_engine(candles, direction):
    """Select SL/TP from a small, walk-forward historical grid.
    Uses only completed historical bars and a conservative same-bar rule.
    """
    if direction not in ("LONG", "SHORT") or len(candles or []) < 160:
        return {"available": False, "status": "DATI INSUFFICIENTI"}
    rows = candles[-900:]
    atr_values = []
    for i in range(len(rows)):
        atr_values.append(atr(rows[:i+1], 14) if i >= 20 else None)
    candidates = []
    sl_mults = (1.0, 1.25, 1.5, 1.75, 2.0)
    tp_mults = (1.5, 2.0, 2.5, 3.0, 3.5, 4.0)
    start = max(30, int(len(rows) * 0.35))
    end = max(start + 1, len(rows) - V5_RISK_HORIZON_BARS - 1)
    split = start + int((end - start) * 0.60)

    def evaluate_grid(a, b):
        outcomes = []
        for i in range(a, b):
            av = atr_values[i]
            entry = safe_float(rows[i].get("close"))
            if av is None or entry is None or av <= 0:
                continue
            for sm in sl_mults:
                for tm in tp_mults:
                    stop = entry - sm * av if direction == "LONG" else entry + sm * av
                    target = entry + tm * av if direction == "LONG" else entry - tm * av
                    result = None
                    for j in range(i + 1, min(i + 1 + V5_RISK_HORIZON_BARS, len(rows))):
                        hi = safe_float(rows[j].get("high")); lo = safe_float(rows[j].get("low"))
                        if hi is None or lo is None: continue
                        hit_stop = lo <= stop if direction == "LONG" else hi >= stop
                        hit_target = hi >= target if direction == "LONG" else lo <= target
                        if hit_stop and hit_target:
                            result = -sm
                            break
                        if hit_target:
                            result = tm
                            break
                        if hit_stop:
                            result = -sm
                            break
                    if result is None:
                        last = safe_float(rows[min(i + V5_RISK_HORIZON_BARS, len(rows)-1)].get("close"))
                        if last is None: continue
                        result = (last-entry)/av if direction == "LONG" else (entry-last)/av
                        result = clamp(result, -sm, tm)
                    outcomes.append((sm, tm, result))
        return outcomes

    train = evaluate_grid(start, split)
    valid = evaluate_grid(split, end)
    if not train or not valid:
        return {"available": False, "status": "NESSUN CAMPIONE"}

    def rank_grid(data):
        best = None
        for sm in sl_mults:
            for tm in tp_mults:
                vals = [r for a,b,r in data if a == sm and b == tm]
                if len(vals) < V5_MIN_RISK_TRADES: continue
                expectancy = mean(vals)
                win = sum(v > 0 for v in vals) / len(vals)
                score = expectancy * 100 + win * 10 - abs(tm / sm - 2.0) * 2
                candidate = (score, sm, tm, expectancy, win, len(vals))
                if best is None or candidate[0] > best[0]: best = candidate
        return best

    train_best = rank_grid(train)
    if not train_best:
        return {"available": False, "status": "CAMPIONE TRAIN INSUFFICIENTE"}
    sm, tm = train_best[1], train_best[2]
    valid_vals = [r for a,b,r in valid if a == sm and b == tm]
    if len(valid_vals) < V5_MIN_RISK_TRADES:
        return {"available": False, "status": "VALIDAZIONE INSUFFICIENTE"}
    valid_expectancy = mean(valid_vals)
    valid_win = sum(v > 0 for v in valid_vals) / len(valid_vals)
    robust = valid_expectancy > 0
    return {"available": True, "status": "VALIDATA" if robust else "NON_VALIDATA",
            "sl_atr": sm, "tp_atr": tm, "train_expectancy": round(train_best[3], 3),
            "train_win_rate": round(train_best[4] * 100, 1), "train_samples": train_best[5],
            "validation_expectancy": round(valid_expectancy, 3),
            "validation_win_rate": round(valid_win * 100, 1), "validation_samples": len(valid_vals),
            "method": "WALK_FORWARD_ATR_GRID"}


def v5_enhance_analysis(name, analysis, candles, intraday_candles=None):
    """Final v5 layer: calibrated probability, smart-money proxy and statistical risk."""
    a = analysis
    direction = a.get("setup_direction") or a.get("model_signal")
    if direction not in ("LONG", "SHORT"):
        return a
    sm = v5_smart_money_proxy(intraday_candles or candles, direction)
    a["smart_money_proxy"] = sm
    # Smart-money proxy is deliberately bounded to avoid turning volume into a fake oracle.
    sm_delta = ((sm.get("score", 50.0) - 50.0) * 0.10) if sm.get("available") else 0.0
    a["score"] = clamp((safe_float(a.get("score"), 0) or 0) + sm_delta, 0, 100)

    cal = v5_probability_calibration(name, direction)
    raw_prob = safe_float(a.get("entry_probability"), None)
    if raw_prob is None:
        raw_prob = (safe_float(a.get("long_probability"), 0.5) or 0.5) * 100
    if direction == "SHORT":
        raw_direction_prob = 100 - raw_prob
    else:
        raw_direction_prob = raw_prob
    if cal["status"] == "VALIDATA":
        final_prob = 0.45 * raw_direction_prob + 0.55 * cal["calibrated_probability"]
    else:
        final_prob = raw_direction_prob
    a["probability_raw"] = round(raw_direction_prob, 1)
    a["probability_validated"] = round(final_prob, 1) if cal["status"] == "VALIDATA" else None
    a["probability_validation"] = cal
    a["probability_status"] = cal["status"]

    risk = v5_statistical_risk_engine(intraday_candles or candles, direction)
    a["statistical_risk"] = risk
    if risk.get("available") and risk.get("status") == "VALIDATA":
        price = safe_float(a.get("price")); av = safe_float(risk.get("sl_atr")); tv = safe_float(risk.get("tp_atr"))
        atr_now = atr(intraday_candles or candles, 14) if (intraday_candles or candles) else None
        if price and atr_now and av and tv:
            if direction == "LONG":
                a["stop"] = _price_round(price - av * atr_now); a["tp1"] = _price_round(price + max(1.5, tv*0.65) * atr_now); a["tp2"] = _price_round(price + tv * atr_now); a["tp3"] = _price_round(price + (tv + 1.0) * atr_now)
            else:
                a["stop"] = _price_round(price + av * atr_now); a["tp1"] = _price_round(price - max(1.5, tv*0.65) * atr_now); a["tp2"] = _price_round(price - tv * atr_now); a["tp3"] = _price_round(price - (tv + 1.0) * atr_now)
            a["risk_method"] = "STATISTICO WALK-FORWARD"
    # Hard entry gate only if explicitly enabled; default preserves paper research flow.
    if V5_REQUIRE_VALIDATED_PROB and cal["status"] != "VALIDATA" and a.get("signal") in ("LONG", "SHORT"):
        a["signal"] = "WAIT"; a["action_label"] = "ATTENDERE"
        a.setdefault("entry_blockers", []).append("PROBABILITA_NON_VALIDATA")
    return a



def long_term_forecast(name, candles, analysis):
    """v5 long-term forecast: commodity-specific, regime-conditioned and explicitly validated."""
    if not LONG_TERM_ENABLED or len(candles or []) < 160:
        return {"enabled": False, "status": "INSUFFICIENT_DATA"}
    rows = candles[-1200:]
    closes = [safe_float(x.get("close")) for x in rows]
    closes = [x for x in closes if x is not None]
    if len(closes) < 160:
        return {"enabled": False, "status": "INSUFFICIENT_DATA"}
    m20 = _daily_momentum(rows,20); m60 = _daily_momentum(rows,60); m120 = _daily_momentum(rows,120)
    model_prob = safe_float(analysis.get("long_probability"),0.5) or 0.5
    model_dir = analysis.get("setup_direction") or analysis.get("model_signal")
    # Current momentum regime: use the sign and rough magnitude of 20d momentum.
    current_sign = 1 if m20 > 0 else -1 if m20 < 0 else 0
    out = {}
    for d in LONG_TERM_HORIZONS_DAYS:
        horizon = min(int(d), 365)
        samples=[]
        # Conditional historical analogues: same 20d momentum sign, then evaluate forward return.
        max_i = len(rows)-horizon-1
        for i in range(30, max_i):
            c0 = safe_float(rows[i].get("close"))
            c1 = safe_float(rows[i+horizon].get("close"))
            if c0 is None or c1 is None or c0 <= 0: continue
            m20_i = _daily_momentum(rows[:i+1],20)
            sign_i = 1 if m20_i > 0 else -1 if m20_i < 0 else 0
            if current_sign == 0 or sign_i == current_sign:
                samples.append(1 if c1 > c0 else 0)
        n=len(samples)
        empirical=(sum(samples)+10*0.5)/(n+10) if n else 0.5
        # Model + trend + conditional analogue. No claim of validation until sample threshold.
        trend_bias = clamp(0.5 + 0.18*math.tanh(m20*18) + 0.10*math.tanh(m60*10) + 0.06*math.tanh(m120*7), 0.05, 0.95)
        if model_dir == "SHORT": model_long = 1-model_prob
        else: model_long = model_prob
        if n >= 20:
            p_long = clamp(0.35*model_long + 0.25*trend_bias + 0.40*empirical, 0.05, 0.95)
            status="VALIDATA"
        else:
            p_long = clamp(0.55*model_long + 0.45*trend_bias, 0.10, 0.90)
            status="NON_VALIDATA"
        p_short=1-p_long
        direction="LONG" if p_long>=0.56 else "SHORT" if p_short>=0.56 else "NEUTRALE"
        out[str(d)]={"direction":direction,"long_probability":round(p_long*100,1),"short_probability":round(p_short*100,1),
                     "confidence":round(abs(p_long-0.5)*200,1),"status":status,"historical_samples":n,
                     "historical_hit_rate":round(empirical*100,1) if n else None}
    return {"enabled":True,"status":"OK","price":safe_float(analysis.get("price")),
            "generated_at":datetime.now(timezone.utc).isoformat(),"horizons":out,
            "drivers":{"momentum20":round(m20*100,2),"momentum60":round(m60*100,2),"momentum120":round(m120*100,2),
                        "model_probability":round(model_prob*100,1),"regime":(analysis.get("market_regime",{}) or {}).get("state","N/D"),
                        "futures":(analysis.get("futures_structure",{}) or {}).get("score",0),
                        "cyclical":(analysis.get("cyclical",{}) or {}).get("score",0),
                        "political":(analysis.get("political",{}) or {}).get("score",0),
                        "weather":(analysis.get("weather",{}) or {}).get("score",0)},
            "method":"MODEL + MOMENTUM + CONDITIONAL HISTORICAL ANALOGUES"}

def v5_daily_report():
    """Actionable EOD report: ranking, validated probability, statistical risk and learning status."""
    local_now = datetime.now(ZoneInfo("Europe/Rome"))
    log = _json_load(PREDICTION_LOG_FILE, []) or []
    if not isinstance(log, list): log = []
    changed = False
    for pred in log:
        if pred.get("status") != "PENDING": continue
        result = evaluate_prediction(pred, _future_candles_for_prediction(pred))
        if result:
            pred.update(result); pred["status"] = "EVALUATED"; changed = True
    if changed: _json_save(PREDICTION_LOG_FILE, log)
    today = local_now.date().isoformat()
    rows = []
    for p in log:
        try: d = datetime.fromisoformat(str(p.get("created_at","")).replace("Z","+00:00")).astimezone(ZoneInfo("Europe/Rome")).date().isoformat()
        except Exception: continue
        if d == today: rows.append(p)
    directional = [p for p in rows if p.get("direction") in ("LONG","SHORT") and p.get("status") == "EVALUATED"]
    correct = sum(p.get("verdict") == "CORRETTA" for p in directional)
    wrong = sum(p.get("verdict") == "ERRATA" for p in directional)
    amb = sum(p.get("verdict") == "AMBIGUA" for p in directional)
    pending = sum(p.get("status") == "PENDING" for p in rows)
    accuracy = correct/(correct+wrong)*100 if correct+wrong else 0.0
    state = _json_load(DAILY_REPORT_FILE,{}) or {}
    if state.get("last_report_date") == today: return None
    lines = [f"🌙 COMMODITIES DAILY REPORT v{BOT_VERSION}", f"📅 {local_now.strftime('%d/%m/%Y')}", "━━━━━━━━━━━━━━━━━━━━",
             f"🎯 INTRADAY: {len(directional)} valutate | {correct} ✅ | {wrong} ❌ | {amb} ⚪ | {pending} aperte",
             f"📈 Accuracy: {accuracy:.1f}%" if directional else "📈 Accuracy: NON ANCORA VALIDABILE", ""]
    # Historical calibration snapshot.
    calib = []
    for p in _v5_directional_log():
        calib.append(p)
    if calib:
        wins = sum(x.get("verdict") == "CORRETTA" for x in calib); total = sum(x.get("verdict") in ("CORRETTA","ERRATA") for x in calib)
        lines.append(f"🧠 VALIDAZIONE STORICA: {wins}/{total} corretti | {wins/total*100:.1f}%" if total else "🧠 VALIDAZIONE STORICA: dati insufficienti")
    else:
        lines.append("🧠 VALIDAZIONE STORICA: in formazione — nessun campione valutato")
    lines += ["", "🏆 COSA OSSERVARE DOMANI"]
    # This section is populated by the latest persisted ranking state when available.
    monitor = _json_load(MONITOR_STATE_FILE,{}) or {}
    ranked = monitor.get("ranked", []) if isinstance(monitor, dict) else []
    if ranked:
        for i, item in enumerate(ranked[:5], 1):
            a = item.get("analysis", {}) or {}; d = a.get("setup_direction") or a.get("model_signal") or "NONE"
            prob = a.get("probability_validated")
            prob_txt = f"{prob:.1f}% VALIDATA" if isinstance(prob,(int,float)) else "non validata"
            risk = a.get("statistical_risk", {}) or {}
            rr = 0.0
            entry, stop, tp2 = a.get("entry") or a.get("price"), a.get("stop"), a.get("tp2")
            if entry and stop and tp2 and abs(entry-stop)>0: rr = abs(tp2-entry)/abs(entry-stop)
            lines.append(f"{i}. {item.get('name','N/D')} | {a.get('signal','WAIT')} | {d} | P {prob_txt} | Score {a.get('score',0):.0f} | R/R {rr:.2f}")
            lines.append(f"   Entry {_fmt_price(entry)} | SL {_fmt_price(stop)} | TP2 {_fmt_price(tp2)} | rischio {risk.get('status','N/D')}")
    else:
        lines.append("Nessun ranking persistito disponibile in questa esecuzione.")
    lines += ["", "🧪 Nota: le probabilità non validate NON vengono presentate come statisticamente dimostrate.", "🔒 PAPER ONLY — nessun ordine reale"]
    state.update({"last_report_date": today, "accuracy": accuracy, "evaluated": len(directional), "total_readings": len(rows), "pending": pending})
    _json_save(DAILY_REPORT_FILE, state)
    return "\n".join(lines)


# ============================================================
# MAIN
# ============================================================


def _safe_direction(value):
    return value if value in ("LONG", "SHORT") else "NONE"


def market_regime_engine(candles, intraday=None):
    """Classifies the market regime without claiming predictive certainty."""
    data = intraday or candles or []
    if len(data) < 30:
        return {"regime":"UNKNOWN", "confidence":0.0, "trend_score":0.0, "volatility":"UNKNOWN"}
    closes = [safe_float(x.get("close")) for x in data[-80:] if safe_float(x.get("close")) is not None]
    if len(closes) < 30:
        return {"regime":"UNKNOWN", "confidence":0.0, "trend_score":0.0, "volatility":"UNKNOWN"}
    fast = sum(closes[-10:]) / 10
    slow = sum(closes[-30:]) / 30
    ret = (closes[-1] / closes[-21] - 1) if closes[-21] else 0
    ranges = []
    for x in data[-30:]:
        h, l, c = safe_float(x.get("high")), safe_float(x.get("low")), safe_float(x.get("close"))
        if h is not None and l is not None and c:
            ranges.append((h-l)/abs(c))
    vol = (sum(ranges)/len(ranges))*100 if ranges else 0
    trend_score = clamp(abs(ret)*1000 + abs(fast/slow-1)*500, 0, 100)
    if trend_score >= 55 and abs(ret) >= 0.006:
        regime = "TREND_UP" if ret > 0 else "TREND_DOWN"
    elif vol >= 1.8:
        regime = "HIGH_VOLATILITY"
    elif trend_score < 25:
        regime = "RANGE"
    else:
        regime = "TRANSITION"
    return {"regime":regime, "confidence":round(clamp(35+trend_score*0.65,0,100),1), "trend_score":round(trend_score,1), "return_20":round(ret*100,2), "volatility_pct":round(vol,3), "volatility":"HIGH" if vol>=1.8 else "NORMAL"}


def cross_market_intelligence(name, usd=None, global_impact=None, political=None, futures=None):
    """Combines already-collected external contexts; no fabricated prices."""
    score = 50.0; reasons=[]
    u = usd or {}
    uscore = safe_float(u.get("score"), 50.0) or 50.0
    if name in ("Oro","Argento","Platino","Palladio"):
        if uscore < 45: score += 7; reasons.append("USD debole favorevole ai metalli")
        elif uscore > 60: score -= 7; reasons.append("USD forte penalizzante per i metalli")
    gi = global_impact or {}
    shock = safe_float(gi.get("shock_intensity"), 0.0) or 0.0
    if shock > 0.7 and name in ("Oro","Petrolio WTI","Petrolio Brent","Gas Naturale"):
        score += 5; reasons.append("shock globale elevato")
    pi = political or {}
    pscore = safe_float(pi.get("score"), 0.0) or 0.0
    if abs(pscore) >= 15:
        score += clamp(pscore*0.15,-8,8); reasons.append("impatto politico rilevante")
    fs = futures or {}
    if isinstance(fs, dict) and fs.get("available"):
        curve = str(fs.get("structure") or fs.get("signal") or "").upper()
        if "BACKWARD" in curve or "BACKWARDATION" in curve:
            score += 3; reasons.append("curva backwardation")
        elif "CONTANGO" in curve:
            score -= 2; reasons.append("curva contango")
    return {"score":round(clamp(score,0,100),1), "reasons":reasons}


def intelligence_fusion_engine(name, analysis, candles, intraday, usd, global_impact, political, futures, weather=None, disasters=None):
    """High-level decision layer: context, regime, conflicts and data quality."""
    a=analysis
    regime=market_regime_engine(candles, intraday)
    cross=cross_market_intelligence(name, usd, global_impact, political, futures)
    direction=_safe_direction(a.get("setup_direction") or a.get("model_signal"))
    votes=[]
    if direction != "NONE":
        if regime["regime"] == "TREND_UP": votes.append(1 if direction=="LONG" else -1)
        elif regime["regime"] == "TREND_DOWN": votes.append(1 if direction=="SHORT" else -1)
        if cross["score"] >= 60: votes.append(1)
        elif cross["score"] <= 40: votes.append(-1)
    regime_bonus = 0
    if direction=="LONG" and regime["regime"]=="TREND_UP": regime_bonus=5
    if direction=="SHORT" and regime["regime"]=="TREND_DOWN": regime_bonus=5
    if regime["regime"]=="HIGH_VOLATILITY": regime_bonus -= 3
    quality=100.0
    sc=a.get("source_check") or {}
    if sc.get("core_data_ok") is False: quality-=20
    if "STALE" in str(DATA_SOURCE_STATS.get(name,{})).upper(): quality-=10
    missing=sum(1 for tf in ("4H","1H","15m","5m") if tf not in (a.get("pattern_timeframes") or {}))
    quality-=min(25,missing*6)
    quality=clamp(quality,0,100)
    a["market_regime"]=regime
    a["cross_market_intelligence"]=cross
    a["intelligence_quality"]=round(quality,1)
    a["intelligence_conflicts"] = {"votes":votes,"agreement":round((sum(1 for v in votes if v>0)-sum(1 for v in votes if v<0))/max(1,len(votes))*100,1)}
    a["score"]=clamp((safe_float(a.get("score"),50) or 50)+regime_bonus,0,100)
    a["intelligence_summary"] = " | ".join([regime["regime"], f"CROSS {cross['score']:.0f}", f"DATA {quality:.0f}"])
    return a


def save_intelligence_feedback(name, analysis):
    """Persistent paper-trading memory for later statistical learning."""
    try:
        try:
            with open(INTELLIGENCE_JOURNAL_FILE,"r",encoding="utf-8") as f: rows=json.load(f)
            if not isinstance(rows,list): rows=[]
        except Exception:
            rows=[]
        rows.append({
            "timestamp":datetime.now(timezone.utc).isoformat(), "name":name,
            "signal":analysis.get("signal"), "direction":analysis.get("setup_direction") or analysis.get("model_signal"),
            "score":round(safe_float(analysis.get("score"),0) or 0,2),
            "probability":analysis.get("probability_validated") or analysis.get("entry_probability"),
            "regime":(analysis.get("market_regime") or {}).get("regime"),
            "data_quality":analysis.get("intelligence_quality"),
            "entry":analysis.get("entry"), "stop":analysis.get("stop"),
            "tp1":analysis.get("tp1"), "tp2":analysis.get("tp2"), "tp3":analysis.get("tp3"),
        })
        rows=rows[-2000:]
        with open(INTELLIGENCE_JOURNAL_FILE,"w",encoding="utf-8") as f: json.dump(rows,f,ensure_ascii=False,indent=2)
    except Exception as exc:
        print(f"   ⚠️ Intelligence journal: {exc}")

def main():
    print()
    print("=" * 70)
    print(f"🌍 COMMODITIES BOT v{BOT_VERSION}")
    print("MORNING 08:00 + USA 14:30 + EOD 21:00 | INTRADAY 15m + LONG TERM JOURNAL | PAPER ONLY")
    print("v4.3 INTELLIGENCE FUSION: ENTER solo con MTF + trigger + L2L + R/R + qualità/confidenza/probabilità")
    print("COMMUNICATION: MORNING + USA + EOD | INTERNAL ANALYSIS EVERY 15m")
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
            print(f"   🧮 Dataset: {len(dataset)} | Fonte: {DATA_SOURCE_STATS.get(name, {}).get('1day', 'N/D')}")

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
            analysis["source_registry"] = INTELLIGENCE_SOURCE_REGISTRY
            # Core-data quality: daily + 1H are mandatory; finer TFs are optional
            # and can be reconstructed/rescued without killing the analysis.
            analysis["source_check"]["core_data_ok"] = len(candles) >= 120 and len(intraday_candles) >= 80
            analysis["source_check"]["data_quality"] = round(clamp(100 - max(0, 120-len(candles))*0.25, 0, 100),1)

            weather = weather_intelligence(name)
            disasters = natural_disaster_intelligence(name)
            apply_weather_and_disaster_layers(analysis, weather, disasters)

            # v4.3: global election intelligence is commodity-specific and bounded.
            elections = election_impact(name)
            apply_election_layer(analysis, elections)

            # v2.9: Level-to-Level technical structure after all current context layers.
            level_to_level_engine(
                analysis, commodity_name=name, candles=candles,
                pattern_timeframes=pattern_timeframes
            )

            # v3.5: price action + adaptive structure/ATR levels. These layers
            # are confirmations and fallbacks; missing risk data never deletes a setup.
            analysis["commodity_name"] = name
            analysis["price_action"] = price_action_context_engine(analysis)
            adaptive_levels = adaptive_risk_levels(analysis, candles, analysis.get("setup_direction") or analysis.get("model_signal"))
            if adaptive_levels.get("available"):
                analysis.update({k: adaptive_levels[k] for k in ("stop","tp1","tp2","tp3")})
                analysis["adaptive_risk"] = adaptive_levels

            # v3.0: optional futures curve context. No data -> no invented signal.
            _curve = futures_structure_engine(name)
            apply_futures_structure(analysis, _curve)
            analysis["v3_context"] = v3_context_summary(analysis)

            # v5.0: calibrated probability + smart-money proxy + walk-forward statistical risk.
            analysis = v5_enhance_analysis(name, analysis, candles, intraday_candles)

            # v6.1: intelligence fusion — regime + cross-market + data quality.
            analysis = intelligence_fusion_engine(
                name, analysis, candles, intraday_candles, usd, global_impact, political, _curve, weather, disasters
            )
            save_intelligence_feedback(name, analysis)

            # v6.1: long-term forecast uses the enhanced intelligent current state.
            analysis["long_term"] = long_term_forecast(name, candles, analysis)

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

    # v3.3: Early Opportunity runs after live layers are finalized.
    if EARLY_OPPORTUNITY_ENABLED:
        apply_early_opportunity(results)
        for _item in results:
            if _item.get("available"):
                _item["analysis"]["v3_context"] = v3_context_summary(_item["analysis"])

    # v2.7: diagnostica trasparente dei blocchi di ingresso per le migliori 5.
    _diag = [x for x in results if x.get("available") and x.get("analysis",{}).get("setup_direction") in ("LONG","SHORT")]
    _diag.sort(key=lambda x: safe_float(x.get("analysis",{}).get("score"),0) or 0, reverse=True)
    print(f"\n🔬 DIAGNOSTICA ENTRY v{BOT_VERSION}")
    for _it in _diag[:5]:
        _a=_it["analysis"]; _t=_a.get("entry_trigger",{}) or {}; _r=_a.get("risk",{}) or {}; _l=_a.get("level_to_level",{}) or {}
        print(f"   {_it['name']}: {_a.get('setup_direction')} | score={_a.get('score',0):.1f} q={_a.get('quality',0):.1f} conf={_a.get('confidence',0):.1f} prob={_a.get('entry_probability',0):.1f}% | L2L={_l.get('score',0):.1f} {_l.get('behaviour','-')} gate={_l.get('gate')} | MTF={_a.get('structural_same',0)} | fast_opp={_a.get('fast_conflicts',0)} | risk={_r.get('mode')} mq={_r.get('market_quality',0):.1f} rb={safe_float(_a.get('risk_benefit',{}).get('score'),0) or 0:.1f} | trigger={_t.get('kind')} {_t.get('timeframe','-')} {_t.get('score',0):.1f} confirmed={_t.get('confirmed')} | state={_a.get('entry_state')} | regime={(_a.get('market_regime',{}) or {}).get('state','N/D')} | blockers={','.join(_a.get('entry_blockers',[])) or 'NESSUNO'} | warnings={','.join(_a.get('entry_warnings',[])) or 'NESSUNO'}")

    new_long = record_long_term_forecasts(results)
    print(f"🧠 Long-Term Journal: {new_long} nuove previsioni congelate")
    new_predictions, _prediction_log = record_predictions(results)
    print(f"📝 Intraday Journal: {new_predictions} nuovi rilevamenti registrati")

    print("\n🧠 V3 CONTEXT")
    for _it in sorted([x for x in results if x.get("available")], key=lambda x: safe_float(x.get("analysis",{}).get("score"),0) or 0, reverse=True)[:5]:
        _a=_it["analysis"]; _v=_a.get("v3_context",{}) or {}; _p=_a.get("political",{}) or {}; _f=_a.get("futures_structure",{}) or {}
        print(f"   {_it['name']}: EARLY={_v.get('early')} {_v.get('early_direction')} | POL={_p.get('direction')} { _p.get('mechanism','N/D')} { _p.get('horizon','N/D')} | CURVE={_f.get('state')} | REV={_v.get('reversal')}")

    print(f"\n🔭 EARLY OPPORTUNITY ENGINE v{BOT_VERSION}")
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

    # Freeze the morning Top 5 so the evening survey tests the same forecast.
    save_daily_top5_snapshot(ranked, _prediction_log)

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
                "🟡 SEGNALE VALIDO — esecuzione automatica disattivata."
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

    # v3.3: due alert separati e compatti ad ogni esecuzione.
    # Il job esterno deve essere schedulato ogni 15 minuti.
    monitor_message = build_telegram_5m(ranked, best, position_message, position)
    if MONITOR_SEND_FULL:
        send_telegram(monitor_message)
    else:
        print("📡 Internal monitor: Telegram alert periodico DISATTIVATO.")
    maybe_send_session_reports(ranked, best, position_message)
    save_monitor_state(ranked, best, position)

    # Fine giornata: valuta le previsioni maturate e invia il report una sola volta.
    eod_report = v5_daily_report() if (datetime.now(ZoneInfo("Europe/Rome")).hour == EOD_REPORT_HOUR and 0 <= datetime.now(ZoneInfo("Europe/Rome")).minute < 30) else None
    if eod_report:
        send_telegram(eod_report)
        print(eod_report)

    # Separate alert: only for the commodity currently held.
    if position:
        held = next((x for x in results if x.get("name") == position.get("name") and x.get("available")), None)
        if held:
            alert = build_reversal_alert(position, held.get("analysis", {}))
            if alert and EVENT_ALERTS_ENABLED:
                _st = _communication_state()
                _key = f"reversal:{position.get('name')}:{position.get('direction')}"
                _sig = alert.replace("\n", "|")
                if _st.get("last_event_signature", {}).get(_key) != _sig:
                    send_telegram(alert)
                    ev = _st.setdefault("last_event_signature", {}); ev[_key] = _sig
                    _save_communication_state(_st)

    print()
    print("=" * 70)
    print(f"⚠️ v{BOT_VERSION}: analisi quantitativa, non garanzia di profitto. PAPER ONLY.")
    print("=" * 70)


if __name__ == "__main__":
    main()
