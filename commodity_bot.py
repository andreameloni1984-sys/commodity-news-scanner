import os
import json
import math
from datetime import datetime, timezone

import requests


# ============================================================
# COMMODITIES BOT v6.2
# QUANT + MULTI-TIMEFRAME + NEWS + USD
# + POLITICAL IMPACT + RANKING + POSITION MANAGEMENT
# + TELEGRAM VERIFICATO
#
# ANALITICO / SIMULATO
# NON ESEGUE ORDINI REALI
# ============================================================


# ============================================================
# CONFIGURAZIONE
# ============================================================

API_KEY = os.getenv("TWELVE_DATA_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


BASE_URL = "https://api.twelvedata.com/time_series"
NEWS_URL = "https://newsapi.org/v2/everything"

POSITION_FILE = "position.json"


LONG_THRESHOLD = 0.62
SHORT_THRESHOLD = 0.38

MIN_SCORE = 60
MIN_CONFIDENCE = 55

STOP_ATR = 1.5
TP1_ATR = 1.5
TP2_ATR = 2.5


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


# ============================================================
# CONTROLLO CONFIGURAZIONE
# ============================================================

if not API_KEY:
    raise RuntimeError(
        "TWELVE_DATA_API_KEY non configurata nei GitHub Secrets."
    )

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError(
        "TELEGRAM_BOT_TOKEN non configurata nei GitHub Secrets."
    )

if not TELEGRAM_CHAT_ID:
    raise RuntimeError(
        "TELEGRAM_CHAT_ID non configurato nei GitHub Secrets."
    )


# ============================================================
# UTILITY
# ============================================================

def safe_float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def mean(values):
    values = [
        x for x in values
        if x is not None and math.isfinite(x)
    ]

    if not values:
        return 0.0

    return sum(values) / len(values)


def clamp(value, low, high):
    return max(low, min(high, value))


def pct(value):
    return f"{value * 100:.1f}%"


def fmt(value, decimals=2):
    if value is None:
        return "N/D"

    return f"{value:.{decimals}f}"


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

        tr = max(
            high - low,
            abs(high - previous_close),
            abs(low - previous_close),
        )

        trs.append(tr)

    if not trs:
        return 0.0

    return sum(trs[-period:]) / min(
        period,
        len(trs)
    )


# ============================================================
# TWELVE DATA
# ============================================================

def get_data(symbol, interval, outputsize=250):
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
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    if data.get("status") == "error":
        raise RuntimeError(
            data.get(
                "message",
                f"Errore Twelve Data per {symbol}"
            )
        )

    values = data.get("values", [])

    candles = []

    for item in values:
        close = safe_float(item.get("close"))

        if close is None:
            continue

        candles.append(
            {
                "datetime": item.get("datetime"),
                "open": safe_float(item.get("open")),
                "high": safe_float(item.get("high")),
                "low": safe_float(item.get("low")),
                "close": close,
                "volume": safe_float(item.get("volume")),
            }
        )

    candles.sort(
        key=lambda x: x.get("datetime") or ""
    )

    # Evita di usare l'ultima candela ancora in formazione.
    if len(candles) > 2:
        candles = candles[:-1]

    return candles


# ============================================================
# ANALISI TIMEFRAME
# ============================================================

def analyze_timeframe(candles):
    if len(candles) < 60:
        return {
            "direction": "NONE",
            "score": 0,
            "price": None,
            "ema20": None,
            "ema50": None,
            "rsi": 50.0,
            "atr": 0.0,
        }

    closes = [
        c["close"]
        for c in candles
    ]

    price = closes[-1]

    ema20 = ema(closes, 20)
    ema50 = ema(closes, 50)

    current_rsi = rsi(closes, 14)
    current_atr = atr(candles, 14)

    score = 0

    if ema20 is not None and ema50 is not None:

        if ema20 > ema50:
            score += 2
        elif ema20 < ema50:
            score -= 2

        if price > ema20:
            score += 1
        elif price < ema20:
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
        "price": price,
        "ema20": ema20,
        "ema50": ema50,
        "rsi": current_rsi,
        "atr": current_atr,
    }


# ============================================================
# MULTI-TIMEFRAME
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
                150,
            )

            result[name] = analyze_timeframe(
                candles
            )

        except Exception as error:

            print(
                f"   ⚠️ {name}: {error}"
            )

            result[name] = {
                "direction": "NONE",
                "score": 0,
                "price": None,
                "ema20": None,
                "ema50": None,
                "rsi": 50.0,
                "atr": 0.0,
            }

    return result


# ============================================================
# USD
# ============================================================

def analyze_usd():

    try:
        candles = get_data(
            "UUP:NYSE",
            "1day",
            120,
        )

        analysis = analyze_timeframe(
            candles
        )

        if analysis["direction"] == "LONG":

            return {
                "direction": "LONG",
                "impact": -1,
                "label": "FORTE / SFAVOREVOLE",
            }

        if analysis["direction"] == "SHORT":

            return {
                "direction": "SHORT",
                "impact": 1,
                "label": "DEBOLE / FAVOREVOLE",
            }

        return {
            "direction": "NONE",
            "impact": 0,
            "label": "NEUTRO",
        }

    except Exception as error:

        print(
            f"⚠️ Dollaro non disponibile: {error}"
        )

        return {
            "direction": "NONE",
            "impact": 0,
            "label": "NON DISPONIBILE",
        }


# ============================================================
# NEWS COMMODITY
# ============================================================

def analyze_news(name):

    if not NEWS_API_KEY:

        return {
            "score": 0,
            "label": "NON DISPONIBILI",
            "count": 0,
        }

    query = NEWS_TERMS.get(
        name,
        name,
    )

    params = {
        "q": query,
        "apiKey": NEWS_API_KEY,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 20,
    }

    try:

        response = requests.get(
            NEWS_URL,
            params=params,
            timeout=20,
        )

        response.raise_for_status()

        data = response.json()

        articles = data.get(
            "articles",
            [],
        )

        if not articles:

            return {
                "score": 0,
                "label": "NEUTRALI",
                "count": 0,
            }

        positive_words = {
            "rise",
            "rises",
            "rising",
            "gain",
            "gains",
            "bullish",
            "surge",
            "higher",
            "increase",
            "shortage",
            "demand",
            "support",
            "strong",
            "rally",
        }

        negative_words = {
            "fall",
            "falls",
            "falling",
            "drop",
            "drops",
            "bearish",
            "weak",
            "lower",
            "decrease",
            "oversupply",
            "collapse",
            "recession",
            "concern",
        }

        total = 0

        for article in articles:

            text = (
                (article.get("title") or "")
                + " "
                + (article.get("description") or "")
            ).lower()

            words = set(text.split())

            positive = len(
                words & positive_words
            )

            negative = len(
                words & negative_words
            )

            if positive > negative:
                total += 1

            elif negative > positive:
                total -= 1

        normalized = clamp(
            total / max(len(articles), 1),
            -1,
            1,
        )

        if normalized >= 0.20:
            label = "POSITIVE"

        elif normalized <= -0.20:
            label = "NEGATIVE"

        else:
            label = "NEUTRALI"

        return {
            "score": normalized,
            "label": label,
            "count": len(articles),
        }

    except Exception as error:

        print(
            f"   ⚠️ News {name}: {error}"
        )

        return {
            "score": 0,
            "label": "ERRORE",
            "count": 0,
        }


# ============================================================
# POLITICAL IMPACT
# ============================================================

def analyze_political_impact(name):

    if not NEWS_API_KEY:

        return {
            "score": 0,
            "label": "NON DISPONIBILE",
            "count": 0,
        }

    political_terms = {
        "Oro": (
            "Trump OR tariffs OR sanctions OR "
            "Federal Reserve OR inflation OR "
            "geopolitical OR war OR Iran OR Russia"
        ),

        "Argento": (
            "Trump OR tariffs OR sanctions OR "
            "Federal Reserve OR inflation OR "
            "geopolitical OR war"
        ),

        "Petrolio WTI": (
            "Trump OR tariffs OR sanctions OR "
            "OPEC OR Iran OR Russia OR "
            "Middle East OR war"
        ),

        "Petrolio Brent": (
            "Trump OR tariffs OR sanctions OR "
            "OPEC OR Iran OR Russia OR "
            "Middle East OR war"
        ),

        "Gas Naturale": (
            "Trump OR sanctions OR Russia OR "
            "Europe OR LNG OR war OR tariffs"
        ),

        "Rame": (
            "Trump OR tariffs OR China OR "
            "trade war OR sanctions OR stimulus"
        ),

        "Grano": (
            "Trump OR tariffs OR Russia OR Ukraine OR "
            "sanctions OR exports OR war"
        ),

        "Mais": (
            "Trump OR tariffs OR China OR "
            "trade war OR exports OR sanctions"
        ),

        "Caffè": (
            "Trump OR tariffs OR Brazil OR "
            "trade OR exports OR sanctions"
        ),
    }

    query = political_terms.get(
        name,
        "Trump OR tariffs OR sanctions OR geopolitics"
    )

    params = {
        "q": query,
        "apiKey": NEWS_API_KEY,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 20,
    }

    try:

        response = requests.get(
            NEWS_URL,
            params=params,
            timeout=20,
        )

        response.raise_for_status()

        data = response.json()

        articles = data.get(
            "articles",
            [],
        )

        if not articles:

            return {
                "score": 0,
                "label": "NEUTRO",
                "count": 0,
            }

        positive_words = {
            "deal",
            "agreement",
            "ceasefire",
            "peace",
            "stimulus",
            "support",
            "recovery",
            "cooperation",
            "easing",
        }

        negative_words = {
            "tariff",
            "tariffs",
            "sanction",
            "sanctions",
            "war",
            "conflict",
            "escalation",
            "tension",
            "ban",
            "embargo",
            "trade war",
            "attack",
        }

        total = 0

        for article in articles:

            text = (
                (article.get("title") or "")
                + " "
                + (article.get("description") or "")
            ).lower()

            positive = 0
            negative = 0

            for word in positive_words:
                if word in text:
                    positive += 1

            for word in negative_words:
                if word in text:
                    negative += 1

            if positive > negative:
                total += 1

            elif negative > positive:
                total -= 1

        normalized = clamp(
            total / max(len(articles), 1),
            -1,
            1,
        )

        if normalized >= 0.20:
            label = "FAVOREVOLE"

        elif normalized <= -0.20:
            label = "SFAVOREVOLE"

        else:
            label = "NEUTRO"

        return {
            "score": normalized,
            "label": label,
            "count": len(articles),
        }

    except Exception as error:

        print(
            f"   ⚠️ Political Impact {name}: {error}"
        )

        return {
            "score": 0,
            "label": "ERRORE",
            "count": 0,
        }


# ============================================================
# DECISIONE
# ============================================================

def calculate_decision(
    a4h,
    a1h,
    a15,
    a5,
    a1,
    usd,
    news,
    political,
):

    scores = [
        a4h["score"],
        a1h["score"],
        a15["score"],
    ]

    base = sum(scores)

    # USD
    base += usd["impact"] * 2

    # News
    base += news["score"] * 3

    # Politica/geopolitica
    base += political["score"] * 4

    max_possible = 18

    probability = (
        0.50
        + (base / max_possible) * 0.40
    )

    probability = clamp(
        probability,
        0.01,
        0.99,
    )

    # Conferme veloci
    fast_confirmation = 0

    if a5["direction"] == (
        "LONG" if probability >= 0.50 else "SHORT"
    ):
        fast_confirmation += 1

    if a1["direction"] == (
        "LONG" if probability >= 0.50 else "SHORT"
    ):
        fast_confirmation += 1

    confidence = (
        abs(probability - 0.50)
        * 200
    )

    confidence += (
        fast_confirmation * 10
    )

    confidence = clamp(
        confidence,
        0,
        100,
    )

    if probability >= LONG_THRESHOLD:

        signal = "LONG"

    elif probability <= SHORT_THRESHOLD:

        signal = "SHORT"

    else:

        signal = "WAIT"

    # Penalizza conflitto forte
    main_direction = (
        "LONG"
        if probability >= 0.50
        else "SHORT"
    )

    opposite = (
        "SHORT"
        if main_direction == "LONG"
        else "LONG"
    )

    conflicts = 0

    for tf in (a4h, a1h, a15):

        if tf["direction"] == opposite:
            conflicts += 1

    if conflicts >= 2:

        signal = "WAIT"
        confidence = min(
            confidence,
            45,
        )

    # Score 0-100
    score = (
        abs(probability - 0.50)
        * 200
    )

    score += confidence * 0.30
    score += fast_confirmation * 8
    score += news["score"] * 5
    score += political["score"] * 8
    score += usd["impact"] * 3

    score -= conflicts * 8

    score = clamp(
        score,
        0,
        100,
    )

    if signal == "LONG" and score >= MIN_SCORE:
        grade = "🟢 FORTE"

    elif signal == "SHORT" and score >= MIN_SCORE:
        grade = "🔴 FORTE"

    elif signal in ("LONG", "SHORT"):
        grade = "🟡 DEBOLE"

    else:
        grade = "⚪ ATTENDERE"

    return {
        "signal": signal,
        "grade": grade,
        "score": score,
        "probability": probability,
        "confidence": confidence,
        "main_direction": main_direction,
        "fast_confirmation": fast_confirmation,
        "conflicts": conflicts,
    }


# ============================================================
# RISCHIO
# ============================================================

def calculate_risk(
    signal,
    price,
    atr_value,
):

    if price is None or atr_value <= 0:
        return None

    sl_distance = (
        atr_value * STOP_ATR
    )

    tp1_distance = (
        atr_value * TP1_ATR
    )

    tp2_distance = (
        atr_value * TP2_ATR
    )

    if signal == "LONG":

        return {
            "entry": price,
            "stop": price - sl_distance,
            "tp1": price + tp1_distance,
            "tp2": price + tp2_distance,
        }

    return {
        "entry": price,
        "stop": price + sl_distance,
        "tp1": price - tp1_distance,
        "tp2": price - tp2_distance,
    }


# ============================================================
# POSITION MEMORY
# ============================================================

def load_position():

    if not os.path.exists(
        POSITION_FILE
    ):
        return None

    try:

        with open(
            POSITION_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            return json.load(file)

    except Exception as error:

        print(
            f"⚠️ Errore posizione: {error}"
        )

        return None


def save_position(position):

    with open(
        POSITION_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            position,
            file,
            indent=2,
            ensure_ascii=False,
        )


def clear_position():

    if os.path.exists(
        POSITION_FILE
    ):

        os.remove(
            POSITION_FILE
        )


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(message):

    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN mancante."
        )

    if not TELEGRAM_CHAT_ID:
        raise RuntimeError(
            "TELEGRAM_CHAT_ID mancante."
        )

    url = (
        "https://api.telegram.org/"
        f"bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
    }

    print(
        "📨 Invio messaggio Telegram..."
    )

    response = requests.post(
        url,
        json=payload,
        timeout=30,
    )

    print(
        f"📡 Telegram HTTP: "
        f"{response.status_code}"
    )

    try:
        data = response.json()
    except Exception:
        data = {}

    if response.status_code != 200:

        raise RuntimeError(
            "Telegram HTTP error "
            f"{response.status_code}: "
            f"{response.text}"
        )

    if not data.get("ok"):

        raise RuntimeError(
            "Telegram ha rifiutato il "
            f"messaggio: {data}"
        )

    print(
        "✅ TELEGRAM: messaggio inviato."
    )


# ============================================================
# FORMAT TELEGRAM
# ============================================================

def signal_icon(signal):

    return {
        "LONG": "🟢",
        "SHORT": "🔴",
        "WAIT": "🟡",
    }.get(
        signal,
        "⚪",
    )


def tf_text(timeframes):

   