import time
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
SIFTING_API_KEY = os.getenv("SIFTING_API_KEY", "").strip()
SIFTING_BASE_URL = os.getenv("SIFTING_BASE_URL", "https://api.sifting.io").rstrip("/")
SIFTING_LIVE_ENABLED = os.getenv("SIFTING_LIVE_ENABLED", "1") == "1"
SIFTING_LIVE_REQUIRED = os.getenv("SIFTING_LIVE_REQUIRED", "0") == "1"
SIFTING_LIVE_MAX_AGE_SECONDS = float(os.getenv("SIFTING_LIVE_MAX_AGE_SECONDS", "30"))
SIFTING_TIMEOUT_SECONDS = float(os.getenv("SIFTING_TIMEOUT_SECONDS", "8"))
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "8002086130")

BASE_URL = "https://api.twelvedata.com/time_series"
NEWS_URL = "https://newsapi.org/v2/everything"

POSITION_FILE = "position.json"
DIRECTION_STATE_FILE = "commodities_direction_state.json"
PREDICTION_LOG_FILE = "commodities_prediction_log.json"
DAILY_REPORT_FILE = "commodities_daily_report_state.json"
PREDICTION_HORIZON_HOURS = int(os.getenv("PREDICTION_HORIZON_HOURS", "6"))
INTRADAY_ALERT_MIN_SCORE = float(os.getenv("INTRADAY_ALERT_MIN_SCORE", "70"))
PERFORMANCE_RETENTION_DAYS = int(os.getenv("PERFORMANCE_RETENTION_DAYS", "90"))
REGIME_ENABLED = os.getenv("REGIME_ENABLED", "1") == "1"
PRICE_ACTION_ENABLED = os.getenv("PRICE_ACTION_ENABLED", "1") == "1"
CANDLE_ENGINE_ENABLED = os.getenv("CANDLE_ENGINE_ENABLED", "1") == "1"
ADAPTIVE_RISK_ENABLED = os.getenv("ADAPTIVE_RISK_ENABLED", "1") == "1"
EXIT_ENGINE_ENABLED = os.getenv("EXIT_ENGINE_ENABLED", "1") == "1"
EOD_REPORT_HOUR = int(os.getenv("EOD_REPORT_HOUR", "21"))

# v5.0 — COMMODITY KNOWLEDGE + PRE-USA TIMING ENGINE
# Source-derived principles are encoded as bounded, explainable context.
# They refine ranking/timing but never bypass the existing safety/entry policy.
KNOWLEDGE_ENGINE_V5_ENABLED = os.getenv("KNOWLEDGE_ENGINE_V5_ENABLED", "1") == "1"
PRE_USA_ENGINE_ENABLED = os.getenv("PRE_USA_ENGINE_ENABLED", "1") == "1"
PRE_USA_REPORT_HOUR = int(os.getenv("PRE_USA_REPORT_HOUR", "14"))
PRE_USA_REPORT_MINUTE = int(os.getenv("PRE_USA_REPORT_MINUTE", "30"))
PRE_USA_WINDOW_MINUTES = int(os.getenv("PRE_USA_WINDOW_MINUTES", "90"))
US_OPEN_CONFIRM_MINUTES = int(os.getenv("US_OPEN_CONFIRM_MINUTES", "60"))
KNOWLEDGE_SCORE_WEIGHT = float(os.getenv("KNOWLEDGE_SCORE_WEIGHT", "0.08"))
KNOWLEDGE_DELTA_CAP = float(os.getenv("KNOWLEDGE_DELTA_CAP", "4.0"))


# v3.0 — multi-horizon research and market-structure layer.
# Real/demo order execution remains OFF by default.
BOT_VERSION = "5.3.10-GAGARIN-LIVE-DATA-SETUP-CANDIDATE"
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

# v4.1 — Market Intelligence / PricePedia-style four-lens layer.
# The layer is analytical only: it never executes real orders and it never
# invents unavailable inventory/COT/futures data. Missing optional sources are
# represented as neutral / unavailable context.
MARKET_INTELLIGENCE_ENABLED = os.getenv("MARKET_INTELLIGENCE_ENABLED", "1") == "1"
MARKET_INTELLIGENCE_MODE = os.getenv("MARKET_INTELLIGENCE_MODE", "PRICEPEDIA_STYLE")
MARKET_INTELLIGENCE_OPTIONAL_SOURCES = os.getenv("MARKET_INTELLIGENCE_OPTIONAL_SOURCES", "1") == "1"
GEOPOLITICAL_IMPACT_ENABLED = os.getenv("GEOPOLITICAL_IMPACT_ENABLED", "1") == "1"
COMMODITY_FUNDAMENTALS_ENABLED = os.getenv("COMMODITY_FUNDAMENTALS_ENABLED", "1") == "1"
MARKET_REGIME_ENABLED = os.getenv("MARKET_REGIME_ENABLED", "1") == "1"
CROSS_COMMODITY_ANALYSIS_ENABLED = os.getenv("CROSS_COMMODITY_ANALYSIS_ENABLED", "1") == "1"
VOLATILITY_CONTEXT_ENABLED = os.getenv("VOLATILITY_CONTEXT_ENABLED", "1") == "1"
INTELLIGENCE_WEIGHT = float(os.getenv("INTELLIGENCE_WEIGHT", "0.20"))
POLITICAL_IMPACT_WEIGHT = float(os.getenv("POLITICAL_IMPACT_WEIGHT", "0.20"))
GEOPOLITICAL_IMPACT_WEIGHT = float(os.getenv("GEOPOLITICAL_IMPACT_WEIGHT", "0.20"))
FUNDAMENTALS_WEIGHT = float(os.getenv("FUNDAMENTALS_WEIGHT", "0.15"))
MARKET_REGIME_WEIGHT = float(os.getenv("MARKET_REGIME_WEIGHT", "0.10"))
CROSS_COMMODITY_WEIGHT = float(os.getenv("CROSS_COMMODITY_WEIGHT", "0.10"))
FUTURES_STRUCTURE_WEIGHT = float(os.getenv("FUTURES_STRUCTURE_WEIGHT", "0.05"))



# v3.3 — 15-minute smart monitoring. The bot is scheduled externally
# (for example by GitHub Actions cron */15); it does not sleep inside a run.
MONITOR_INTERVAL_MINUTES = int(os.getenv("MONITOR_INTERVAL_MINUTES", "15"))
MONITOR_TOP_N = int(os.getenv("MONITOR_TOP_N", "3"))
MONITOR_SEND_FULL = os.getenv("MONITOR_SEND_FULL", "0") == "1"
TELEGRAM_COMPACT_MODE = os.getenv("TELEGRAM_COMPACT_MODE", "1") == "1"

# v3.6 — Morning / USA / Event Driven communication. Internal analysis can run often,
# but Telegram is intentionally quiet except for scheduled decision points,
# material scenario changes, and the daily statistical report.
COMMUNICATION_MODE = os.getenv("COMMUNICATION_MODE", "MORNING_USA_EVENT")
ON_DEMAND_ONLY = os.getenv("ON_DEMAND_ONLY", "0") == "1"
ON_DEMAND_TELEGRAM_REQUEST = os.getenv("ON_DEMAND_TELEGRAM_REQUEST", "").strip()
ON_DEMAND_TELEGRAM_CHAT_ID = os.getenv("ON_DEMAND_TELEGRAM_CHAT_ID", "").strip()
MORNING_REPORT_HOUR = int(os.getenv("MORNING_REPORT_HOUR", "8"))
MORNING_REPORT_MINUTE = int(os.getenv("MORNING_REPORT_MINUTE", "0"))
USA_REPORT_HOUR = int(os.getenv("USA_REPORT_HOUR", "14"))
USA_REPORT_MINUTE = int(os.getenv("USA_REPORT_MINUTE", "30"))
EOD_REPORT_HOUR = int(os.getenv("EOD_REPORT_HOUR", "21"))
EVENT_ALERTS_ENABLED = os.getenv("EVENT_ALERTS_ENABLED", "1") == "1"
SILENT_INTERNAL_ANALYSIS = os.getenv("SILENT_INTERNAL_ANALYSIS", "1") == "1"
MONITOR_STATE_FILE = "commodities_monitor_state.json"
MIN_ENTRY_PROBABILITY = float(os.getenv("MIN_ENTRY_PROBABILITY", "62"))
MIN_ENTRY_QUALITY = float(os.getenv("MIN_ENTRY_QUALITY", "55"))
MIN_ENTRY_CONFIDENCE = float(os.getenv("MIN_ENTRY_CONFIDENCE", "60"))
MIN_ENTRY_RR = float(os.getenv("MIN_ENTRY_RR", "2.5"))
MIN_ENTRY_RR_TP1 = float(os.getenv("MIN_ENTRY_RR_TP1", "1.5"))
MIN_ENTRY_RR_TP2 = float(os.getenv("MIN_ENTRY_RR_TP2", "2.0"))
MAX_ENTRY_STOP_ATR = float(os.getenv("MAX_ENTRY_STOP_ATR", "2.5"))

# ============================================================
# v5.2-GAGARIN SL/TP 3.0 — ROBUST STRUCTURE + VOLATILITY + CFD EXECUTION
# Technical levels are determined before R/R. ATR is a volatility
# buffer/validation layer, not the target generator.
# ============================================================
SLTP_ENGINE_VERSION = os.getenv("SLTP_ENGINE_VERSION", "3.0-ROBUST-STRUCTURAL-CFD")
SL_STRUCTURE_BUFFER_ATR = float(os.getenv("SL_STRUCTURE_BUFFER_ATR", "0.15"))
SL_ROBUSTNESS_BAND_ATR = float(os.getenv("SL_ROBUSTNESS_BAND_ATR", "0.35"))
SL_EMA_REFERENCE_ENABLED = os.getenv("SL_EMA_REFERENCE_ENABLED", "1") == "1"
SL_MIN_ATR = float(os.getenv("SL_MIN_ATR", "0.80"))
CFD_SPREAD_BUFFER_MULT = float(os.getenv("CFD_SPREAD_BUFFER_MULT", "1.0"))
SL_STRUCTURE_LOOKBACK_15M = int(os.getenv("SL_STRUCTURE_LOOKBACK_15M", "80"))
SL_STRUCTURE_LOOKBACK_1H = int(os.getenv("SL_STRUCTURE_LOOKBACK_1H", "80"))
TP_STRUCTURE_LOOKBACK_15M = int(os.getenv("TP_STRUCTURE_LOOKBACK_15M", "120"))
TP_STRUCTURE_LOOKBACK_1H = int(os.getenv("TP_STRUCTURE_LOOKBACK_1H", "120"))
TP_STRUCTURE_LOOKBACK_4H = int(os.getenv("TP_STRUCTURE_LOOKBACK_4H", "120"))
TP_STRUCTURE_LOOKBACK_DAILY = int(os.getenv("TP_STRUCTURE_LOOKBACK_DAILY", "120"))


# ============================================================
# v4.7 — ENTRY POLICY
# Separa BIAS da ENTRY reale.
# Il motore mantiene il proprio calcolo di direzione, ma
# autorizza un ingresso solo quando la confluenza è sufficiente.
# ============================================================

L2L_STRONG_CONTRARY = float(os.getenv("L2L_STRONG_CONTRARY", "35"))
L2L_WEAK_CONTRARY = float(os.getenv("L2L_WEAK_CONTRARY", "45"))
L2L_CONFIRMED = float(os.getenv("L2L_CONFIRMED", "55"))

QUALITY_HARD_FLOOR = float(os.getenv("QUALITY_HARD_FLOOR", "45"))
CONFIDENCE_HARD_FLOOR = float(os.getenv("CONFIDENCE_HARD_FLOOR", "50"))

TRIGGER_ENTRY_MIN = float(os.getenv("TRIGGER_ENTRY_MIN", "85"))
MTF_ENTRY_MIN = float(os.getenv("MTF_ENTRY_MIN", "80"))

PROBABILITY_ENTRY_MIN = float(
    os.getenv("PROBABILITY_ENTRY_MIN", str(MIN_ENTRY_PROBABILITY))
)
QUALITY_ENTRY_MIN = float(
    os.getenv("QUALITY_ENTRY_MIN", str(MIN_ENTRY_QUALITY))
)
CONFIDENCE_ENTRY_MIN = float(
    os.getenv("CONFIDENCE_ENTRY_MIN", str(MIN_ENTRY_CONFIDENCE))
)
RR_TP1_ENTRY_MIN = float(
    os.getenv("RR_TP1_ENTRY_MIN", str(MIN_ENTRY_RR_TP1))
)
RR_TP2_ENTRY_MIN = float(
    os.getenv("RR_TP2_ENTRY_MIN", str(MIN_ENTRY_RR_TP2))
)


def classify_l2l(score):
    try:
        score = float(score)
    except (TypeError, ValueError):
        score = 50.0

    if score < L2L_STRONG_CONTRARY:
        return "STRONG_CONTRARY"
    if score < L2L_WEAK_CONTRARY:
        return "WEAK_CONTRARY"
    if score >= L2L_CONFIRMED:
        return "CONFIRMED"
    return "NEUTRAL"


def evaluate_entry_policy(
    direction,
    probability,
    quality,
    confidence,
    mtf_score,
    trigger_score,
    l2l_score,
    rr_tp1,
    rr_tp2,
    regime=None,
):
    """
    v4.7:
    - BIAS = direzione del modello
    - ENTRY = autorizzazione effettiva
    - L2L contrario forte = blocco
    - L2L debole/neutro = attesa conferma
    """

    direction = str(direction or "").upper()

    def _num(value, default=0.0):
        try:
            value = float(value)
            return value if math.isfinite(value) else default
        except (TypeError, ValueError):
            return default

    probability = _num(probability)
    quality = _num(quality)
    confidence = _num(confidence)
    mtf_score = _num(mtf_score)
    trigger_score = _num(trigger_score)
    l2l_score = _num(l2l_score, 50.0)
    rr_tp1 = _num(rr_tp1)
    rr_tp2 = _num(rr_tp2)

    l2l_state = classify_l2l(l2l_score)
    blockers = []
    warnings = []

    if direction not in ("LONG", "SHORT"):
        return {
            "policy_version": "4.13",
            "bias": "NEUTRAL",
            "bias_strength": "NONE",
            "entry_status": "NO_ENTRY",
            "entry_label": "🔴 NO ENTRY",
            "entry_allowed": False,
            "l2l_state": l2l_state,
            "l2l_score": l2l_score,
            "quality": quality,
            "confidence": confidence,
            "mtf": mtf_score,
            "trigger": trigger_score,
            "probability": probability,
            "rr_tp1": rr_tp1,
            "rr_tp2": rr_tp2,
            "blockers": ["DIREZIONE NON VALIDA"],
            "warnings": [],
            "regime": regime,
        }

    if probability >= 80 and mtf_score >= 85 and trigger_score >= 85:
        bias_strength = "STRONG"
    elif probability >= PROBABILITY_ENTRY_MIN and mtf_score >= 70:
        bias_strength = "MODERATE"
    else:
        bias_strength = "WEAK"

    # Hard gates
    if probability < PROBABILITY_ENTRY_MIN:
        blockers.append(
            f"PROBABILITÀ {probability:.1f} < {PROBABILITY_ENTRY_MIN:.1f}"
        )

    if quality < QUALITY_HARD_FLOOR:
        blockers.append(
            f"QUALITÀ TROPPO BASSA {quality:.1f} < {QUALITY_HARD_FLOOR:.1f}"
        )

    if confidence < CONFIDENCE_HARD_FLOOR:
        blockers.append(
            f"CONFIDENZA TROPPO BASSA {confidence:.1f} < {CONFIDENCE_HARD_FLOOR:.1f}"
        )

    if mtf_score < MTF_ENTRY_MIN:
        blockers.append(
            f"MTF INSUFFICIENTE {mtf_score:.1f} < {MTF_ENTRY_MIN:.1f}"
        )

    if trigger_score < TRIGGER_ENTRY_MIN:
        blockers.append(
            f"TRIGGER INSUFFICIENTE {trigger_score:.1f} < {TRIGGER_ENTRY_MIN:.1f}"
        )

    # Floating-point tolerance: 1.50 is accepted as 1.50.
    if rr_tp1 + 0.005 < RR_TP1_ENTRY_MIN:
        blockers.append(
            f"RR TP1 INSUFFICIENTE {rr_tp1:.2f} < {RR_TP1_ENTRY_MIN:.2f}"
        )

    if rr_tp2 + 0.005 < RR_TP2_ENTRY_MIN:
        blockers.append(
            f"RR TP2 INSUFFICIENTE {rr_tp2:.2f} < {RR_TP2_ENTRY_MIN:.2f}"
        )

    if l2l_state == "STRONG_CONTRARY":
        blockers.append(f"L2L FORTEMENTE CONTRARIO ({l2l_score:.1f})")

    # Soft conditions
    if QUALITY_HARD_FLOOR <= quality < QUALITY_ENTRY_MIN:
        warnings.append(f"QUALITÀ DA CONFERMARE ({quality:.1f})")

    if CONFIDENCE_HARD_FLOOR <= confidence < CONFIDENCE_ENTRY_MIN:
        warnings.append(f"CONFIDENZA DA CONFERMARE ({confidence:.1f})")

    if l2l_state == "WEAK_CONTRARY":
        warnings.append(f"L2L DEBOLMENTE CONTRARIO ({l2l_score:.1f})")
    elif l2l_state == "NEUTRAL":
        warnings.append(f"L2L NEUTRALE ({l2l_score:.1f})")

    if blockers:
        return {
            "policy_version": "4.13",
            "bias": direction,
            "bias_strength": bias_strength,
            "entry_status": "NO_ENTRY",
            "entry_label": f"🔴 NO ENTRY — BIAS {direction}",
            "entry_allowed": False,
            "l2l_state": l2l_state,
            "l2l_score": l2l_score,
            "quality": quality,
            "confidence": confidence,
            "mtf": mtf_score,
            "trigger": trigger_score,
            "probability": probability,
            "rr_tp1": rr_tp1,
            "rr_tp2": rr_tp2,
            "blockers": blockers,
            "warnings": warnings,
            "regime": regime,
        }

    clean_entry = (
        probability >= PROBABILITY_ENTRY_MIN
        and quality >= QUALITY_ENTRY_MIN
        and confidence >= CONFIDENCE_ENTRY_MIN
        and mtf_score >= MTF_ENTRY_MIN
        and trigger_score >= TRIGGER_ENTRY_MIN
        and rr_tp1 + 0.005 >= RR_TP1_ENTRY_MIN
        and rr_tp2 + 0.005 >= RR_TP2_ENTRY_MIN
        and l2l_state == "CONFIRMED"
    )

    if clean_entry:
        return {
            "policy_version": "4.13",
            "bias": direction,
            "bias_strength": bias_strength,
            "entry_status": "ENTRY_CONFIRMED",
            "entry_label": f"🟢 ENTRY CONFERMATA {direction}",
            "entry_allowed": True,
            "l2l_state": l2l_state,
            "l2l_score": l2l_score,
            "quality": quality,
            "confidence": confidence,
            "mtf": mtf_score,
            "trigger": trigger_score,
            "probability": probability,
            "rr_tp1": rr_tp1,
            "rr_tp2": rr_tp2,
            "blockers": [],
            "warnings": warnings,
            "regime": regime,
        }

    # Nessun hard blocker, ma manca una conferma di confluenza.
    return {
        "policy_version": "4.13",
        "bias": direction,
        "bias_strength": bias_strength,
        "entry_status": "WAIT_CONFIRMATION",
        "entry_label": f"🟡 ASPETTARE CONFERMA {direction}",
        "entry_allowed": False,
        "l2l_state": l2l_state,
        "l2l_score": l2l_score,
        "quality": quality,
        "confidence": confidence,
        "mtf": mtf_score,
        "trigger": trigger_score,
        "probability": probability,
        "rr_tp1": rr_tp1,
        "rr_tp2": rr_tp2,
        "blockers": [],
        "warnings": warnings + ["CONFLUENZA NON ANCORA COMPLETA"],
        "regime": regime,
    }


# v4.5 — Sole 24 Ore Context Engine. Public pages only; no paywalled content
# is bypassed. The module is advisory and can refine, never replace, the quant core.
SOLE24_ENABLED = os.getenv("SOLE24_ENABLED", "1") == "1"
SOLE24_TIMEOUT = int(os.getenv("SOLE24_TIMEOUT", "12"))
SOLE24_CACHE_FILE = os.getenv("SOLE24_CACHE_FILE", "sole24_context_cache.json")
SOLE24_CACHE_HOURS = int(os.getenv("SOLE24_CACHE_HOURS", "3"))
SOLE24_WEIGHT = float(os.getenv("SOLE24_WEIGHT", "0.15"))
SOLE24_URLS = [
    "https://lab24.ilsole24ore.com/guerra-iran-impatto-energia-gas-economia/",
    "https://lab24.ilsole24ore.com/prezzo-benzina/",
    "https://www.agrisole.ilsole24ore.com/home/Mercati",
]

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
    # Metaskill — complete trading course (multiday, risk, SL/TP, inversioni, R/R)
    "https://www.youtube.com/watch?v=ZG4VUC8ilnY",
    # Marco Casario — Commodity Spread Trading / seasonality
    "https://www.youtube.com/watch?v=AEOybn3gfRk",
    "https://www.youtube.com/watch?v=tRcm3sBmvRs",
    # Alpha4All — introduction to commodities and spread trading
    "https://www.youtube.com/watch?v=YREvTwb61ZQ",
    # Alfio Bardolla — commodity spread trading / paper trading / business-like risk discipline
    "https://www.youtube.com/watch?v=lVBjUOJPVjU",
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
    "seasonality": ["seasonality", "stagionalità", "seasonal", "stagionale"],
    "spread_trading": ["spread trading", "spread", "commodity spread", "spread multileg"],
    "contango_backwardation": ["contango", "backwardation"],
    "volume_orderflow": ["volume", "volumi", "volume profile", "order flow", "volumetrico"],
    "wyckoff": ["wyckoff", "accumulation", "distribution", "markup", "markdown", "effort vs result"],
    "chart_patterns": [
        "double top", "double bottom", "head and shoulders", "head & shoulders",
        "cup and handle", "triangle", "wedge", "flag", "pennant", "rectangle",
        "ascending triangle", "descending triangle", "symmetrical triangle",
    ],
    "backtesting": ["backtest", "backtesting", "test storico", "testing"],
    "mechanical_rules": ["mechanical", "rule-based", "regole", "replicable", "replicabile"],
    "position_sizing": ["position sizing", "size della posizione", "dimensionamento", "risk per trade"],
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
    # Precious / industrial metals
    "Oro": "XAU/USD",
    "Argento": "XAG/USD",
    "Rame": "COPPER/USD",
    "Platino": "XPT/USD",
    "Palladio": "XPD/USD",
    # Energy
    "Petrolio WTI": "WTI/USD",
    "Petrolio Brent": "BRN/USD",
    "Benzina RBOB": "RB/USD",
    "Heating Oil": "HOIL/USD",
    "Gas Naturale": "NATGAS/USD",
    # Agriculture / food / soft commodities
    "Grano": "WHEAT/USD",
    "Mais": "CORN/USD",
    "Soia": "SOYBEAN/USD",
    "Riso": "RICE/USD",
    "Zucchero": "SUGAR/USD",
    "Cacao": "COCOA/USD",
    "Caffè": "COFFEE/USD",
    "Cotone": "COTTON/USD",
    # Livestock
    "Bovini vivi": "CATTLE/USD",
    "Feeder Cattle": "FEEDC/USD",
    "Maiali magri": "HOGS/USD",
}


# ============================================================
# v4.6 — SIFTINGIO LIVE PRICE ENGINE
# REST top-of-book quote: BID / ASK / timestamp.
# SiftingIO is a reference/aggregated market-data feed, not a broker.
# ============================================================
SIFTING_COMMODITY_SYMBOLS = {
    "Oro": "XAUUSD",
    "Argento": "XAGUSD",
    "Platino": "XPTUSD",
    "Palladio": "XPDUSD",
    "Petrolio WTI": "WTIUSD",
    "Petrolio Brent": "UKOUSD",
    "Benzina RBOB": "RBUSD",
    "Gas Naturale": "NATGAS",
    "Heating Oil": "HOILUSD",
    "Rame": "COPPERUSD",
    "Alluminio": "XALUSD",
    "Nichel": "XNIUSD",
    "Zinco": "XZNUSD",
    "Grano": "WHEATUSD",
    "Mais": "CORNUSD",
    "Soia": "SOYBUSD",
    "Riso": "RICEUSD",
    "Olio di soia": "SBOILUSD",
    "Caffè": "COFFEEUSD",
    "Cacao": "COCOAUSD",
    "Zucchero": "SUGARUSD",
    "Cotone": "COTTONUSD",
    "Bovini vivi": "CATTLEUSD",
    "Maiali magri": "HOGSUSD",
    "Feeder Cattle": "FEEDCUSD",
}


def get_sifting_live_quote(name, symbol=None):
    """Return the latest SiftingIO top-of-book quote for a commodity.

    Returns a normalized dict with bid/ask/mid/spread/timestamp/provider.
    A stale or malformed quote is rejected instead of being silently used.
    """
    if not SIFTING_LIVE_ENABLED:
        return None
    if not SIFTING_API_KEY:
        return None

    sifting_symbol = SIFTING_COMMODITY_SYMBOLS.get(name)
    if not sifting_symbol:
        return None

    # Per-cycle/in-process cache: never request the same quote twice within the TTL.
    now = time.time()
    cached = SIFTING_QUOTE_CACHE.get(sifting_symbol)
    if cached and now - cached.get("cached_at", 0) <= SIFTING_CACHE_TTL_SECONDS:
        return dict(cached.get("quote") or {})

    url = f"{SIFTING_BASE_URL}/v1/last/quote/commodities/{sifting_symbol}"
    headers = {
        "X-API-Key": SIFTING_API_KEY,
        "Accept": "application/json",
        "User-Agent": "CommoditiesBot/4.6",
    }

    response = requests.get(url, headers=headers, timeout=SIFTING_TIMEOUT_SECONDS)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise RuntimeError("SiftingIO risposta non valida")

    bid = safe_float(data.get("b"))
    ask = safe_float(data.get("a"))
    timestamp_ms = safe_float(data.get("t"))
    if bid is None and ask is None:
        raise RuntimeError(f"SiftingIO {sifting_symbol}: BID/ASK mancanti")

    if bid is not None and bid <= 0:
        bid = None
    if ask is not None and ask <= 0:
        ask = None

    if bid is None and ask is None:
        raise RuntimeError(f"SiftingIO {sifting_symbol}: quotazione non positiva")

    if bid is not None and ask is not None and ask < bid:
        raise RuntimeError(f"SiftingIO {sifting_symbol}: ASK < BID")

    now_ms = datetime.now(timezone.utc).timestamp() * 1000.0
    age_seconds = None
    if timestamp_ms is not None and timestamp_ms > 0:
        age_seconds = max(0.0, (now_ms - timestamp_ms) / 1000.0)
        if age_seconds > SIFTING_LIVE_MAX_AGE_SECONDS:
            raise RuntimeError(
                f"SiftingIO {sifting_symbol}: dato vecchio {age_seconds:.1f}s "
                f"> soglia {SIFTING_LIVE_MAX_AGE_SECONDS:.1f}s"
            )

    if bid is not None and ask is not None:
        mid = (bid + ask) / 2.0
        spread = ask - bid
    else:
        mid = bid if bid is not None else ask
        spread = None

    quote = {
        "provider": "SIFTINGIO",
        "symbol": sifting_symbol,
        "bid": bid,
        "ask": ask,
        "mid": mid,
        "spread": spread,
        "timestamp_ms": timestamp_ms,
        "age_seconds": age_seconds,
    }
    SIFTING_QUOTE_CACHE[sifting_symbol] = {"cached_at": now, "quote": dict(quote)}
    return quote


def apply_sifting_live_price(analysis, name):
    """Replace analytical candle price with the current SiftingIO quote.

    LONG entries use ASK, SHORT entries use BID, and neutral/WAIT uses MID.
    The historical candles remain untouched: they continue to drive ATR and
    structure, while the current entry reference is the live quote.
    """
    if not SIFTING_LIVE_ENABLED:
        analysis["live_price_status"] = "DISABLED"
        return analysis

    try:
        quote = get_sifting_live_quote(name, analysis.get("symbol"))
        if not quote:
            analysis["live_price_status"] = "UNAVAILABLE"
            if SIFTING_LIVE_REQUIRED:
                raise RuntimeError("SiftingIO live price non disponibile")
            return analysis

        direction = str(
            analysis.get("setup_direction")
            or analysis.get("signal")
            or analysis.get("model_signal")
            or ""
        ).upper()

        if direction == "LONG" and quote.get("ask") is not None:
            execution_price = quote["ask"]
            execution_side = "ASK"
        elif direction == "SHORT" and quote.get("bid") is not None:
            execution_price = quote["bid"]
            execution_side = "BID"
        else:
            execution_price = quote.get("mid")
            execution_side = "MID"

        if execution_price is None or execution_price <= 0:
            raise RuntimeError("SiftingIO prezzo live non valido")

        old_price = safe_float(analysis.get("price"))
        analysis["historical_price"] = old_price
        analysis["price"] = _price_round(execution_price)
        analysis["entry"] = _price_round(execution_price)
        analysis["live_price"] = _price_round(execution_price)
        analysis["live_price_bid"] = quote.get("bid")
        analysis["live_price_ask"] = quote.get("ask")
        analysis["live_price_mid"] = quote.get("mid")
        analysis["live_price_spread"] = quote.get("spread")
        analysis["live_price_timestamp_ms"] = quote.get("timestamp_ms")
        analysis["live_price_age_seconds"] = quote.get("age_seconds")
        analysis["live_price_provider"] = quote.get("provider")
        analysis["live_price_symbol"] = quote.get("symbol")
        analysis["live_price_side"] = execution_side
        analysis["live_price_status"] = "LIVE"

        return analysis

    except Exception as exc:
        analysis["live_price_status"] = "ERROR"
        analysis["live_price_error"] = str(exc)
        if SIFTING_LIVE_REQUIRED:
            raise
        print(f"   ⚠️ SiftingIO LIVE {name}: {exc}")
        return analysis


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


def educational_methodology_engine(knowledge):
    """Summarizes the educational methods found in public sources.

    This layer is deliberately descriptive: it never creates a trade direction.
    It can only provide a small, capped validation bonus to the existing model.
    """
    profile = (knowledge or {}).get("profile", {}) or {}
    def c(name):
        return float(profile.get(name, 0) or 0)

    groups = {
        "technical_structure": c("trend") + c("structure") + c("support_resistance") + c("breakout") + c("pullback"),
        "risk": c("risk") + c("position_sizing"),
        "commodity": c("seasonality") + c("spread_trading") + c("contango_backwardation") + c("fundamental"),
        "systematic": c("backtesting") + c("mechanical_rules"),
        "flow": c("volume_orderflow") + c("wyckoff"),
        "patterns": c("chart_patterns") + c("candlestick"),
    }
    total = sum(groups.values())
    if total <= 0:
        return {"score": 0.0, "label": "NO_TEXT", "groups": groups, "delta": 0.0}

    # Normalize each group independently so one long transcript cannot dominate.
    normalized = {k: min(100.0, v / max(1.0, total) * 600.0) for k, v in groups.items()}
    score = (
        normalized["technical_structure"] * 0.24 +
        normalized["risk"] * 0.22 +
        normalized["commodity"] * 0.20 +
        normalized["systematic"] * 0.16 +
        normalized["flow"] * 0.10 +
        normalized["patterns"] * 0.08
    )
    if score >= 70:
        label = "FORTE"
    elif score >= 50:
        label = "BUONA"
    elif score >= 30:
        label = "MISTA"
    else:
        label = "DEBOLE"

    # Educational material may refine validation only; it cannot override Safety Policy.
    delta = clamp((score - 50.0) / 20.0, -1.5, 1.5)
    return {
        "score": round(score, 1),
        "label": label,
        "groups": {k: round(v, 1) for k, v in normalized.items()},
        "delta": round(delta, 2),
    }


def knowledge_bias_for_setup(knowledge, direction, analysis):
    """Small, capped educational prior. Market data always dominates."""
    profile = (knowledge or {}).get("profile", {})
    if not profile:
        return 0.0
    total = max(1, sum(profile.values()))
    # Knowledge increases validation quality rather than inventing a direction.
    method = educational_methodology_engine(knowledge)
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



def _prediction_pivots(rows, field, lookback=80):
    """Small deterministic pivot extractor used only by the v5.3 prediction layer."""
    data = rows if isinstance(rows, list) else []
    data = data[-lookback:]
    if len(data) < 7:
        return []
    out = []
    for i in range(2, len(data)-2):
        r = data[i] if isinstance(data[i], dict) else {}
        v = safe_float(r.get(field))
        if v is None:
            continue
        neigh=[]
        for j in (i-2,i-1,i+1,i+2):
            rr=data[j] if isinstance(data[j],dict) else {}
            x=safe_float(rr.get(field))
            if x is not None: neigh.append(x)
        if len(neigh)==4 and (all(v <= x for x in neigh) if field=='low' else all(v >= x for x in neigh)):
            out.append((i,v))
    return out


def _prediction_trendline(rows, direction):
    """Estimate whether the recent swing-line geometry agrees with direction."""
    if direction not in ('LONG','SHORT'):
        return {'state':'N/D','score':50.0,'touches':0,'reason':'NESSUNA DIREZIONE'}
    lows=_prediction_pivots(rows,'low')
    highs=_prediction_pivots(rows,'high')
    pts=lows if direction=='LONG' else highs
    if len(pts)<2:
        return {'state':'NON_CONFERMATA','score':50.0,'touches':len(pts),'reason':'PUNTI INSUFFICIENTI'}
    (i1,v1),(i2,v2)=pts[-2],pts[-1]
    slope=v2-v1
    ok=slope>0 if direction=='LONG' else slope<0
    score=72.0 if ok else 35.0
    return {'state':'CONFERMATA' if ok else 'CONTRARIA','score':score,'touches':len(pts),'slope':round(slope,8),
            'reason':'SWING LINE COERENTE' if ok else 'SWING LINE CONTRARIA'}


def _prediction_structure(rows, direction):
    """Classify recent HH/HL or LH/LL structure without forecasting from labels alone."""
    if direction not in ('LONG','SHORT'):
        return {'state':'N/D','score':50.0,'detail':'NONE'}
    highs=_prediction_pivots(rows,'high')[-4:]
    lows=_prediction_pivots(rows,'low')[-4:]
    if len(highs)<2 or len(lows)<2:
        return {'state':'INCOMPLETA','score':45.0,'detail':'PIVOT INSUFFICIENTI'}
    h_ok=highs[-1][1] > highs[-2][1]
    l_ok=lows[-1][1] > lows[-2][1]
    if direction=='LONG':
        ok=h_ok and l_ok
        detail='HH+HL' if ok else ('HH senza HL' if h_ok else 'STRUTTURA MISTA')
    else:
        h_ok=highs[-1][1] < highs[-2][1]
        l_ok=lows[-1][1] < lows[-2][1]
        ok=h_ok and l_ok
        detail='LH+LL' if ok else ('LL senza LH' if l_ok else 'STRUTTURA MISTA')
    return {'state':'COERENTE' if ok else 'MISTA','score':78.0 if ok else 42.0,'detail':detail}


def _prediction_123(rows, direction):
    """Conservative 1-2-3 detector following the source-derived pivot/confirmation logic."""
    if direction not in ('LONG','SHORT'):
        return {'state':'N/D','confirmed':False,'score':50.0}
    highs=_prediction_pivots(rows,'high')
    lows=_prediction_pivots(rows,'low')
    if direction=='LONG' and len(lows)>=2 and len(highs)>=1:
        p1=lows[-2][1]; p3=lows[-1][1]; p2=highs[-1][1]
        valid=p3 >= p1
        # Confirmation requires a break above pivot 2.
        last=safe_float((rows or [])[-1].get('close')) if rows else None
        confirmed=bool(valid and last is not None and last > p2)
        return {'state':'CONFERMATO' if confirmed else ('FORMATO' if valid else 'INVALIDO'),
                'confirmed':confirmed,'score':88.0 if confirmed else (62.0 if valid else 25.0),
                'p1':p1,'p2':p2,'p3':p3,'confirmation':p2}
    if direction=='SHORT' and len(highs)>=2 and len(lows)>=1:
        p1=highs[-2][1]; p3=highs[-1][1]; p2=lows[-1][1]
        valid=p3 <= p1
        last=safe_float((rows or [])[-1].get('close')) if rows else None
        confirmed=bool(valid and last is not None and last < p2)
        return {'state':'CONFERMATO' if confirmed else ('FORMATO' if valid else 'INVALIDO'),
                'confirmed':confirmed,'score':88.0 if confirmed else (62.0 if valid else 25.0),
                'p1':p1,'p2':p2,'p3':p3,'confirmation':p2}
    return {'state':'NON RILEVATO','confirmed':False,'score':50.0}


def prediction_engine_v53(analysis):
    """Prediction chain v5.3: regime → structure → zone → pattern → confirmation → space.

    It produces a scenario state, not a guaranteed price forecast. A pattern alone
    never authorizes an entry. The 1-2-3 confirmation logic follows the referenced
    FBS structure: pivots 1/2/3 and confirmation at pivot 2.
    """
    a=analysis if isinstance(analysis,dict) else {}
    direction=a.get('setup_direction') or a.get('model_signal') or 'NONE'
    if direction not in ('LONG','SHORT'):
        return {'state':'SCENARIO_NEUTRO','direction':'NONE','score':50.0,'operational':False,'reasons':['NESSUNA DIREZIONE']}
    pts=a.get('pattern_timeframes') or {}
    rows15=pts.get('15m') or pts.get('1H') or []
    rows5=pts.get('5m') or rows15
    regime=market_regime_engine(a)
    regime_state=str(regime.get('state','UNKNOWN')).upper()
    structure=_prediction_structure(rows15,direction)
    trendline=_prediction_trendline(rows15,direction)
    pa=a.get('price_action') or price_action_context_engine(a)
    l2l=a.get('level_to_level') or {}
    location_score=safe_float(l2l.get('score'),50) or 50
    breakout=bool(l2l.get('breakout'))
    retest=bool(l2l.get('retest')) and not bool(l2l.get('fakeout'))
    trigger=a.get('entry_trigger') or {}
    trigger_confirmed=bool(trigger.get('confirmed')) or retest
    patterns=pa.get('patterns',[]) if isinstance(pa,dict) else []
    pattern_score=safe_float(pa.get('score'),50) if isinstance(pa,dict) else 50
    pattern_score=clamp(50+pattern_score*12,0,100)
    chart=_prediction_123(rows5,direction)
    mtf=a.get('timeframes') or {}
    mtf_dirs=[(mtf.get(tf) or {}).get('direction') for tf in ('4H','1H','15m')]
    mtf_alignment=sum(x==direction for x in mtf_dirs)
    mtf_score=35+21*mtf_alignment
    # Real space comes from the already-calculated structural SL/TP plan.
    ar=a.get('adaptive_risk') or {}
    rr1=safe_float(ar.get('rr_tp1'),0) or 0
    rr2=safe_float(ar.get('rr_tp2'),0) or 0
    rr3=safe_float(ar.get('rr_tp3'),0) or 0
    space_score=clamp((min(rr1/1.5,1)*25)+(min(rr2/2.0,1)*25)+(min(rr3/2.5,1)*30),0,80)
    if ar.get('theoretical_only'): space_score=min(space_score,30)
    score=clamp(
        safe_float(regime.get('score'),50)*0.12 + structure['score']*0.16 + trendline['score']*0.08 +
        location_score*0.12 + pattern_score*0.10 + mtf_score*0.12 +
        (88 if trigger_confirmed else 35)*0.10 + space_score*0.20,
        0,100)
    reasons=[]
    if regime_state in ('SHOCK','UNKNOWN'): reasons.append('REGIME NON CONFERMATO')
    if structure['state']!='COERENTE': reasons.append('STRUTTURA DA CONFERMARE')
    if trendline['state']!='CONFERMATA': reasons.append('TRENDLINE DA CONFERMARE')
    if not breakout and not retest: reasons.append('BREAKOUT/RETEST NON CONFERMATO')
    if not trigger_confirmed: reasons.append('TRIGGER NON CONFERMATO')
    if rr1 < MIN_ENTRY_RR_TP1: reasons.append('SPAZIO TP1 INSUFFICIENTE')
    if rr2 < MIN_ENTRY_RR_TP2: reasons.append('SPAZIO TP2 INSUFFICIENTE')
    if rr3 < MIN_ENTRY_RR: reasons.append('SPAZIO TP3 INSUFFICIENTE')
    hard_ok=(regime_state not in ('SHOCK','UNKNOWN') and structure['state']=='COERENTE' and
             trigger_confirmed and rr1>=MIN_ENTRY_RR_TP1 and rr2>=MIN_ENTRY_RR_TP2 and rr3>=MIN_ENTRY_RR)
    state='PREVISIONE_OPERATIVA' if hard_ok else ('PREVISIONE_IN_FORMAZIONE' if direction in ('LONG','SHORT') else 'SCENARIO_NEUTRO')
    if regime_state=='SHOCK': state='SCENARIO_INVALIDATO'

    # Diagnostic decomposition: this is DISPLAY/ANALYSIS ONLY. It does not
    # relax or modify any entry gate. It tells us exactly which prediction
    # component is preventing a setup from becoming operational.
    components = {
        'regime': regime_state not in ('SHOCK','UNKNOWN'),
        'structure': structure.get('state') == 'COERENTE',
        'trendline': trendline.get('state') == 'CONFERMATA',
        'zone': location_score >= 60.0,
        'pattern': pattern_score >= 60.0,
        'breakout_or_retest': bool(breakout or retest),
        'trigger': bool(trigger_confirmed),
        'space_tp1': rr1 >= MIN_ENTRY_RR_TP1,
        'space_tp2': rr2 >= MIN_ENTRY_RR_TP2,
        'space_tp3': rr3 >= MIN_ENTRY_RR,
    }
    missing_components = [k for k,v in components.items() if not v]
    component_labels = {
        'regime':'REGIME','structure':'STRUTTURA','trendline':'TRENDLINE',
        'zone':'ZONA','pattern':'PATTERN','breakout_or_retest':'BREAKOUT/RETEST',
        'trigger':'TRIGGER','space_tp1':'SPAZIO TP1','space_tp2':'SPAZIO TP2',
        'space_tp3':'SPAZIO TP3'
    }
    component_summary = ' | '.join(
        f"{component_labels[k]} {'OK' if components[k] else 'NO'}"
        for k in components
    )
    return {
        'version':'5.3','state':state,'direction':direction,'score':round(score,1),'operational':bool(hard_ok),
        'components': components,
        'missing_components': missing_components,
        'component_summary': component_summary,
        'regime':regime,'structure':structure,'trendline':trendline,'location_score':round(location_score,1),
        'patterns':patterns[:10],'pattern_score':round(pattern_score,1),'chart_123':chart,
        'breakout':breakout,'retest':retest,'trigger_confirmed':trigger_confirmed,
        'mtf_alignment':mtf_alignment,'mtf_score':round(mtf_score,1),
        'rr_tp1':round(rr1,3),'rr_tp2':round(rr2,3),'rr_tp3':round(rr3,3),'space_score':round(space_score,1),
        'reasons':reasons[:10]
    }

def prediction_authority_v531(analysis):
    """Canonical v5.3.1 prediction authority for display and entry gating.

    One label is used everywhere: regime/setup/trigger/prediction. The legacy
    trigger is never allowed to override the prediction confirmation layer.
    This is a scenario/confirmation gate, not a claim of guaranteed outcome.
    """
    a = analysis if isinstance(analysis, dict) else {}
    pred = a.get("prediction_v53") if isinstance(a.get("prediction_v53"), dict) else {}
    g = a.get("gagarin") if isinstance(a.get("gagarin"), dict) else {}
    regime_obj = g.get("regime") if isinstance(g.get("regime"), dict) else {}
    setup_obj = g.get("setup") if isinstance(g.get("setup"), dict) else {}
    trigger_obj = g.get("trigger") if isinstance(g.get("trigger"), dict) else {}

    direction = pred.get("direction") or a.get("setup_direction") or a.get("model_signal") or "NONE"
    regime = str(regime_obj.get("state") or pred.get("regime", {}).get("state") or "UNKNOWN").upper()
    setup = str(setup_obj.get("type") or "NONE").upper()
    prediction_trigger = bool(pred.get("trigger_confirmed"))
    gagarin_trigger = bool(trigger_obj.get("confirmed"))
    # Both layers must agree. This eliminates the previous "TRIGGER True" vs
    # "TRIGGER NON CONFERMATO" contradiction.
    trigger_confirmed = prediction_trigger and gagarin_trigger
    breakout = bool(pred.get("breakout"))
    retest = bool(pred.get("retest"))
    pstate = str(pred.get("state") or "SCENARIO_NEUTRO").upper()

    reasons = list(pred.get("reasons") or [])
    if not prediction_trigger:
        reasons.append("TRIGGER PREDICTION NON CONFERMATO")
    if prediction_trigger and not gagarin_trigger:
        reasons.append("TRIGGER GAGARIN NON CONFERMATO")
    if regime in {"SHOCK", "UNKNOWN"}:
        reasons.append(f"REGIME {regime}")

    # Operational authorization is intentionally stricter than the scenario
    # state: the existing Gagarin policy, SL/TP and thresholds must also pass.
    g_allowed = bool(a.get("operational_entry_allowed"))
    operational = bool(pred.get("operational")) and g_allowed and trigger_confirmed
    if operational:
        state = "PREVISIONE_OPERATIVA"
    elif pstate == "SCENARIO_INVALIDATO" or regime == "SHOCK":
        state = "SCENARIO_INVALIDATO"
    elif direction in ("LONG", "SHORT"):
        state = "PREVISIONE_IN_FORMAZIONE"
    else:
        state = "SCENARIO_NEUTRO"

    # Keep ordering and values visible for diagnostics without manufacturing
    # targets or changing any existing entry thresholds.
    return {
        "version": "5.3.1",
        "direction": direction,
        "regime": regime,
        "setup": setup,
        "breakout": breakout,
        "retest": retest,
        "trigger_confirmed": trigger_confirmed,
        "prediction_trigger_confirmed": prediction_trigger,
        "gagarin_trigger_confirmed": gagarin_trigger,
        "state": state,
        "operational": operational,
        "score": safe_float(pred.get("score"), 0.0) or 0.0,
        "structure": (pred.get("structure") or {}).get("detail", "N/D"),
        "chart_123": (pred.get("chart_123") or {}).get("state", "N/D"),
        "space_score": safe_float(pred.get("space_score"), 0.0) or 0.0,
        "rr_tp1": safe_float(pred.get("rr_tp1"), 0.0) or 0.0,
        "rr_tp2": safe_float(pred.get("rr_tp2"), 0.0) or 0.0,
        "rr_tp3": safe_float(pred.get("rr_tp3"), 0.0) or 0.0,
        "reasons": list(dict.fromkeys(str(x) for x in reasons if x))[:12],
    }


def adaptive_risk_levels(analysis, candles, direction):
    """SL/TP Engine 3.0 — structural invalidation, volatility/robustness validation and CFD execution.

    Structural levels determine the stop; ATR only validates breathing room and
    rejects structurally distant stops. R/R is a filter, never a target generator.
    """
    if not ADAPTIVE_RISK_ENABLED or direction not in ("LONG", "SHORT") or not candles:
        return {"available": False, "engine_version": SLTP_ENGINE_VERSION}

    price = safe_float(analysis.get("entry"), safe_float(analysis.get("price"), 0.0)) or 0.0
    if price <= 0:
        return {"available": False, "engine_version": SLTP_ENGINE_VERSION, "reason": "NO_ENTRY_PRICE"}
    atr_value = safe_float(analysis.get("atr"), 0.0) or 0.0
    if atr_value <= 0:
        atr_value = atr(candles, 14) or price * 0.01
    if atr_value <= 0:
        return {"available": False, "engine_version": SLTP_ENGINE_VERSION, "reason": "NO_ATR"}

    def rows(obj): return obj if isinstance(obj, list) else []
    def vals(arr, field):
        return [v for r in rows(arr) if isinstance(r, dict)
                for v in [safe_float(r.get(field))] if v is not None and v > 0]
    def pivots(arr, field):
        data = rows(arr)
        if len(data) < 5: return []
        out = []
        for i in range(2, len(data) - 2):
            r = data[i] if isinstance(data[i], dict) else {}
            v = safe_float(r.get(field))
            if v is None: continue
            neigh = []
            for j in (i-2, i-1, i+1, i+2):
                rr = data[j] if isinstance(data[j], dict) else {}
                x = safe_float(rr.get(field))
                if x is not None: neigh.append(x)
            if len(neigh) == 4 and (all(v <= x for x in neigh) if field == "low" else all(v >= x for x in neigh)):
                out.append(v)
        return out
    def cluster(values, tolerance):
        values = sorted(set(round(float(x), 8) for x in values if x is not None and x > 0))
        if not values: return []
        groups = [[values[0]]]
        for v in values[1:]:
            center = sum(groups[-1]) / len(groups[-1])
            if abs(v - center) <= tolerance: groups[-1].append(v)
            else: groups.append([v])
        return [sum(g) / len(g) for g in groups]

    pattern = analysis.get("pattern_timeframes") or {}
    t5 = rows(pattern.get("5m"))[-120:]
    t15 = rows(pattern.get("15m"))[-120:]
    t1h = rows(pattern.get("1H") or analysis.get("intraday_candles"))[-120:]
    t4h = rows(pattern.get("4H"))[-TP_STRUCTURE_LOOKBACK_4H:]
    td = rows(candles)[-TP_STRUCTURE_LOOKBACK_DAILY:]

    l2l = analysis.get("level_to_level") or {}
    support = safe_float(l2l.get("support"))
    resistance = safe_float(l2l.get("resistance"))
    vp = analysis.get("volume_profile") or {}
    avwap = analysis.get("anchored_vwap") or analysis.get("avwap") or {}
    avwap_value = safe_float(avwap.get("value")) if isinstance(avwap, dict) else safe_float(avwap)
    poc, vah, val = safe_float(vp.get("poc")), safe_float(vp.get("vah")), safe_float(vp.get("val"))
    # EMA is a reference/validation layer, never the sole invalidation level.
    ema_refs = []
    if SL_EMA_REFERENCE_ENABLED:
        for tf, arr in (("15m", t15), ("1H", t1h)):
            closes = vals(arr, "close")
            if len(closes) >= 50:
                ema50 = ema(closes, 50) if 'ema' in globals() else None
                if ema50 is not None:
                    ema_refs.append((tf, "EMA50", float(ema50)))
    spread = safe_float(analysis.get("live_price_spread"), 0.0) or 0.0
    min_stop_distance = max(SL_MIN_ATR * atr_value, 2.0 * spread)

    sl_candidates = []
    sl_structural_valid = True
    if direction == "LONG":
        for tf, arr in (("5m", t5), ("15m", t15), ("1H", t1h)):
            sl_candidates += [(v, tf, "PIVOT_LOW") for v in pivots(arr, "low") if v < price]
            sl_candidates += [(v, tf, "RECENT_LOW") for v in vals(arr[-30:], "low") if v < price]
        if support is not None and support < price: sl_candidates.append((support, "L2L", "SUPPORT"))
        if val is not None and val < price: sl_candidates.append((val, "VP", "VALUE_LOW"))
        viable = [x for x in sl_candidates
                  if price - x[0] >= min_stop_distance
                  and (price - x[0]) / atr_value <= MAX_ENTRY_STOP_ATR]
        if not viable:
            # Theoretical fallback only: keep SL visible for diagnostics/journaling.
            # It can NEVER authorize an operational entry.
            fallback_distance = min(max(SL_MIN_ATR * atr_value, 1.0 * atr_value), MAX_ENTRY_STOP_ATR * atr_value)
            structural_stop, sl_tf, sl_reason = price - fallback_distance, "FALLBACK", "ATR_THEORETICAL_ONLY"
            technical_stop = structural_stop
            execution_stop = technical_stop - CFD_SPREAD_BUFFER_MULT * spread
            sl_structural_valid = False
        else:
            # Prefer the nearest valid structural invalidation. A small ATR band around
            # that level is considered the robust zone; we never optimize to a single
            # lucky historical value.
            nearest_distance = min(price - x[0] for x in viable)
            robust_viable = [x for x in viable if (price - x[0]) <= nearest_distance + SL_ROBUSTNESS_BAND_ATR * atr_value]
            structural_stop, sl_tf, sl_reason = max(robust_viable, key=lambda x: x[0])
            technical_stop = min(structural_stop - SL_STRUCTURE_BUFFER_ATR * atr_value, price - min_stop_distance)
            execution_stop = technical_stop - CFD_SPREAD_BUFFER_MULT * spread
    else:
        for tf, arr in (("5m", t5), ("15m", t15), ("1H", t1h)):
            sl_candidates += [(v, tf, "PIVOT_HIGH") for v in pivots(arr, "high") if v > price]
            sl_candidates += [(v, tf, "RECENT_HIGH") for v in vals(arr[-30:], "high") if v > price]
        if resistance is not None and resistance > price: sl_candidates.append((resistance, "L2L", "RESISTANCE"))
        if vah is not None and vah > price: sl_candidates.append((vah, "VP", "VALUE_HIGH"))
        viable = [x for x in sl_candidates
                  if x[0] - price >= min_stop_distance
                  and (x[0] - price) / atr_value <= MAX_ENTRY_STOP_ATR]
        if not viable:
            # Theoretical fallback only: keep SL visible for diagnostics/journaling.
            # It can NEVER authorize an operational entry.
            fallback_distance = min(max(SL_MIN_ATR * atr_value, 1.0 * atr_value), MAX_ENTRY_STOP_ATR * atr_value)
            structural_stop, sl_tf, sl_reason = price + fallback_distance, "FALLBACK", "ATR_THEORETICAL_ONLY"
            technical_stop = structural_stop
            execution_stop = technical_stop + CFD_SPREAD_BUFFER_MULT * spread
            sl_structural_valid = False
        else:
            nearest_distance = min(x[0] - price for x in viable)
            robust_viable = [x for x in viable if (x[0] - price) <= nearest_distance + SL_ROBUSTNESS_BAND_ATR * atr_value]
            structural_stop, sl_tf, sl_reason = min(robust_viable, key=lambda x: x[0])
            technical_stop = max(structural_stop + SL_STRUCTURE_BUFFER_ATR * atr_value, price + min_stop_distance)
            execution_stop = technical_stop + CFD_SPREAD_BUFFER_MULT * spread

    stop = _price_round(execution_stop)
    risk_distance = abs(price - stop)
    stop_atr = risk_distance / atr_value if atr_value else 999.0

    raw = []
    if direction == "LONG":
        for tf, arr in (("15m", t15), ("1H", t1h), ("4H", t4h), ("Daily", td)):
            raw += [(v, tf, "PIVOT_HIGH") for v in pivots(arr, "high") if v > price]
            raw += [(v, tf, "STRUCTURAL_HIGH") for v in vals(arr, "high") if v > price]
        for v, tf, reason in ((resistance, "L2L", "RESISTANCE"), (vah, "VP", "VALUE_HIGH"),
                              (poc, "VP", "POC"), (avwap_value, "AVWAP", "AVWAP")):
            if v is not None and v > price: raw.append((v, tf, reason))
        raw = [x for x in raw if x[0] - price >= max(0.35 * atr_value, spread)]
        reverse = False
    else:
        for tf, arr in (("15m", t15), ("1H", t1h), ("4H", t4h), ("Daily", td)):
            raw += [(v, tf, "PIVOT_LOW") for v in pivots(arr, "low") if v < price]
            raw += [(v, tf, "STRUCTURAL_LOW") for v in vals(arr, "low") if v < price]
        for v, tf, reason in ((support, "L2L", "SUPPORT"), (val, "VP", "VALUE_LOW"),
                              (poc, "VP", "POC"), (avwap_value, "AVWAP", "AVWAP")):
            if v is not None and v < price: raw.append((v, tf, reason))
        raw = [x for x in raw if price - x[0] >= max(0.35 * atr_value, spread)]
        reverse = True

    raw.sort(key=lambda x: x[0], reverse=reverse)
    grouped, tol = [], max(0.30 * atr_value, 1e-9)
    for item in raw:
        if not grouped or abs(item[0] - grouped[-1]["price"]) > tol:
            grouped.append({"price": item[0], "sources": [(item[1], item[2])]})
        else:
            grouped[-1]["sources"].append((item[1], item[2]))
    for g in grouped:
        g["timeframes"] = sorted(set(tf for tf, _ in g["sources"]))
        g["htf"] = any(tf in ("4H", "Daily") for tf in g["timeframes"])

    if not grouped:
        # No structural TP exists. Expose a theoretical R-multiple ladder for
        # diagnostics/journaling only; this does NOT make the setup tradable.
        if direction == "LONG":
            tp1, tp2, tp3 = price + 1.5 * risk_distance, price + 2.0 * risk_distance, price + 2.5 * risk_distance
        else:
            tp1, tp2, tp3 = price - 1.5 * risk_distance, price - 2.0 * risk_distance, price - 2.5 * risk_distance
        return {
            "available": True, "valid": False, "engine_version": SLTP_ENGINE_VERSION,
            "reason": "NO_STRUCTURAL_TP", "theoretical_only": True,
            "stop": stop, "tp1": _price_round(tp1), "tp2": _price_round(tp2), "tp3": _price_round(tp3),
            "structural_stop": _price_round(structural_stop), "technical_stop": _price_round(technical_stop),
            "execution_stop": stop, "risk_distance": round(risk_distance, 6), "stop_atr": round(stop_atr, 3),
            "sl_structural_valid": bool(sl_structural_valid),
            "sl_selected": {"price": _price_round(structural_stop), "tf": sl_tf, "reason": sl_reason},
            "sl_candidates": [{"price": _price_round(x[0]), "tf": x[1], "reason": x[2]} for x in sl_candidates[-50:]],
            "tp_candidates": [], "tp_method": "THEORETICAL_R_MULTIPLE_FALLBACK",
            "rr_tp1": 1.5, "rr_tp2": 2.0, "rr_tp3": 2.5
        }

    tp1_obj = grouped[0]
    htf = [g for g in grouped[1:] if g["htf"]]
    tp2_obj = htf[0] if htf else (grouped[1] if len(grouped) > 1 else None)
    tp3_obj = htf[1] if len(htf) > 1 else (grouped[2] if len(grouped) > 2 else None)
    targets = [tp1_obj["price"], tp2_obj["price"] if tp2_obj else None, tp3_obj["price"] if tp3_obj else None]
    targets = [x for x in targets if x is not None]
    targets = sorted(set(round(x, 8) for x in targets), reverse=reverse)
    tp1, tp2, tp3 = (targets + [None, None, None])[:3]

    def rr(x): return abs(x - price) / risk_distance if x is not None and risk_distance > 0 else 0.0
    rr1, rr2, rr3 = rr(tp1), rr(tp2), rr(tp3)
    ordering_ok = all((a < b) if direction == "LONG" else (a > b) for a, b in zip(targets, targets[1:]))
    target_quality = []
    for label, obj, value in (("TP1", tp1_obj, tp1), ("TP2", tp2_obj, tp2), ("TP3", tp3_obj, tp3)):
        if value is not None:
            target_quality.append({
                "target": label, "price": _price_round(value),
                "distance_atr": round(abs(value - price) / atr_value, 3),
                "htf": bool(obj and obj.get("htf")),
                "sources": sorted(set(f"{tf}:{reason}" for tf, reason in (obj or {}).get("sources", [])))[:8]
            })

    return {
        "available": True, "engine_version": SLTP_ENGINE_VERSION,
        "valid": bool(sl_structural_valid and ordering_ok),
        "theoretical_only": bool(not sl_structural_valid),
        "method": "STRUCTURAL INVALIDATION + MICRO/SETUP/HTF + ATR BUFFER + CFD EXECUTION",
        "atr": round(atr_value, 6), "entry": _price_round(price),
        "stop": stop, "tp1": _price_round(tp1 or 0.0), "tp2": _price_round(tp2 or 0.0), "tp3": _price_round(tp3 or 0.0),
        "risk_distance": round(risk_distance, 6), "stop_atr": round(stop_atr, 3),
        "rr_tp1": round(rr1, 3), "rr_tp2": round(rr2, 3), "rr_tp3": round(rr3, 3),
        "structural_stop": _price_round(structural_stop), "technical_stop": _price_round(technical_stop),
        "sl_structural_valid": bool(sl_structural_valid),
        "execution_stop": stop, "spread": round(spread, 8),
        "robustness_band_atr": round(SL_ROBUSTNESS_BAND_ATR, 3),
        "ema_references": [{"tf": tf, "kind": kind, "price": _price_round(v)} for tf, kind, v in ema_refs],
        "sl_selected": {"price": _price_round(structural_stop), "tf": sl_tf, "reason": sl_reason,
                        "distance_atr": round(abs(price - structural_stop) / atr_value, 3)},
        "sl_candidates": [{"price": _price_round(x[0]), "tf": x[1], "reason": x[2]} for x in sl_candidates[-50:]],
        "tp_candidates": [{"price": _price_round(g["price"]), "timeframes": g["timeframes"], "htf": g["htf"],
                           "sources": sorted(set(f"{tf}:{reason}" for tf, reason in g["sources"]))[:8]} for g in grouped[:20]],
        "target_quality": target_quality, "ordering_ok": bool(ordering_ok),
        "stop_filter_pass": bool(stop_atr <= MAX_ENTRY_STOP_ATR + 1e-9),
        "rr_filter": {
            "tp1_pass": rr1 + 0.005 >= MIN_ENTRY_RR_TP1,
            "tp2_pass": rr2 + 0.005 >= MIN_ENTRY_RR_TP2 if tp2 is not None else False,
            "main_pass": rr3 + 0.005 >= MIN_ENTRY_RR if tp3 is not None else False
        },
        "valid": bool(ordering_ok and stop_atr <= MAX_ENTRY_STOP_ATR + 1e-9),
        "selection_reason": {
            "sl": "nearest valid structural invalidation outside minimum noise distance",
            "tp1": "first meaningful structural obstacle",
            "tp2": "next HTF obstacle when available",
            "tp3": "second HTF obstacle/extension when available",
            "rr": "filter only; levels are never moved to manufacture R/R"
        }
    }

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
    rr1_ok = rr1 + 0.005 >= MIN_ENTRY_RR_TP1
    rr2_ok = rr2 + 0.005 >= MIN_ENTRY_RR_TP2
    rr3_ok = rr3 + 1e-9 >= MIN_ENTRY_RR
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

    # v4.1: tiered entry gate. The strict gate remains the preferred path,
    # but an exceptionally strong setup may enter when only soft confirmations
    # (L2L and/or later TP RR) are missing. Safety blockers can never be bypassed.
    soft_missing = sum([not l2l_ok, not rr2_ok, not rr3_ok])
    relaxed_core_ok = (structural_ok and fast_ok and trigger_ok and rr1_ok and
                       stop_ok and prob >= 65 and quality >= 52 and
                       conf >= 55 and not safety_block)
    relaxed_entry_ok = relaxed_core_ok and soft_missing <= 2 and intraday >= 78

    # v4.8 — the Entry Policy is now the final authority for entry permission.
    # It separates directional BIAS from actual ENTRY authorization and prevents
    # a merely strong trend/trigger from being treated as an immediate entry.
    policy_mtf_score = clamp(structural_same / 3 * 75 + fast_same / 2 * 25, 0, 100)
    entry_policy = evaluate_entry_policy(
        direction=d,
        probability=prob,
        quality=quality,
        confidence=conf,
        mtf_score=policy_mtf_score,
        trigger_score=safe_float(trigger.get("score"), 0) or 0,
        l2l_score=l2l_score,
        rr_tp1=rr1,
        rr_tp2=rr2,
        regime=analysis.get("regime"),
    )

    if entry_policy["entry_status"] == "ENTRY_CONFIRMED":
        state, action, signal = "ENTRY_CONFIRMED", ("COMPRA ORA" if d == "LONG" else "VENDI ORA"), d
    elif entry_policy["entry_status"] == "WAIT_CONFIRMATION":
        state, action, signal = "ACTIVE_SETUP", ("LONG — ASPETTARE CONFERMA" if d == "LONG" else "SHORT — ASPETTARE CONFERMA"), "WAIT"
    else:
        state, action, signal = "BLOCKED", "NON ENTRARE", "WAIT"

    if safety_block:
        state, action, signal = "SAFETY_BLOCK", "NON ENTRARE", "WAIT"
    elif entry_policy["entry_status"] == "ENTRY_CONFIRMED":
        state, action, signal = "ENTRY_CONFIRMED", ("COMPRA ORA" if d == "LONG" else "VENDI ORA"), d
    elif entry_policy["entry_status"] == "WAIT_CONFIRMATION":
        state, action, signal = "ACTIVE_SETUP", ("LONG — ASPETTARE CONFERMA" if d == "LONG" else "SHORT — ASPETTARE CONFERMA"), "WAIT"
    else:
        state, action, signal = "BLOCKED", "NON ENTRARE", "WAIT"
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
    analysis["entry_policy"] = entry_policy
    # v4.12: explicit separation between directional BIAS/SETUP and entry permission.
    _risk_mode = str((analysis.get("risk", {}) or {}).get("mode", "")).upper()
    _safety = (
        _risk_mode in ("SHOCK", "ALERT")
        or (analysis.get("reversal", {}) or {}).get("stage") == "CONFIRMED"
    )
    if d in ("LONG", "SHORT"):
        if _safety:
            analysis["setup_status"] = "SETUP_ACTIVE_ENTRY_BLOCKED"
        elif entry_policy.get("entry_status") == "ENTRY_CONFIRMED":
            analysis["setup_status"] = "ENTRY_CONFIRMED"
        elif entry_policy.get("entry_status") == "WAIT_CONFIRMATION":
            analysis["setup_status"] = "SETUP_ACTIVE_WAIT_CONFIRMATION"
        else:
            analysis["setup_status"] = "SETUP_BLOCKED"
    else:
        analysis["setup_status"] = "NO_SETUP"
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
    """Record actionable intraday alerts for later objective evaluation.

    We only journal actionable LONG/SHORT alerts (ENTRARE or ENTRATA POSSIBILE),
    because a WAIT is not a trade prediction. Each record contains the regime,
    trigger and score so the EOD report can identify which setups work.
    """
    log = _json_load(PREDICTION_LOG_FILE, [])
    if not isinstance(log, list): log=[]
    now=datetime.now(timezone.utc)
    cutoff=now-timedelta(days=PERFORMANCE_RETENTION_DAYS)
    new_items=0
    for item in results:
        if not item.get("available"): continue
        a=item.get("analysis",{}) or {}
        action=str(a.get("action_label",""))
        direction=a.get("setup_direction") or a.get("model_signal")
        if direction not in ("LONG","SHORT") or action not in ("COMPRA ORA","VENDI ORA","ENTRATA POSSIBILE"):
            continue
        price=safe_float(a.get("price"))
        if price is None: continue
        trig=a.get("entry_trigger",{}) or {}
        score=safe_float(a.get("intraday_score"),0) or 0
        bucket="80-100" if score>=80 else "70-79"
        # One alert per commodity/direction/trigger/15-minute cycle.
        cycle=now.replace(minute=(now.minute//15)*15,second=0,microsecond=0).isoformat()
        rec={
            "id":f"{item['name']}|{cycle}|{direction}|{trig.get('kind','SETUP')}",
            "created_at":now.isoformat(),"name":item["name"],"symbol":item["symbol"],
            "direction":direction,"action":action,"price":price,
            "entry":safe_float(a.get("entry")),"stop":safe_float(a.get("stop")),
            "tp1":safe_float(a.get("tp1")),"tp2":safe_float(a.get("tp2")),
            "tp3":safe_float(a.get("tp3")),"atr":safe_float(a.get("atr")) or 0.0,
            "score":score,"score_bucket":bucket,"probability":safe_float(a.get("entry_probability"),0) or 0,
            "confidence":safe_float(a.get("confidence"),0) or 0,"quality":safe_float(a.get("quality"),0) or 0,
            "setup":trig.get("kind") or a.get("entry_method","N/D"),"trigger_tf":trig.get("timeframe","N/D"),
            "regime":(a.get("market_regime",{}) or {}).get("state","N/D"),
            "status":"PENDING"
        }
        if not any(x.get("id")==rec["id"] for x in log):
            log.append(rec); new_items+=1
    log=[x for x in log if x.get("created_at","")>=cutoff.isoformat()]
    _json_save(PREDICTION_LOG_FILE,log)
    return new_items,log

def _future_candles_for_prediction(prediction):
    created=datetime.fromisoformat(prediction["created_at"].replace("Z","+00:00"))
    if datetime.now(timezone.utc) < created+timedelta(hours=PREDICTION_HORIZON_HOURS): return []
    try: rows=get_data(prediction["symbol"],"1h",1200)
    except Exception: return []
    end=created+timedelta(hours=PREDICTION_HORIZON_HOURS)
    out=[]
    for row in rows:
        try: dt=datetime.fromisoformat(str(row["datetime"]).replace("Z","+00:00"))
        except Exception: continue
        if created < dt <= end: out.append(row)
    return out

def evaluate_prediction(prediction,future):
    if not future: return None
    p=safe_float(prediction.get("price")); direction=prediction.get("direction","WAIT")
    if p is None or direction not in ("LONG","SHORT"): return None
    sl=safe_float(prediction.get("stop")); tp1=safe_float(prediction.get("tp1")); close_end=safe_float(future[-1].get("close"))
    if close_end is None: return None
    first_hit="NONE"
    for c in future:
        hi,lo=safe_float(c.get("high")),safe_float(c.get("low"))
        if hi is None or lo is None: continue
        hit_tp=tp1 is not None and (hi>=tp1 if direction=="LONG" else lo<=tp1)
        hit_sl=sl is not None and (lo<=sl if direction=="LONG" else hi>=sl)
        if hit_tp and hit_sl: first_hit="AMBIGUO"; break
        if hit_tp: first_hit="TP1"; break
        if hit_sl: first_hit="SL"; break
    close_correct=close_end>p if direction=="LONG" else close_end<p
    verdict="CORRETTA" if first_hit=="TP1" or (first_hit=="NONE" and close_correct) else "ERRATA"
    if first_hit=="AMBIGUO": verdict="AMBIGUA"
    return {"verdict":verdict,"first_hit":first_hit,"close_end":close_end,
            "move_pct":(close_end/p-1)*100,"evaluated_at":datetime.now(timezone.utc).isoformat()}

def run_end_of_day_test(force=False):
    log=_json_load(PREDICTION_LOG_FILE,[])
    if not isinstance(log,list) or not log: return None
    local_now=datetime.now(ZoneInfo("Europe/Rome"))
    if not force and local_now.hour<EOD_REPORT_HOUR: return None
    changed=False
    for pred in log:
        if pred.get("status")!="PENDING": continue
        result=evaluate_prediction(pred,_future_candles_for_prediction(pred))
        if result:
            pred.update(result); pred["status"]="EVALUATED"; changed=True
    if changed: _json_save(PREDICTION_LOG_FILE,log)
    today=local_now.date().isoformat()
    evaluated=[]; pending=[]
    for pred in log:
        try: d=datetime.fromisoformat(pred.get("created_at","").replace("Z","+00:00")).astimezone(ZoneInfo("Europe/Rome")).date().isoformat()
        except Exception: continue
        if d==today:
            (evaluated if pred.get("status")=="EVALUATED" else pending).append(pred)
    if not evaluated and not pending: return None
    correct=sum(p.get("verdict")=="CORRETTA" for p in evaluated); wrong=sum(p.get("verdict")=="ERRATA" for p in evaluated); ambiguous=sum(p.get("verdict")=="AMBIGUA" for p in evaluated)
    accuracy=correct/(correct+wrong)*100 if correct+wrong else 0.0
    lines=[f"📊 COMMODITIES BOT v{BOT_VERSION} — PERFORMANCE INTRADAY", "", f"📅 {local_now.strftime('%d/%m/%Y')}","━━━━━━━━━━━━━━━━━━━━",
           f"🎯 Segnali valutati: {len(evaluated)}",f"✅ Azzeccati: {correct}",f"❌ Sbagliati: {wrong}",f"⚪ Ambigui: {ambiguous}",f"🟡 Ancora in valutazione: {len(pending)}",f"📈 Accuratezza: {accuracy:.1f}%"]
    lines += ["", "🔒 PAPER ONLY"]
    state=_json_load(DAILY_REPORT_FILE,{})
    if state.get("last_report_date")==today and not force: return None
    state.update({"last_report_date":today,"accuracy":accuracy,"evaluated":len(evaluated),"pending":len(pending)})
    _json_save(DAILY_REPORT_FILE,state)
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
    """Send a Telegram message safely, splitting oversized messages."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram non configurato.")
        return False

    text = str(message or "").strip()
    if not text:
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    # Telegram's practical text limit is 4096 characters. Keep a small margin.
    chunks = [text[i:i+3900] for i in range(0, len(text), 3900)]
    ok = True
    for chunk in chunks:
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": chunk}
        try:
            response = requests.post(url, json=payload, timeout=20)
            response.raise_for_status()
        except Exception as error:
            ok = False
            print(f"⚠️ Errore Telegram: {error}")
    return ok


TELEGRAM_COMMAND_OFFSET_FILE = "telegram_update_offset.json"
TELEGRAM_COMMAND_MAX_AGE_SECONDS = int(os.getenv("TELEGRAM_COMMAND_MAX_AGE_SECONDS", "900"))


def _telegram_command_ranking(ranked):
    """Complete user-facing ranking for manual decision making.

    The list is sorted by MARKET ranking, not by executable opportunity score.
    Every commodity remains visible and carries the operational state so the
    user can distinguish market strength from an actually authorized entry.
    """
    available = [x for x in (ranked or []) if x.get("available")]

    def market_key(item):
        return safe_float(
            item.get("market_ranking_score"),
            safe_float((item.get("analysis", {}) or {}).get("score"), 0),
        ) or 0

    available.sort(key=market_key, reverse=True)

    lines = [
        f"🌍 COMMODITIES BOT v{BOT_VERSION}",
        "",
        "🏆 CLASSIFICA COMPLETA — DECISIONALE",
        "━━━━━━━━━━━━━━━━━━━━",
        "MKT = forza scenario | OPP = operatività",
        "",
    ]

    if not available:
        lines += ["⚪ Nessuna commodity disponibile.", "", "🧪 PAPER ONLY"]
        return "\n".join(lines)

    for i, item in enumerate(available, 1):
        a = item.get("analysis", {}) or {}
        pred = a.get("prediction_v53") or {}
        g_raw = a.get("gagarin_state") or a.get("gagarin") or {}
        if isinstance(g_raw, dict):
            g = g_raw
        else:
            g = {"state": str(g_raw)}

        direction = (
            a.get("final_direction")
            or a.get("setup_direction")
            or a.get("model_signal")
            or "NONE"
        )
        score = safe_float(a.get("score"), 0) or 0
        market_score = market_key(item)

        prob_raw = safe_float(
            a.get("entry_probability", a.get("probability", 0)), 0
        ) or 0
        prob = prob_raw * 100 if prob_raw <= 1.5 else prob_raw

        policy = a.get("entry_policy", {}) or {}
        quality = safe_float(
            policy.get("quality"),
            safe_float(a.get("quality"), 0),
        ) or 0
        confidence = safe_float(
            policy.get("confidence"),
            safe_float(a.get("confidence"), 0),
        ) or 0

        g_state = str(
            g.get("state")
            or a.get("gagarin_state_label")
            or ""
        ).upper()

        # Canonical operational state.
        operational = bool(a.get("operational_entry_allowed"))
        prediction_state = str(pred.get("state") or "").upper()
        setup = str(pred.get("setup") or g.get("setup") or "NONE").upper()
        trigger_ok = bool(pred.get("trigger_confirmed"))
        rr3 = safe_float(pred.get("rr_tp3"), safe_float(
            (a.get("adaptive_risk", {}) or {}).get("rr_tp3"), 0
        )) or 0

        if operational:
            decision = "🟢 READY"
        elif not item.get("available"):
            decision = "⚪ DATA"
        elif prediction_state in (
            "PREVISIONE_IN_FORMAZIONE",
            "PREVISIONE IN FORMAZIONE",
        ):
            decision = "🟡 FORMAZIONE"
        elif g_state in ("BLOCKED", "SAFETY_BLOCK") or not trigger_ok:
            decision = "🔴 BLOCCATO"
        else:
            decision = "🟡 ATTENDI"

        direction_icon = (
            "🟢" if direction == "LONG"
            else "🔴" if direction == "SHORT"
            else "🟡"
        )
        trigger_label = "OK" if trigger_ok else "NO"

        lines.append(
            f"{i:02d}. {item['name']} | "
            f"{direction_icon}{direction} | "
            f"MKT {market_score:.0f} | "
            f"Prob {prob:.0f}% | "
            f"Q {quality:.0f} C {confidence:.0f}"
        )
        lines.append(
            f"    {decision} | G:{g_state or 'N/D'} | "
            f"Setup:{setup} | Trig:{trigger_label} | RR3:{rr3:.2f}"
        )

    lines += [
        "",
        "📌 COME LEGGERLA",
        "🟢 READY = tutti i gate operativi superati",
        "🟡 FORMAZIONE/ATTENDI = scenario da monitorare",
        "🔴 BLOCCATO = almeno un gate impedisce l'ingresso",
        "⚪ DATA = dati insufficienti/non disponibili",
        "⚠️ MKT e Prob non autorizzano da soli un ingresso.",
        "",
        "🧪 PAPER ONLY",
    ]
    return "\n".join(lines)

def _telegram_normalize_command(text):
    """Normalize a Telegram command/message for simple natural-language matching."""
    normalized = re.sub(r"\s+", " ", str(text or "").strip().lower())
    normalized = normalized.replace("/", "")
    return normalized



def telegram_requested_scope(request):
    """Return the configured commodity name for a single-commodity Telegram request.

    Ranking/weekly/monthly/signals/help requests return None because they need the
    full cross-commodity universe.
    """
    q = _telegram_normalize_command(request)
    if not q:
        return None
    broad = (
        "classifica", "ranking", "rank", "migliore", "miglior setup",
        "settimanale", "weekly", "settimana", "mensile", "monthly", "mese",
        "segnali", "signals", "signal", "help", "aiuto", "comandi", "start"
    )
    if any(x in q for x in broad):
        return None
    aliases = {
        "oro": "Oro", "gold": "Oro",
        "argento": "Argento", "silver": "Argento",
        "platino": "Platino", "platinum": "Platino",
        "palladio": "Palladio", "palladium": "Palladio",
        "wti": "Petrolio WTI", "petrolio": "Petrolio WTI", "crude": "Petrolio WTI", "crude oil": "Petrolio WTI",
        "brent": "Petrolio Brent", "petrolio brent": "Petrolio Brent",
        "gas": "Gas Naturale", "gas naturale": "Gas Naturale", "natural gas": "Gas Naturale",
        "benzina": "Benzina RBOB", "rbob": "Benzina RBOB", "gasoline": "Benzina RBOB",
        "heating oil": "Heating Oil", "gasolio": "Heating Oil",
        "gas naturale": "Gas Naturale", "natural gas": "Gas Naturale",
        "caffè": "Caffè", "caffe": "Caffè", "coffee": "Caffè",
        "cotone": "Cotone", "cotton": "Cotone",
        "live cattle": "Bovini vivi", "bovini vivi": "Bovini vivi", "cattle": "Bovini vivi",
        "feeder cattle": "Feeder Cattle",
        "lean hogs": "Maiali magri", "lean hog": "Maiali magri", "hogs": "Maiali magri", "maiali magri": "Maiali magri",
        "rame": "Rame", "copper": "Rame",
        "alluminio": "Alluminio", "aluminum": "Alluminio", "aluminium": "Alluminio",
        "nichel": "Nichel", "nickel": "Nichel",
        "zinco": "Zinco", "zinc": "Zinco",
        "piombo": "Piombo", "lead": "Piombo",
        "grano": "Grano", "wheat": "Grano", "grain": "Grano",
        "mais": "Mais", "corn": "Mais", "maize": "Mais",
        "soia": "Soia", "soybean": "Soia", "soybeans": "Soia",
        "farina di soia": "Farina di soia", "soybean meal": "Farina di soia",
        "olio di soia": "Olio di soia", "soybean oil": "Olio di soia",
        "avena": "Avena", "oats": "Avena",
        "riso": "Riso", "rice": "Riso",
        "caffè": "Caffè", "caffe": "Caffè", "coffee": "Caffè",
        "cacao": "Cacao", "cocoa": "Cacao",
        "zucchero": "Zucchero", "sugar": "Zucchero",
        "cotone": "Cotone", "cotton": "Cotone",
        "succo d'arancia": "Succo d'arancia", "orange juice": "Succo d'arancia",
        "bovini vivi": "Bovini vivi", "live cattle": "Bovini vivi",
        "maiali magri": "Maiali magri", "lean hogs": "Maiali magri", "hogs": "Maiali magri",
        "feeder cattle": "Feeder Cattle",
    }
    for alias, name in sorted(aliases.items(), key=lambda kv: len(kv[0]), reverse=True):
        if alias in q and name in COMMODITIES:
            return name
    # Exact configured commodity name match.
    for name in COMMODITIES:
        if _telegram_normalize_command(name) in q:
            return name
    return None

def _telegram_find_commodity(ranked, query):
    """Find a commodity from a Telegram command, including natural-language requests."""
    q = _telegram_normalize_command(query)
    aliases = {
        "oro": "oro", "gold": "oro",
        "argento": "argento", "silver": "argento",
        "platino": "platino", "platinum": "platino",
        "palladio": "palladio", "palladium": "palladio",
        "wti": "petrolio wti", "petrolio": "petrolio wti", "crude oil": "petrolio wti", "crude": "petrolio wti",
        "brent": "petrolio brent", "oil brent": "petrolio brent", "petrolio brent": "petrolio brent",
        "gas": "gas naturale", "gas naturale": "gas naturale", "natural gas": "gas naturale",
        "benzina": "benzina rbob", "rbob": "benzina rbob", "gasoline": "benzina rbob",
        "heating oil": "heating oil", "gasolio": "heating oil",
        "rame": "rame", "copper": "rame",
        "alluminio": "alluminio", "aluminum": "alluminio", "aluminium": "alluminio",
        "nichel": "nichel", "nickel": "nichel", "zinco": "zinco", "zinc": "zinco", "piombo": "piombo", "lead": "piombo",
        "grano": "grano", "wheat": "grano", "chicago srw wheat": "grano",
        "mais": "mais", "corn": "mais",
        "soia": "soia", "soybean": "soia",
        "farina di soia": "farina di soia", "soybean meal": "farina di soia",
        "olio di soia": "olio di soia", "soybean oil": "olio di soia",
        "avena": "avena", "oats": "avena",
        "riso": "riso", "rice": "riso", "rough rice": "riso",
        "caffe": "caffè", "caffè": "caffè", "coffee": "caffè",
        "cacao": "cacao", "cocoa": "cacao",
        "zucchero": "zucchero", "sugar": "zucchero",
        "cotone": "cotone", "cotton": "cotone",
        "succo d'arancia": "succo d'arancia", "orange juice": "succo d'arancia", "arancia": "succo d'arancia",
        "bovini": "bovini vivi", "bovini vivi": "bovini vivi", "live cattle": "bovini vivi",
        "maiali": "maiali magri", "maiali magri": "maiali magri", "lean hogs": "maiali magri", "lean hog": "maiali magri",
        "feeder": "feeder cattle", "feeder cattle": "feeder cattle",
    }
    candidates = [x for x in ranked if x.get("available")]

    # Exact command first.
    target = aliases.get(q, q)
    exact = [x for x in candidates if _telegram_normalize_command(x.get("name")) == target]
    if exact:
        return exact[0]

    # Natural-language command: "dammi oro con tp e sl", "analizza gold", etc.
    # Prefer the longest alias so "petrolio brent" wins over "petrolio".
    for alias in sorted(aliases, key=len, reverse=True):
        if alias in q:
            target = aliases[alias]
            exact = [x for x in candidates if _telegram_normalize_command(x.get("name")) == target]
            if exact:
                return exact[0]
            partial = [x for x in candidates if target in _telegram_normalize_command(x.get("name"))]
            if partial:
                return partial[0]

    partial = [x for x in candidates if target in _telegram_normalize_command(x.get("name")) or _telegram_normalize_command(x.get("name")) in target]
    return partial[0] if partial else None


def _telegram_entry_status(a):
    """v4.12: separate directional setup from actual entry authorization."""
    direction = a.get("final_direction") or a.get("setup_direction") or a.get("model_signal") or "N/D"
    policy = a.get("entry_policy", {}) or {}
    status = str(policy.get("entry_status", "")).upper()
    risk = a.get("risk", {}) or {}
    reversal = a.get("reversal", {}) or {}
    se = a.get("signal_engine_v42", {}) or {}

    safety = (
        risk.get("mode") in ("SHOCK", "ALERT")
        or reversal.get("stage") == "CONFIRMED"
        or "SAFETY BLOCK" in [str(x).upper() for x in (a.get("entry_blockers") or [])]
        or "SAFETY BLOCK" in [str(x).upper() for x in (se.get("blockers") or [])]
    )

    if direction not in ("LONG", "SHORT"):
        return "⚪ NO SETUP", "NEUTRAL", "NO_SETUP"

    if status == "ENTRY_CONFIRMED" and not safety:
        return f"🟢 {direction} — 🟢 ENTRATA CONFERMATA", "ENTRY", status

    if safety:
        # The direction remains visible, but the safety layer has absolute authority.
        return f"🟠 {direction} — 🛑 SETUP ATTIVO, ENTRATA BLOCCATA", "BLOCKED", "SAFETY_BLOCK"

    if status == "WAIT_CONFIRMATION":
        return f"🟡 {direction} — ⏳ SETUP ATTIVO, ASPETTARE CONFERMA", "WAIT", status

    return f"⚪ {direction} — 🔴 NON ENTRARE", "BLOCKED", status or "NO_ENTRY"


def _telegram_commodity_detail(item):
    """Compact single-commodity Telegram report. Analysis stays internal."""
    if not item:
        return "⚪ Commodity non trovata. Scrivi HELP."
    a = item.get("analysis", {}) or {}
    plan_label = gagarin_plan_label(a)
    name = item.get("name", "N/D")
    direction = a.get("final_direction") or a.get("setup_direction") or a.get("model_signal") or "N/D"
    action = str(a.get("action_label", "ATTENDERE"))
    score = safe_float(a.get("score"), 0) or 0
    prob_raw = safe_float(a.get("entry_probability", a.get("probability", 0)), 0) or 0
    prob = prob_raw * 100 if prob_raw <= 1.5 else prob_raw
    policy = a.get("entry_policy", {}) or {}
    quality = safe_float(policy.get("quality"), safe_float(a.get("entry_quality", a.get("quality", 0)), 0)) or 0
    conf = safe_float(policy.get("confidence"), safe_float(a.get("confidence", 0), 0)) or 0
    se = a.get("signal_engine_v42", {}) or {}
    ar = a.get("adaptive_risk", {}) or {}
    entry = safe_float(ar.get("entry"), safe_float(a.get("entry"), safe_float(se.get("entry"), safe_float(a.get("price"), 0)))) or 0
    stop = safe_float(ar.get("stop"), safe_float(a.get("stop"), safe_float(se.get("stop"), 0))) or 0
    tp1 = safe_float(ar.get("tp1"), safe_float(a.get("tp1"), safe_float(se.get("tp1"), 0))) or 0
    tp2 = safe_float(ar.get("tp2"), safe_float(a.get("tp2"), safe_float(se.get("tp2"), 0))) or 0
    tp3 = safe_float(ar.get("tp3"), safe_float(a.get("tp3"), safe_float(se.get("tp3"), 0))) or 0
    rr1 = safe_float(ar.get("rr_tp1"), 0) or 0
    rr2 = safe_float(ar.get("rr_tp2"), 0) or 0
    rr3 = safe_float(ar.get("rr_tp3"), safe_float(se.get("rr_tp3"), safe_float((a.get("intraday_core", {}) or {}).get("rr_tp3"), 0))) or 0
    trigger = a.get("entry_trigger", {}) or {}
    # v5.3.1 Authority: never present a legacy trigger as confirmed when the
    # canonical prediction authority has not confirmed it.
    pred_auth = a.get("prediction_authority_v531") or prediction_authority_v531(a)
    auth_trigger_ok = bool(pred_auth.get("trigger_confirmed", False))
    auth_trigger_kind = str(trigger.get("kind") or "TRIGGER")
    auth_trigger_tf = str(trigger.get("timeframe") or "")
    if auth_trigger_ok:
        telegram_trigger_line = f"🔥 Trigger: {auth_trigger_kind} {auth_trigger_tf}".strip()
    else:
        telegram_trigger_line = "🔥 Trigger: ❌ NON CONFERMATO"
    if action == "ENTRARE":
        status = "🟢 ENTRATA CONFERMATA"
    elif action == "ENTRATA POSSIBILE":
        status = "🟡 ENTRATA POSSIBILE"
    elif action == "NON ENTRARE":
        status = "🔴 NON ENTRARE"
    else:
        status = "🟡 ATTENDERE"
    icon = "🟢" if direction == "LONG" else "🔴" if direction == "SHORT" else "🟡"
    lines = [
        f"🌍 COMMODITIES BOT v{BOT_VERSION}", "", f"📌 {name}",
        f"{icon} {direction} — {status}",
        f"💰 Prezzo: {_fmt_price(a.get('price'))}",
        f"📊 Score {score:.0f} | Prob {prob:.0f}% | Qualità {quality:.0f} | Conf {conf:.0f}",
    ]
    if entry > 0:
        lines += ["", f"📐 {plan_label}", f"📍 Entry: {_fmt_price(entry)}"]
        if stop > 0: lines.append(f"🛑 SL: {_fmt_price(stop)}")
        if tp1 > 0: lines.append(f"🎯 TP1: {_fmt_price(tp1)}" + (f" | R/R {rr1:.2f}" if rr1 > 0 else ""))
        if tp2 > 0: lines.append(f"🎯 TP2: {_fmt_price(tp2)}" + (f" | R/R {rr2:.2f}" if rr2 > 0 else ""))
        if tp3 > 0: lines.append(f"🎯 TP3: {_fmt_price(tp3)}" + (f" | R/R {rr3:.2f}" if rr3 > 0 else ""))
        if ar.get("theoretical_only"):
            lines.append("🧪 SL/TP: TEORICI — nessuna autorizzazione all'ingresso")
    lines.append(telegram_trigger_line)
    policy_blockers = [str(x) for x in (policy.get("blockers") or []) if x]
    risk_mode = str((a.get("risk", {}) or {}).get("mode", "")).upper()
    if risk_mode in ("SHOCK", "ALERT"):
        lines.append(f"🛑 BLOCCO SICUREZZA: RISCHIO {risk_mode}")
    elif policy_blockers:
        lines.append("⏳ " + " | ".join(policy_blockers[:2]))
    # Show only a material event, never a headline dump.
    global_impact = a.get("global_impact", {}) or {}
    if global_impact.get("mode") in ("SHOCK", "ALERT"):
        lines.append(f"⚠️ EVENTO MERCATO: {global_impact.get('mode')}")
    lines += ["", "🧪 PAPER ONLY"]
    return "\n".join(lines)


def _telegram_weekly_plan(item):
    """Build a WEEKLY scenario from the existing daily candles only.
    This is a scenario/forecast, not a real order. Historical 5-session
    outcomes are calculated strictly from candles that precede the latest bar.
    """
    if not item or not item.get("available"):
        return None
    a = item.get("analysis", {}) or {}
    candles = item.get("candles", []) or []
    if len(candles) < 40:
        return None

    direction = a.get("setup_direction") or a.get("model_signal") or "NONE"
    if direction not in ("LONG", "SHORT"):
        return None

    price = safe_float(a.get("price"), 0) or 0
    if price <= 0:
        try:
            price = safe_float(candles[-1].get("close"), 0) or 0
        except Exception:
            price = 0
    if price <= 0:
        return None

    # Historical next-5-session direction probability.  No future bars after
    # the latest candle are used for the current forecast.
    hist = []
    for i in range(0, len(candles) - 5):
        c = safe_float(candles[i].get("close"))
        f = safe_float(candles[i + 5].get("close"))
        if c and f:
            r = f / c - 1.0
            hist.append(r if direction == "LONG" else -r)
    hist = hist[-1000:]
    hist_win = sum(1 for r in hist if r > 0) / len(hist) if hist else 0.50
    hist_avg = mean(hist) if hist else 0.0

    # Current trend from daily closes.
    closes = [safe_float(x.get("close")) for x in candles if safe_float(x.get("close")) is not None]
    ret20 = closes[-1] / closes[-21] - 1.0 if len(closes) >= 21 else 0.0
    trend_aligned = ret20 >= 0 if direction == "LONG" else ret20 <= 0

    cyc = a.get("cyclical", {}) or {}
    weekly_cycle = cyc.get("weekly", {}) or {}
    cyc_quality = safe_float(weekly_cycle.get("quality"), 50) or 50

    score = safe_float(a.get("score"), 0) or 0
    confidence = safe_float(a.get("confidence"), 0) or 0
    quality = safe_float(a.get("quality", a.get("entry_quality", 0)), 0) or 0
    # Conservative weekly score: current engine + historical 5-day edge +
    # daily trend + the existing cyclical weekly component.
    trend_component = 100 if trend_aligned else 35
    weekly_score = clamp(
        score * 0.40 + hist_win * 100 * 0.25 + quality * 0.15
        + trend_component * 0.10 + cyc_quality * 0.10,
        0, 100,
    )
    probability = clamp(
        0.45 * hist_win + 0.30 * ((score / 100.0) if score else 0.5)
        + 0.15 * ((confidence / 100.0) if confidence else 0.5)
        + 0.10 * ((cyc_quality / 100.0) if cyc_quality else 0.5),
        0.05, 0.95,
    )

    # Weekly risk plan from daily ATR and recent structure. These levels are
    # explicitly labelled as weekly scenario levels, not intraday triggers.
    try:
        av = atr(candles[-100:], 14)
    except Exception:
        av = 0.0
    av = safe_float(av, 0) or 0
    if av <= 0:
        av = price * 0.01
    recent = candles[-20:]
    lows = [safe_float(x.get("low")) for x in recent if safe_float(x.get("low")) is not None]
    highs = [safe_float(x.get("high")) for x in recent if safe_float(x.get("high")) is not None]
    buffer = av * 0.15
    if direction == "LONG":
        structure_sl = min(lows) - buffer if lows else price - av
        stop = min(price - av * 0.80, structure_sl)
        if stop >= price:
            stop = price - av
        risk = price - stop
        tp1, tp2, tp3 = price + risk * 1.5, price + risk * 2.0, price + risk * 2.5
    else:
        structure_sl = max(highs) + buffer if highs else price + av
        stop = max(price + av * 0.80, structure_sl)
        if stop <= price:
            stop = price + av
        risk = stop - price
        tp1, tp2, tp3 = price - risk * 1.5, price - risk * 2.0, price - risk * 2.5

    return {
        "name": item.get("name", "N/D"), "direction": direction,
        "score": weekly_score, "probability": probability * 100,
        "history_win": hist_win * 100, "history_avg": hist_avg * 100,
        "trend20": ret20 * 100, "cyc_quality": cyc_quality,
        "price": price, "entry": price, "stop": stop,
        "tp1": tp1, "tp2": tp2, "tp3": tp3,
        "rr1": 1.5, "rr2": 2.0, "rr3": 2.5,
    }


def _telegram_weekly(ranked):
    plans = []
    for item in ranked:
        plan = _telegram_weekly_plan(item)
        if plan:
            plans.append(plan)
    if not plans:
        return "⚪ Nessun dato sufficiente per una previsione settimanale."
    plans.sort(key=lambda x: x["score"], reverse=True)
    best = plans[0]
    lines = [
        f"🌍 COMMODITIES BOT v{BOT_VERSION}", "", "🏆 MIGLIORE DELLA SETTIMANA",
        "━━━━━━━━━━━━━━━━━━━━",
        f"🥇 {best['name']}",
        f"{'🟢' if best['direction']=='LONG' else '🔴'} BIAS: {best['direction']}",
        f"📊 Score settimanale: {best['score']:.1f}/100",
        f"🎯 Probabilità stimata: {best['probability']:.1f}%",
        f"📚 Storico 5 sessioni: {best['history_win']:.1f}% favorevole",
        f"📈 Rendimento medio storico 5 sessioni: {best['history_avg']:+.2f}%",
        f"📉 Trend 20 sessioni: {best['trend20']:+.2f}%",
        f"🔄 Ciclo settimanale: {best['cyc_quality']:.0f}/100",
        "",
        "📐 {plan_label} SETTIMANALE — SCENARIO",
        f"💰 Prezzo/Entry scenario: {_fmt_price(best['entry'])}",
        f"🛑 SL: {_fmt_price(best['stop'])}",
        f"🎯 TP1: {_fmt_price(best['tp1'])} | R/R 1:1.5",
        f"🎯 TP2: {_fmt_price(best['tp2'])} | R/R 1:2.0",
        f"🎯 TP3: {_fmt_price(best['tp3'])} | R/R 1:2.5",
        "",
        "📆 Orizzonte: prossime 5 sessioni",
        "⚠️ Invalidazione: chiusura giornaliera oltre lo SL/scenario",
        "🧪 PAPER ONLY — nessun ordine reale.",
    ]
    if len(plans) > 1:
        lines += ["", "🏆 TOP 5 SETTIMANA"]
        for i, p in enumerate(plans[:5], 1):
            icon = "🟢" if p["direction"] == "LONG" else "🔴"
            lines.append(f"{i}. {p['name']} | {icon} {p['direction']} | {p['score']:.0f} | {p['probability']:.0f}%")
    return "\n".join(lines)


def _telegram_monthly_plan(item):
    """Build a longer-horizon monthly scenario from the daily history."""
    if not item or not item.get("available"):
        return None
    a = item.get("analysis", {}) or {}
    candles = item.get("candles", []) or []
    if len(candles) < 90:
        return None
    direction = a.get("setup_direction") or a.get("model_signal") or "NONE"
    if direction not in ("LONG", "SHORT"):
        return None
    closes = [safe_float(x.get("close")) for x in candles if safe_float(x.get("close")) is not None]
    if len(closes) < 31:
        return None
    rows = []
    for i in range(len(closes) - 20):
        r = closes[i + 20] / closes[i] - 1.0
        rows.append(r if direction == "LONG" else -r)
    rows = rows[-1000:]
    win = sum(1 for r in rows if r > 0) / len(rows) if rows else 0.5
    avg = mean(rows) if rows else 0.0
    score = safe_float(a.get("score"), 0) or 0
    cyc = a.get("cyclical", {}) or {}
    monthly_q = safe_float((cyc.get("monthly", {}) or {}).get("quality"), 50) or 50
    monthly_score = clamp(score * .45 + win * 100 * .30 + monthly_q * .15 + safe_float(a.get("confidence"),50) * .10, 0, 100)
    prob = clamp(0.55 * win + 0.30 * (score / 100.0) + 0.15 * (monthly_q / 100.0), .05, .95)
    return {"name":item.get("name","N/D"),"direction":direction,"score":monthly_score,"probability":prob*100,"history_win":win*100,"history_avg":avg*100,"monthly_q":monthly_q}


def _telegram_monthly(ranked):
    plans = [p for p in (_telegram_monthly_plan(x) for x in ranked) if p]
    if not plans:
        return "⚪ Nessun dato sufficiente per una previsione mensile."
    plans.sort(key=lambda x:x["score"], reverse=True)
    lines=[f"🌍 COMMODITIES BOT v{BOT_VERSION}","","🏆 MIGLIORE DEL MESE","━━━━━━━━━━━━━━━━━━━━"]
    for i,p in enumerate(plans[:5],1):
        icon="🟢" if p["direction"]=="LONG" else "🔴"
        lines.append(f"{i}. {p['name']} | {icon} {p['direction']} | Score {p['score']:.0f} | Prob {p['probability']:.0f}%")
    b=plans[0]
    lines += ["",f"🥇 SCELTA: {b['name']}",f"📚 Storico 20 sessioni: {b['history_win']:.1f}% favorevole",f"📈 Rendimento medio: {b['history_avg']:+.2f}%",f"🔄 Ciclo mensile: {b['monthly_q']:.0f}/100","","🧪 PAPER ONLY — nessun ordine reale."]
    return "\n".join(lines)


def telegram_set_commands():
    """Expose the main commands in Telegram's / menu."""
    if not TELEGRAM_BOT_TOKEN:
        return
    commands = [
        {"command":"start","description":"Menu Commodities Bot"},
        {"command":"classifica","description":"Classifica attuale"},
        {"command":"migliore","description":"Migliore setup adesso"},
        {"command":"settimanale","description":"Migliore commodity della settimana"},
        {"command":"mensile","description":"Migliore commodity del mese"},
        {"command":"segnali","description":"Segnali operativi"},
        {"command":"help","description":"Guida ai comandi"},
    ]
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setMyCommands",
            json={"commands": commands}, timeout=10
        ).raise_for_status()
    except Exception as exc:
        print(f"⚠️ Telegram setMyCommands: {exc}")

def _telegram_best(ranked):
    available = [x for x in (ranked or []) if x.get("available")]
    operational = [
        x for x in available
        if (x.get("analysis", {}) or {}).get("operational_entry_allowed")
    ]
    operational.sort(
        key=lambda x: safe_float(
            x.get("opportunity_score_v53"),
            x.get("ranking_score", -1),
        ) or -1,
        reverse=True,
    )
    if operational:
        return "🎯 MIGLIORE OPPORTUNITÀ OPERATIVA\n\n" + _telegram_commodity_detail(operational[0])

    if not available:
        return "⚪ Nessuna commodity disponibile."

    market = sorted(
        available,
        key=lambda x: safe_float(
            x.get("market_ranking_score"),
            (x.get("analysis", {}) or {}).get("score", 0),
        ) or 0,
        reverse=True,
    )[0]
    a = market.get("analysis", {}) or {}
    direction = (
        a.get("final_direction")
        or a.get("setup_direction")
        or a.get("model_signal")
        or "NONE"
    )
    prob = safe_float(a.get("entry_probability"), 0) or 0
    prob = prob * 100 if prob <= 1.5 else prob
    return (
        "🟡 NESSUNA OPPORTUNITÀ OPERATIVA\n\n"
        "📊 SCENARIO DI MERCATO PIÙ FORTE\n"
        f"{market.get('name','N/D')} | {direction} | "
        f"MKT {safe_float(market.get('market_ranking_score'),0) or 0:.0f} | "
        f"Prob {prob:.0f}%\n"
        "⚠️ Solo informativo: NON è un segnale d'ingresso."
    )


def _telegram_signals(ranked):
    candidates = []
    for item in ranked:
        if not item.get("available"):
            continue
        a = item.get("analysis", {}) or {}
        if str(a.get("action_label", "")).upper() in ("ENTRARE", "ENTRATA POSSIBILE"):
            candidates.append(item)
    candidates.sort(key=lambda x: safe_float(x.get("ranking_score", x.get("analysis", {}).get("score", 0)), 0) or 0, reverse=True)
    lines = [f"🌍 COMMODITIES BOT v{BOT_VERSION}", "", "🎯 SEGNALI", "━━━━━━━━━━━━━━━━━━━━"]
    if not candidates:
        lines.append("🟡 Nessun segnale operativo confermato.")
    else:
        for i, item in enumerate(candidates[:5], 1):
            a = item.get("analysis", {}) or {}
            d = a.get("setup_direction") or a.get("model_signal") or "N/D"
            lines.append(f"{i}. {item['name']} | {'🟢' if d=='LONG' else '🔴'} {d} | {safe_float(a.get('score'),0) or 0:.0f}")
    lines += ["", "🧪 PAPER ONLY"]
    return "\n".join(lines)


def _telegram_help():
    return (
        f"🌍 COMMODITIES BOT v{BOT_VERSION}\n\n"
        "🤖 COMANDI\n"
        "🏆 classifica — top commodity\n"
        "🥇 migliore — miglior setup\n"
        "🎯 segnali — soli segnali\n"
        "📌 oro / brent / wti / rame / grano / cacao — analisi + TP/SL\n"
        "💬 Puoi scrivere: \"dammi oro con tp e sl\"\n\n"
        "🧪 PAPER ONLY"
    )


def process_telegram_on_demand(ranked):
    """Answer exactly one Telegram request passed by the webhook bridge.

    This path never calls getUpdates: Telegram delivery is handled by the
    external HTTPS webhook bridge, which dispatches this workflow with the
    request text and chat id as workflow inputs.
    """
    global TELEGRAM_CHAT_ID
    raw_text = ON_DEMAND_TELEGRAM_REQUEST.strip()
    chat_id = ON_DEMAND_TELEGRAM_CHAT_ID.strip() or str(TELEGRAM_CHAT_ID or "").strip()
    if not raw_text:
        return
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        print("⚠️ On-demand Telegram: token/chat id mancanti")
        return

    try:
        telegram_set_commands()
        normalized = _telegram_normalize_command(raw_text)
        command = normalized
        if any(x in normalized for x in (
            "mandami la classifica", "dammi la classifica", "inviami la classifica"
        )):
            command = "classifica"
        elif any(x in normalized for x in (
            "migliore della settimana", "miglior della settimana", "migliore settimanale",
            "miglior settimanale", "top della settimana", "top settimana",
            "previsione settimanale", "previsione della settimana"
        )):
            command = "settimanale"
        elif any(x in normalized for x in (
            "migliore del mese", "miglior del mese", "migliore mensile",
            "miglior mensile", "top del mese", "top mensile",
            "previsione mensile", "previsione del mese"
        )):
            command = "mensile"

        if command in {"start", "help", "aiuto", "comandi"}:
            reply = _telegram_help()
        elif command in {"classifica", "ranking", "rank"}:
            reply = _telegram_command_ranking(ranked)
        elif command in {"migliore", "best", "miglior setup", "migliore setup"}:
            reply = _telegram_best(ranked)
        elif command in {"settimanale", "weekly", "settimana"}:
            reply = _telegram_weekly(ranked)
        elif command in {"mensile", "monthly", "mese"}:
            reply = _telegram_monthly(ranked)
        elif command in {"segnali", "signals", "signal"}:
            reply = _telegram_signals(ranked)
        else:
            item = _telegram_find_commodity(ranked, normalized)
            if item:
                reply = _telegram_commodity_detail(item)
            else:
                reply = (
                    "❓ Comando non riconosciuto.\n\n"
                    + _telegram_help()
                )

        # send_telegram reads TELEGRAM_CHAT_ID at module level, so temporarily
        # align it with the request chat when the workflow input is present.
        original_chat_id = TELEGRAM_CHAT_ID
        TELEGRAM_CHAT_ID = chat_id
        try:
            send_telegram(reply)
        finally:
            TELEGRAM_CHAT_ID = original_chat_id
        print(f"📨 Telegram on-demand: {raw_text!r} → {command}")
    except Exception as exc:
        print(f"⚠️ Telegram on-demand error: {exc}")


def process_telegram_commands(ranked):
    """Poll Telegram and answer on-demand commands from the configured chat."""
    if os.getenv("TELEGRAM_COMMANDS_ENABLED", "1") != "1":
        return
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    try:
        telegram_set_commands()
        state = _json_load(TELEGRAM_COMMAND_OFFSET_FILE, {}) or {}
        offset = int(state.get("offset", 0) or 0)
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        params = {"timeout": 5, "allowed_updates": json.dumps(["message"])}
        if offset > 0:
            params["offset"] = offset
        response = requests.get(url, params=params, timeout=12)
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            print(f"⚠️ Telegram getUpdates non OK: {data}")
            return

        updates = data.get("result", []) or []
        if not updates:
            return

        now = datetime.now(timezone.utc)
        newest_offset = offset
        for update in updates:
            update_id = int(update.get("update_id", 0) or 0)
            newest_offset = max(newest_offset, update_id + 1)
            message = update.get("message", {}) or {}
            chat = message.get("chat", {}) or {}
            chat_id = str(chat.get("id", ""))
            if chat_id != str(TELEGRAM_CHAT_ID):
                continue
            raw_text = str(message.get("text", "") or "").strip()
            if not raw_text:
                continue
            ts = message.get("date")
            if ts:
                age = (now - datetime.fromtimestamp(int(ts), tz=timezone.utc)).total_seconds()
                if age > TELEGRAM_COMMAND_MAX_AGE_SECONDS:
                    print(f"ℹ️ Telegram comando ignorato: vecchio di {age:.0f}s")
                    continue
                if age < -60:
                    continue

            normalized = _telegram_normalize_command(raw_text)
            command = normalized
            if "mandami la classifica" in normalized or "dammi la classifica" in normalized or "inviami la classifica" in normalized:
                command = "classifica"
            elif any(x in normalized for x in ("migliore della settimana", "miglior della settimana", "migliore settimanale", "miglior settimanale", "top della settimana", "top settimana", "previsione settimanale", "previsione della settimana")):
                command = "settimanale"
            elif any(x in normalized for x in ("migliore del mese", "miglior del mese", "migliore mensile", "miglior mensile", "top del mese", "top mensile", "previsione mensile", "previsione del mese")):
                command = "mensile"

            if command in {"classifica", "ranking", "rank"}:
                print("📨 Telegram: comando CLASSIFICA ricevuto")
                send_telegram(_telegram_command_ranking(ranked))
            elif command in {"migliore", "best", "miglior setup", "migliore setup"}:
                print("📨 Telegram: comando MIGLIORE ricevuto")
                send_telegram(_telegram_best(ranked))
            elif command in {"settimanale", "weekly", "settimana"}:
                print("📨 Telegram: previsione SETTIMANALE richiesta")
                send_telegram(_telegram_weekly(ranked))
            elif command in {"mensile", "monthly", "mese"}:
                print("📨 Telegram: previsione MENSILE richiesta")
                send_telegram(_telegram_monthly(ranked))
            elif command in {"segnali", "signals", "setup"}:
                print("📨 Telegram: comando SEGNALI ricevuto")
                send_telegram(_telegram_signals(ranked))
            elif command in {"help", "aiuto", "comandi", "menu", "start"}:
                print("📨 Telegram: comando HELP ricevuto")
                send_telegram(_telegram_help())
            else:
                item = _telegram_find_commodity(ranked, command)
                if item:
                    print(f"📨 Telegram: analisi {item.get('name')} richiesta")
                    send_telegram(_telegram_commodity_detail(item))
                else:
                    send_telegram(
                        "⚪ Non ho riconosciuto la commodity.\n\n"
                        "Esempi: `oro`, `dammi oro con tp e sl`, `analizza Brent`, `fammi il piano del caffè`."
                    )

        _json_save(TELEGRAM_COMMAND_OFFSET_FILE, {"offset": newest_offset, "updated_at": now.isoformat()})
    except Exception as exc:
        print(f"⚠️ Telegram command handler: {exc}")


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
    signal = analysis.get("final_direction") or analysis.get("setup_direction") or analysis.get("model_signal")
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
    """Compact intraday alert: action, levels and one reason only."""
    candidates=[x for x in ranked if x.get("available") and x.get("analysis",{}).get("setup_direction") in ("LONG","SHORT")]
    candidates.sort(key=lambda x:safe_float(x["analysis"].get("intraday_score",0),0) or 0, reverse=True)
    if not candidates:
        return "⚡ INTRADAY\n\n⚪ Nessun setup operativo."
    item=candidates[0]; a=item["analysis"]; d=a.get("setup_direction"); action=str(a.get("action_label","ATTENDERE"))
    icon="🟢" if d=="LONG" else "🔴"
    lines=["⚡ INTRADAY", "", f"🥇 {item['name']}", f"{icon} {d} — {action}", f"💰 {_fmt_price(a.get('price'))}"]
    for label,key in (("📍 Entry","entry"),("🛑 SL","stop"),("🎯 TP1","tp1"),("🎯 TP2","tp2")):
        if a.get(key) is not None: lines.append(f"{label} {_fmt_price(a.get(key))}")
    trig=a.get("entry_trigger",{}) or {}
    if trig.get("kind"): lines.append(f"🔥 {trig.get('kind')} {trig.get('timeframe','')}")
    blockers=a.get("entry_blockers",[]) or []
    if blockers and action in ("ATTENDERE","NON ENTRARE"): lines.append("⏳ " + " | ".join(blockers[:2]))
    risk_mode=str((a.get("risk",{}) or {}).get("mode","")).upper()
    if risk_mode in ("SHOCK","ALERT"): lines.append(f"🛑 RISCHIO {risk_mode}")
    if position_message: lines += ["", "📌 POSIZIONE", position_message]
    lines += ["", "🧪 PAPER ONLY"]
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
# v4.2 SIGNAL ENGINE — LEVEL-TO-LEVEL + STRUCTURE + RISK
# ============================================================
def _v42_order_block(analysis, candles):
    """Detect a simple, non-future-looking order-block style zone.

    This is deliberately conservative: it only labels a recent opposite candle
    before an impulse larger than 1 ATR. It does not invent order-book data.
    """
    d = analysis.get("setup_direction") or analysis.get("model_signal")
    if d not in ("LONG", "SHORT") or not candles or len(candles) < 12:
        return {"available": False, "state": "N/D"}
    atrv = safe_float(analysis.get("atr"), 0) or atr(candles, 14) or 0.0
    if atrv <= 0:
        return {"available": False, "state": "N/D"}
    look = candles[-14:]
    for i in range(len(look) - 2, 1, -1):
        row = look[i]
        nxt = look[i + 1]
        o = safe_float(row.get("open")); h = safe_float(row.get("high")); lo = safe_float(row.get("low")); c = safe_float(row.get("close"))
        nc = safe_float(nxt.get("close"))
        if None in (o, h, lo, c, nc):
            continue
        body = abs(c - o)
        impulse = abs(nc - c)
        opposite = (d == "LONG" and c < o) or (d == "SHORT" and c > o)
        if opposite and body > 0 and impulse >= 1.0 * atrv:
            return {
                "available": True,
                "state": "IDENTIFICATO",
                "direction": d,
                "high": round(h, 8),
                "low": round(lo, 8),
                "source": "recent opposing candle + impulse",
            }
    return {"available": False, "state": "NON IDENTIFICATO"}


def signal_engine_v42(analysis, candles=None):
    """Turn existing analysis layers into one actionable, explainable signal.

    Source-derived concepts used here: Level-to-Level, supply/demand context,
    multi-timeframe confirmation, futures context, and predefined SL/TP/RR.
    No real execution is performed.
    """
    d = analysis.get("setup_direction") or analysis.get("model_signal")
    if d not in ("LONG", "SHORT"):
        analysis["signal_engine_v42"] = {"available": False, "decision": "NO TRADE", "score": 0.0}
        return analysis

    l2l = analysis.get("level_to_level", {}) or {}
    intel = analysis.get("market_intelligence_v41", {}) or {}
    curve = analysis.get("futures_structure", {}) or {}
    risk = analysis.get("risk", {}) or {}
    trigger = analysis.get("entry_trigger", {}) or {}
    tfs = analysis.get("timeframes", {}) or {}
    order_block = _v42_order_block(analysis, candles or analysis.get("_candles") or [])

    aligned = sum(1 for tf in ("4H", "1H", "15m") if (tfs.get(tf, {}) or {}).get("direction") == d)
    fast_aligned = sum(1 for tf in ("5m", "1m") if (tfs.get(tf, {}) or {}).get("direction") == d)
    mtf_score = clamp(aligned / 3 * 75 + fast_aligned / 2 * 25, 0, 100)
    l2l_score = safe_float(l2l.get("score"), 50) or 50
    intel_score = safe_float(intel.get("score"), 50) or 50
    curve_score = 50.0
    curve_dir = str(curve.get("direction", "NONE"))
    if curve_dir == d:
        curve_score = 72.0
    elif curve_dir in ("LONG", "SHORT"):
        curve_score = 28.0
    trigger_score = safe_float(trigger.get("score"), 0) or 0
    if trigger.get("confirmed"):
        trigger_score = max(trigger_score, 78.0)
    if l2l.get("retest"):
        trigger_score = max(trigger_score, 90.0)
    if l2l.get("fakeout"):
        trigger_score = min(trigger_score, 20.0)

    entry = safe_float(analysis.get("entry"), safe_float(analysis.get("price"), 0)) or 0
    stop = safe_float(analysis.get("stop"), 0) or 0
    tp1 = safe_float(analysis.get("tp1"), 0) or 0
    tp2 = safe_float(analysis.get("tp2"), 0) or 0
    tp3 = safe_float(analysis.get("tp3"), 0) or 0
    rd = abs(entry - stop) if entry and stop else 0
    rr1 = abs(tp1-entry)/rd if rd else 0
    rr2 = abs(tp2-entry)/rd if rd else 0
    rr3 = abs(tp3-entry)/rd if rd else 0
    rr_score = clamp((min(rr1/1.5,1) + min(rr2/2.0,1) + min(rr3/2.5,1)) / 3 * 100, 0, 100)
    quality = safe_float(analysis.get("quality"), 0) or 0
    confidence = safe_float(analysis.get("confidence"), 0) or 0
    risk_score = clamp((quality * 0.45 + confidence * 0.35 + safe_float(risk.get("market_quality"), 50) * 0.20), 0, 100)

    raw_score = (
        mtf_score * 0.18 +
        l2l_score * 0.22 +
        intel_score * 0.15 +
        trigger_score * 0.20 +
        rr_score * 0.15 +
        risk_score * 0.10
    )
    if order_block.get("available"):
        raw_score += 3.0
    if curve_dir == d:
        raw_score += 2.0
    raw_score = clamp(raw_score, 0, 100)

    safety = risk.get("mode") in ("SHOCK", "ALERT") or (analysis.get("reversal", {}) or {}).get("stage") == "CONFIRMED"
    blockers = []
    if safety: blockers.append("SAFETY BLOCK")
    if aligned < 2: blockers.append("MTF INCOMPLETO")
    if not trigger.get("confirmed"): blockers.append("TRIGGER NON CONFERMATO")
    if l2l.get("fakeout"): blockers.append("FAKEOUT")
    if rr1 + 0.005 < 1.5: blockers.append("RR TP1 INSUFFICIENTE")
    if rd <= 0: blockers.append("SL NON VALIDO")

    if safety or l2l.get("fakeout"):
        decision = "NON ENTRARE"
        state = "BLOCKED"
    elif trigger.get("confirmed") and raw_score >= 82 and rr1 + 0.005 >= 1.5 and rd > 0:
        decision = "ENTRARE"
        state = "CONFIRMED"
    elif raw_score >= 68 and rd > 0 and rr1 + 0.005 >= 1.5:
        decision = f"ENTRATA POSSIBILE {d}"
        state = "POSSIBLE"
    elif raw_score >= 52:
        decision = f"{d} — ASPETTARE"
        state = "WAIT"
    else:
        decision = "NON ENTRARE"
        state = "BLOCKED"

    # v4.10 — reconcile Signal Engine with the single Entry Policy authority.
    # The legacy SE may still calculate diagnostics, but it must not overwrite
    # the final entry permission decided by evaluate_entry_policy().
    _policy = analysis.get("entry_policy") or {}
    _policy_status = str(_policy.get("entry_status", "")).upper()
    if _policy_status:
        if safety:
            decision = "NON ENTRARE"
            state = "BLOCKED"
        elif _policy_status == "ENTRY_CONFIRMED":
            decision = "ENTRARE"
            state = "CONFIRMED"
        elif _policy_status == "WAIT_CONFIRMATION":
            decision = f"{d} — ASPETTARE"
            state = "WAIT"
        else:
            decision = "NON ENTRARE"
            state = "BLOCKED"

        # Rebuild the visible blockers from the policy rather than the legacy
        # confluence gate, avoiding false "RR TP1 INSUFFICIENTE" diagnostics.
        _policy_blockers = list(_policy.get("blockers") or [])
        if safety and "SAFETY BLOCK" not in _policy_blockers:
            _policy_blockers.insert(0, "SAFETY BLOCK")
        blockers = _policy_blockers[:6]

    # v4.10 — reconcile Signal Engine with the single Entry Policy authority
    analysis["signal_engine_v42"] = {
        "available": True,
        "decision": decision,
        "state": state,
        "direction": d,
        "score": round(raw_score, 1),
        "mtf": round(mtf_score, 1),
        "level_to_level": round(l2l_score, 1),
        "intelligence": round(intel_score, 1),
        "trigger": round(trigger_score, 1),
        "rr": round(rr_score, 1),
        "risk": round(risk_score, 1),
        "order_block": order_block,
        "entry": entry,
        "stop": stop,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "rr_tp1": round(rr1, 2),
        "rr_tp2": round(rr2, 2),
        "rr_tp3": round(rr3, 2),
        "blockers": blockers[:6],
        "method": "LEVEL-TO-LEVEL + MTF + INTELLIGENCE + FUTURES + RISK/REWARD",
    }
    return analysis


def apply_signal_engine_v42(results):
    for item in results:
        if item.get("available"):
            signal_engine_v42(item.get("analysis", {}), item.get("candles") or [])
    return results


# ============================================================
# v5.0 COMMODITY KNOWLEDGE ENGINE
# ============================================================
# Principles distilled from the requested educational sources:
# - commodity price is driven by supply/demand, macro conditions,
#   USD/rates, geopolitics and weather;
# - different commodity families require different drivers;
# - spot/continuous and futures can behave differently around expiry/roll;
# - risk management and timing are part of the setup, not an afterthought.
# These are contextual features, not claims of guaranteed predictive power.

COMMODITY_KNOWLEDGE_PROFILES = {
    "Oro": {"family":"PRECIOUS_METAL", "drivers":["USD","rates","safe_haven","central_banks","real_yields","geopolitics"], "pre_usa_weight":1.00},
    "Argento": {"family":"PRECIOUS_METAL", "drivers":["USD","rates","industrial_demand","solar","gold_beta"], "pre_usa_weight":0.95},
    "Platino": {"family":"PRECIOUS_METAL", "drivers":["USD","auto_demand","supply","industrial_demand"], "pre_usa_weight":0.90},
    "Palladio": {"family":"PRECIOUS_METAL", "drivers":["USD","auto_demand","supply","industrial_demand"], "pre_usa_weight":0.90},
    "Petrolio WTI": {"family":"ENERGY", "drivers":["supply","demand","inventories","geopolitics","USD","OPEC"], "pre_usa_weight":1.00},
    "Petrolio Brent": {"family":"ENERGY", "drivers":["supply","demand","inventories","geopolitics","USD","OPEC"], "pre_usa_weight":1.00},
    "Gas Naturale": {"family":"ENERGY", "drivers":["weather","storage","production","LNG","demand"], "pre_usa_weight":0.95},
    "Benzina RBOB": {"family":"ENERGY", "drivers":["refinery","inventories","seasonality","crude","demand"], "pre_usa_weight":0.95},
    "Heating Oil": {"family":"ENERGY", "drivers":["refinery","inventories","weather","diesel_demand","crude"], "pre_usa_weight":0.95},
    "Rame": {"family":"INDUSTRIAL_METAL", "drivers":["China","global_growth","USD","inventories","supply"], "pre_usa_weight":0.90},
    "Alluminio": {"family":"INDUSTRIAL_METAL", "drivers":["China","global_growth","USD","inventories","energy_costs"], "pre_usa_weight":0.85},
    "Nichel": {"family":"INDUSTRIAL_METAL", "drivers":["China","stainless_demand","inventories","supply","USD"], "pre_usa_weight":0.85},
    "Zinco": {"family":"INDUSTRIAL_METAL", "drivers":["China","construction","inventories","supply","USD"], "pre_usa_weight":0.85},
    "Piombo": {"family":"INDUSTRIAL_METAL", "drivers":["industrial_demand","inventories","supply","USD"], "pre_usa_weight":0.80},
    "Grano": {"family":"AGRICULTURAL", "drivers":["weather","crop","exports","stocks","USD","seasonality"], "pre_usa_weight":0.80},
    "Mais": {"family":"AGRICULTURAL", "drivers":["weather","crop","ethanol","exports","stocks","USD"], "pre_usa_weight":0.80},
    "Soia": {"family":"AGRICULTURAL", "drivers":["weather","crop","China","exports","stocks","USD"], "pre_usa_weight":0.80},
    "Farina di soia": {"family":"AGRICULTURAL", "drivers":["weather","feed_demand","China","crush","stocks"], "pre_usa_weight":0.75},
    "Olio di soia": {"family":"AGRICULTURAL", "drivers":["biofuel","crush","stocks","weather","vegetable_oils"], "pre_usa_weight":0.75},
    "Avena": {"family":"AGRICULTURAL", "drivers":["weather","crop","stocks","exports","USD"], "pre_usa_weight":0.70},
    "Riso": {"family":"AGRICULTURAL", "drivers":["weather","crop","exports","stocks","seasonality"], "pre_usa_weight":0.70},
    "Caffè": {"family":"SOFT", "drivers":["weather","crop","Brazil","Vietnam","stocks","USD"], "pre_usa_weight":0.75},
    "Cacao": {"family":"SOFT", "drivers":["weather","crop","West_Africa","stocks","demand"], "pre_usa_weight":0.75},
    "Zucchero": {"family":"SOFT", "drivers":["weather","crop","Brazil","ethanol","stocks","USD"], "pre_usa_weight":0.75},
    "Cotone": {"family":"SOFT", "drivers":["weather","crop","China","textile_demand","stocks","USD"], "pre_usa_weight":0.70},
    "Succo d'arancia": {"family":"SOFT", "drivers":["weather","hurricane","crop","disease","stocks"], "pre_usa_weight":0.75},
    "Bovini vivi": {"family":"LIVESTOCK", "drivers":["herd","feed_cost","slaughter","exports","demand"], "pre_usa_weight":0.65},
    "Maiali magri": {"family":"LIVESTOCK", "drivers":["herd","feed_cost","slaughter","exports","demand"], "pre_usa_weight":0.65},
    "Feeder Cattle": {"family":"LIVESTOCK", "drivers":["herd","feed_cost","cattle_demand","supply"], "pre_usa_weight":0.65},
}

FAMILY_RULES_V5 = {
    "PRECIOUS_METAL": {"news_terms":["gold","silver","metals","central bank","rates","dollar","safe haven","yield"], "timing":"USD/rates and US session can dominate short-term moves."},
    "ENERGY": {"news_terms":["oil","energy","opec","inventory","refinery","gas","lng","crude"], "timing":"US inventory/energy headlines can produce abrupt intraday repricing."},
    "INDUSTRIAL_METAL": {"news_terms":["copper","aluminium","aluminum","nickel","zinc","china","manufacturing","construction"], "timing":"China/global-growth signals matter; USD can amplify moves."},
    "AGRICULTURAL": {"news_terms":["wheat","corn","soybean","crop","harvest","weather","export","stocks"], "timing":"Weather/crop reports can dominate technical signals."},
    "SOFT": {"news_terms":["coffee","cocoa","sugar","cotton","orange","weather","crop","harvest"], "timing":"Weather and crop/supply shocks can overwhelm normal trend signals."},
    "LIVESTOCK": {"news_terms":["cattle","hog","livestock","feed","slaughter","export"], "timing":"Supply/feed/demand reports can create discontinuous moves."},
}


def _knowledge_news_bias(name, news, global_intel):
    profile = COMMODITY_KNOWLEDGE_PROFILES.get(name, {})
    family = profile.get("family", "")
    rules = FAMILY_RULES_V5.get(family, {})
    corpus = " ".join(str(x.get("title", "")) + " " + str(x.get("description", "")) for x in (global_intel or {}).get("articles", []) or [])
    corpus += " " + str((news or {}).get("label", ""))
    low = corpus.lower()
    relevant = sum(1 for term in rules.get("news_terms", []) if term.lower() in low)
    bull_terms = (V41_FUNDAMENTAL_TERMS.get(name, {}) or {}).get("bull", [])
    bear_terms = (V41_FUNDAMENTAL_TERMS.get(name, {}) or {}).get("bear", [])
    bull = sum(1 for term in bull_terms if term.lower() in low)
    bear = sum(1 for term in bear_terms if term.lower() in low)
    raw = clamp((bull - bear) / 6.0, -1.0, 1.0)
    return raw, relevant, bull, bear


def commodity_knowledge_engine_v5(name, analysis, news=None, usd=None, global_intel=None):
    if not KNOWLEDGE_ENGINE_V5_ENABLED:
        return {"enabled":False,"score":50.0,"direction":"NEUTRALE","confidence":0.0,"family":"N/D","drivers":[],"delta":0.0}
    profile = COMMODITY_KNOWLEDGE_PROFILES.get(name, {"family":"GENERIC","drivers":[],"pre_usa_weight":0.7})
    family = profile.get("family", "GENERIC")
    d = analysis.get("setup_direction") or analysis.get("model_signal") or "NONE"
    raw_news, relevant, bull, bear = _knowledge_news_bias(name, news, global_intel)
    usd_score = safe_float((usd or {}).get("score"), 0) or 0
    # USD score is assumed directional from the existing USD engine; invert for commodities
    # when the setup is LONG and keep the sign aligned with the proposed direction.
    usd_raw = clamp(usd_score / 100.0 if abs(usd_score) > 1 else usd_score, -1.0, 1.0)
    usd_component = -usd_raw
    regime = str((analysis.get("market_regime", {}) or {}).get("state", "N/D"))
    regime_component = 0.25 if regime in ("TREND", "TREND UP", "TREND DOWN") else 0.0
    weather = safe_float((analysis.get("weather_impact") or {}).get("score"), 50) or 50
    weather_component = clamp((weather - 50) / 50.0, -1, 1)
    contextual = clamp(0.50 * raw_news + 0.25 * usd_component + 0.15 * weather_component + 0.10 * regime_component, -1, 1)
    if d == "SHORT":
        aligned = -contextual
    else:
        aligned = contextual
    score = clamp(50 + aligned * 50, 0, 100)
    confidence = clamp(abs(aligned) * 100 + min(relevant * 4, 20), 0, 100)
    direction = "FAVOREVOLE" if aligned >= .20 else "SFAVOREVOLE" if aligned <= -.20 else "NEUTRALE"
    delta = clamp(aligned * KNOWLEDGE_DELTA_CAP, -KNOWLEDGE_DELTA_CAP, KNOWLEDGE_DELTA_CAP)
    method = educational_methodology_engine({"profile": {
        "trend": analysis.get("knowledge_trend", 0),
        "structure": analysis.get("knowledge_structure", 0),
        "support_resistance": analysis.get("knowledge_support_resistance", 0),
        "breakout": analysis.get("knowledge_breakout", 0),
        "pullback": analysis.get("knowledge_pullback", 0),
        "risk": analysis.get("knowledge_risk", 0),
        "position_sizing": analysis.get("knowledge_position_sizing", 0),
        "seasonality": analysis.get("knowledge_seasonality", 0),
        "spread_trading": analysis.get("knowledge_spread_trading", 0),
        "contango_backwardation": analysis.get("knowledge_contango_backwardation", 0),
        "fundamental": analysis.get("knowledge_fundamental", 0),
        "backtesting": analysis.get("knowledge_backtesting", 0),
        "mechanical_rules": analysis.get("knowledge_mechanical_rules", 0),
        "volume_orderflow": analysis.get("knowledge_volume_orderflow", 0),
        "wyckoff": analysis.get("knowledge_wyckoff", 0),
        "chart_patterns": analysis.get("knowledge_chart_patterns", 0),
        "candlestick": analysis.get("knowledge_candlestick", 0),
    }})
    return {
        "enabled":True,"version":"5.1","family":family,"drivers":profile.get("drivers",[]),
        "direction":direction,"score":round(score,1),"confidence":round(confidence,1),"delta":round(delta,2),
        "news_relevance":relevant,"bull_hits":bull,"bear_hits":bear,"regime":regime,
        "timing_note":FAMILY_RULES_V5.get(family,{}).get("timing","Context-specific commodity drivers."),
        "pre_usa_weight":profile.get("pre_usa_weight",0.7),
    }


def apply_commodity_knowledge_engine_v5(analysis, name, news=None, usd=None, global_intel=None):
    k = commodity_knowledge_engine_v5(name, analysis, news, usd, global_intel)
    analysis["commodity_knowledge_v5"] = k
    if k.get("enabled"):
        # Small bounded refinement only. Existing safety/entry gates remain authoritative.
        delta = safe_float(k.get("delta"), 0) or 0
        analysis["score"] = clamp((safe_float(analysis.get("score"), 0) or 0) + delta, 0, 100)
        analysis["knowledge_delta_v5"] = delta
    return analysis


def pre_usa_timing_engine_v5(analysis, name=None, now=None):
    if not PRE_USA_ENGINE_ENABLED:
        return {"enabled":False,"phase":"DISABLED"}
    now = now or datetime.now(ZoneInfo("Europe/Rome"))
    ny = now.astimezone(ZoneInfo("America/New_York"))
    open_dt = ny.replace(hour=9, minute=30, second=0, microsecond=0)
    diff_min = (open_dt - ny).total_seconds() / 60.0
    if 0 < diff_min <= PRE_USA_WINDOW_MINUTES:
        phase = "PRE_USA"
    elif -US_OPEN_CONFIRM_MINUTES <= diff_min <= 0:
        phase = "USA_OPEN_CONFIRM"
    elif diff_min > PRE_USA_WINDOW_MINUTES:
        phase = "BEFORE_PRE_USA"
    elif diff_min < -US_OPEN_CONFIRM_MINUTES:
        phase = "POST_USA_OPEN"
    else:
        phase = "USA_OPEN_CONFIRM"
    d = analysis.get("setup_direction") or analysis.get("model_signal") or "NONE"
    state = analysis.get("entry_state", "WATCH")
    if phase == "PRE_USA":
        recommendation = "PRE-SIGNAL" if d in ("LONG","SHORT") else "NO-SIGNAL"
    elif phase == "USA_OPEN_CONFIRM":
        recommendation = "CONFIRM/INVALIDATE" if d in ("LONG","SHORT") else "WAIT"
    else:
        recommendation = "MONITOR"
    k = analysis.get("commodity_knowledge_v5", {}) or {}
    return {
        "enabled":True,"phase":phase,"rome_time":now.strftime("%H:%M"),"ny_time":ny.strftime("%H:%M"),
        "minutes_to_open":round(diff_min,1),"direction":d,"entry_state":state,
        "recommendation":recommendation,"knowledge_score":safe_float(k.get("score"),50) or 50,
        "timing_note":k.get("timing_note",""),
    }


def apply_pre_usa_timing_v5(analysis, name=None, now=None):
    timing = pre_usa_timing_engine_v5(analysis, name, now)
    analysis["pre_usa_v5"] = timing
    return analysis


def pre_usa_summary_v5(analysis):
    t = analysis.get("pre_usa_v5", {}) or {}
    if not t.get("enabled"):
        return "N/D"
    mins = safe_float(t.get("minutes_to_open"), 0) or 0
    if t.get("phase") == "PRE_USA":
        return f"PRE-USA | {t.get('recommendation')} | open ~{mins:.0f}m"
    if t.get("phase") == "USA_OPEN_CONFIRM":
        return "USA OPEN | CONFERMA/INVALIDA"
    return str(t.get("phase", "N/D"))


# ============================================================
# v3.6 COMMUNICATION ENGINE
# ============================================================
def _communication_state():
    return _json_load("commodities_communication_state.json", {}) or {}

def _save_communication_state(state):
    _json_save("commodities_communication_state.json", state)

def _scheduled_operational_best(ranked):
    """Return only a fully authorized operational candidate for scheduled plans.

    The market ranking may identify a strong directional scenario even when
    Gagarin/Prediction/SLTP/Safety block an entry. Scheduled plans must never
    promote that analytical leader into an operational plan.
    """
    operational = [
        item for item in (ranked or [])
        if item.get("available")
        and (item.get("analysis", {}) or {}).get("operational_entry_allowed")
    ]
    operational.sort(
        key=lambda item: safe_float(
            item.get("opportunity_score_v53"),
            item.get("ranking_score", -1),
        ) or -1,
        reverse=True,
    )
    return operational[0] if operational else None


def _session_message(label, ranked, best, position_message=None):
    """Compact scheduled Telegram message; never turns market rank into a trade."""
    operational_best = _scheduled_operational_best(ranked)
    if operational_best is None:
        market_best = next(
            (
                item for item in (ranked or [])
                if item.get("available")
            ),
            None,
        )
        lines = [
            label,
            "",
            "🟡 NESSUNA OPPORTUNITÀ OPERATIVA",
            "━━━━━━━━━━━━━━━━━━━━",
            "Nessun setup ha superato tutti i gate operativi.",
        ]
        if market_best:
            ma = market_best.get("analysis", {}) or {}
            md = ma.get("final_direction") or ma.get("setup_direction") or ma.get("model_signal") or "NONE"
            ms = safe_float(market_best.get("market_ranking_score"), ma.get("score", 0)) or 0
            mp = safe_float(ma.get("entry_probability"), 0) or 0
            lines += [
                "",
                "📊 SCENARIO DI MERCATO",
                f"🥇 {market_best.get('name','N/D')}",
                f"{'🟢' if md == 'LONG' else '🔴' if md == 'SHORT' else '🟡'} {md} | MKT {ms:.0f} | Prob {mp:.0f}%",
                "⚠️ Solo informativo: NON è un segnale d'ingresso.",
            ]
        if position_message:
            lines += ["", "📌 POSIZIONE", position_message]
        lines += ["", "🧪 PAPER ONLY"]
        return "\n".join(lines)

    best = operational_best
    a = best.get("analysis", {}) or {}
    direction = a.get("final_direction") or a.get("setup_direction") or a.get("model_signal") or "NONE"
    action = str(a.get("action_label", "ATTENDERE"))
    icon = "🟢" if direction == "LONG" else "🔴" if direction == "SHORT" else "🟡"
    status = "ENTRARE" if action == "ENTRARE" else "ATTENDERE" if action in ("ATTENDERE", "ENTRATA POSSIBILE") else "NON ENTRARE"
    policy = a.get("entry_policy", {}) or {}
    quality = safe_float(policy.get("quality"), safe_float(a.get("quality"), 0)) or 0
    conf = safe_float(policy.get("confidence"), safe_float(a.get("confidence"), 0)) or 0
    lines = [label, "", f"🥇 {best.get('name','N/D')}", f"{icon} {direction} — {status}",
             f"💰 {_fmt_price(a.get('price'))}",
             f"📊 Score {safe_float(a.get('score'),0) or 0:.0f} | Prob {safe_float(a.get('entry_probability'),0) or 0:.0f}% | Q {quality:.0f} | C {conf:.0f}"]
    if a.get("entry") is not None: lines.append(f"📍 Entry {_fmt_price(a.get('entry'))}")
    if a.get("stop") is not None: lines.append(f"🛑 SL {_fmt_price(a.get('stop'))}")
    if a.get("tp1") is not None: lines.append(f"🎯 TP1 {_fmt_price(a.get('tp1'))}")
    if a.get("tp2") is not None: lines.append(f"🎯 TP2 {_fmt_price(a.get('tp2'))}")
    if a.get("tp3") is not None: lines.append(f"🎯 TP3 {_fmt_price(a.get('tp3'))}")
    trig = a.get("entry_trigger", {}) or {}
    if trig.get("kind"): lines.append(f"🔥 {trig.get('kind')} {trig.get('timeframe','')}")
    risk_mode = str((a.get("risk", {}) or {}).get("mode", "")).upper()
    if risk_mode in ("SHOCK", "ALERT"): lines.append(f"🛑 BLOCCO: RISCHIO {risk_mode}")
    gi = a.get("global_impact", {}) or {}
    if gi.get("mode") in ("SHOCK", "ALERT") and risk_mode not in ("SHOCK", "ALERT"):
        lines.append(f"⚠️ EVENTO MERCATO: {gi.get('mode')}")
    if position_message: lines += ["", "📌 POSIZIONE", position_message]
    lines += ["", "🧪 PAPER ONLY"]
    return "\n".join(lines)


def maybe_send_session_reports(ranked, best, position_message=None):
    if COMMUNICATION_MODE != "MORNING_USA_EVENT": return
    now=datetime.now(ZoneInfo("Europe/Rome")); today=now.date().isoformat(); state=_communication_state()
    sent=state.setdefault("sent", {})
    if now.hour==MORNING_REPORT_HOUR and MORNING_REPORT_MINUTE <= now.minute < MORNING_REPORT_MINUTE+30 and sent.get("morning") != today:
        send_telegram(_session_message("🌅 MORNING SIGNAL", ranked, best, position_message))
        sent["morning"]=today
    if now.hour==PRE_USA_REPORT_HOUR and PRE_USA_REPORT_MINUTE <= now.minute < PRE_USA_REPORT_MINUTE+30 and sent.get("pre_usa") != today:
        send_telegram(_session_message("🇺🇸 PRE-USA SIGNAL — APERTURA AMERICA", ranked, best, position_message))
        sent["pre_usa"]=today
    if now.hour==USA_REPORT_HOUR and USA_REPORT_MINUTE <= now.minute < USA_REPORT_MINUTE+30 and sent.get("usa") != today:
        send_telegram(_session_message("🇺🇸 USA SESSION UPDATE", ranked, best, position_message))
        sent["usa"]=today
    _save_communication_state(state)


# ============================================================
# v4.1 MARKET INTELLIGENCE ENGINE
# ============================================================
# PricePedia-style four lenses translated into bounded, explainable features:
# 1) micro: supply/demand proxies from commodity-specific news
# 2) macro: rates/USD/global risk/geopolitics
# 3) qualitative: political/geopolitical/event context
# 4) financial: trend, momentum, volatility, curve and cross-commodity context
# Optional data are never treated as hard blockers.

V41_FUNDAMENTAL_TERMS = {
    "Oro": {"bull": ["central bank", "safe haven", "demand", "buying", "rate cuts", "weaker dollar"], "bear": ["strong dollar", "rate hike", "selling", "demand slowdown"]},
    "Argento": {"bull": ["industrial demand", "solar demand", "supply deficit", "mine supply", "weaker dollar"], "bear": ["industrial slowdown", "strong dollar", "oversupply"]},
    "Platino": {"bull": ["supply deficit", "mine disruption", "automotive demand", "hydrogen demand"], "bear": ["oversupply", "weak auto demand", "recession"]},
    "Palladio": {"bull": ["supply disruption", "mine disruption", "automotive demand", "sanctions"], "bear": ["oversupply", "weak auto demand", "substitution"]},
    "Petrolio WTI": {"bull": ["opec", "production cut", "inventory draw", "supply disruption", "demand growth", "refinery demand"], "bear": ["inventory build", "oversupply", "production increase", "demand slowdown", "recession"]},
    "Petrolio Brent": {"bull": ["opec", "production cut", "inventory draw", "supply disruption", "demand growth", "hormuz"], "bear": ["inventory build", "oversupply", "production increase", "demand slowdown", "recession"]},
    "Gas Naturale": {"bull": ["storage draw", "cold weather", "heat wave", "lng demand", "lng outage", "pipeline disruption"], "bear": ["storage build", "warm weather", "oversupply", "mild weather", "demand slowdown"]},
    "Benzina RBOB": {"bull": ["refinery outage", "gasoline demand", "inventory draw", "driving season", "supply disruption"], "bear": ["inventory build", "weak demand", "refinery restart", "oversupply"]},
    "Heating Oil": {"bull": ["diesel demand", "refinery outage", "inventory draw", "cold weather", "supply disruption"], "bear": ["inventory build", "weak demand", "refinery restart", "warm weather"]},
    "Rame": {"bull": ["china stimulus", "china demand", "industrial demand", "mine disruption", "smelter cuts", "inventory draw"], "bear": ["china slowdown", "recession", "oversupply", "inventory build", "smelter restart"]},
    "Alluminio": {"bull": ["smelter cuts", "supply disruption", "inventory draw", "china stimulus", "industrial demand"], "bear": ["oversupply", "inventory build", "production increase", "china slowdown"]},
    "Nichel": {"bull": ["mine disruption", "supply cuts", "stainless demand", "battery demand"], "bear": ["oversupply", "production increase", "weak stainless demand", "weak battery demand"]},
    "Zinco": {"bull": ["mine disruption", "smelter cuts", "inventory draw", "industrial demand"], "bear": ["oversupply", "inventory build", "china slowdown"]},
    "Piombo": {"bull": ["supply disruption", "mine disruption", "battery demand", "inventory draw"], "bear": ["oversupply", "inventory build", "industrial slowdown"]},
    "Grano": {"bull": ["drought", "frost", "crop failure", "export ban", "ukraine", "russia", "inventory draw", "supply disruption"], "bear": ["harvest increase", "crop improvement", "oversupply", "inventory build", "export increase"]},
    "Mais": {"bull": ["drought", "frost", "crop failure", "export demand", "inventory draw", "supply disruption"], "bear": ["crop improvement", "harvest increase", "oversupply", "inventory build"]},
    "Soia": {"bull": ["drought", "crop failure", "china demand", "export demand", "inventory draw"], "bear": ["crop improvement", "harvest increase", "oversupply", "china slowdown"]},
    "Farina di soia": {"bull": ["soybean meal demand", "feed demand", "china demand", "supply disruption"], "bear": ["oversupply", "weak feed demand", "china slowdown"]},
    "Olio di soia": {"bull": ["biofuel demand", "biodiesel demand", "supply disruption", "vegetable oil demand"], "bear": ["oversupply", "weak biofuel demand", "demand slowdown"]},
    "Avena": {"bull": ["drought", "frost", "crop failure", "supply disruption"], "bear": ["harvest increase", "oversupply", "inventory build"]},
    "Riso": {"bull": ["flood", "drought", "crop failure", "export restriction", "supply disruption"], "bear": ["harvest increase", "oversupply", "export increase"]},
    "Caffè": {"bull": ["brazil frost", "brazil drought", "vietnam drought", "crop failure", "supply disruption", "export demand"], "bear": ["harvest increase", "crop improvement", "oversupply"]},
    "Cacao": {"bull": ["crop failure", "drought", "disease", "supply disruption", "west africa supply"], "bear": ["harvest increase", "crop improvement", "oversupply"]},
    "Zucchero": {"bull": ["drought", "crop failure", "supply disruption", "ethanol demand"], "bear": ["harvest increase", "oversupply", "crop improvement"]},
    "Cotone": {"bull": ["drought", "crop failure", "textile demand", "supply disruption"], "bear": ["oversupply", "weak textile demand", "harvest increase"]},
    "Succo d'arancia": {"bull": ["hurricane", "frost", "citrus greening", "crop failure", "supply disruption"], "bear": ["harvest increase", "crop improvement", "oversupply"]},
    "Bovini vivi": {"bull": ["cattle supply", "tight supply", "feed costs", "export demand", "herd reduction"], "bear": ["herd expansion", "oversupply", "weak demand", "slaughter increase"]},
    "Maiali magri": {"bull": ["hog supply", "tight supply", "export demand", "herd reduction"], "bear": ["herd expansion", "oversupply", "weak demand", "production increase"]},
    "Feeder Cattle": {"bull": ["tight supply", "feed demand", "cattle demand", "herd reduction"], "bear": ["herd expansion", "oversupply", "weak demand"]},
}


def _v41_text_from_news(news):
    # analyze_news() deliberately returns compact metadata, so this layer uses
    # its label/count plus the existing commodity/global headline corpus when available.
    return str((news or {}).get("label", "")) if isinstance(news, dict) else ""


def _v41_sentiment_from_articles(articles, terms):
    text = " ".join(str(a.get("title", "")) + " " + str(a.get("description", "")) for a in (articles or [])).lower()
    bull = sum(1 for t in terms.get("bull", []) if t in text)
    bear = sum(1 for t in terms.get("bear", []) if t in text)
    return clamp((bull - bear) / 6.0, -1.0, 1.0), bull, bear


def _v41_directional_value(value, direction):
    v = safe_float(value, 0.0) or 0.0
    if direction == "SHORT":
        return -v
    return v


def _v41_financial_context(analysis):
    d = analysis.get("setup_direction") or analysis.get("model_signal")
    if d not in ("LONG", "SHORT"):
        return {"score": 50.0, "direction": "NONE", "trend": 50.0, "momentum": 50.0, "volatility": 50.0}
    tfs = analysis.get("timeframes", {}) or {}
    aligned = sum(1 for tf in ("4H", "1H", "15m") if tfs.get(tf, {}).get("direction") == d)
    opposite = sum(1 for tf in ("4H", "1H", "15m") if tfs.get(tf, {}).get("direction") not in (d, "NONE"))
    trend = clamp(50 + aligned * 16 - opposite * 14, 0, 100)
    momentum = clamp(50 + _v41_directional_value(analysis.get("mtf_bias", 0), d) * 50, 0, 100)
    atr_pct = safe_float(analysis.get("atr_pct"), None)
    if atr_pct is None:
        price = safe_float(analysis.get("price"), 0) or 0
        atr_v = safe_float(analysis.get("atr"), 0) or 0
        atr_pct = atr_v / price if price else 0.0
    vol = clamp(70 - max(0.0, atr_pct * 100 - 1.0) * 8, 30, 80)
    score = clamp(trend * .45 + momentum * .35 + vol * .20, 0, 100)
    return {"score": round(score, 1), "direction": d, "trend": round(trend, 1), "momentum": round(momentum, 1), "volatility": round(vol, 1)}



def _sole24_strip_html(raw):
    """Convert a public Sole 24 Ore HTML page into compact searchable text."""
    if not raw:
        return ""
    text = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", raw)
    text = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", text)
    text = re.sub(r"(?is)<!--.*?-->", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text, flags=re.I)
    text = re.sub(r"&amp;", "&", text, flags=re.I)
    text = re.sub(r"&#39;|&apos;", "'", text, flags=re.I)
    text = re.sub(r"&quot;", '"', text, flags=re.I)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _sole24_fetch_page(url):
    try:
        r = requests.get(
            url,
            timeout=SOLE24_TIMEOUT,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; CommoditiesBot/4.5; +https://github.com/)"
            },
        )
        if r.status_code != 200:
            return "", f"HTTP {r.status_code}"
        return _sole24_strip_html(r.text), "OK"
    except Exception as exc:
        return "", str(exc)


def _sole24_cache_load():
    try:
        if not os.path.exists(SOLE24_CACHE_FILE):
            return {}
        data = _json_load(SOLE24_CACHE_FILE, {})
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _sole24_cache_save(data):
    try:
        _json_save(SOLE24_CACHE_FILE, data)
    except Exception as exc:
        print(f"   ⚠️ Sole24 cache: {exc}")


def sole24_context_engine(name):
    """Read public Sole 24 Ore/24 Ore Lab/Agrisole context for one commodity.

    It uses public pages only. If a page is unavailable, the source is marked
    unavailable and the rest of the bot continues with a neutral Sole24 score.
    """
    neutral = {
        "enabled": False,
        "available": False,
        "score": 50.0,
        "direction": "NEUTRALE",
        "confidence": 0.0,
        "delta": 0.0,
        "sources": 0,
        "pages": 0,
        "bull_hits": 0,
        "bear_hits": 0,
        "data": {},
        "status": "N/D",
    }
    if not SOLE24_ENABLED:
        neutral["status"] = "DISATTIVATO"
        return neutral

    cache = _sole24_cache_load()
    cache_key = str(name)
    now = datetime.now(timezone.utc)
    cached = cache.get(cache_key) if isinstance(cache, dict) else None
    if isinstance(cached, dict):
        try:
            ts = datetime.fromisoformat(str(cached.get("timestamp")).replace("Z", "+00:00"))
            if (now - ts).total_seconds() <= SOLE24_CACHE_HOURS * 3600:
                return cached.get("value", neutral)
        except Exception:
            pass

    terms = V41_FUNDAMENTAL_TERMS.get(name, {"bull": [], "bear": []})
    commodity_aliases = {
        "Oro": ["oro", "gold"], "Argento": ["argento", "silver"],
        "Platino": ["platino", "platinum"], "Palladio": ["palladio", "palladium"],
        "Petrolio WTI": ["wti", "petrolio", "greggio", "brent"],
        "Petrolio Brent": ["brent", "petrolio", "greggio"],
        "Gas Naturale": ["gas naturale", "gas", "lng"],
        "Benzina RBOB": ["benzina", "carburanti", "gasoline", "raffiner"],
        "Heating Oil": ["gasolio", "diesel", "carburanti"],
        "Rame": ["rame", "copper", "metalli"], "Alluminio": ["alluminio", "metalli"],
        "Nichel": ["nichel", "metalli"], "Zinco": ["zinco", "metalli"],
        "Piombo": ["piombo", "metalli"],
        "Grano": ["grano", "frumento", "cereali"], "Mais": ["mais", "cereali"],
        "Soia": ["soia", "semi oleosi"], "Farina di soia": ["soia", "farina di soia"],
        "Olio di soia": ["soia", "oli vegetali"], "Avena": ["avena", "cereali"],
        "Riso": ["riso", "cereali"], "Caffè": ["caffè", "coffee"],
        "Cacao": ["cacao", "cocoa"], "Zucchero": ["zucchero", "sugar"],
        "Cotone": ["cotone", "cotton"], "Succo d'arancia": ["arancia", "agrumi"],
        "Bovini vivi": ["bovini", "carne", "cattle"], "Maiali magri": ["maiali", "carne", "hog"],
        "Feeder Cattle": ["bovini", "cattle"],
    }
    aliases = commodity_aliases.get(name, [name.lower()])
    positive = [
        "rialzo", "aumento", "aumenta", "crescita", "rincaro", "salita", "record",
        "carenza", "scarsità", "deficit", "crisi dell'offerta", "supply disruption",
        "tensione", "blocco", "supply shock", "domanda forte", "domanda in crescita",
        "export demand", "drought", "siccità", "gelate", "raccolti in calo",
    ]
    negative = [
        "ribasso", "calo", "diminuzione", "scende", "discesa", "surplus", "eccesso",
        "offerta abbondante", "domanda debole", "rallentamento della domanda",
        "raccolti in aumento", "scorte in aumento", "produzione in aumento",
    ]

    pages = []
    data = {}
    statuses = []
    for url in SOLE24_URLS:
        text, status = _sole24_fetch_page(url)
        statuses.append(status)
        if text:
            pages.append((url, text))

    if not pages:
        neutral["status"] = "; ".join(statuses[:3]) if statuses else "N/D"
        return neutral

    relevant_text = []
    source_hits = 0
    for url, text in pages:
        low = text.lower()
        if any(a in low for a in aliases):
            relevant_text.append(text)
            source_hits += 1
        elif name in ("Oro", "Argento", "Petrolio WTI", "Petrolio Brent", "Gas Naturale") and any(
            x in low for x in ("inflazione", "tassi", "dollaro", "geopolitica", "hormuz", "energia")
        ):
            relevant_text.append(text)
            source_hits += 1

    text = " ".join(relevant_text).lower()
    bull_hits = sum(1 for term in terms.get("bull", []) if term.lower() in text)
    bear_hits = sum(1 for term in terms.get("bear", []) if term.lower() in text)
    bull_hits += sum(1 for term in positive if term in text and any(a in text for a in aliases))
    bear_hits += sum(1 for term in negative if term in text and any(a in text for a in aliases))

    raw = clamp((bull_hits - bear_hits) / 8.0, -1.0, 1.0)
    score = clamp(50.0 + raw * 50.0, 0, 100)
    confidence = clamp(min(100.0, (bull_hits + bear_hits) * 7.5 + source_hits * 10), 0, 100)
    direction = "LONG" if raw >= 0.12 else "SHORT" if raw <= -0.12 else "NEUTRALE"
    delta = clamp(raw * 4.0, -4.0, 4.0)

    # Public numeric indicators explicitly visible on Lab24 pages.
    patterns = {
        "brent_max_usd": r"(?:prezzo massimo\s+brent|brent[^0-9]{0,80}(?:prezzo massimo|maximum|superato))[^0-9]{0,40}(\d+[\.,]\d+)",
        "gas_max_eur_mwh": r"(?:prezzo massimo\s+gas|gas[^0-9]{0,80}(?:prezzo massimo|maximum))[^0-9]{0,40}(\d+[\.,]\d+)",
        "fuel_italy_eur_l": r"benzina[^0-9]{0,100}(\d+[\.,]\d+)\s*(?:euro|€)?\s*(?:/|al)?\s*litro",
        "urea_monthly_pct": r"urea[^%]{0,180}(?:quasi|circa)?\s*(\d+[\.,]\d+)\s*%[^a-z]{0,30}(?:su base mensile|mensile)",
        "wheat_monthly_pct": r"grano[^%]{0,100}(?:\+|aumento|rialzo)[^%]{0,60}(\d+[\.,]\d+)\s*%",
    }
    for key, pattern in patterns.items():
        m = re.search(pattern, text, flags=re.I)
        if m:
            try:
                data[key] = float(m.group(1).replace(".", "").replace(",", "."))
            except Exception:
                pass

    result = {
        "enabled": True,
        "available": True,
        "score": round(score, 1),
        "direction": direction,
        "confidence": round(confidence, 1),
        "delta": round(delta, 2),
        "sources": source_hits,
        "pages": len(pages),
        "bull_hits": bull_hits,
        "bear_hits": bear_hits,
        "data": data,
        "status": "OK",
        "source_names": ["Il Sole 24 Ore Lab24", "Il Sole 24 Ore Agrisole"],
    }
    cache[cache_key] = {"timestamp": now.isoformat(), "value": result}
    _sole24_cache_save(cache)
    return result


def apply_sole24_context(analysis, name):
    """Merge Sole24 context into the existing intelligence brain.

    The Sole24 layer is deliberately bounded: it can refine the score and the
    intelligence score, but it cannot remove safety blocks or create a trade alone.
    """
    sole = sole24_context_engine(name)
    analysis["sole24_intelligence"] = sole
    if not sole.get("available"):
        return analysis

    sole_delta = safe_float(sole.get("delta"), 0) or 0
    analysis["score"] = clamp((safe_float(analysis.get("score"), 0) or 0) + sole_delta, 0, 100)
    analysis["sole24_delta"] = round(sole_delta, 2)

    intel = analysis.get("market_intelligence_v41")
    if isinstance(intel, dict) and intel.get("enabled"):
        old_intel_score = safe_float(intel.get("score"), 50) or 50
        weight = clamp(SOLE24_WEIGHT, 0, 0.30)
        combined = old_intel_score * (1.0 - weight) + (safe_float(sole.get("score"), 50) or 50) * weight
        old_delta = safe_float(intel.get("delta"), 0) or 0
        intel["score"] = round(clamp(combined, 0, 100), 1)
        intel["sole24_weight"] = round(weight, 3)
        intel["sole24_score"] = round(safe_float(sole.get("score"), 50) or 50, 1)
        intel["sole24_direction"] = sole.get("direction", "NEUTRALE")
        intel["sole24_confidence"] = round(safe_float(sole.get("confidence"), 0) or 0, 1)
        intel["delta"] = round(clamp(old_delta + sole_delta, -12, 12), 2)
        intel["direction"] = "FAVOREVOLE" if intel["score"] >= 60 else "SFAVOREVOLE" if intel["score"] <= 40 else "NEUTRALE"
        analysis["market_intelligence_v41"] = intel
    return analysis

def market_intelligence_v41(name, analysis, news=None, political=None, global_intel=None):
    """Build the v4.1 four-lens intelligence block without inventing data."""
    if not MARKET_INTELLIGENCE_ENABLED:
        return {"enabled": False, "score": 50.0, "label": "DISATTIVATA", "direction": "NEUTRALE", "confidence": 0.0}

    d = analysis.get("setup_direction") or analysis.get("model_signal")
    if d not in ("LONG", "SHORT"):
        d = "LONG"

    political = political or {}
    global_intel = global_intel or {}
    news = news or {}

    # Qualitative/news lens. We intentionally use existing fetched headlines;
    # no second news scrape is performed here.
    relevant_articles = global_intel.get("articles", []) or []
    fundamentals = _v41_sentiment_from_articles(relevant_articles, V41_FUNDAMENTAL_TERMS.get(name, {"bull": [], "bear": []}))
    news_score = safe_float(news.get("score"), 0.0) or 0.0
    global_score = safe_float(global_intel.get("score"), 0.0) or 0.0
    political_score = safe_float(political.get("score"), 0.0) or 0.0
    commodity_global = analysis.get("global_impact", {}) or {}
    geo_score = safe_float(commodity_global.get("score"), 0.0) or 0.0 if GEOPOLITICAL_IMPACT_ENABLED else 0.0

    micro = fundamentals[0] if COMMODITY_FUNDAMENTALS_ENABLED else 0.0
    macro = clamp(0.55 * global_score + 0.45 * news_score, -1, 1)
    qualitative = clamp(0.55 * political_score + 0.45 * geo_score, -1, 1)
    financial = _v41_financial_context(analysis)
    financial_signed = _v41_directional_value((financial["score"] - 50) / 50.0, d)

    # Convert context into a directional score. The four lenses are deliberately
    # bounded so intelligence can refine, but not overpower, the quantitative engine.
    # Configurable weights from the workflow. We normalise them so changing
    # one weight does not accidentally change the score scale.
    w_micro = max(0.0, FUNDAMENTALS_WEIGHT)
    w_macro = max(0.0, INTELLIGENCE_WEIGHT)
    w_qual = max(0.0, POLITICAL_IMPACT_WEIGHT + GEOPOLITICAL_IMPACT_WEIGHT)
    w_fin = max(0.0, MARKET_REGIME_WEIGHT + VOLATILITY_CONTEXT_ENABLED * 0.05)
    w_curve = max(0.0, FUTURES_STRUCTURE_WEIGHT)
    w_total = max(w_micro + w_macro + w_qual + w_fin + w_curve, 1e-9)
    curve = analysis.get("futures_structure", {}) or {}
    curve_dir = str(curve.get("direction", "NONE"))
    curve_score = 0.0
    if curve_dir in ("LONG", "SHORT"):
        curve_score = 0.35 if curve_dir == d else -0.35
    contextual = clamp(
        (w_micro * micro + w_macro * macro + w_qual * qualitative +
         w_fin * financial_signed + w_curve * curve_score) / w_total,
        -1, 1,
    )
    direction_score = contextual if d == "LONG" else -contextual
    delta = clamp(direction_score * 8.0, -8.0, 8.0)

    regime = "TREND" if financial["trend"] >= 68 else "MIXED" if financial["trend"] >= 48 else "RANGE/CONTRARIAN"
    shock_mode = str(commodity_global.get("mode", global_intel.get("mode", "NORMAL")))
    if shock_mode == "SHOCK":
        regime = "SHOCK"

    return {
        "enabled": True,
        "mode": MARKET_INTELLIGENCE_MODE,
        "score": round(50 + contextual * 50, 1),
        "direction": "FAVOREVOLE" if contextual >= .20 else "SFAVOREVOLE" if contextual <= -.20 else "NEUTRALE",
        "delta": round(delta, 2),
        "confidence": round(abs(contextual) * 100, 1),
        "micro_supply_demand": {"score": round(50 + micro * 50, 1), "raw": round(micro, 3), "bull_hits": fundamentals[1], "bear_hits": fundamentals[2]},
        "macro": {"score": round(50 + macro * 50, 1), "raw": round(macro, 3)},
        "qualitative": {"score": round(50 + qualitative * 50, 1), "political": round(political_score, 3), "geopolitical": round(geo_score, 3)},
        "financial": financial,
        "market_regime": {"state": regime, "score": round(financial["score"], 1)},
        "global_mode": shock_mode,
        "global_articles": int(global_intel.get("count", 0) or 0),
        "news_articles": int(news.get("count", 0) or 0),
        "sources": int(global_intel.get("source_count", 0) or 0),
    }


def apply_market_intelligence_v41(analysis, name, news, political, global_intel):
    intel = market_intelligence_v41(name, analysis, news, political, global_intel)
    analysis["market_intelligence_v41"] = intel
    if intel.get("enabled"):
        old = safe_float(analysis.get("score"), 0) or 0
        # Apply a small bounded adjustment. The core quant model remains primary.
        analysis["score"] = clamp(old + safe_float(intel.get("delta"), 0), 0, 100)
        analysis["intelligence_delta"] = safe_float(intel.get("delta"), 0) or 0
    return analysis


def apply_cross_commodity_intelligence_v41(results):
    """Relative-strength/dispersion lens across the currently available basket."""
    if not CROSS_COMMODITY_ANALYSIS_ENABLED:
        return results
    rows = []
    for item in results:
        if not item.get("available"):
            continue
        candles = item.get("candles") or []
        if len(candles) < 25:
            continue
        try:
            p0 = safe_float(candles[-21].get("close")); p1 = safe_float(candles[-1].get("close"))
            if p0 and p1:
                ret20 = (p1 / p0) - 1
                rows.append((item, ret20))
        except Exception:
            continue
    if not rows:
        return results
    values = [r for _, r in rows]
    m = mean(values); sd = std(values)
    for item, ret in rows:
        a = item["analysis"]
        d = a.get("setup_direction") or a.get("model_signal")
        signed = ret if d == "LONG" else -ret if d == "SHORT" else 0.0
        z = clamp((ret - m) / sd, -2.5, 2.5) if sd > 1e-9 else 0.0
        cross_score = clamp(50 + signed * 500 + z * 5, 0, 100)
        a["market_intelligence_v41"]["cross_commodity"] = {
            "score": round(cross_score, 1), "ret20": round(ret * 100, 2), "basket_mean": round(m * 100, 2), "zscore": round(z, 2), "sample": len(rows)
        }
        delta = clamp((cross_score - 50) * CROSS_COMMODITY_WEIGHT * 0.08, -4, 4)
        a["score"] = clamp((safe_float(a.get("score"), 0) or 0) + delta, 0, 100)
        a["intelligence_delta"] = round((safe_float(a.get("intelligence_delta"), 0) or 0) + delta, 2)
    return results


def intelligence_v41_summary(analysis):
    i = analysis.get("market_intelligence_v41", {}) or {}
    if not i.get("enabled"):
        return "N/D"
    micro = (i.get("micro_supply_demand") or {}).get("score", 50)
    macro = (i.get("macro") or {}).get("score", 50)
    qual = (i.get("qualitative") or {}).get("score", 50)
    fin = (i.get("financial") or {}).get("score", 50)
    regime = (i.get("market_regime") or {}).get("state", "N/D")
    return f"MICRO {micro:.0f} | MACRO {macro:.0f} | QUAL {qual:.0f} | FIN {fin:.0f} | REGIME {regime}"


# ============================================================
# SOYUZ v5.2 GAGARIN — ARCHITECTURE ORCHESTRATOR
# ============================================================
# The Gagarin layer consolidates the legacy engines into one explicit
# decision pipeline. Legacy engines remain available as implementation
# adapters; they no longer define the architecture by themselves.
# PAPER ONLY: this layer never places broker orders.

GAGARIN_ARCHITECTURE_VERSION = "5.3.1-GAGARIN-PREDICTION-AUTHORITY-1"
GAGARIN_FINAL_AUTHORITY = True
GAGARIN_REQUIRE_LIVE_FOR_ENTRY = os.getenv("GAGARIN_REQUIRE_LIVE_FOR_ENTRY", "1") == "1"
SIFTING_CACHE_TTL_SECONDS = float(os.getenv("SIFTING_CACHE_TTL_SECONDS", "20"))
SIFTING_QUOTE_CACHE = {}
GAGARIN_STATES = {
    "NO_DATA", "WAIT_SETUP", "SETUP_ACTIVE_ENTRY_BLOCKED",
    "READY_LONG", "READY_SHORT", "MANAGED", "NO_TRADE"
}


def gagarin_data_quality(name, candles, timeframes, intraday_candles=None):
    """Hard data-quality gate. Missing data becomes an explicit state."""
    issues = []
    if not candles or len(candles) < 120:
        issues.append("DAILY_DATA_INSUFFICIENT")
    if not intraday_candles or len(intraday_candles) < 80:
        issues.append("INTRADAY_DATA_INSUFFICIENT")
    required = ("4H", "1H", "15m")
    missing = [tf for tf in required if not (timeframes or {}).get(tf)]
    if missing:
        issues.append("MTF_MISSING:" + ",".join(missing))
    quality = 100.0
    quality -= 35.0 if "DAILY_DATA_INSUFFICIENT" in issues else 0.0
    quality -= 35.0 if "INTRADAY_DATA_INSUFFICIENT" in issues else 0.0
    quality -= min(30.0, 10.0 * len(missing))
    return {
        "state": "OK" if not issues else "DEGRADED",
        "quality": max(0.0, quality),
        "issues": issues,
        "commodity": name,
    }


def gagarin_regime_engine(analysis, candles):
    """Explainable regime layer using existing quantitative OHLC features."""
    inst = institutional_style_features(candles or [])
    legacy = (analysis.get("market_regime") or {})
    state = str(legacy.get("state") or legacy.get("regime") or inst.get("regime") or "UNKNOWN").upper()
    mapping = {
        "HIGH_VOL": "SHOCK" if safe_float(inst.get("volatility_percentile"), 0.0) >= 0.92 else "TRANSITION",
        "LOW_VOL": "RANGE",
        "NORMAL": "TREND" if inst.get("direction") in ("LONG", "SHORT") and inst.get("score", 0) >= 45 else "RANGE",
    }
    if state in mapping:
        state = mapping[state]
    if state not in {"TREND", "RANGE", "TRANSITION", "SHOCK", "UNKNOWN"}:
        state = "UNKNOWN"
    direction = inst.get("direction") or analysis.get("setup_direction") or analysis.get("model_signal") or "NONE"
    return {
        "state": state,
        "direction": direction,
        "score": round(safe_float(inst.get("score"), 0.0) or 0.0, 1),
        "volatility_percentile": round(safe_float(inst.get("volatility_percentile"), 0.5) or 0.5, 3),
        "source": "institutional_style_features + existing market_regime",
    }


def gagarin_structure_engine(analysis):
    """Unify MTF structure and Level-to-Level into one structural object."""
    d = analysis.get("setup_direction") or analysis.get("model_signal") or "NONE"
    tfs = analysis.get("timeframes") or {}
    structural = {tf: (tfs.get(tf, {}) or {}).get("direction", "NONE") for tf in ("4H", "1H", "15m")}
    fast = {tf: (tfs.get(tf, {}) or {}).get("direction", "NONE") for tf in ("5m", "1m")}
    aligned = sum(v == d for v in structural.values()) if d in ("LONG", "SHORT") else 0
    conflicts = sum(v not in ("NONE", d) for v in structural.values()) if d in ("LONG", "SHORT") else 0
    l2l = analysis.get("level_to_level") or {}
    return {
        "direction": d,
        "higher_tf": structural,
        "fast_tf": fast,
        "aligned": aligned,
        "conflicts": conflicts,
        "l2l_state": l2l.get("state", "N/D"),
        "l2l_score": safe_float(l2l.get("score"), 0.0) or 0.0,
        "behaviour": l2l.get("behaviour", "NESSUNA"),
        "breakout": bool(l2l.get("breakout")),
        "retest": bool(l2l.get("retest")),
        "fakeout": bool(l2l.get("fakeout")),
    }


def gagarin_location_engine(analysis):
    """Location is context, never an independent directional vote."""
    l2l = analysis.get("level_to_level") or {}
    avwap = analysis.get("anchored_vwap") or analysis.get("avwap") or {}
    vp = analysis.get("volume_profile") or {}
    return {
        "support": l2l.get("support"),
        "resistance": l2l.get("resistance"),
        "poc": vp.get("poc"),
        "vah": vp.get("vah"),
        "val": vp.get("val"),
        "avwap": avwap.get("value") if isinstance(avwap, dict) else avwap,
        "behaviour": l2l.get("behaviour", "NESSUNA"),
        "source": "L2L / structural levels / optional VP / AVWAP",
    }


def gagarin_strategy_router(regime, structure):
    """Select compatible strategy families before looking for a trigger."""
    state = regime.get("state", "UNKNOWN")
    behaviour = structure.get("behaviour")
    strategies = []
    if state == "TREND":
        strategies += ["TREND_PULLBACK", "BREAKOUT_RETEST"]
        if structure.get("breakout"):
            strategies.append("BREAKOUT")
    elif state == "RANGE":
        strategies += ["RANGE_REJECTION", "MEAN_REVERSION"]
        if structure.get("fakeout"):
            strategies.append("REVERSAL_SFP")
    elif state == "TRANSITION":
        strategies += ["BREAKOUT_RETEST", "REVERSAL_SFP"]
    elif state == "SHOCK":
        strategies = []
    else:
        strategies = []
    if behaviour == "BREAKOUT_RETEST" and "BREAKOUT_RETEST" not in strategies:
        strategies.append("BREAKOUT_RETEST")
    return {"regime": state, "allowed": list(dict.fromkeys(strategies))}


def gagarin_setup_engine(analysis, router):
    d = analysis.get("setup_direction") or analysis.get("model_signal") or "NONE"
    l2l = analysis.get("level_to_level") or {}
    behaviour = l2l.get("behaviour", "NESSUNA")
    if d not in ("LONG", "SHORT") or not router.get("allowed"):
        return {"state": "NONE", "direction": d, "type": "NONE", "quality": 0.0}
    if behaviour == "BREAKOUT_RETEST" and "BREAKOUT_RETEST" in router["allowed"]:
        stype = "BREAKOUT_RETEST"
    elif behaviour == "BREAKOUT" and "BREAKOUT" in router["allowed"]:
        stype = "BREAKOUT"
    elif behaviour == "FAKEOUT" and "REVERSAL_SFP" in router["allowed"]:
        stype = "REVERSAL_SFP"
    elif router["regime"] == "TREND":
        stype = "TREND_PULLBACK"
    elif router["regime"] == "RANGE":
        stype = "RANGE_REJECTION"
    else:
        stype = "TRANSITION"
    quality = safe_float(l2l.get("score"), 0.0) or 0.0
    return {"state": "ACTIVE" if quality >= 50 else "FORMING", "direction": d, "type": stype, "quality": round(quality, 1)}


def gagarin_trigger_engine(analysis):
    trigger = analysis.get("entry_trigger") or {}
    l2l = analysis.get("level_to_level") or {}
    confirmed = bool(trigger.get("confirmed"))
    if l2l.get("retest") and not l2l.get("fakeout"):
        confirmed = True
    if l2l.get("fakeout"):
        confirmed = False
    return {
        "confirmed": confirmed,
        "kind": trigger.get("kind") or l2l.get("behaviour", "NONE"),
        "timeframe": trigger.get("timeframe", "5m"),
        "score": safe_float(trigger.get("score"), 0.0) or 0.0,
        "source": "entry_trigger + L2L retest/fakeout",
    }


def gagarin_risk_engine(analysis):
    entry = safe_float(analysis.get("entry"), safe_float(analysis.get("price"), 0.0)) or 0.0
    stop = safe_float(analysis.get("stop"), 0.0) or 0.0
    atrv = safe_float(analysis.get("atr"), 0.0) or 0.0
    risk_distance = abs(entry - stop) if entry and stop else 0.0
    stop_atr = risk_distance / atrv if atrv > 0 else 999.0
    tp = [safe_float(analysis.get(k), 0.0) or 0.0 for k in ("tp1", "tp2", "tp3")]
    rr = [abs(x-entry)/risk_distance if risk_distance else 0.0 for x in tp]
    return {
        "valid_stop": risk_distance > 0,
        "stop_distance": risk_distance,
        "stop_atr": stop_atr,
        "rr_tp1": rr[0], "rr_tp2": rr[1], "rr_tp3": rr[2],
        "rr_main": rr[2],
        "risk_mode": (analysis.get("risk") or {}).get("mode", "UNKNOWN"),
    }


def gagarin_safety_engine(analysis, data_quality, regime, setup, trigger, risk):
    blockers = []
    if data_quality.get("state") == "DEGRADED": blockers += data_quality.get("issues", [])
    if regime.get("state") in ("SHOCK", "UNKNOWN"): blockers.append("REGIME_" + regime.get("state"))
    if setup.get("state") == "NONE": blockers.append("NO_SETUP")
    if not risk.get("valid_stop"): blockers.append("INVALID_STOP")
    if risk.get("stop_atr", 999) > MAX_ENTRY_STOP_ATR: blockers.append("STOP_GT_MAX_ATR")
    if risk.get("rr_tp1", 0) + 0.005 < MIN_ENTRY_RR_TP1: blockers.append("RR_TP1_FAIL")
    if risk.get("rr_tp2", 0) + 0.005 < MIN_ENTRY_RR_TP2: blockers.append("RR_TP2_FAIL")
    if risk.get("rr_main", 0) + 1e-9 < MIN_ENTRY_RR: blockers.append("RR_MAIN_FAIL")
    legacy_risk = analysis.get("risk") or {}
    if legacy_risk.get("mode") in ("SHOCK", "ERROR"): blockers.append("LEGACY_RISK_" + str(legacy_risk.get("mode")))
    if (analysis.get("reversal") or {}).get("stage") == "CONFIRMED": blockers.append("REVERSAL_CONFIRMED")
    pred = analysis.get("prediction_v53") or {}
    if pred and not pred.get("operational", False):
        blockers.append("PREDICTION_NOT_CONFIRMED")
    return {"safe": not blockers, "blockers": list(dict.fromkeys(blockers))}


def gagarin_entry_policy(analysis, setup, trigger, risk, safety):
    """Final permission: hard blockers first, then existing thresholds."""
    d = setup.get("direction")
    prob = safe_float(analysis.get("entry_probability"), safe_float(analysis.get("probability"), 0.0)) or 0.0
    prob = prob * 100.0 if prob <= 1.5 else prob
    quality = safe_float(analysis.get("quality"), 0.0) or 0.0
    confidence = safe_float(analysis.get("confidence"), 0.0) or 0.0
    if not safety.get("safe"):
        return {"state": "BLOCKED", "decision": "NO TRADE", "direction": d, "probability": prob,
                "blockers": safety["blockers"]}
    missing = []
    if d not in ("LONG", "SHORT"): missing.append("DIRECTION")
    if not trigger.get("confirmed"): missing.append("TRIGGER")
    if prob < MIN_ENTRY_PROBABILITY: missing.append("PROBABILITY")
    if quality < MIN_ENTRY_QUALITY: missing.append("QUALITY")
    if confidence < MIN_ENTRY_CONFIDENCE: missing.append("CONFIDENCE")
    if risk.get("rr_main", 0) + 1e-9 < MIN_ENTRY_RR: missing.append("RR")
    if missing:
        return {"state": "WAIT", "decision": f"{d} — ASPETTARE" if d in ("LONG", "SHORT") else "WAIT",
                "direction": d, "probability": prob, "blockers": missing}
    return {"state": "READY_LONG" if d == "LONG" else "READY_SHORT", "decision": "ENTRARE",
            "direction": d, "probability": prob, "blockers": []}



def gagarin_normalize_final_state(analysis):
    """Keep one coherent final Gagarin snapshot; never overwrite valid values with UNKNOWN/NONE."""
    try:
        g = analysis.get("gagarin")
        if not isinstance(g, dict):
            g = {}
            analysis["gagarin"] = g

        # Accept both nested and legacy top-level representations.
        regime = g.get("regime") or analysis.get("gagarin_regime")
        setup = g.get("setup") or analysis.get("gagarin_setup")
        trigger = g.get("trigger")
        if trigger is None:
            trigger = analysis.get("gagarin_trigger")

        # Prefer an already computed, meaningful value.
        if regime and str(regime).upper() not in {"UNKNOWN", "NONE", "N/A", "NULL"}:
            g["regime"] = regime
        elif analysis.get("regime") and str(analysis.get("regime")).upper() not in {"UNKNOWN", "NONE"}:
            g["regime"] = analysis["regime"]

        if setup and str(setup).upper() not in {"UNKNOWN", "NONE", "N/A", "NULL"}:
            g["setup"] = setup

        if trigger is not None:
            g["trigger"] = bool(trigger)

        # If the state is blocked/waiting, preserve the concrete blockers but
        # don't invent UNKNOWN/NO_SETUP when a valid setup/regime exists.
        blockers = g.get("blockers")
        if not isinstance(blockers, list):
            blockers = list(analysis.get("gagarin_blockers") or [])

        regime_final = str(g.get("regime") or "").upper()
        setup_final = str(g.get("setup") or "").upper()

        blockers = [str(x) for x in blockers if x]
        if regime_final not in {"", "UNKNOWN", "NONE"}:
            blockers = [x for x in blockers if x != "REGIME_UNKNOWN"]
        if setup_final not in {"", "UNKNOWN", "NONE"}:
            blockers = [x for x in blockers if x != "NO_SETUP"]

        g["blockers"] = blockers
        analysis["gagarin"] = g
        analysis["gagarin_blockers"] = blockers

        # Keep the displayed state separate from fresh-entry eligibility.
        # A present trigger never authorizes an entry by itself.
        if not analysis.get("operational_entry_allowed"):
            current_state = str(g.get("state") or analysis.get("gagarin_state") or "WAIT").upper()
            if current_state in {"READY", "ENTRY_CONFIRMED", "ENTRY_AUTHORIZED"}:
                g["state"] = "BLOCKED"
                analysis["gagarin_state"] = "BLOCKED"

        return analysis
    except Exception:
        return analysis

def gagarin_apply_final_authority(item):
    """Rebuild Gagarin after every legacy/finalization layer and make it authoritative."""
    if not item.get("available"):
        return
    a = item.get("analysis") or {}
    candles = item.get("candles") or []
    timeframes = a.get("timeframes") or {}
    intraday = a.get("intraday_candles") or []
    dq = gagarin_data_quality(item.get("name", a.get("commodity_name", "N/D")), candles, timeframes, intraday)
    live_status = a.get("live_price_status", "NOT_CHECKED")
    if GAGARIN_REQUIRE_LIVE_FOR_ENTRY and live_status != "LIVE":
        dq.setdefault("issues", []).append("LIVE_PRICE_NOT_FRESH")
        dq["state"] = "DEGRADED"
        dq["quality"] = min(float(dq.get("quality", 100.0)), 50.0)
    regime = gagarin_regime_engine(a, candles)
    structure = gagarin_structure_engine(a)
    location = gagarin_location_engine(a)
    router = gagarin_strategy_router(regime, structure)
    setup = gagarin_setup_engine(a, router)
    trigger = gagarin_trigger_engine(a)
    risk = gagarin_risk_engine(a)
    safety = gagarin_safety_engine(a, dq, regime, setup, trigger, risk)
    policy = gagarin_entry_policy(a, setup, trigger, risk, safety)
    # Absolute final authority: legacy signal can never override Gagarin.
    legacy_signal = a.get("signal")
    a["legacy_signal_shadow"] = legacy_signal
    if policy["state"] == "READY_LONG":
        a["signal"] = "LONG"
    elif policy["state"] == "READY_SHORT":
        a["signal"] = "SHORT"
    else:
        a["signal"] = "WAIT"
        a["action_label"] = "ATTENDERE"
        a["strong_confirmation"] = False
    a["gagarin"] = {
        "architecture_version": GAGARIN_ARCHITECTURE_VERSION,
        "data_quality": dq, "regime": regime, "structure": structure,
        "location": location, "strategy_router": router, "setup": setup,
        "trigger": trigger, "risk": risk, "safety": safety, "entry_policy": policy,
    }
    a["gagarin_state"] = policy["state"]
    a["gagarin_blockers"] = policy.get("blockers", [])
    a["gagarin_authority"] = True
    a["operational_entry_allowed"] = policy["state"] in ("READY_LONG", "READY_SHORT")



def gagarin_position_management(position, analysis, current_price):
    """Gagarin position-management decision for an already-open paper position.

    This is deliberately different from the entry policy: an existing position
    is not required to satisfy the fresh-entry thresholds again.  The question
    is whether the original thesis is still valid, invalidated, or needs risk
    protection.
    """
    if not position or not analysis or current_price is None:
        return {"action": "HOLD", "status": "HOLD", "reason": "DATI INSUFFICIENTI PER UNA NUOVA DECISIONE"}

    direction = str(position.get("direction", "WAIT")).upper()
    opposite = "SHORT" if direction == "LONG" else "LONG"
    g = analysis.get("gagarin", {}) or {}
    regime = (g.get("regime") or {}).get("state", "UNKNOWN")
    structure = g.get("structure") or {}
    setup = g.get("setup") or {}
    trigger = g.get("trigger") or {}
    dq = g.get("data_quality") or {}

    blockers = []
    if dq.get("state") == "DEGRADED":
        # Data degradation alone does not force an exit; it prevents a new
        # thesis from being declared and keeps the position under observation.
        blockers.extend(dq.get("issues", [])[:4])

    if regime == "SHOCK":
        return {
            "action": "HOLD_PROTECT", "status": "HOLD_PROTECT",
            "reason": "REGIME SHOCK — NON CHIUDERE AUTOMATICAMENTE, PROTEGGERE IL RISCHIO",
            "blockers": ["REGIME_SHOCK"],
        }

    structural_direction = structure.get("direction", "NONE")
    aligned = int(structure.get("aligned", 0) or 0)
    conflicts = int(structure.get("conflicts", 0) or 0)
    reversal_stage = str((analysis.get("reversal") or {}).get("stage", "")).upper()
    opposite_signal = str(analysis.get("signal", "WAIT")).upper() == opposite

    # Absolute invalidation: confirmed reversal against the held direction.
    if reversal_stage == "CONFIRMED" and opposite_signal:
        return {
            "action": "EXIT", "status": "EXIT",
            "reason": "TESI INVALIDATA — INVERSIONE OPPOSTA CONFERMATA",
            "blockers": ["REVERSAL_CONFIRMED"],
        }

    # Structural invalidation is stronger than a temporary weak trigger.
    if structural_direction == opposite and aligned >= 2 and conflicts >= 2:
        return {
            "action": "EXIT", "status": "EXIT",
            "reason": f"STRUTTURA MTF CONTRO {direction} — TESI INVALIDATA",
            "blockers": ["STRUCTURE_OPPOSITE"],
        }

    # If the setup has disappeared but higher-timeframe structure is still on
    # our side, keep the position rather than forcing an exit.
    if structural_direction == direction and aligned >= 1 and conflicts <= 1:
        return {
            "action": "HOLD", "status": "HOLD",
            "reason": f"NON CHIUDERE — TESI {direction} ANCORA VALIDA",
            "details": {
                "regime": regime,
                "aligned_htf": aligned,
                "conflicts": conflicts,
                "setup": setup.get("type", "N/D"),
                "trigger_confirmed": bool(trigger.get("confirmed")),
            },
        }

    # Transition/range with no confirmed opposite signal is a caution state,
    # not an automatic exit.
    return {
        "action": "HOLD_PROTECT", "status": "HOLD_PROTECT",
        "reason": f"MANTENERE CON ATTENZIONE — TESI {direction} NON INVALIDATA",
        "details": {
            "regime": regime,
            "aligned_htf": aligned,
            "conflicts": conflicts,
            "setup": setup.get("type", "N/D"),
            "trigger_confirmed": bool(trigger.get("confirmed")),
        },
        "blockers": blockers,
    }

def soyuz_gagarin_pipeline(name, symbol, usd, global_intel, trading_knowledge):
    """Single commodity orchestration pipeline for Soyuz v5.2 Gagarin."""
    candles = get_daily_data(symbol)
    if len(candles) < 120:
        raise RuntimeError(f"Dati giornalieri insufficienti ({len(candles)}/120)")
    source_check = compare_sources(name, symbol, candles)
    dataset = build_dataset(candles)
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
    hint = analysis_direction_hint(timeframes)
    session = session_engine(name, symbol, hint if hint in ("LONG", "SHORT") else "NONE")
    intraday_candles = get_data(symbol, "1h", 1200)
    if len(intraday_candles) < 80:
        raise RuntimeError(f"Storico 1H insufficiente per Entry/Timing ({len(intraday_candles)}/80)")
    pattern_timeframes = {"1H": intraday_candles}
    for tf, interval, size in (("4H", "4h", 500), ("15m", "15min", 500), ("5m", "5min", 500), ("1m", "1min", 500)):
        try:
            c = get_data(symbol, interval, size)
            if len(c) >= 30:
                pattern_timeframes[tf] = c
        except Exception as exc:
            print(f"   ⚠️ Pattern {tf}: {exc}")
    analysis = analyze(candles, dataset, model, bt, usd, news, timeframes, political,
                       commodity_name=name, global_impact=global_impact, session=session,
                       intraday_candles=intraday_candles, pattern_timeframes=pattern_timeframes,
                       trading_knowledge=trading_knowledge)
    if analysis is None:
        raise RuntimeError("Analisi quantitativa non disponibile")
    analysis.update({"symbol": symbol, "pattern_timeframes": pattern_timeframes or {}, "source_check": source_check or {}, "commodity_name": name, "timeframes": timeframes, "intraday_candles": intraday_candles})
    weather = weather_intelligence(name)
    disasters = natural_disaster_intelligence(name)
    apply_weather_and_disaster_layers(analysis, weather, disasters)
    level_to_level_engine(analysis, commodity_name=name, candles=candles, pattern_timeframes=pattern_timeframes)
    analysis["price_action"] = price_action_context_engine(analysis)
    # v5.3 prediction chain: scenario/confirmation layer before final Gagarin authority.
    analysis["prediction_v53"] = prediction_engine_v53(analysis)
    try:
        adaptive_levels = adaptive_risk_levels(analysis, candles, analysis.get("setup_direction") or analysis.get("model_signal"))
    except Exception as _sltp_exc:
        # SL/TP failure must never turn valid market data into DATA_UNAVAILABLE.
        _price = safe_float(analysis.get("entry"), safe_float(analysis.get("price"), 0)) or 0
        _atr = safe_float(analysis.get("atr"), 0) or 0
        _atr = _atr if _atr > 0 else max(_price * 0.01, 1e-9)
        _dir = analysis.get("setup_direction") or analysis.get("model_signal")
        _risk = _atr
        if _dir == "LONG":
            _stop = _price - _risk
            _tp1, _tp2, _tp3 = _price + 1.5*_risk, _price + 2.0*_risk, _price + 2.5*_risk
        elif _dir == "SHORT":
            _stop = _price + _risk
            _tp1, _tp2, _tp3 = _price - 1.5*_risk, _price - 2.0*_risk, _price - 2.5*_risk
        else:
            _stop = _tp1 = _tp2 = _tp3 = None
        adaptive_levels = {
            "available": bool(_price > 0 and _dir in ("LONG","SHORT")), "valid": False,
            "theoretical_only": True, "engine_version": SLTP_ENGINE_VERSION,
            "reason": f"SLTP_ENGINE_ERROR:{str(_sltp_exc)[:120]}",
            "entry": _price, "stop": _price_round(_stop) if _stop else None,
            "tp1": _price_round(_tp1) if _tp1 else None, "tp2": _price_round(_tp2) if _tp2 else None,
            "tp3": _price_round(_tp3) if _tp3 else None, "risk_distance": round(_risk,6),
            "rr_tp1": 1.5 if _stop else 0.0, "rr_tp2": 2.0 if _stop else 0.0, "rr_tp3": 2.5 if _stop else 0.0,
        }
    # SLTP 3.0 can be computationally available but intentionally unable to
    # produce a valid structural stop/target plan. Never index missing keys and
    # never fall back to the legacy synthetic levels in that case.
    analysis["adaptive_risk"] = adaptive_levels
    # Recompute once after SL/TP so prediction uses the actual structural space.
    analysis["prediction_v53"] = prediction_engine_v53(analysis)
    analysis["data_available"] = True
    analysis["sl_tp_available"] = bool(adaptive_levels.get("available"))
    analysis["sl_tp_theoretical_only"] = bool(adaptive_levels.get("theoretical_only"))
    analysis["plan_status"] = "THEORETICAL_ONLY" if adaptive_levels.get("theoretical_only") or not adaptive_levels.get("valid") else "OPERATIONAL_CANDIDATE"
    if adaptive_levels.get("available") and all(k in adaptive_levels for k in ("stop", "tp1", "tp2", "tp3")):
        analysis.update({k: adaptive_levels[k] for k in ("stop", "tp1", "tp2", "tp3")})
    elif adaptive_levels.get("reason") == "NO_STRUCTURAL_SL_WITHIN_MAX_ATR":
        analysis.update({"stop": None, "tp1": None, "tp2": None, "tp3": None})
    apply_futures_structure(analysis, futures_structure_engine(name))
    apply_market_intelligence_v41(analysis, name, news, political, global_intel)
    apply_sole24_context(analysis, name)
    apply_commodity_knowledge_engine_v5(analysis, name, news, usd, global_intel)
    apply_pre_usa_timing_v5(analysis, name)
    analysis["v3_context"] = v3_context_summary(analysis)

    # Explicit architecture objects.
    dq = gagarin_data_quality(name, candles, timeframes, intraday_candles)
    regime = gagarin_regime_engine(analysis, candles)
    structure = gagarin_structure_engine(analysis)
    location = gagarin_location_engine(analysis)
    router = gagarin_strategy_router(regime, structure)
    setup = gagarin_setup_engine(analysis, router)
    trigger = gagarin_trigger_engine(analysis)
    risk = gagarin_risk_engine(analysis)
    safety = gagarin_safety_engine(analysis, dq, regime, setup, trigger, risk)
    policy = gagarin_entry_policy(analysis, setup, trigger, risk, safety)
    analysis["gagarin"] = {
        "architecture_version": GAGARIN_ARCHITECTURE_VERSION,
        "data_quality": dq, "regime": regime, "structure": structure,
        "location": location, "strategy_router": router, "setup": setup,
        "trigger": trigger, "risk": risk, "safety": safety, "entry_policy": policy,
    }
    analysis["gagarin_state"] = policy["state"]
    analysis["gagarin_blockers"] = policy.get("blockers", [])
    # The legacy signal remains available for diagnostics; Gagarin is the
    # authoritative architecture state once all later finalization layers run.
    analysis = gagarin_finalize_consistent_snapshot(analysis)
    return {"candles": candles, "analysis": analysis, "backtest": bt, "source_check": source_check}

# ============================================================

# --- GAGARIN TELEGRAM SAFETY LABEL ---
def gagarin_plan_label(analysis):
    """Render only a resolved user-facing plan label."""
    try:
        snap = gagarin_display_snapshot(analysis)
        if snap["operational_entry_allowed"] and str(snap["state"]).upper() in {
            "READY", "ENTRY_CONFIRMED", "ENTRY_AUTHORIZED"
        }:
            return "PIANO OPERATIVO — ENTRATA AUTORIZZATA"
    except Exception:
        pass
    return "PIANO POTENZIALE — NON ENTRARE"


def gagarin_finalize_consistent_snapshot(analysis):
    """Create one authoritative, coherent Gagarin snapshot for display and gating."""
    if not isinstance(analysis, dict):
        return analysis

    g = analysis.get("gagarin")
    if not isinstance(g, dict):
        g = {}
        analysis["gagarin"] = g

    # Recover the last concrete values before any generic fallback can overwrite them.
    regime_candidates = [
        g.get("regime"),
        analysis.get("gagarin_regime"),
        analysis.get("regime"),
    ]
    setup_candidates = [
        g.get("setup"),
        analysis.get("gagarin_setup"),
    ]

    def concrete(value, invalid=("UNKNOWN", "NONE", "N/A", "NULL", "")):
        if value is None:
            return None
        s = str(value).strip()
        return None if s.upper() in invalid else value

    regime = next((concrete(v) for v in regime_candidates if concrete(v) is not None), None)
    setup = next((concrete(v) for v in setup_candidates if concrete(v) is not None), None)

    # Gagarin objects are dictionaries; display must use their explicit state/type
    # rather than stringifying the whole dictionary (which previously produced
    # UNKNOWN/NONE in the final summary despite valid earlier values).
    if isinstance(regime, dict):
        regime = concrete(regime.get("state") or regime.get("regime"))
    if isinstance(setup, dict):
        setup = concrete(setup.get("type") or setup.get("state"))

    # Preserve explicit trigger information, but never treat it as authorization.
    trigger = g.get("trigger")
    if trigger is None:
        trigger = analysis.get("gagarin_trigger")
    if trigger is not None:
        trigger = bool(trigger)

    # Prefer explicit final state; otherwise derive a safe state.
    state = str(
        g.get("state")
        or analysis.get("gagarin_state")
        or analysis.get("state")
        or "WAIT"
    ).upper()

    blockers = g.get("blockers")
    if not isinstance(blockers, list):
        blockers = list(analysis.get("gagarin_blockers") or [])
    blockers = [str(x) for x in blockers if x]

    if regime is not None:
        blockers = [x for x in blockers if x != "REGIME_UNKNOWN"]
    if setup is not None:
        blockers = [x for x in blockers if x != "NO_SETUP"]

    # Operational authorization remains a separate boolean.
    allowed = bool(analysis.get("operational_entry_allowed") or g.get("operational_entry_allowed"))

    # Safety/threshold blockers always prevent an unauthorized READY state.
    if not allowed and state in {"READY", "ENTRY_CONFIRMED", "ENTRY_AUTHORIZED"}:
        state = "BLOCKED"

    g["regime"] = regime or "UNKNOWN"
    g["setup"] = setup or "NONE"
    g["trigger"] = trigger
    g["state"] = state
    g["blockers"] = blockers
    g["operational_entry_allowed"] = allowed

    analysis["gagarin"] = g
    analysis["gagarin_state"] = state
    analysis["gagarin_blockers"] = blockers
    analysis["operational_entry_allowed"] = allowed

    return analysis


def gagarin_plan_label(analysis):
    """Render the plan label from the already-finalized canonical Gagarin state."""
    try:
        snap = gagarin_display_snapshot(analysis)
        state = str(snap.get("state", "")).upper()
        if snap.get("operational_entry_allowed") and state in {"READY", "ENTRY_CONFIRMED", "ENTRY_AUTHORIZED", "READY_LONG", "READY_SHORT"}:
            return "PIANO OPERATIVO — ENTRATA AUTORIZZATA"
    except Exception:
        pass
    return "PIANO TEORICO — NON OPERATIVO"


def gagarin_display_snapshot(analysis):
    """Return the single canonical Gagarin state already stored in analysis.

    IMPORTANT: this function is display-only. It must never re-run the full
    commodity pipeline, because doing so can create recursive/recomputed states.
    """
    a = analysis if isinstance(analysis, dict) else {}
    g = a.get("gagarin") if isinstance(a.get("gagarin"), dict) else {}
    policy = g.get("entry_policy") if isinstance(g.get("entry_policy"), dict) else {}
    regime = g.get("regime", {})
    setup = g.get("setup", {})
    trigger = g.get("trigger", {})
    state = a.get("gagarin_state") or policy.get("state") or "WAIT"
    blockers = a.get("gagarin_blockers")
    if blockers is None:
        blockers = policy.get("blockers", [])
    allowed = a.get("operational_entry_allowed")
    if allowed is None:
        allowed = policy.get("operational_entry_allowed", False)
    pa = a.get("prediction_authority_v531") if isinstance(a.get("prediction_authority_v531"), dict) else None
    if pa:
        regime = pa.get("regime", regime)
        setup = pa.get("setup", setup)
        trigger = dict(trigger) if isinstance(trigger, dict) else {}
        trigger["confirmed"] = bool(pa.get("trigger_confirmed", False))
        state = pa.get("state", state)
    return {
        "regime": regime,
        "setup": setup,
        "trigger": trigger,
        "state": state,
        "blockers": list(blockers or []),
        "operational_entry_allowed": bool(allowed),
    }

# MAIN
# ============================================================

def main():
    print()
    print("=" * 70)
    print(f"🌍 COMMODITIES BOT v{BOT_VERSION}")
    print("MORNING + USA + EVENT-DRIVEN + DAILY STATS | PAPER ONLY")
    print("SOYUZ GAGARIN ARCHITECTURE | DATA → REGIME → STRUCTURE → ZONE → PATTERN → CONFIRM → SL/TP → PREDICTION → RISK → SAFETY")
    print("COMMUNICATION: MORNING + USA + MATERIAL EVENTS | INTERNAL ANALYSIS SILENT")
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

    # In on-demand mode, a request for a single commodity analyzes only that
    # commodity. Cross-sectional commands (classifica, migliore, weekly,
    # monthly, segnali) keep the full universe because they need all rankings.
    requested_scope = telegram_requested_scope(ON_DEMAND_TELEGRAM_REQUEST) if ON_DEMAND_ONLY else None
    analysis_names = [requested_scope] if requested_scope else list(COMMODITIES)
    if requested_scope:
        print(f"🎯 ON-DEMAND SCOPE: {requested_scope} — analisi singola commodity")

    for name in analysis_names:
        symbol = resolved_symbols.get(name, COMMODITIES[name])
        print(f"🔎 Analizzo {name} [{symbol}]...")

        # Safe per-commodity fallbacks used only if the analysis raises.
        global_impact = global_intel or {
            "score": 0.0, "direction": "NEUTRALE", "mode": "NORMAL",
            "shock_intensity": 0.0,
        }
        candles = []
        analysis = {}
        bt = {}
        source_check = {}

        try:
            pipeline = soyuz_gagarin_pipeline(
                name=name, symbol=symbol, usd=usd, global_intel=global_intel,
                trading_knowledge=trading_knowledge,
            )
            candles = pipeline["candles"]
            analysis = pipeline["analysis"]
            # v5.3.1: canonical prediction authority after final Gagarin state.
            analysis["prediction_authority_v531"] = prediction_authority_v531(analysis)
            bt = pipeline["backtest"]
            source_check = pipeline["source_check"]
            gdisp = gagarin_display_snapshot(analysis)
            greg = gdisp.get("regime")
            if isinstance(greg, dict):
                greg = greg.get("state") or greg.get("regime") or greg.get("label") or "UNKNOWN"
            gsetup = gdisp.get("setup")
            if isinstance(gsetup, dict):
                gsetup = gsetup.get("type") or gsetup.get("setup") or gsetup.get("name") or "NONE"
            gtrigger = gdisp.get("trigger")
            if isinstance(gtrigger, dict):
                gtrigger = gtrigger.get("confirmed")
            _pa = analysis.get("prediction_authority_v531") or {}
            if _pa:
                greg = _pa.get("regime", greg)
                gsetup = _pa.get("setup", gsetup)
                gtrigger = _pa.get("trigger_confirmed", False)
            print(
                f"   🧭 GAGARIN: {gdisp.get('state')} | REGIME {greg} | "
                f"SETUP {gsetup} | TRIGGER {gtrigger}"
            )
            _ar_diag = analysis.get("adaptive_risk", {}) or {}
            print(
                f"   🧪 DATA=OK | SLTP={'THEORETICAL' if _ar_diag.get('theoretical_only') else 'OK' if _ar_diag.get('available') else 'N/A'} | "
                f"ENTRY={'YES' if analysis.get('operational_entry_allowed') else 'NO'} | "
                f"PLAN={analysis.get('plan_status','N/D')}"
            )

            results.append({
                "name": name,
                "symbol": symbol,
                "candles": candles,
                "analysis": analysis,
                "backtest": bt,
                "available": True,
                "source_check": source_check,
            })

            try:
                print(
                    f"   ✅ ANALIZZATA | MODELLO {analysis.get('model_signal','N/D')} | "
                    f"OPERATIVO {analysis.get('signal','WAIT')} | SCORE {safe_float(analysis.get('score'),0) or 0:.0f} | "
                    f"QUALITÀ {safe_float((analysis.get('risk') or {}).get('market_quality'),0) or 0:.0f} | "
                    f"SESSIONE {(analysis.get('session') or {}).get('current_band','N/D')}"
                )
            except Exception as _display_error:
                print(f"   ⚠️ ANALISI OK | errore sola visualizzazione: {_display_error}")

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

    # v4.1: cross-commodity relative-strength/dispersion lens.
    apply_cross_commodity_intelligence_v41(results)

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

    # v4.6: SiftingIO LIVE PRICE.
    # The analytical history remains unchanged. Only the current price/entry
    # reference is replaced by the live BID/ASK quote, then SL/TP and the final
    # signal engine are recalculated from that live reference.
    if SIFTING_LIVE_ENABLED:
        for _item in results:
            if not _item.get("available"):
                continue
            _a = _item["analysis"]
            _name = _item.get("name")
            apply_sifting_live_price(_a, _name)

            if _a.get("live_price_status") == "LIVE":
                _direction = _a.get("setup_direction") or _a.get("model_signal") or _a.get("signal")
                _adaptive_live = adaptive_risk_levels(
                    _a,
                    _item.get("candles") or [],
                    _direction,
                )
                _a["adaptive_risk"] = _adaptive_live
                _a["data_available"] = True
                _a["sl_tp_available"] = bool(_adaptive_live.get("available"))
                _a["sl_tp_theoretical_only"] = bool(_adaptive_live.get("theoretical_only"))
                _a["plan_status"] = "THEORETICAL_ONLY" if _adaptive_live.get("theoretical_only") or not _adaptive_live.get("valid") else "OPERATIONAL_CANDIDATE"
                if _adaptive_live.get("available") and all(k in _adaptive_live for k in ("stop", "tp1", "tp2", "tp3")):
                    _a.update({
                        "stop": _adaptive_live["stop"],
                        "tp1": _adaptive_live["tp1"],
                        "tp2": _adaptive_live["tp2"],
                        "tp3": _adaptive_live["tp3"],
                    })
                elif _adaptive_live.get("reason") == "NO_STRUCTURAL_SL_WITHIN_MAX_ATR":
                    _a.update({"stop": None, "tp1": None, "tp2": None, "tp3": None})

                # Refresh dependent final metrics using the live entry.
                finalize_v26_analysis(_a)

                # IMPORTANT: live SL/TP can change RR, STOP/ATR and confluence.
                # Re-run the entry/confluence policy first, then rebuild the
                # authoritative Signal Engine from the same live levels.
                smart_entry_engine(_a)
                signal_engine_v42(_a, _item.get("candles") or [])
                apply_pre_usa_timing_v5(_a, _name)
                # SL/TP 2.0 is now part of final Gagarin authority: after live
                # execution price and every legacy recalculation, rebuild the
                # structural CFD risk/target model and re-run policy.
                try:
                    _a["final_direction"] = _a.get("setup_direction") or _a.get("model_signal") or _a.get("signal")
                    _g = _a.get("gagarin") or {}
                    _dq = gagarin_data_quality(_name, _item.get("candles") or [], _a.get("timeframes") or {}, _a.get("intraday_candles") or [])
                    _reg = gagarin_regime_engine(_a, _item.get("candles") or [])
                    _str = gagarin_structure_engine(_a)
                    _loc = gagarin_location_engine(_a)
                    _router = gagarin_strategy_router(_reg, _str)
                    _setup = gagarin_setup_engine(_a, _router)
                    _trig = gagarin_trigger_engine(_a)
                    _risk = gagarin_risk_engine(_a)
                    _safe = gagarin_safety_engine(_a, _dq, _reg, _setup, _trig, _risk)
                    _policy = gagarin_entry_policy(_a, _setup, _trig, _risk, _safe)
                    _a["gagarin"] = {"architecture_version": GAGARIN_ARCHITECTURE_VERSION, "data_quality": _dq, "regime": _reg, "structure": _str, "location": _loc, "strategy_router": _router, "setup": _setup, "trigger": _trig, "risk": _risk, "safety": _safe, "entry_policy": _policy}
                    _a["gagarin_state"] = _policy["state"]
                    _a["gagarin_blockers"] = _policy.get("blockers", [])
                    _a["gagarin_authority"] = True
                    _a["operational_entry_allowed"] = _policy["state"] in ("READY_LONG", "READY_SHORT")
                    if not _a["operational_entry_allowed"]:
                        _a["signal"] = "WAIT"
                        _a["action_label"] = "ATTENDERE"
                        _a["strong_confirmation"] = False
                except Exception as _gexc:
                    _a["gagarin_sltp2_error"] = str(_gexc)

    # v4.6 coherence: setup_direction is the single final analytical direction.
    # model_signal remains the raw quantitative model direction for diagnostics,
    # while operational signal may be WAIT because of risk/confluence gates.
    for _item in results:
        if _item.get("available"):
            _a = _item["analysis"]
            _a["final_direction"] = _a.get("setup_direction") or _a.get("model_signal") or "WAIT"

    # v4.2: build one actionable, explainable signal from the finalized layers.
    apply_signal_engine_v42(results)

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
        print(f"   {_it['name']}: {_a.get('setup_direction')} | score={_a.get('score',0):.1f} q={_a.get('quality',0):.1f} conf={_a.get('confidence',0):.1f} prob={_a.get('entry_probability',0):.1f}% | L2L={_l.get('score',0):.1f} {_l.get('behaviour','-')} gate={_l.get('gate')} | MTF={_a.get('structural_same',0)} | fast_opp={_a.get('fast_conflicts',0)} | risk={_r.get('mode')} mq={_r.get('market_quality',0):.1f} rb={safe_float(_a.get('risk_benefit',{}).get('score'),0) or 0:.1f} | trigger={_t.get('kind')} {_t.get('timeframe','-')} {_t.get('score',0):.1f} confirmed={_t.get('confirmed')} | state={_a.get('entry_state')} | GAGARIN={_a.get('gagarin_state','N/D')} | regime={(_a.get('market_regime',{}) or {}).get('state','N/D')} | blockers={','.join(_a.get('gagarin_blockers',[]) or _a.get('entry_blockers',[])) or 'NESSUNO'} | warnings={','.join(_a.get('entry_warnings',[])) or 'NESSUNO'}")

    new_predictions, _prediction_log = record_predictions(results)
    print(f"📝 Prediction Journal: {new_predictions} nuove previsioni registrate")

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
    # FINAL GAGARIN AUTHORITY + DUAL RANKING
    # ========================================================
    # Re-run the architecture after ALL legacy/finalization/live layers.
    # This closes the previous failure where RBOB could be LONG 99 while
    # Gagarin simultaneously reported SHOCK/NO_SETUP/BLOCKED.
    for item in results:
        gagarin_apply_final_authority(item)

    # MARKET RANKING = analytical opportunity, regardless of entry permission.
    for item in results:
        if item.get("available"):
            a = item["analysis"]
            rb = a.get("risk_benefit", {})
            base_rb = safe_float(rb.get("score"), a.get("score", 0)) or 0
            q = safe_float(a.get("quality"), 0) or 0
            conf = safe_float(a.get("confidence"), 0) or 0
            pred = a.get("prediction_v53") or {}
            rr3 = safe_float(pred.get("rr_tp3"), 0) or 0
            pred_score = safe_float(pred.get("score"), 50) or 50
            space = safe_float(pred.get("space_score"), 0) or 0
            item["market_ranking_score"] = clamp(base_rb * 0.60 + q * 0.25 + conf * 0.15 + safe_float(a.get("early_alignment_bonus"), 0), 0, 100)
            # Operational ranking is deliberately separate: only a fully authorized
            # setup with structural prediction + real SL/TP space can enter this list.
            if a.get("operational_entry_allowed"):
                item["opportunity_score_v53"] = clamp(
                    item["market_ranking_score"]*0.35 + pred_score*0.25 + q*0.15 + conf*0.10 +
                    min(rr3/2.5, 1.0)*10 + min(space/80.0,1.0)*5, 0, 100)
                item["ranking_score"] = item["opportunity_score_v53"]
            else:
                item["opportunity_score_v53"] = -1
                item["ranking_score"] = -1
        else:
            item["market_ranking_score"] = -1
            item["ranking_score"] = -1

    market_ranked = sorted(results, key=lambda x: x.get("market_ranking_score", -1), reverse=True)
    ranked = sorted(results, key=lambda x: x.get("ranking_score", -1), reverse=True)
    available_ranked = [x for x in ranked if x.get("available") and x.get("analysis",{}).get("operational_entry_allowed")]
    market_available_ranked = [x for x in market_ranked if x.get("available") and x.get("analysis",{}).get("score", -1) >= 0]
    # If there is no executable setup, still report the best MARKET opportunity,
    # but it is explicitly WAIT and can never open a position.
    best = available_ranked[0] if available_ranked else (market_available_ranked[0] if market_available_ranked else None)
    if best is None:
        raise RuntimeError("Nessuna commodity analizzabile: tutte le pipeline dati hanno fallito.")

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

            # Existing-position thesis check is separate from fresh-entry policy.
            gagarin_management = gagarin_position_management(
                position, current["analysis"], current_price
            )
            management = manage_position(
                position,
                current["analysis"],
                current_price,
            )
            # Gagarin has final authority for thesis invalidation. Mechanical
            # SL/TP handling from manage_position remains active underneath it.
            if gagarin_management.get("action") == "EXIT":
                management = {
                    "action": "EXIT",
                    "reason": gagarin_management.get("reason", "GAGARIN EXIT"),
                    "new_stop": position.get("stop"),
                }
            elif management.get("action") == "HOLD":
                management["gagarin_status"] = gagarin_management.get("status", "HOLD")
                management["gagarin_reason"] = gagarin_management.get("reason", "NON CHIUDERE")
                if gagarin_management.get("action") == "HOLD_PROTECT":
                    management["action"] = "HOLD_PROTECT"

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

                if management["action"] == "MOVE_STOP":
                    icon = "🟡"
                    headline = management["reason"]
                elif management["action"] == "HOLD_PROTECT":
                    icon = "🟠"
                    headline = management.get("gagarin_reason", management["reason"])
                else:
                    icon = "🟢"
                    headline = management.get("gagarin_reason", "NON CHIUDERE")
                position_message = (
                    f"{icon} POSIZIONE {position['direction']} — {headline}\n"
                    f"STOP ATTUALE: {position['stop']:.4f}"
                )

    # ========================================================
    # NUOVA POSIZIONE
    # ========================================================

    if not position and best["analysis"].get("operational_entry_allowed") and best["analysis"]["signal"] in ("LONG", "SHORT"):
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
    final_direction = a.get("setup_direction") or a.get("model_signal") or "WAIT"
    model_prob = safe_float(a.get("probability"), 0) or 0
    model_prob = model_prob * 100 if model_prob <= 1.5 else model_prob
    final_prob = safe_float(a.get("entry_probability", a.get("probability", 0)), 0) or 0
    final_prob = final_prob * 100 if final_prob <= 1.5 else final_prob
    print(f"Segnale modello quantitativo: {a['model_signal']}")
    print(f"Direzione finale setup: {final_direction}")
    print(f"Segnale operativo GAGARIN: {a['signal']} | authority={a.get('gagarin_authority', False)} | legacy-shadow={a.get('legacy_signal_shadow', 'N/D')}")
    print(f"Market ranking: {best.get('market_ranking_score', -1):.1f} | Operational ranking: {best.get('ranking_score', -1):.1f}")
    print(f"Score: {a['score']:.1f}/100")
    print(f"Probabilità modello: {model_prob:.1f}%")
    print(f"Probabilità direzione finale: {final_prob:.1f}%")
    print(f"Confidenza: {a['confidence']:.1f}/100")
    print(f"Qualità: {a['quality']:.1f}/100")
    _snap = gagarin_display_snapshot(a)
    _rg = _snap.get("regime")
    _su = _snap.get("setup")
    _tr = _snap.get("trigger")
    _rg_state = _rg.get("state") if isinstance(_rg,dict) else _rg
    _su_type = _su.get("type") if isinstance(_su,dict) else _su
    _tr_ok = _tr.get("confirmed",False) if isinstance(_tr,dict) else bool(_tr)
    _pa_display = a.get("prediction_authority_v531") or prediction_authority_v531(a)
    _rg_state = _pa_display.get("regime", _rg_state)
    _su_type = _pa_display.get("setup", _su_type)
    _tr_ok = bool(_pa_display.get("trigger_confirmed", False))
    print(f"GAGARIN: {_rg_state or 'N/D'} | SETUP {_su_type or 'N/D'} | TRIGGER {_tr_ok} | STATE {_snap.get('state','N/D')}")
    _pred = a.get("prediction_authority_v531") or prediction_authority_v531(a)
    print(f"PREVISIONE v5.3.1: {_pred.get('state','N/D')} | {_pred.get('direction','N/D')} | REGIME {_pred.get('regime','N/D')} | SETUP {_pred.get('setup','N/D')} | BREAKOUT {'SI' if _pred.get('breakout') else 'NO'} | RETEST {'SI' if _pred.get('retest') else 'NO'} | TRIGGER {'SI' if _pred.get('trigger_confirmed') else 'NO'}")
    print(f"PREVISIONE DETTAGLI: struttura {_pred.get('structure','N/D')} | 1-2-3 {_pred.get('chart_123','N/D')} | spazio {_pred.get('space_score',0):.1f} | RR1 {_pred.get('rr_tp1',0):.2f} | RR2 {_pred.get('rr_tp2',0):.2f} | RR3 {_pred.get('rr_tp3',0):.2f}")
    if _pred.get('reasons'):
        print("PREVISIONE CONDIZIONI: " + "; ".join(_pred.get('reasons',[])[:8]))
    if a.get("gagarin_blockers"):
        print("GAGARIN BLOCKERS: " + ", ".join(a.get("gagarin_blockers", [])[:8]))
    if a.get("live_price_status") == "LIVE":
        print(
            f"LIVE PRICE: {a.get('live_price', a.get('price'))} | "
            f"BID {a.get('live_price_bid')} | ASK {a.get('live_price_ask')} | "
            f"age {safe_float(a.get('live_price_age_seconds'), 0):.1f}s | "
            f"provider {a.get('live_price_provider')}"
        )
    else:
        print(f"LIVE PRICE: {a.get('live_price_status', 'N/D')}")
        if a.get("adaptive_risk"):
            _ar = a.get("adaptive_risk") or {}
            print(f"SL/TP 2.1: {_ar.get('method')} | StructSL {_ar.get('structural_stop')} | TechSL {_ar.get('technical_stop')} | ExecSL {_ar.get('execution_stop')} | StopATR {_ar.get('stop_atr')} | RR1 {_ar.get('rr_tp1')} RR2 {_ar.get('rr_tp2')} RR3 {_ar.get('rr_tp3')} | Spread {_ar.get('spread')}")
    print(f"Knowledge Engine: {a.get('trading_knowledge', {}).get('usable', 0)} fonti | bias {a.get('knowledge_bias', 0):+.1f}")
    print(f"Learning Engine: {len(a.get('learning_validated_rules', []))} regole validate | attive {', '.join(a.get('learning_current_hits', [])) or 'nessuna'} | score {a.get('learning_score', 0):.1f}")
    print(f"Market Intelligence v4.1: {intelligence_v41_summary(a)} | delta {a.get('intelligence_delta', 0):+.1f}")
    _se = a.get("signal_engine_v42", {}) or {}
    print(f"Signal Engine v4.2: {_se.get('decision','N/D')} | score {_se.get('score',0):.1f} | MTF {_se.get('mtf',0):.1f} | L2L {_se.get('level_to_level',0):.1f} | Trigger {_se.get('trigger',0):.1f} | RR {_se.get('rr',0):.1f}")
    _l2l = a.get("level_to_level", {}) or {}
    print(f"Level-to-Level: {_l2l.get('state','N/D')} | score {_l2l.get('score',50):.1f} | trend {_l2l.get('trend','N/D')} | {_l2l.get('behaviour','N/D')} | gate {_l2l.get('gate')}")
    print(
        f"Ricorrenza storica: "
        f"{a['repetition']['direction']} | "
        f"{a['repetition']['frequency'] * 100:.1f}%"
    )

    print()
    print("=" * 70)
    print("📊 CLASSIFICA MERCATO")
    print("=" * 70)
    for i, item in enumerate(market_ranked[:10], 1):
        if not item.get("available"): continue
        x=item["analysis"]
        print(f"{i}. {item['name']} | {x.get('setup_direction') or x.get('model_signal') or 'WAIT'} | MKT {item.get('market_ranking_score',-1):.1f}")

    print()
    print("🎯 CLASSIFICA OPPORTUNITÀ OPERATIVE")
    print("=" * 70)
    if available_ranked:
        for i,item in enumerate(available_ranked[:5],1):
            x=item["analysis"]; pred=x.get("prediction_v53") or {}
            print(f"{i}. {item['name']} | {x.get('signal')} | OPP {item.get('ranking_score',-1):.1f} | RR3 {pred.get('rr_tp3',0):.2f} | {pred.get('state','N/D')}")
    else:
        print("⚪ NESSUNA OPPORTUNITÀ OPERATIVA — la classifica mercato resta informativa.")

    print()
    print("📊 RANKING COMPLETO — DECISIONALE")
    print("=" * 70)

    # Complete ranking is intentionally market-sorted. Operational permission
    # is shown as a separate decision field and never replaced by market score.
    for i, item in enumerate(market_ranked, 1):
        x = item.get("analysis", {}) or {}
        if not item.get("available"):
            print(f"{i}. ⚪ {item['name']} | DATI NON DISPONIBILI | {item.get('error', '')}")
            continue

        final_direction = (
            x.get("final_direction")
            or x.get("setup_direction")
            or x.get("model_signal")
            or "WAIT"
        )
        direction_prob = safe_float(
            x.get("entry_probability"),
            x.get("short_probability", 0) if final_direction == "SHORT"
            else x.get("long_probability", 0),
        ) or 0
        direction_prob = direction_prob * 100 if direction_prob <= 1.5 else direction_prob

        policy = x.get("entry_policy", {}) or {}
        quality = safe_float(policy.get("quality"), safe_float(x.get("quality"), 0)) or 0
        confidence = safe_float(policy.get("confidence"), safe_float(x.get("confidence"), 0)) or 0
        pred = x.get("prediction_v53") or {}
        g_raw = x.get("gagarin_state") or x.get("gagarin") or {}
        # Gagarin state is historically stored both as a dict and as a label string.
        # Normalize it here so the complete ranking can never crash on .get().
        if isinstance(g_raw, dict):
            g = g_raw
        else:
            g = {"state": str(g_raw)}

        g_state = str(g.get("state") or x.get("gagarin_state_label") or "").upper()
        setup = str(pred.get("setup") or g.get("setup") or "NONE").upper()
        trigger_ok = bool(pred.get("trigger_confirmed"))
        rr3 = safe_float(
            pred.get("rr_tp3"),
            safe_float((x.get("adaptive_risk", {}) or {}).get("rr_tp3"), 0),
        ) or 0
        comps = pred.get("components") if isinstance(pred.get("components"), dict) else {}
        def _ck(key): return '✓' if comps.get(key) else '✗'
        comp_line = (
            f"STR {_ck('structure')} | TL {_ck('trendline')} | Z {_ck('zone')} | "
            f"PAT {_ck('pattern')} | BO/RT {_ck('breakout_or_retest')} | "
            f"TR {_ck('trigger')} | SP {_ck('space_tp1')}/{_ck('space_tp2')}/{_ck('space_tp3')}"
        )

        if x.get("operational_entry_allowed"):
            decision = "READY"
        elif str(pred.get("state") or "").upper() == "PREVISIONE_IN_FORMAZIONE":
            decision = "FORMAZIONE"
        elif g_state in ("BLOCKED", "SAFETY_BLOCK") or not trigger_ok:
            decision = "BLOCCATO"
        else:
            decision = "ATTENDI"

        print(
            f"{i:02d}. {icon_for_signal(x.get('signal','WAIT'))} {item['name']} | "
            f"{final_direction} | MKT {safe_float(item.get('market_ranking_score'),0) or 0:.1f} | "
            f"Prob {direction_prob:.1f}% | Q {quality:.1f} | C {confidence:.1f} | "
            f"G:{g_state or 'N/D'} | Setup:{setup} | Trigger:{'OK' if trigger_ok else 'NO'} | "
            f"RR3:{rr3:.2f} | {decision}"
        )
        print(f"    🔎 {comp_line}")


    if ON_DEMAND_ONLY:
        # True on-demand mode: no periodic polling, no scheduled reports and
        # no event push. Telegram receives exactly the requested answer.
        process_telegram_on_demand(ranked)
        save_monitor_state(ranked, best, position)
    else:
        # Standard scheduled/event-driven mode.
        monitor_message = build_telegram_5m(ranked, best, position_message, position)
        if MONITOR_SEND_FULL:
            send_telegram(monitor_message)
        else:
            print("📡 Internal monitor: Telegram alert periodico DISATTIVATO.")
        maybe_send_session_reports(ranked, best, position_message)
        process_telegram_commands(ranked)

        # ENTRY NOW: only after final Gagarin authorization in scheduled mode.
        if ENTRY_NOW_ALERT_ENABLED and not position:
            for _entry_item in ranked:
                _entry_alert = gagarin_entry_now_alert(_entry_item)
                if _entry_alert:
                    send_telegram(_entry_alert)
                    print(_entry_alert)
                    break

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



# ========================= ENTRY NOW ALERT ENGINE =========================
ENTRY_NOW_ALERT_ENABLED = os.getenv("ENTRY_NOW_ALERT_ENABLED", "1") == "1"
ENTRY_NOW_COOLDOWN_SECONDS = int(os.getenv("ENTRY_NOW_COOLDOWN_SECONDS", "1800"))
ENTRY_NOW_MIN_SCORE = float(os.getenv("ENTRY_NOW_MIN_SCORE", "62"))
ENTRY_NOW_MIN_QUALITY = float(os.getenv("MIN_ENTRY_QUALITY", "55"))
ENTRY_NOW_MIN_CONFIDENCE = float(os.getenv("MIN_ENTRY_CONFIDENCE", "60"))
ENTRY_NOW_MIN_PROBABILITY = float(os.getenv("MIN_ENTRY_PROBABILITY", "62"))
ENTRY_NOW_MIN_RR = float(os.getenv("MIN_ENTRY_RR", "2.5"))
_ENTRY_NOW_LAST_ALERT = {}

def _entry_now_float(d, *keys, default=0.0):
    if not isinstance(d, dict):
        return default
    for k in keys:
        try:
            v = d.get(k)
            if v is not None:
                return float(v)
        except (TypeError, ValueError):
            pass
    return default

def gagarin_entry_now_check(item):
    if not isinstance(item, dict):
        return {"state": "WAIT", "authorized": False, "blockers": ["NO_ITEM"]}
    a = item.get("analysis", {}) or {}
    if not isinstance(a, dict):
        a = {}
    g = a.get("gagarin", {}) or {}
    if not isinstance(g, dict):
        g = {}
    policy = g.get("entry_policy", {}) or {}
    if not isinstance(policy, dict):
        policy = {}

    direction = str(a.get("direction_final") or a.get("signal") or policy.get("direction") or "").upper()
    if direction not in {"LONG", "SHORT"}:
        return {"state": "WAIT", "authorized": False, "blockers": ["NO_DIRECTION"]}

    state = str(a.get("gagarin_state") or policy.get("state") or "").upper()
    quality = _entry_now_float(a, "quality", "entry_quality")
    confidence = _entry_now_float(a, "confidence", "entry_confidence")
    probability = _entry_now_float(a, "probability_final", "probability", "entry_probability")
    score = _entry_now_float(a, "score", "final_score")
    rr = _entry_now_float(a, "rr", "risk_reward", "rr_tp3")

    if not rr:
        entry = _entry_now_float(a, "entry", "entry_price")
        sl = _entry_now_float(a, "sl", "stop_loss")
        tp3 = _entry_now_float(a, "tp3")
        risk = abs(entry - sl) if entry and sl else 0.0
        if risk and tp3:
            rr = abs(tp3 - entry) / risk

    blockers = []
    authorized = bool(policy.get("authorized") or policy.get("entry_authorized") or a.get("operational_entry_allowed"))
    if state not in {"READY", "ENTRY", "ENTRY_NOW", "AUTHORIZED"} and not authorized:
        blockers.append("GAGARIN_NOT_READY")
    if probability < ENTRY_NOW_MIN_PROBABILITY: blockers.append("PROBABILITY")
    if quality < ENTRY_NOW_MIN_QUALITY: blockers.append("QUALITY")
    if confidence < ENTRY_NOW_MIN_CONFIDENCE: blockers.append("CONFIDENCE")
    if score and score < ENTRY_NOW_MIN_SCORE: blockers.append("SCORE")
    if rr < ENTRY_NOW_MIN_RR: blockers.append("RR")

    risk = g.get("risk", {})
    risk_state = ""
    if isinstance(risk, dict):
        risk_state = str(risk.get("state") or "").upper()
    risk_state = risk_state or str(a.get("risk_state") or "").upper()
    if any(x in risk_state for x in ("ALERT", "BLOCK", "DANGER", "HIGH_RISK")):
        blockers.append("RISK")

    safety = g.get("safety", {})
    if isinstance(safety, dict) and safety.get("ok") is False:
        blockers.append("SAFETY")

    trigger = g.get("trigger", {})
    if isinstance(trigger, dict):
        if not bool(trigger.get("confirmed")):
            blockers.append("TRIGGER")
    elif not bool(trigger):
        blockers.append("TRIGGER")

    blockers = list(dict.fromkeys(blockers))
    if blockers:
        return {"state": "WAIT", "authorized": False, "direction": direction,
                "quality": quality, "confidence": confidence, "probability": probability,
                "score": score, "rr": rr, "blockers": blockers}
    return {"state": "ENTRY_NOW", "authorized": True, "direction": direction,
            "quality": quality, "confidence": confidence, "probability": probability,
            "score": score, "rr": rr, "blockers": []}

def gagarin_entry_now_alert(item):
    if not ENTRY_NOW_ALERT_ENABLED:
        return None
    d = gagarin_entry_now_check(item)
    if d.get("state") != "ENTRY_NOW":
        return None

    import time as _entry_now_time
    name = item.get("name") or item.get("commodity") or item.get("label") or "Commodity"
    key = f"{name}:{d.get('direction')}"
    now = _entry_now_time.time()
    if now - _ENTRY_NOW_LAST_ALERT.get(key, 0.0) < ENTRY_NOW_COOLDOWN_SECONDS:
        return None
    _ENTRY_NOW_LAST_ALERT[key] = now

    a = item.get("analysis", {}) or {}
    entry = _entry_now_float(a, "entry", "entry_price")
    sl = _entry_now_float(a, "sl", "stop_loss")
    tp1 = _entry_now_float(a, "tp1")
    tp2 = _entry_now_float(a, "tp2")
    tp3 = _entry_now_float(a, "tp3")
    return "\n".join([
        "🚨 ENTRA ORA — GAGARIN",
        "",
        f"📌 {name}",
        "🟢 LONG" if d["direction"] == "LONG" else "🔴 SHORT",
        f"💰 Entry: {entry:.4f}" if entry else "💰 Entry: N/D",
        f"🛑 SL: {sl:.4f}" if sl else "🛑 SL: N/D",
        f"🎯 TP1: {tp1:.4f}" if tp1 else "🎯 TP1: N/D",
        f"🎯 TP2: {tp2:.4f}" if tp2 else "🎯 TP2: N/D",
        f"🎯 TP3: {tp3:.4f}" if tp3 else "🎯 TP3: N/D",
        f"📐 R/R: {d['rr']:.2f}",
        "",
        "✅ GAGARIN: ENTRY AUTHORIZED",
        "🔥 Trigger confermato",
        "🧪 PAPER ONLY",
    ])


if __name__ == "__main__":
    main()
