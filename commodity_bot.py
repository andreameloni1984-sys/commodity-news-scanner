import os
import json
import math
from datetime import datetime, timezone

import requests


# ============================================================
# COMMODITY TRADING BOT v8.3
# QUANT MODEL + MULTI-TIMEFRAME + NEWS + USD + SEASONALITY
# + RANKING + POSITION MANAGEMENT
#
# Analitico/simulato: NON esegue ordini reali.
# ============================================================

API_KEY = os.getenv("TWELVE_DATA_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "8002086130")

BASE_URL = "https://api.twelvedata.com/time_series"
NEWS_URL = "https://newsapi.org/v2/everything"

POSITION_FILE = "position.json"

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
    "Oro": "XAU/USD",
    "Argento": "XAG/USD",
    "Petrolio WTI": "WTI/USD",
    "Petrolio Brent": "BRN/USD",
    "Gas Naturale": "NG/USD",
    "Rame": "COPPER/USD",
    "Grano": "WHEAT/USD",
    "Mais": "CORN/USD",
    "Caffè": "COFFEE/USD",
}

NEWS_TERMS = {
    "Oro": "gold OR bullion OR XAU",
    "Argento": "silver OR XAG",
    "Petrolio WTI": "oil OR crude OR WTI",
    "Petrolio Brent": "oil OR crude OR Brent",
    "Gas Naturale": "natural gas",
    "Rame": "copper",
    "Grano": "wheat OR grain",
    "Mais": "corn OR maize",
    "Caffè": "coffee",
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

def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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
    "Oro": "GC=F",
    "Argento": "SI=F",
    "Petrolio WTI": "CL=F",
    "Petrolio Brent": "BZ=F",
    "Gas Naturale": "NG=F",
    "Rame": "HG=F",
    "Grano": "ZW=F",
    "Mais": "ZC=F",
    "Caffè": "KC=F",
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
        "Oro": ["gold spot", "gold"],
        "Argento": ["silver spot", "silver"],
        "Petrolio WTI": ["crude oil wti", "wti"],
        "Petrolio Brent": ["brent spot", "brent", "crude oil brent"],
        "Gas Naturale": ["natural gas", "natural gas spot"],
        "Rame": ["copper spot", "copper"],
        "Grano": ["wheat", "wheat spot"],
        "Mais": ["corn", "corn spot", "maize"],
        "Caffè": ["coffee", "coffee spot"],
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
        ("modello", analysis.get("model_signal") == analysis.get("signal") and analysis.get("signal") in ("LONG", "SHORT")),
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
    if confirmed_shocks >= 2:
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
# SIGNAL
# ============================================================

def analyze(candles, dataset, model, bt, usd, news, timeframes, political=None, commodity_name=None, global_impact=None, session=None, intraday_candles=None, pattern_timeframes=None):
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
    }
    result["_candles"] = candles
    result = v83_setup_engine(result, intraday_candles=intraday_candles, commodity_name=commodity_name, pattern_timeframes=pattern_timeframes)
    # Ricalcola R/B con l'entry effettiva trovata dal motore V8.
    result["risk_benefit"] = risk_benefit_engine(result, cyclical)
    return {k:v for k,v in result.items() if k != "_candles"} | {"_candles": candles}


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
        current_analysis.get("strong_confirmation", False)
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

def build_telegram(ranked, best, position_message=None):
    """Telegram operativo V8: niente dettagli tecnici interni."""
    available=[x for x in ranked if x.get('available')][:3]
    lines=['🌍 COMMODITIES BOT v8.3','', '🏆 CLASSIFICA']
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
                  f'🎯 AZIONE: {action}', f'🧭 DIREZIONE: {direction}',
                  f'💰 PREZZO ATTUALE: {price:.4f}' if price is not None else '💰 PREZZO ATTUALE: N/D',
                  f'📥 ENTRATA: {entry:.4f}' if entry is not None else '📥 ENTRATA: N/D', f'📌 SETUP: {a.get("entry_method","N/D")}', f'🕯️ PATTERN: {pattern}', f'📚 STORICO SETUP: {a.get("pattern_backtest",{}).get("win_rate",0)*100:.0f}% successo' if a.get("pattern_backtest",{}).get("samples",0)>=5 else '📚 STORICO SETUP: dati insufficienti']
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
    return '\n'.join(lines)

def analysis_direction_hint(timeframes):
    vals = [timeframes.get(tf, {}).get("direction", "NONE") for tf in ("4H", "1H", "15m")]
    if vals.count("LONG") >= 2:
        return "LONG"
    if vals.count("SHORT") >= 2:
        return "SHORT"
    return "NONE"


# ============================================================
# MAIN
# ============================================================

def main():
    print()
    print("=" * 70)
    print("🌍 COMMODITIES BOT v8.3")
    print("RANKING RISK/BENEFIT + CYCLICAL ENGINE + GOLD ENGINE v15.1 + GLOBAL INTELLIGENCE + SESSION ENGINE + RISK ENGINE")
    print("=" * 70)
    print()

    position = load_position()
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
            political = political_impact(name)
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
                global_impact=global_impact, session=session, intraday_candles=intraday_candles, pattern_timeframes=pattern_timeframes
            )
            if analysis is None:
                raise RuntimeError("Analisi Gold Engine non disponibile")

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

    # ========================================================
    # RANKING
    # ========================================================

    # Ranking finale: non basta il segnale; privilegiamo opportunità, rischio e R/R.
    for item in results:
        if item.get("available"):
            rb = item["analysis"].get("risk_benefit", {})
            item["ranking_score"] = rb.get("score", item["analysis"].get("score", 0))
        else:
            item["ranking_score"] = -1

    ranked = sorted(results, key=lambda x: x.get("ranking_score", -1), reverse=True)
    available_ranked = [x for x in ranked if x.get("available") and x["analysis"]["score"] >= 0]
    if not available_ranked:
        raise RuntimeError("Nessuna commodity dispone di dati sufficienti per il Gold Engine. Controllare simboli/API quota.")
    best = available_ranked[0]

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

    message = build_telegram(
        ranked,
        best,
        position_message,
    )

    send_telegram(message)

    print()
    print("=" * 70)
    print("⚠️ Analisi quantitativa, non garanzia di profitto.")
    print("=" * 70)


if __name__ == "__main__":
    main()
