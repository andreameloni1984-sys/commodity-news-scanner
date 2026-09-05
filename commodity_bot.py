import os
import math
import requests
from datetime import datetime, timezone
from statistics import mean
# ============================================================
# 🏆 COMMODITY TRADING BOT
# Analisi di:
# - Trend
# - Momentum
# - Volatilità
# - Volume
# - Notizie
# ============================================================
API_KEY = os.getenv("TWELVE_DATA_API_KEY")
if not API_KEY:
    raise RuntimeError(
        "TWELVE_DATA_API_KEY non configurata nei GitHub Secrets."
    )
BASE_URL = "https://api.twelvedata.com"
# ============================================================
# MATERIE PRIME
# ============================================================
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
# ============================================================
# PAROLE PER ANALISI NOTIZIE
# ============================================================
POSITIVE_WORDS = [
    "surge",
    "rises",
    "rise",
    "higher",
    "gain",
    "gains",
    "bullish",
    "strong",
    "demand",
    "shortage",
    "boost",
    "record",
    "support",
    "optimism",
    "upside",
    "growth",
    "cuts",
    "cut",
    "tight supply",
    "supply concern",
]
NEGATIVE_WORDS = [
    "falls",
    "fall",
    "lower",
    "drop",
    "drops",
    "decline",
    "bearish",
    "weak",
    "oversupply",
    "surplus",
    "slump",
    "recession",
    "risk",
    "downside",
    "collapse",
    "selling",
    "inventory build",
    "demand concern",
]
# ============================================================
# API
# ============================================================
def api_get(endpoint, params):
    params = dict(params)
    params["apikey"] = API_KEY
    response = requests.get(
        f"{BASE_URL}/{endpoint}",
        params=params,
        timeout=20
    )
    response.raise_for_status()
    data = response.json()
    if isinstance(data, dict) and data.get("status") == "error":
        raise RuntimeError(
            data.get("message", "Errore Twelve Data")
        )
    return data
# ============================================================
# PREZZI
# ============================================================
def get_prices(symbol, interval="1h", outputsize=100):
    data = api_get(
        "time_series",
        {
            "symbol": symbol,
            "interval": interval,
            "outputsize": outputsize,
        }
    )
    values = data.get("values", [])
    if not values:
        raise RuntimeError(
            f"Nessun dato ricevuto per {symbol}"
        )
    values = list(reversed(values))
    cleaned = []
    for row in values:
        try:
            cleaned.append(
                {
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row.get("volume") or 0),
                }
            )
        except (
            KeyError,
            TypeError,
            ValueError,
        ):
            continue
    if len(cleaned) < 30:
        raise RuntimeError(
            f"Dati insufficienti per {symbol}: "
            f"{len(cleaned)} candele"
        )
    return cleaned
# ============================================================
# NOTIZIE
# ============================================================
def get_news(query):
    try:
        import xml.etree.ElementTree as ET
        url = "https://news.google.com/rss/search"
        response = requests.get(
            url,
            params={
                "q": f"{query} commodity",
                "hl": "en-US",
                "gl": "US",
                "ceid": "US:en",
            },
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0"
            },
        )
        response.raise_for_status()
        root = ET.fromstring(
            response.text
        )
        headlines = []
        for item in root.findall(".//item")[:10]:
            title = item.findtext("title")
            if title:
                headlines.append(title)
        return headlines
    except Exception:
        return []
# ============================================================
# SMA
# ============================================================
def sma(values, period):
    if len(values) < period:
        return None
    return mean(values[-period:])
# ============================================================
# MOMENTUM
# ============================================================
def calculate_returns(
    closes,
    period
):
    if len(closes) <= period:
        return 0
    old_price = closes[-period - 1]
    new_price = closes[-1]
    if old_price == 0:
        return 0
    return (
        (new_price / old_price) - 1
    ) * 100
# ============================================================
# VOLATILITÀ
# ============================================================
def calculate_volatility(
    closes,
    period=20
):
    if len(closes) < period + 1:
        return 0
    returns = []
    start = len(closes) - period
    for i in range(
        start,
        len(closes)
    ):
        previous = closes[i - 1]
        if previous != 0:
            returns.append(
                (
                    closes[i] / previous - 1
                ) * 100
            )
    if not returns:
        return 0
    average = mean(returns)
    variance = mean(
        [
            (x - average) ** 2
            for x in returns
        ]
    )
    return math.sqrt(variance)
# ============================================================
# ANALISI NOTIZIE
# ============================================================
def analyze_news(headlines):
    if not headlines:
        return {
            "score": 0,
            "positive": 0,
            "negative": 0,
            "headlines": [],
        }
    positive = 0
    negative = 0
    classified = []
    for headline in headlines:
        text = headline.lower()
        positive_hits = sum(
            1
            for word in POSITIVE_WORDS
            if word in text
        )
        negative_hits = sum(
            1
            for word in NEGATIVE_WORDS
            if word in text
        )
        if positive_hits > negative_hits:
            positive += 1
            classified.append(
                (
                    "POSITIVA",
                    headline
                )
            )
        elif negative_hits > positive_hits:
            negative += 1
            classified.append(
                (
                    "NEGATIVA",
                    headline
                )
            )
    total = positive + negative
    if total == 0:
        score = 0
    else:
        score = (
            (positive - negative)
            / total
        ) * 100
    return {
        "score": score,
        "positive": positive,
        "negative": negative,
        "headlines": classified,
    }
# ============================================================
# ANALISI MATERIA PRIMA
# ============================================================
def analyze_commodity(
    name,
    symbol
):
    prices = get_prices(symbol)
    closes = [
        x["close"]
        for x in prices
    ]
    volumes = [
        x["volume"]
        for x in prices
    ]
    current_price = closes[-1]
    sma20 = sma(
        closes,
        20
    )
    sma50 = sma(
        closes,
        50
    )
    momentum_6h = calculate_returns(
        closes,
        6
    )
    momentum_24h = calculate_returns(
        closes,
        24
    )
    volatility = calculate_volatility(
        closes,
        20
    )
    # ========================================================
    # TREND
    # ========================================================
    trend_score = 0
    if sma20 is not None:
        if current_price > sma20:
            trend_score += 25
        else:
            trend_score -= 25
    if sma50 is not None:
        if current_price > sma50:
            trend_score += 25
        else:
            trend_score -= 25
    if (
        sma20 is not None
        and sma50 is not None
    ):
        if sma20 > sma50:
            trend_score += 20
        else:
            trend_score -= 20
    # ========================================================
    # MOMENTUM
    # ========================================================
    momentum_score = 0
    if momentum_6h > 0:
        momentum_score += 15
    else:
        momentum_score -= 15
    if momentum_24h > 0:
        momentum_score += 15
    else:
        momentum_score -= 15
    momentum_score = max(
        -30,
        min(
            30,
            momentum_score
        )
    )
    # ========================================================
    # VOLUME
    # ========================================================
    volume_score = 0
    valid_volumes = [
        v
        for v in volumes[-20:]
        if v > 0
    ]
    recent_volumes = [
        v
        for v in volumes[-5:]
        if v > 0
    ]
    if (
        valid_volumes
        and recent_volumes
    ):
        average_volume = mean(
            valid_volumes
        )
        recent_average = mean(
            recent_volumes
        )
        if recent_average > average_volume * 1.20:
            volume_score = 10
        elif recent_average < average_volume * 0.80:
            volume_score = -5
    # ========================================================
    # NOTIZIE
    # ========================================================
    headlines = get_news(name)
    news_analysis = analyze_news(
        headlines
    )
    news_score = news_analysis["score"]
    news_points = max(
        -20,
        min(
            20,
            news_score * 0.20
        )
    )
    # ========================================================
    # PUNTEGGIO
    # ========================================================
    raw_score = (
        trend_score
        + momentum_score
        + volume_score
        + news_points
    )
    final_score = 50 + raw_score
    final_score = max(
        0,
        min(
            100,
            final_score
        )
    )
    # ========================================================
    # SEGNALE
    # ========================================================
    if final_score >= 70:
        signal = "🟢 LONG"
    elif final_score <= 30:
        signal = "🔴 SHORT"
    else:
        signal = "🟡 ASPETTARE"
    return {
        "name": name,
        "symbol": symbol,
        "price": current_price,
        "score": final_score,
        "signal": signal,
        "trend": trend_score,
        "momentum": momentum_score,
        "volume": volume_score,
        "news_points": news_points,
        "momentum_6h": momentum_6h,
        "momentum_24h": momentum_24h,
        "volatility": volatility,
        "news_count": len(headlines),
        "news_positive": news_analysis[
            "positive"
        ],
        "news_negative": news_analysis[
            "negative"
        ],
        "news_headlines": news_analysis[
            "headlines"
        ],
    }
# ============================================================
# REPORT
# ============================================================
def print_report(results):
    print()
    print("=" * 70)
    print("          🏆 COMMODITY TRADING BOT")
    print("=" * 70)
    now = datetime.now(
        timezone.utc
    ).strftime(
        "%Y-%m-%d %H:%M UTC"
    )
    print(
        f"🕒 Aggiornamento: {now}"
    )
    print()
    # Classifica dal migliore al peggiore
    results.sort(
        key=lambda x: x["score"],
        reverse=True
    )
    print("📊 CLASSIFICA")
    print("-" * 70)
    for position, result in enumerate(
        results,
        1
    ):
        print(
            f"{position}. "
            f"{result['name']:<18} "
            f"{result['score']:>5.1f}/100 "
            f"{result['signal']}"
        )
    print()
    # Migliore opportunità
    best = results[0]
    print("=" * 70)
    print("🥇 MIGLIOR SETUP")
    print("=" * 70)
    print(
        f"Materia prima : {best['name']}"
    )
    print(
        f"Simbolo       : {best['symbol']}"
    )
    print(
        f"Prezzo        : {best['price']:.4f}"
    )
    print(
        f"Segnale       : {best['signal']}"
    )
    print(
        f"Forza         : {best['score']:.1f}/100"
    )
    print()
    print("📈 COMPONENTI")
    print(
        f"Trend         : "
        f"{best['trend']:+.1f}"
    )
    print(
        f"Momentum      : "
        f"{best['momentum']:+.1f}"
    )
    print(
        f"Volume        : "
        f"{best['volume']:+.1f}"
    )
    print(
        f"Notizie       : "
        f"{best['news_points']:+.1f}"
    )
    print()
    print("📊 MOMENTUM")
    print(
        f"6 ore         : "
        f"{best['momentum_6h']:+.2f}%"
    )
    print(
        f"24 ore        : "
        f"{best['momentum_24h']:+.2f}%"
    )
    print()
    print("🌪️ VOLATILITÀ")
    print(
        f"20 periodi    : "
        f"{best['volatility']:.3f}%"
    )
    print()
    print("📰 NOTIZIE")
    print(
        f"Totali        : "
        f"{best['news_count']}"
    )
    print(
        f"Positive      : "
        f"{best['news_positive']}"
    )
    print(
        f"Negative      : "
        f"{best['news_negative']}"
    )
    if best["news_headlines"]:
        print()
        for sentiment, headline in (
            best["news_headlines"][:5]
        ):
            print(
                f"- {sentiment}: "
                f"{headline}"
            )
    else:
        print(
            "- Nessuna notizia "
            "classificabile."
        )
    print()
    print("=" * 70)
    if best["score"] >= 70:
        print(
            "🎯 CONCLUSIONE: "
            "setup rialzista forte."
        )
    elif best["score"] <= 30:
        print(
            "🎯 CONCLUSIONE: "
            "setup ribassista forte."
        )
    else:
        print(
            "🎯 CONCLUSIONE: "
            "nessun setup abbastanza forte."
        )
    print(
        "⚠️ Il punteggio è un indicatore "
        "automatico e non garantisce profitti."
    )
    print("=" * 70)
# ============================================================
# AVVIO
# ============================================================
def main():
    results = []
    print()
    print(
        "🚀 Avvio Commodity Trading Bot..."
    )
    print()
    for name, symbol in (
        COMMODITIES.items()
    ):
        print(
            f"🔎 Analizzo "
            f"{name} ({symbol})..."
        )
        try:
            result = analyze_commodity(
                name,
                symbol
            )
            results.append(result)
            print(
                f"   ✅ "
                f"{result['score']:.1f}/100 "
                f"{result['signal']}"
            )
        except Exception as error:
            print(
                f"   ⚠️ {name}: "
                f"{error}"
            )
    if not results:
        raise RuntimeError(
            "Nessuna materia prima "
            "è stata analizzata."
        )
    print_report(
        results
    )
if __name__ == "__main__":
    main()