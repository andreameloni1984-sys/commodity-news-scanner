import os
import json
import math
import re
from datetime import datetime, timezone

import requests


# ============================================================
# 🌍 COMMODITIES BOT v7.0
# ============================================================
# Analisi automatica delle commodity disponibili su Twelve Data
#
# - Scoperta automatica dei simboli
# - Multi-timeframe
# - Dollaro UUP
# - News GDELT
# - Trend / RSI / EMA / ATR
# - Pressione acquisti-vendite
# - Ranking delle commodity
# - Storico
# - SL / TP
# - Telegram
#
# ⚠️ ANALITICO / SIMULATO
# ⚠️ NON ESEGUE ORDINI REALI
# ============================================================


# ============================================================
# CONFIGURAZIONE
# ============================================================

API_KEY = os.getenv("TWELVE_DATA_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "8002086130")

BASE_URL = "https://api.twelvedata.com/time_series"
COMMODITIES_URL = "https://api.twelvedata.com/commodities"
GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

POSITION_FILE = "position.json"

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CommoditiesBot/7.0)"
}


if not API_KEY:
    raise RuntimeError(
        "TWELVE_DATA_API_KEY non configurata nei GitHub Secrets."
    )

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError(
        "TELEGRAM_BOT_TOKEN non configurata nei GitHub Secrets."
    )


# ============================================================
# PARAMETRI
# ============================================================

HISTORY_SIZE = 600
MIN_HISTORY = 120

STOP_ATR = 1.5
TP1_ATR = 2.0
TP2_ATR = 3.0

MIN_SCORE = 60
MIN_CONFIDENCE = 55
MIN_RANK_MARGIN = 4


# ============================================================
# COMMODITY CHE VOGLIAMO CERCARE
# ============================================================

TARGETS = {
    "Oro": [
        "gold",
        "gold spot",
        "xau",
    ],

    "Argento": [
        "silver",
        "silver spot",
        "xag",
    ],

    "Petrolio WTI": [
        "wti",
        "west texas",
        "crude oil",
    ],

    "Petrolio Brent": [
        "brent",
        "brent crude",
    ],

    "Gas Naturale": [
        "natural gas",
        "nat gas",
    ],

    "Rame": [
        "copper",
    ],

    "Grano": [
        "wheat",
    ],

    "Mais": [
        "corn",
        "maize",
    ],

    "Caffè": [
        "coffee",
    ],
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


# ============================================================
# UTILITY
# ============================================================

def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def mean(values):
    values = [
        x for x in values
        if x is not None and math.isfinite(x)
    ]

    if not values:
        return 0.0

    return sum(values) / len(values)


def std(values):
    values = [
        x for x in values
        if x is not None and math.isfinite(x)
    ]

    if len(values) < 2:
        return 1.0

    m = mean(values)

    variance = sum(
        (x - m) ** 2 for x in values
    ) / (len(values) - 1)

    return max(math.sqrt(variance), 1e-8)


def clamp(value, low, high):
    return max(low, min(high, value))


def pct(value):
    return f"{value * 100:.1f}%"


# ============================================================
# INDICATORI
# ============================================================

def ema(values, period):
    if len(values) < period:
        return None

    multiplier = 2 / (period + 1)

    result = sum(values[:period]) / period

    for price in values[period:]:
        result = (
            (price - result) * multiplier
            + result
        )

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

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (
            (avg_gain * (period - 1))
            + gains[i]
        ) / period

        avg_loss = (
            (avg_loss * (period - 1))
            + losses[i]
        ) / period

    if avg_loss == 0:
        return 100.0

    return 100 - (
        100 / (1 + avg_gain / avg_loss)
    )


def atr(candles, period=14):
    if len(candles) < period + 1:
        return 0.0

    trs = []

    for i in range(1, len(candles)):

        high = candles[i]["high"]
        low = candles[i]["low"]
        previous_close = candles[i - 1]["close"]

        if high is None or low is None:
            continue

        trs.append(
            max(
                high - low,
                abs(high - previous_close),
                abs(low - previous_close),
            )
        )

    if not trs:
        return 0.0

    return sum(trs[-period:]) / min(
        period,
        len(trs)
    )


# ============================================================
# PRESSIONE
# ============================================================

def buying_selling_pressure(candles, period=20):

    recent = candles[-period:]

    buying = 0.0
    selling = 0.0

    for candle in recent:

        high = candle["high"]
        low = candle["low"]
        close = candle["close"]

        if high is None or low is None:
            continue

        if high == low:
            continue

        position = (
            (close - low)
            / (high - low)
        )

        buying += position
        selling += 1 - position

    return buying, selling


# ============================================================
# STRUTTURA
# ============================================================

def price_structure(candles, lookback=8):

    if len(candles) < lookback + 2:
        return "NEUTRALE"

    recent = candles[-lookback:]

    half = lookback // 2

    first = recent[:half]
    second = recent[half:]

    first_high = max(
        x["high"] for x in first
    )

    second_high = max(
        x["high"] for x in second
    )

    first_low = min(
        x["low"] for x in first
    )

    second_low = min(
        x["low"] for x in second
    )

    if (
        second_high > first_high
        and second_low > first_low
    ):
        return "BULLISH"

    if (
        second_high < first_high
        and second_low < first_low
    ):
        return "BEARISH"

    return "NEUTRALE"


# ============================================================
# TWELVE DATA — SCOPERTA COMMODITY
# ============================================================

def discover_commodities():

    print("🔎 Cerco le commodity disponibili su Twelve Data...")

    response = requests.get(
        COMMODITIES_URL,
        params={"apikey": API_KEY},
        headers=REQUEST_HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    if isinstance(data, dict):

        if data.get("status") == "error":
            raise RuntimeError(
                data.get(
                    "message",
                    "Errore endpoint commodities"
                )
            )

        items = (
            data.get("data")
            or data.get("commodities")
            or data.get("values")
            or []
        )

    else:
        items = data

    if not isinstance(items, list):
        raise RuntimeError(
            "Formato inatteso dalla lista commodity."
        )

    discovered = {}

    for target_name, keywords in TARGETS.items():

        candidates = []

        for item in items:

            if not isinstance(item, dict):
                continue

            symbol = str(
                item.get("symbol", "")
            ).strip()

            name = str(
                item.get("name", "")
            ).lower()

            description = str(
                item.get("description", "")
            ).lower()

            category = str(
                item.get("category", "")
            ).lower()

            haystack = (
                symbol.lower()
                + " "
                + name
                + " "
                + description
                + " "
                + category
            )

            score = 0

            for keyword in keywords:

                if keyword.lower() in haystack:
                    score += 10

            if score == 0:
                continue

            # Preferiamo quotazioni USD.
            if symbol.upper().endswith("/USD"):
                score += 20

            # Preferiamo simboli più semplici.
            if "/" in symbol:
                score += 5

            candidates.append(
                (score, symbol)
            )

        if candidates:

            candidates.sort(
                key=lambda x: x[0],
                reverse=True
            )

            discovered[target_name] = (
                candidates[0][1]
            )

    # Fallback garantito per l'oro.
    if "Oro" not in discovered:
        discovered["Oro"] = "XAU/USD"

    print()

    for name, symbol in discovered.items():
        print(
            f"   ✅ {name}: {symbol}"
        )

    return discovered


# ============================================================
# TWELVE DATA — DATI
# ============================================================

def get_data(
    symbol,
    interval="1day",
    outputsize=400
):

    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "apikey": API_KEY,
        "order": "ASC",
    }

    response = requests.get(
        BASE_URL,
        params=params,
        headers=REQUEST_HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    if data.get("status") == "error":

        raise RuntimeError(
            data.get(
                "message",
                f"Errore Twelve Data: {symbol}"
            )
        )

    values = data.get("values", [])

    if not values:
        raise RuntimeError(
            f"Nessun dato per {symbol} {interval}"
        )

    candles = []

    for item in values:

        close = safe_float(
            item.get("close")
        )

        if close is None:
            continue

        candles.append({
            "datetime": item.get("datetime"),

            "open": safe_float(
                item.get("open")
            ),

            "high": safe_float(
                item.get("high")
            ),

            "low": safe_float(
                item.get("low")
            ),

            "close": close,

            "volume": safe_float(
                item.get("volume")
            ),
        })

    candles.sort(
        key=lambda x: x["datetime"] or ""
    )

    return candles


# ============================================================
# TIMEFRAME
# ============================================================

def timeframe_direction(candles):

    if not candles or len(candles) < 60:
        return {
            "direction": "NONE",
            "score": 0,
        }

    closes = [
        x["close"]
        for x in candles
    ]

    fast = ema(closes, 20)
    slow = ema(closes, 50)

    current = closes[-1]

    current_rsi = rsi(
        closes,
        14
    )

    score = 0

    if fast and slow:

        if fast > slow:
            score += 2

        elif fast < slow:
            score -= 2

    if fast:

        if current > fast:
            score += 1

        elif current < fast:
            score -= 1

    if current_rsi > 55:
        score += 1

    elif current_rsi < 45:
        score -= 1

    if score >= 2:
        direction = "LONG"

    elif score <= -2:
        direction = "SHORT"

    else:
        direction = "NONE"

    return {
        "direction": direction,
        "score": score,
    }


# ============================================================
# MULTI TIMEFRAME
# ============================================================

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

            candles = get_data(
                symbol,
                interval,
                120
            )

            result[name] = (
                timeframe_direction(
                    candles
                )
            )

        except Exception as error:

            print(
                f"   ⚠️ {name}: {error}"
            )

            result[name] = {
                "direction": "NONE",
                "score": 0,
            }

    return result


# ============================================================
# DOLLARO UUP
# ============================================================

def analyze_usd():

    try:

        candles = get_data(
            "UUP:NYSE",
            "1day",
            120
        )

        result = timeframe_direction(
            candles
        )

        direction = result["direction"]

        if direction == "LONG":

            return {
                "direction": "LONG",
                "score": -2,
                "label": "FORTE / SFAVOREVOLE",
            }

        if direction == "SHORT":

            return {
                "direction": "SHORT",
                "score": 2,
                "label": "DEBOLE / FAVOREVOLE",
            }

        return {
            "direction": "NONE",
            "score": 0,
            "label": "NEUTRO",
        }

    except Exception as error:

        print(
            f"⚠️ UUP non disponibile: {error}"
        )

        return {
            "direction": "NONE",
            "score": 0,
            "label": "NON DISPONIBILE",
        }


# ============================================================
# GDELT
# ============================================================

def gdelt_search(query, timespan="3days"):

    params = {
        "query": query,
        "mode": "artlist",
        "format": "json",
        "maxrecords": 25,
        "timespan": timespan,
        "sort": "datedesc",
    }

    response = requests.get(
        GDELT_URL,
        params=params,
        headers=REQUEST_HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    return data.get(
        "articles",
        []
    )


# ============================================================
# NEWS SENTIMENT
# ============================================================

POSITIVE_WORDS = {
    "rise",
    "rises",
    "rising",
    "gain",
    "gains",
    "higher",
    "increase",
    "increases",
    "surge",
    "surges",
    "bullish",
    "strong",
    "demand",
    "shortage",
    "support",
    "rally",
    "rallies",
    "tight supply",
    "supply cut",
    "production cut",
    "production cuts",
    "disruption",
    "disruptions",
}


NEGATIVE_WORDS = {
    "fall",
    "falls",
    "falling",
    "drop",
    "drops",
    "lower",
    "decrease",
    "decreases",
    "bearish",
    "weak",
    "oversupply",
    "collapse",
    "recession",
    "slump",
    "selloff",
    "selling",
}


def article_sentiment(article):

    title = (
        article.get("title")
        or ""
    )

    description = (
        article.get("seendate")
        or ""
    )

    text = (
        title
        + " "
        + description
    ).lower()

    score = 0

    for word in POSITIVE_WORDS:

        if word in text:
            score += 1

    for word in NEGATIVE_WORDS:

        if word in text:
            score -= 1

    return score


def analyze_news(name):

    query = NEWS_TERMS.get(
        name,
        name
    )

    try:

        articles = gdelt_search(
            query,
            "3days"
        )

        if not articles:

            simple_query = re.sub(
                r'\bOR\b',
                " ",
                query,
                flags=re.I
            )

            articles = gdelt_search(
                simple_query,
                "3days"
            )

        if not articles:

            return {
                "score": 0,
                "label": "NEUTRALE",
                "count": 0,
                "headline": None,
                "source": None,
            }

        total = 0
        positive = 0
        negative = 0

        latest = articles[0]

        for article in articles:

            s = article_sentiment(
                article
            )

            total += s

            if s > 0:
                positive += 1

            elif s < 0:
                negative += 1

        score = clamp(
            total / 3,
            -5,
            5
        )

        if score >= 1:
            label = "POSITIVA"

        elif score <= -1:
            label = "NEGATIVA"

        else:
            label = "NEUTRALE"

        return {
            "score": score,
            "label": label,
            "count": len(articles),
            "positive": positive,
            "negative": negative,
            "headline": latest.get("title"),
            "source": latest.get(
                "domain"
            ),
        }

    except Exception as error:

        print(
            f"⚠️ News {name}: {error}"
        )

        return {
            "score": 0,
            "label": "ERRORE",
            "count": 0,
            "positive": 0,
            "negative": 0,
            "headline": None,
            "source": None,
            "error": str(error),
        }


# ============================================================
# ANALISI PRINCIPALE
# ============================================================

def analyze_commodity(
    name,
    symbol,
    usd
):

    print(
        f"\n🔎 Analizzo {name} — {symbol}"
    )

    daily = get_data(
        symbol,
        "1day",
        HISTORY_SIZE
    )

    if len(daily) < MIN_HISTORY:

        raise RuntimeError(
            f"Dati insufficienti: {len(daily)}"
        )

    closes = [
        x["close"]
        for x in daily
    ]

    price = closes[-1]

    e20 = ema(closes, 20)
    e50 = ema(closes, 50)
    e200 = ema(closes, 200)

    current_rsi = rsi(
        closes,
        14
    )

    current_atr = atr(
        daily,
        14
    )

    buying, selling = (
        buying_selling_pressure(
            daily
        )
    )

    structure = price_structure(
        daily
    )

    score = 0

    # Trend
    if e20 and e50:

        if e20 > e50:
            score += 2

        elif e20 < e50:
            score -= 2

    if e50 and e200:

        if e50 > e200:
            score += 2

        elif e50 < e200:
            score -= 2

    # Prezzo
    if e50:

        if price > e50:
            score += 1

        elif price < e50:
            score -= 1

    # RSI
    if current_rsi > 55:
        score += 2

    elif current_rsi < 45:
        score -= 2

    # Pressione
    if buying > selling:
        score += 2

    elif selling > buying:
        score -= 2

    # Struttura
    if structure == "BULLISH":
        score += 2

    elif structure == "BEARISH":
        score -= 2

    # Multi timeframe
    timeframes = get_multitimeframe(
        symbol
    )

    tf_score = (
        timeframes["4H"]["score"]
        + timeframes["1H"]["score"]
        + timeframes["15m"]["score"]
    )

    if tf_score >= 3:
        score += 3

    elif tf_score <= -3:
        score -= 3

    # Dollaro
    score += usd["score"]

    # News
    news = analyze_news(
        name
    )

    if news["score"] > 0:
        score += 2

    elif news["score"] < 0:
        score -= 2

    # ========================================================
    # NORMALIZZAZIONE
    # ========================================================

    score = clamp(
        50 + score * 4,
        0,
        100
    )

    # ========================================================
    # DIREZIONE
    # ========================================================

    if score >= 58:
        model_signal = "LONG"

    elif score <= 42:
        model_signal = "SHORT"

    else:
        model_signal = "WAIT"

    # ========================================================
    # CONFIDENZA
    # ========================================================

    confidence = clamp(
        50
        + abs(score - 50) * 1.1,
        0,
        100
    )

    # ========================================================
    # CONFERME VELOCI
    # ========================================================

    fast_long = 0
    fast_short = 0

    if timeframes["5m"]["direction"] == "LONG":
        fast_long += 1

    if timeframes["1m"]["direction"] == "LONG":
        fast_long += 1

    if timeframes["5m"]["direction"] == "SHORT":
        fast_short += 1

    if timeframes["1m"]["direction"] == "SHORT":
        fast_short += 1

    fast_conflict = (
        fast_long > 0
        and fast_short > 0
    )

    operational_signal = model_signal

    if model_signal == "LONG":

        if fast_short >= 2:
            operational_signal = "WAIT"

    elif model_signal == "SHORT":

        if fast_long >= 2:
            operational_signal = "WAIT"

    # ========================================================
    # ENTRY / SL / TP
    # ========================================================

    stop = None
    tp1 = None
    tp2 = None

    if operational_signal == "LONG":

        stop = price - (
            current_atr * STOP_ATR
        )

        tp1 = price + (
            current_atr * TP1_ATR
        )

        tp2 = price + (
            current_atr * TP2_ATR
        )

    elif operational_signal == "SHORT":

        stop = price + (
            current_atr * STOP_ATR
        )

        tp1 = price - (
            current_atr * TP1_ATR
        )

        tp2 = price - (
            current_atr * TP2_ATR
        )

    # ========================================================
    # STORICO SEMPLICE
    # ========================================================

    historical_direction = "NEUTRALE"
    historical_frequency = 0.50

    if len(closes) >= 60:

        recent_return = (
            closes[-1]
            / closes[-21]
            - 1
        )

        if recent_return > 0.01:

            historical_direction = "LONG"
            historical_frequency = 0.55

        elif recent_return < -0.01:

            historical_direction = "SHORT"
            historical_frequency = 0.55

    # ========================================================
    # GRADE
    # ========================================================

    if (
        operational_signal in
        ("LONG", "SHORT")
        and confidence >= 70
        and not fast_conflict
        and abs(score - 50) >= 18
    ):

        grade = "🟢 FORTE"

    elif operational_signal in (
        "LONG",
        "SHORT"
    ):

        grade = "🟡 IN FOR"