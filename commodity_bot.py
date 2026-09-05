import os
import math
import requests
from datetime import datetime, timezone
from statistics import mean
# ============================================================
# 🏆 COMMODITY TRADING BOT v2
# ============================================================
API_KEY = os.getenv("TWELVE_DATA_API_KEY")
if not API_KEY:
    raise RuntimeError(
        "TWELVE_DATA_API_KEY non configurata nei GitHub Secrets."
    )
BASE_URL = "https://api.twelvedata.com"
# Materie prime principali.
# Se una non è disponibile sul tuo piano/API viene saltata.
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
POSITIVE_WORDS = [
    "surge", "rises", "rise", "higher", "gain", "gains",
    "bullish", "strong", "demand", "shortage", "boost",
    "record", "support", "optimism", "upside", "growth",
    "cuts", "cut", "tight supply", "supply concern"
]
NEGATIVE_WORDS = [
    "falls", "fall", "lower", "drop", "drops", "decline",
    "bearish", "weak", "oversupply", "surplus", "slump",
    "recession", "risk", "downside", "collapse", "selling",
    "inventory build", "demand concern"
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
            "outputsize": outputsize
        }
    )
    values = data.get("values", [])
    if not values:
        raise RuntimeError(
            f"Nessun dato disponibile per {symbol}"
        )
    values = list(reversed(values))
    result = []
    for row in values:
        try:
            result.append({
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row.get("volume") or 0)
            })
        except (KeyError, TypeError, ValueError):
            continue
    if len(result) < 30:
        raise RuntimeError(
            f"Dati insufficienti per {symbol}"
        )
    return result
# ============================================================
# NOTIZIE
# ============================================================
def get_news(query):
    try:
        import xml.etree.ElementTree as ET
        response = requests.get(
            "https://news.google.com/rss/search",
            params={
                "q": f"{query} commodity",
                "hl": "en-US",
                "gl": "US",
                "ceid": "US:en"
            },
            headers={
                "User-Agent": "Mozilla/5.0"
            },
            timeout=15
        )
        response.raise_for_status()
        root = ET.fromstring(response.text)
        headlines = []
        for item in root.findall(".//item")[:15]:
            title = item.findtext("title")
            if title:
                headlines.append(title)
        return headlines
    except Exception:
        return []
def analyze_news(headlines):
    positive = 0
    negative = 0
    classified = []
    for headline in headlines:
        text = headline.lower()
        pos = sum(
            1 for word in POSITIVE_WORDS
            if word in text
        )
        neg = sum(
            1 for word in NEGATIVE_WORDS
            if word in text
        )
        if pos > neg:
            positive += 1
            classified.append(
                ("POSITIVA", headline)
            )
        elif neg > pos:
            negative += 1
            classified.append(
                ("NEGATIVA", headline)
            )
    total = positive + negative
    if total == 0:
        score = 0
    else:
        score = (
            (positive - negative) / total
        ) * 100
    return {
        "score": score,
        "positive": positive,
        "negative": negative,
        "classified": classified
    }
# ============================================================
# INDICATORI
# ============================================================
def sma(values, period):
    if len(values) < period:
        return None
    return mean(values[-period:])
def percentage_change(values, period):
    if len(values) <= period:
        return 0
    old = values[-period - 1]
    new = values[-1]
    if old == 0:
        return 0
    return ((new / old) - 1) * 100
def calculate_volatility(values, period=20):
    if len(values) < period + 1:
        return 0
    returns = []
    for i in range(
        len(values) - period,
        len(values)
    ):
        previous = values[i - 1]
        if previous != 0:
            returns.append(
                ((values[i] / previous) - 1) * 100
            )
    if not returns:
        return 0
    avg = mean(returns)
    variance = mean(
        [(x - avg) ** 2 for x in returns]
    )
    return math.sqrt(variance)
def calculate_atr(candles, period=14):
    if len(candles) < period + 1:
        return 0
    true_ranges = []
    for i in range(
        len(candles) - period,
        len(candles)
    ):
        current = candles[i]
        previous = candles[i - 1]
        high = current["high"]
        low = current["low"]
        previous_close = previous["close"]
        tr = max(
            high - low,
            abs(high - previous_close),
            abs(low - previous_close)
        )
        true_ranges.append(tr)
    return mean(true_ranges)
# ============================================================
# ANALISI COMPLETA
# ============================================================
def analyze_commodity(name, symbol):
    candles = get_prices(symbol)
    closes = [
        x["close"]
        for x in candles
    ]
    volumes = [
        x["volume"]
        for x in candles
    ]
    current = closes[-1]
    sma20 = sma(closes, 20)
    sma50 = sma(closes, 50)
    momentum_6h = percentage_change(
        closes, 6
    )
    momentum_24h = percentage_change(
        closes, 24
    )
    volatility = calculate_volatility(
        closes, 20
    )
    atr = calculate_atr(
        candles, 14
    )
    # ========================================================
    # TREND
    # ========================================================
    trend_score = 0
    if sma20 is not None:
        if current > sma20:
            trend_score += 20
        else:
            trend_score -= 20
    if sma50 is not None:
        if current > sma50:
            trend_score += 20
        else:
            trend_score -= 20
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
    # ========================================================
    # PRESSIONE ACQUISTI / VENDITE
    # ========================================================
    buying_pressure = 0
    selling_pressure = 0
    for candle in candles[-20:]:
        candle_range = (
            candle["high"] - candle["low"]
        )
        if candle_range <= 0:
            continue
        position = (
            candle["close"] - candle["low"]
        ) / candle_range
        if position >= 0.60:
            buying_pressure += 1
        elif position <= 0.40:
            selling_pressure += 1
    total_pressure = (
        buying_pressure
        + selling_pressure
    )
    if total_pressure > 0:
        pressure_score = (
            (
                buying_pressure
                - selling_pressure
            )
            / total_pressure
        ) * 20
    else:
        pressure_score = 0
    # ========================================================
    # VOLUME
    # ========================================================
    volume_score = 0
    valid_volumes = [
        x for x in volumes[-20:]
        if x > 0
    ]
    recent_volumes = [
        x for x in volumes[-5:]
        if x > 0
    ]
    if valid_volumes and recent_volumes:
        avg_volume = mean(
            valid_volumes
        )
        recent_average = mean(
            recent_volumes
        )
        if recent_average > avg_volume * 1.20:
            volume_score = 10
        elif recent_average < avg_volume * 0.80:
            volume_score = -5
    # ========================================================
    # NOTIZIE
    # ========================================================
    headlines = get_news(name)
    news = analyze_news(
        headlines
    )
    news_points = max(
        -15,
        min(
            15,
            news["score"] * 0.15
        )
    )
    # ========================================================
    # SCORE
    # ========================================================
    raw_score = (
        trend_score
        + momentum_score
        + pressure_score
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
    # DIREZIONE
    # ========================================================
    if final_score >= 65:
        direction = "LONG"
    elif final_score <= 35:
        direction = "SHORT"
    else:
        direction = "WAIT"
    # ========================================================
    # ENTRY / SL / TP
    # ========================================================
    if atr <= 0:
        atr = current * 0.01
    if direction == "LONG":
        entry = current
        stop_loss = current - (
            atr * 1.5
        )
        risk = entry - stop_loss
        take_profit_1 = entry + (
            risk * 1.5
        )
        take_profit_2 = entry + (
            risk * 2.5
        )
    elif direction == "SHORT":
        entry = current
        stop_loss = current + (
            atr * 1.5
        )
        risk = stop_loss - entry
        take_profit_1 = entry - (
            risk * 1.5
        )
        take_profit_2 = entry - (
            risk * 2.5
        )
    else:
        entry = current
        stop_loss = None
        take_profit_1 = None
        take_profit_2 = None
        risk = None
    # ========================================================
    # FORZA SETUP
    # ========================================================
    if final_score >= 80 or final_score <= 20:
        strength = "🔥 MOLTO FORTE"
    elif final_score >= 70 or final_score <= 30:
        strength = "💪 FORTE"
    elif final_score >= 60 or final_score <= 40:
        strength = "⚠️ MODERATA"
    else:
        strength = "🟡 DEBOLE"
    # Se la direzione è WAIT, non proponiamo operazione.
    if direction == "WAIT":
        signal = "🟡 ASPETTARE"
    elif direction == "LONG":
        signal = "🟢 LONG"
    else:
        signal = "🔴 SHORT"
    return {
        "name": name,
        "symbol": symbol,
        "price": current,
        "score": final_score,
        "direction": direction,
        "signal": signal,
        "strength": strength,
        "trend": trend_score,
        "momentum": momentum_score,
        "pressure": pressure_score,
        "volume": volume_score,
        "news_points": news_points,
        "buying_pressure": buying_pressure,
        "selling_pressure": selling_pressure,
        "momentum_6h": momentum_6h,
        "momentum_24h": momentum_24h,
        "volatility": volatility,
        "atr": atr,
        "entry": entry,
        "stop_loss": stop_loss,
        "take_profit_1": take_profit_1,
        "take_profit_2": take_profit_2,
        "risk": risk,
        "news_count": len(headlines),
        "news_positive": news["positive"],
        "news_negative": news["negative"],
        "news_headlines": news["classified"]
    }
# ============================================================
# REPORT
# ============================================================
def print_report(results):
    print()
    print("=" * 75)
    print("             🏆 COMMODITY TRADING BOT v2")
    print("=" * 75)
    now = datetime.now(
        timezone.utc
    ).strftime(
        "%Y-%m-%d %H:%M UTC"
    )
    print(
        f"🕒 Aggiornamento: {now}"
    )
    print()
    print("📊 CLASSIFICA")
    print("-" * 75)
    results.sort(
        key=lambda x: x["score"],
        reverse=True
    )
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
    # ========================================================
    # MIGLIOR SETUP
    # ========================================================
    tradable = [
        r for r in results
        if r["direction"] != "WAIT"
    ]
    if not tradable:
        print()
        print("=" * 75)
        print(
            "🟡 NESSUNA OPPORTUNITÀ "
            "ABBASTANZA FORTE"
        )
        print("=" * 75)
        print(
            "Il bot consiglia di aspettare."
        )
        return
    best = tradable[0]
    print()
    print("=" * 75)
    print("🥇 MIGLIOR OPPORTUNITÀ")
    print("=" * 75)
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
    print(
        f"Setup         : {best['strength']}"
    )
    # ========================================================
    # LIVELLI
    # ========================================================
    print()
    print("🎯 LIVELLI OPERATIVI")
    print("-" * 75)
    print(
        f"Entry         : {best['entry']:.4f}"
    )
    print(
        f"Stop Loss     : {best['stop_loss']:.4f}"
    )
    print(
        f"Take Profit 1 : {best['take_profit_1']:.4f}"
    )
    print(
        f"Take Profit 2 : {best['take_profit_2']:.4f}"
    )
    if best["risk"] and best["risk"] > 0:
        rr1 = (
            abs(
                best["take_profit_1"]
                - best["entry"]
            )
            / best["risk"]
        )
        rr2 = (
            abs(
                best["take_profit_2"]
                - best["entry"]
            )
            / best["risk"]
        )
        print(
            f"R/R TP1      : 1:{rr1:.1f}"
        )
        print(
            f"R/R TP2      : 1:{rr2:.1f}"
        )
    # ========================================================
    # ANALISI
    # ========================================================
    print()
    print("📈 ANALISI")
    print("-" * 75)
    print(
        f"Trend         : "
        f"{best['trend']:+.1f}"
    )
    print(
        f"Momentum      : "
        f"{best['momentum']:+.1f}"
    )
    print(
        f"Pressione     : "
        f"{best['pressure']:+.1f}"
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
    print("🐂 PRESSIONE")
    print(
        f"Acquisti      : "
        f"{best['buying_pressure']}"
    )
    print(
        f"Vendite       : "
        f"{best['selling_pressure']}"
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
        f"Volatilità    : "
        f"{best['volatility']:.3f}%"
    )
    print(
        f"ATR           : "
        f"{best['atr']:.4f}"
    )
    # ========================================================
    # NOTIZIE
    # ========================================================
    print()
    print("📰 NOTIZIE")
    print("-" * 75)
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
    print("=" * 75)
    print(
        "⚠️ I livelli sono calcolati "
        "automaticamente sulla volatilità "
        "e non garantiscono il risultato."
    )
    print("=" * 75)
# ============================================================
# AVVIO
# ============================================================
def main():
    print()
    print(
        "🚀 Avvio Commodity Trading Bot v2..."
    )
    print()
    results = []
    for name, symbol in COMMODITIES.items():
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
                f"   ⚠️ "
                f"{name}: {error}"
            )
    if not results:
        raise RuntimeError(
            "Nessuna materia prima "
            "è stata analizzata."
        )
    print_report(results)
if __name__ == "__main__":
    main()