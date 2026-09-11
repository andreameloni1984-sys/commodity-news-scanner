import os
import json
import math
import time
import statistics
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests


# ============================================================
# COMMODITIES BOT v4.1
# MARKET INTELLIGENCE ENGINE
# PRICEPEDIA STYLE + TECHNICAL + GEOPOLITICAL + POLITICAL
# PAPER ONLY
# ============================================================

VERSION = "4.1"

TWELVE_KEY = os.getenv("TWELVE_DATA_API_KEY", "")
NEWS_KEY = os.getenv("NEWS_API_KEY", "")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

PAPER_ONLY = os.getenv("PAPER_TRADING_ONLY", "1") == "1"

INTELLIGENCE_ENABLED = os.getenv(
    "MARKET_INTELLIGENCE_ENABLED", "1"
) == "1"

MIN_PROBABILITY = float(os.getenv("MIN_ENTRY_PROBABILITY", "62"))
MIN_QUALITY = float(os.getenv("MIN_ENTRY_QUALITY", "55"))
MIN_CONFIDENCE = float(os.getenv("MIN_ENTRY_CONFIDENCE", "60"))
MIN_RR = float(os.getenv("MIN_ENTRY_RR", "2.5"))

INTELLIGENCE_WEIGHT = float(
    os.getenv("INTELLIGENCE_WEIGHT", "0.20")
)

POLITICAL_WEIGHT = float(
    os.getenv("POLITICAL_IMPACT_WEIGHT", "0.20")
)

GEOPOLITICAL_WEIGHT = float(
    os.getenv("GEOPOLITICAL_IMPACT_WEIGHT", "0.20")
)

FUNDAMENTALS_WEIGHT = float(
    os.getenv("FUNDAMENTALS_WEIGHT", "0.15")
)

REGIME_WEIGHT = float(
    os.getenv("MARKET_REGIME_WEIGHT", "0.10")
)

CROSS_WEIGHT = float(
    os.getenv("CROSS_COMMODITY_WEIGHT", "0.10")
)

FUTURES_WEIGHT = float(
    os.getenv("FUTURES_STRUCTURE_WEIGHT", "0.05")
)


# ============================================================
# COMMODITIES
# ============================================================

COMMODITIES = {
    "Gold": {
        "symbol": "XAU/USD",
        "keywords": [
            "gold",
            "bullion",
            "central bank",
            "safe haven"
        ],
        "group": "metals"
    },
    "Silver": {
        "symbol": "XAG/USD",
        "keywords": [
            "silver",
            "industrial metals"
        ],
        "group": "metals"
    },
    "Platinum": {
        "symbol": "XPT/USD",
        "keywords": [
            "platinum"
        ],
        "group": "metals"
    },
    "Palladium": {
        "symbol": "XPD/USD",
        "keywords": [
            "palladium"
        ],
        "group": "metals"
    },
    "WTI": {
        "symbol": "WTI/USD",
        "keywords": [
            "oil",
            "crude",
            "wti",
            "opec"
        ],
        "group": "energy"
    },
    "Brent": {
        "symbol": "XBR/USD",
        "keywords": [
            "brent",
            "oil",
            "opec"
        ],
        "group": "energy"
    },
    "Natural Gas": {
        "symbol": "NG/USD",
        "keywords": [
            "natural gas",
            "lng",
            "gas storage"
        ],
        "group": "energy"
    },
    "Copper": {
        "symbol": "HG1",
        "keywords": [
            "copper",
            "china",
            "industrial metals"
        ],
        "group": "metals"
    },
}


# ============================================================
# UTILS
# ============================================================

def now():
    return datetime.now(timezone.utc)


def safe_float(value):
    try:
        return float(value)
    except Exception:
        return None


def clamp(value, low=0, high=100):
    return max(low, min(high, value))


def average(values):
    values = [v for v in values if v is not None]
    return statistics.mean(values) if values else 0.0


# ============================================================
# TWELVE DATA
# ============================================================

def twelve_price(symbol: str) -> Optional[float]:
    if not TWELVE_KEY:
        return None

    try:
        url = "https://api.twelvedata.com/price"

        response = requests.get(
            url,
            params={
                "symbol": symbol,
                "apikey": TWELVE_KEY
            },
            timeout=12
        )

        if response.status_code != 200:
            return None

        data = response.json()

        return safe_float(data.get("price"))

    except Exception:
        return None


def twelve_series(symbol: str, interval="15min", outputsize=100):
    if not TWELVE_KEY:
        return []

    try:
        url = "https://api.twelvedata.com/time_series"

        response = requests.get(
            url,
            params={
                "symbol": symbol,
                "interval": interval,
                "outputsize": outputsize,
                "apikey": TWELVE_KEY
            },
            timeout=15
        )

        if response.status_code != 200:
            return []

        data = response.json()

        values = []

        for row in data.get("values", []):
            close = safe_float(row.get("close"))

            if close is not None:
                values.append(close)

        return list(reversed(values))

    except Exception:
        return []


# ============================================================
# TECHNICAL ENGINE
# ============================================================

def sma(values, period):
    if len(values) < period:
        return None

    return average(values[-period:])


def momentum(values, period=10):
    if len(values) <= period:
        return 0

    old = values[-period - 1]
    new = values[-1]

    if old == 0:
        return 0

    return ((new - old) / old) * 100


def volatility(values, period=20):
    if len(values) < period + 1:
        return 0

    returns = []

    for i in range(-period, 0):
        old = values[i - 1]
        new = values[i]

        if old:
            returns.append((new - old) / old)

    if len(returns) < 2:
        return 0

    return statistics.stdev(returns) * 100


def technical_analysis(values):

    if len(values) < 30:
        return {
            "direction": "WAIT",
            "score": 50,
            "trend": "UNKNOWN",
            "volatility": 0
        }

    price = values[-1]

    fast = sma(values, 10)
    slow = sma(values, 30)

    mom = momentum(values, 10)
    vol = volatility(values)

    score = 50

    if fast and slow:

        if price > fast:
            score += 10

        else:
            score -= 10

        if fast > slow:
            score += 20

        else:
            score -= 20

    if mom > 0.15:
        score += 10

    elif mom < -0.15:
        score -= 10

    score = clamp(score)

    if score >= 60:
        direction = "LONG"
        trend = "BULLISH"

    elif score <= 40:
        direction = "SHORT"
        trend = "BEARISH"

    else:
        direction = "WAIT"
        trend = "NEUTRAL"

    return {
        "direction": direction,
        "score": score,
        "trend": trend,
        "momentum": mom,
        "volatility": vol
    }


# ============================================================
# NEWS ENGINE
# ============================================================

def news_articles(query):
    if not NEWS_KEY:
        return []

    try:
        url = "https://newsapi.org/v2/everything"

        response = requests.get(
            url,
            params={
                "q": query,
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": 20,
                "apiKey": NEWS_KEY
            },
            timeout=15
        )

        if response.status_code != 200:
            return []

        return response.json().get("articles", [])

    except Exception:
        return []


# ============================================================
# POLITICAL / GEOPOLITICAL ENGINE
# ============================================================

POLITICAL_WORDS = [
    "trump",
    "tariff",
    "sanction",
    "election",
    "government",
    "fed",
    "white house",
    "policy",
    "tax",
    "trade war"
]

GEOPOLITICAL_WORDS = [
    "war",
    "iran",
    "israel",
    "russia",
    "ukraine",
    "china",
    "taiwan",
    "conflict",
    "attack",
    "missile",
    "military",
    "ceasefire",
    "sanctions"
]


def impact_from_articles(articles):

    political_hits = 0
    geopolitical_hits = 0
    total = 0

    for article in articles:

        title = (
            str(article.get("title", "")) +
            " " +
            str(article.get("description", ""))
        ).lower()

        total += 1

        if any(word in title for word in POLITICAL_WORDS):
            political_hits += 1

        if any(word in title for word in GEOPOLITICAL_WORDS):
            geopolitical_hits += 1

    if total == 0:
        return {
            "political": 50,
            "geopolitical": 50
        }

    political = clamp(
        50 + (political_hits / total) * 100
    )

    geopolitical = clamp(
        50 + (geopolitical_hits / total) * 100
    )

    return {
        "political": political,
        "geopolitical": geopolitical
    }


# ============================================================
# PRICEPEDIA-STYLE MARKET INTELLIGENCE
# ============================================================

def fundamentals_score(name):

    """
    Proxy fundamentals layer.

    In assenza di un feed fondamentale dedicato:
    non inventa dati.
    Restituisce neutralità.

    Potrà essere alimentato successivamente da:
    - scorte
    - domanda
    - offerta
    - produzione
    - calendario macro
    """

    return 50


def futures_structure_score(name):

    """
    CME/futures è opzionale.
    Se non disponibile non penalizza il mercato.
    """

    return 50


def market_regime(technical):

    trend = technical["trend"]
    vol = technical["volatility"]

    if trend == "BULLISH" and vol < 2:
        return 65

    if trend == "BEARISH" and vol < 2:
        return 65

    if vol > 4:
        return 40

    return 50


def cross_commodity_score(name, technical_results):

    data = technical_results.get(name)

    if not data:
        return 50

    direction = data["direction"]

    same_group = []

    group = COMMODITIES[name]["group"]

    for commodity, result in technical_results.items():

        if commodity == name:
            continue

        if COMMODITIES.get(commodity, {}).get("group") == group:
            same_group.append(result["direction"])

    if not same_group:
        return 50

    confirmations = same_group.count(direction)

    return clamp(
        50 + confirmations * 12
    )


def intelligence_engine(
    name,
    technical,
    political,
    geopolitical,
    technical_results
):

    fundamental = fundamentals_score(name)
    regime = market_regime(technical)
    cross = cross_commodity_score(
        name,
        technical_results
    )
    futures = futures_structure_score(name)

    raw = (
        political * POLITICAL_WEIGHT +
        geopolitical * GEOPOLITICAL_WEIGHT +
        fundamental * FUNDAMENTALS_WEIGHT +
        regime * REGIME_WEIGHT +
        cross * CROSS_WEIGHT +
        futures * FUTURES_WEIGHT
    )

    return {
        "score": clamp(raw),
        "political": political,
        "geopolitical": geopolitical,
        "fundamentals": fundamental,
        "regime": regime,
        "cross": cross,
        "futures": futures
    }


# ============================================================
# SETUP / ENTRY / SL / TP
# ============================================================

def calculate_trade(price, technical):

    direction = technical["direction"]

    if direction == "WAIT" or price is None:
        return None

    vol = technical["volatility"]

    # volatilità percentuale -> buffer adattivo
    atr_proxy = max(
        price * max(vol / 100, 0.002),
        price * 0.002
    )

    if direction == "LONG":

        entry = price
        sl = price - atr_proxy * 1.0

        risk = entry - sl

        tp1 = entry + risk * 1.5
        tp2 = entry + risk * 2.0
        tp3 = entry + risk * 2.5

    else:

        entry = price
        sl = price + atr_proxy * 1.0

        risk = sl - entry

        tp1 = entry - risk * 1.5
        tp2 = entry - risk * 2.0
        tp3 = entry - risk * 2.5

    return {
        "direction": direction,
        "entry": entry,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "rr": 2.5
    }


# ============================================================
# FINAL SCORE
# ============================================================

def final_analysis(
    name,
    price,
    technical,
    intelligence
):

    if price is None:
        return None

    tech_score = technical["score"]

    intelligence_score = intelligence["score"]

    score = (
        tech_score * (1 - INTELLIGENCE_WEIGHT)
        +
        intelligence_score * INTELLIGENCE_WEIGHT
    )

    direction = technical["direction"]

    confidence = score

    quality = score

    if direction == "WAIT":
        probability = 50

    else:
        probability = score

    trade = calculate_trade(
        price,
        technical
    )

    operational = "ATTENDERE"

    if (
        trade
        and probability >= MIN_PROBABILITY
        and quality >= MIN_QUALITY
        and confidence >= MIN_CONFIDENCE
        and trade["rr"] >= MIN_RR
    ):
        operational = "SETUP"

    return {
        "name": name,
        "price": price,
        "direction": direction,
        "score": round(score, 1),
        "probability": round(probability, 1),
        "quality": round(quality, 1),
        "confidence": round(confidence, 1),
        "operational": operational,
        "technical": technical,
        "intelligence": intelligence,
        "trade": trade
    }


# ============================================================
# RANKING
# ============================================================

def ranking(results):

    valid = [
        x for x in results
        if x is not None
    ]

    valid.sort(
        key=lambda x: (
            x["operational"] == "SETUP",
            x["score"]
        ),
        reverse=True
    )

    return valid


# ============================================================
# TELEGRAM
# ============================================================

def telegram_send(message):

    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print(message)
        return

    try:

        url = (
            f"https://api.telegram.org/bot"
            f"{TELEGRAM_TOKEN}/sendMessage"
        )

        requests.post(
            url,
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message
            },
            timeout=15
        )

    except Exception as exc:
        print("Telegram error:", exc)


# ============================================================
# TELEGRAM FORMAT
# ============================================================

def format_ranking(results):

    text = "🌍 COMMODITIES BOT v4.1\n\n"
    text += "🏆 CLASSIFICA\n\n"

    medals = ["🥇", "🥈", "🥉"]

    for index, result in enumerate(results[:3]):

        medal = medals[index]

        text += (
            f"{medal} {result['name']}\n"
            f"➡️ {result['direction']}\n"
            f"💰 Prezzo: {result['price']:.4f}\n"
            f"📊 Score: {result['score']:.1f}\n"
            f"🎯 Probabilità: {result['probability']:.1f}%\n"
            f"⭐ Qualità: {result['quality']:.1f}\n"
            f"🧠 Confidence: {result['confidence']:.1f}\n"
            f"⚙️ Stato: {result['operational']}\n"
        )

        trade = result.get("trade")

        if trade:

            text += (
                f"📍 Entry: {trade['entry']:.4f}\n"
                f"🛑 SL: {trade['sl']:.4f}\n"
                f"🎯 TP1: {trade['tp1']:.4f}\n"
                f"🎯 TP2: {trade['tp2']:.4f}\n"
                f"🎯 TP3: {trade['tp3']:.4f}\n"
            )

        intelligence = result["intelligence"]

        text += (
            f"🌐 Intelligence: {intelligence['score']:.1f}\n"
            f"🏛 Politico: {intelligence['political']:.1f}\n"
            f"🌍 Geopolitico: {intelligence['geopolitical']:.1f}\n"
            f"📦 Fondamentali: {intelligence['fundamentals']:.1f}\n"
            f"🔄 Regime: {intelligence['regime']:.1f}\n"
            f"🔗 Cross-market: {intelligence['cross']:.1f}\n"
            f"📈 Futures: {intelligence['futures']:.1f}\n\n"
        )

    return text


# ============================================================
# TELEGRAM COMMANDS
# ============================================================

def telegram_updates(offset=None):

    if not TELEGRAM_TOKEN:
        return []

    try:

        url = (
            f"https://api.telegram.org/bot"
            f"{TELEGRAM_TOKEN}/getUpdates"
        )

        params = {
            "timeout": 5
        }

        if offset is not None:
            params["offset"] = offset

        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        if response.status_code != 200:
            return []

        return response.json().get(
            "result",
            []
        )

    except Exception:
        return []


def handle_commands(results):

    updates = telegram_updates()

    for update in updates:

        message = update.get("message", {})
        text = message.get("text", "").lower().strip()

        if (
            "classifica" in text
            or "ranking" in text
            or "mandami la classifica" in text
        ):

            telegram_send(
                format_ranking(results)
            )


# ============================================================
# MAIN ANALYSIS
# ============================================================

def run_analysis():

    print(
        f"COMMODITIES BOT v{VERSION} "
        f"| PAPER ONLY={PAPER_ONLY}"
    )

    prices = {}
    series = {}

    for name, config in COMMODITIES.items():

        symbol = config["symbol"]

        price = twelve_price(symbol)

        values = twelve_series(
            symbol,
            interval="15min",
            outputsize=100
        )

        prices[name] = price
        series[name] = values

        print(
            name,
            symbol,
            price,
            len(values)
        )

    technical_results = {}

    for name in COMMODITIES:

        technical_results[name] = technical_analysis(
            series[name]
        )

    results = []

    for name, config in COMMODITIES.items():

        technical = technical_results[name]

        articles = news_articles(
            " OR ".join(config["keywords"])
        )

        impacts = impact_from_articles(
            articles
        )

        intelligence = intelligence_engine(
            name=name,
            technical=technical,
            political=impacts["political"],
            geopolitical=impacts["geopolitical"],
            technical_results=technical_results
        )

        result = final_analysis(
            name=name,
            price=prices[name],
            technical=technical,
            intelligence=intelligence
        )

        results.append(result)

    ranked = ranking(results)

    message = format_ranking(ranked)

    print(message)

    # Telegram
    telegram_send(message)

    # Comandi Telegram
    handle_commands(ranked)

    return ranked


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:
        run_analysis()

    except Exception as exc:

        print(
            "BOT ERROR:",
            repr(exc)
        )