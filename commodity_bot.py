import os
import math
import requests
from datetime import datetime, timezone
from statistics import mean

# ============================================================
# BOT MATERIE PRIME
# Analisi: trend + momentum + volatilità + volume + notizie
# ============================================================

API_KEY = os.getenv("TWELVE_DATA_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "TWELVE_DATA_API_KEY non configurata nei GitHub Secrets."
    )

BASE_URL = "https://api.twelvedata.com"

# Materie prime da confrontare.
# I simboli vengono verificati tramite Twelve Data.
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

# Parole positive/negative per una prima classificazione delle notizie.
# NON è intelligenza artificiale: è un filtro iniziale.
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


# ------------------------------------------------------------
# FUNZIONI API
# ------------------------------------------------------------

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
        raise RuntimeError(data.get("message", "Errore Twelve Data"))

    return data


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
        raise RuntimeError(f"Nessun dato ricevuto per {symbol}")

    # Twelve Data normalmente restituisce i dati dal più recente
    # al più vecchio. Li invertiamo per lavorare cronologicamente.
    values = list(reversed(values))

    cleaned = []

    for row in values:
        try:
            cleaned.append({
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row.get("volume") or 0)
            })
        except (KeyError, TypeError, ValueError):
            continue

    if len(cleaned) < 30:
        raise RuntimeError(
            f"Dati insufficienti per {symbol}: {len(cleaned)} candele"
        )

    return cleaned


def get_news(query):
    """
    Usa Google News RSS senza bisogno di una seconda API key.
    Se il feed non è disponibile, il bot continua comunque
    con l'analisi tecnica.
    """

    try:
        import xml.etree.ElementTree as ET

        url = "https://news.google.com/rss/search"

        response = requests.get(
            url,
            params={
                "q": f"{query} commodity",
                "hl": "en-US",
                "gl": "US",
                "ceid": "US:en"
            },
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        response.raise_for_status()

        root = ET.fromstring(response.text)

        headlines = []

        for item in root.findall(".//item")[:10]:
            title = item.findtext("title")

            if title:
                headlines.append(title)

        return headlines

    except Exception:
        return []


# ------------------------------------------------------------
# INDICATORI
# ------------------------------------------------------------

def sma(values, period):
    if len(values) < period:
        return None

    return mean(values[-period:])


def calculate_returns(closes, period):
    if len(closes) <= period:
        return 0

    old = closes[-period - 1]
    new = closes[-1]

    if old == 0:
        return 0

    return (new / old - 1) * 100


def volatility(closes, period=20):
    if len(closes) < period + 1:
        return 0

    returns = []

    for i in range(len(closes) - period, len(closes)):
        previous = closes[i - 1]

        if previous != 0:
            returns.append((closes[i] / previous - 1) * 100)

    if not returns:
        return 0

    avg = mean(returns)

    variance = mean(
        [(x - avg) ** 2 for x in returns]
    )

    return math.sqrt(variance)


def analyze_news(headlines):
    if not headlines:
        return 0, 0, []

    positive = 0
    negative = 0
    relevant = []

    for headline in headlines:
        text = headline.lower()

        pos_hits = sum(
            1 for word in POSITIVE_WORDS
            if word in text
        )

        neg_hits = sum(
            1 for word in NEGATIVE_WORDS
            if word in text
        )

        if pos_hits > neg_hits:
            positive += 1
            relevant.append(("POSITIVA", headline))

        elif neg_hits > pos_hits:
            negative += 1
            relevant.append(("NEGATIVA", headline))

    total = positive + negative

    if total == 0:
        score = 0
    else:
        score = ((positive - negative) / total) * 100

    return score, total, relevant


# ------------------------------------------------------------
# ANALISI COMPLETA
# ------------------------------------------------------------

def analyze_commodity(name, symbol):

    prices = get_prices(symbol)

    closes = [x["close"] for x in prices]
    volumes = [x["volume"] for x in prices]

    current = closes[-1]

    sma20 = sma(closes, 20)
    sma50 = sma(closes, 50)

    momentum_6h = calculate_returns(closes, 6)
    momentum_24h = calculate_returns(closes, 24)

    vol = volatility(closes, 20)

    # ----------------------------
    # TREND
    # ----------------------------

    trend_score = 0

    if sma20 and current > sma20:
        trend_score += 25

    if sma50 and current > sma50:
        trend_score += 25

    if sma20 and sma50 and sma20 > sma50:
        trend_score += 20

    # ----------------------------
    # MOMENTUM
    # ----------------------------

    momentum_score = 0

    if momentum_6h > 0:
        momentum_score += 15

    if momentum_24h > 0:
        momentum_score += 15

    if momentum_6h < 0:
        momentum_score -= 15

    if momentum_24h < 0:
        momentum_score -= 15

    # Normalizzazione
    momentum_score = max(-30, min(30, momentum_score))

    # ----------------------------
    # VOLUME
    # ----------------------------

    volume_score = 0

    recent_volume = volumes[-5:]

    if any(v > 0 for v in recent_volume):
        avg_volume = mean(
            [v for v in volumes[-20:] if v > 0]
        ) if any(v > 0 for v in volumes[-20:]) else 0

        if avg_volume > 0 and mean(recent_volume) > avg_volume * 1.2:
            volume_score = 10

        elif avg_volume > 0 and mean(recent_volume) < avg_volume * 0.8:
            volume_score = -5

    # ----------------------------
    # NOTIZIE
    # ----------------------------

    news_score, news_count, relevant_news = analyze_news(
        get_news(name)
    )

    # Le notizie hanno peso massimo di 20 punti.
    news_points = max(-20, min(20, news_score * 0.20))

    # ----------------------------
    # PUNTEGGIO FINALE
    # ----------------------------

    raw_score = (
        trend_score
        + momentum_score
        + volume_score
        + news_points
    )

    # Convertiamo in 0-100.
    final_score = 50 + raw_score

    final_score = max(
        0,
        min(100, final_score)
    )

    # ----------------------------
    # SEGNALE
    # ----------------------------

    if final_score >= 70:
        signal = "🟢 LONG"

    elif final_score <= 30:
        signal = "🔴 SHORT"

    else:
        signal = "🟡 ASPETTARE"

    return {
        "name": name,
        "symbol": symbol,
        "price": current,
        "score": final_score,
        "signal": signal,
        "trend": trend_score,
        "momentum": momentum_score,
        "volume": volume_score,
        "news": news_points,
        "momentum_6h": momentum_6h,
        "momentum_24h": momentum_24h,
        "volatility": vol,
        "news_count": news_count,
        "news": relevant_news
    }


# ------------------------------------------------------------
# REPORT
# ------------------------------------------------------------

def print_report(results):

    print()
    print("=" * 65)
    print("          🏆 COMMODITY TRADING BOT")
    print("=" * 65)

    now = datetime.now(
        timezone.utc
    ).strftime("%Y-%m-%d %H:%M UTC")

    print(f"🕒 Aggiornamento: {now}")
    print()

    results.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    print("CLASSIFICA")
    print("-" * 65)

    for i, result in enumerate(results, 1):

        print(
            f"{i}. {result['name']:<18} "
            f"{result['score']:>5.1f}/100 "
            f"{result['signal']}"
        )

    print()
    print("=" * 65)

    best = results[0]

    print("🥇 MIGLIOR SETUP")
    print("-" * 65)

    print(f"Materia prima : {best['name']}")
    print(f"Prezzo        : {best['price']:.4f}")
    print(f"Segnale       : {best['signal']}")
    print(f"Forza         : {best['score']:.1f}/100")

    print()
    print("📊 COMPONENTI")
    print(f"Trend         : {best['trend']:+.1f}")
    print(f"Momentum      : {best['momentum']:+.1f}")
    print(f"Volume        : {best['volume']:+.1f}")
    print(f"Notizie       : {best['news']:+.1f}")

    print()
    print("📈 MOMENTUM")
    print(f"6 ore         : {best['momentum_6h']:+.2f}%")
    print(f"24 ore        : {best['momentum_24h']:+.2f}%")

    print()
    print("📰 NOTIZIE")

    if best["news"]:
        for sentiment, headline in best["news"][:5]:
            print(f"- {sentiment}: {headline}")
    else:
        print("- Nessuna notizia classificabile trovata.")

    print()
    print("=" * 65)

    if best["score"] >= 70:
        print(
            "🎯 CONCLUSIONE: il setup migliore è "
            "rialzista, ma il segnale non costituisce "
            "una garanzia di profitto."
        )

    elif best["score"] <= 30:
        print(
            "🎯 CONCLUSIONE: il setup migliore è "
            "ribassista, ma il segnale non costituisce "
            "una garanzia di profitto."
        )

    else:
        print(
            "🎯 CONCLUSIONE: nessun setup abbastanza forte. "
            "Meglio ASPETTARE."
        )

    print("=" * 65)


# ------------------------------------------------------------
# AVVIO
# ------------------------------------------------------------

def main():

    results = []

    for name, symbol in COMMODITIES.items():

        print(f"Analizzo {name} ({symbol})...")

        try:
            result = analyze_commodity(
                name,
                symbol
            )

            results.append(result)

        except Exception as e:
            print(
                f"⚠️ {name}: dati non disponibili "
                f"({e})"
            )

    if not results:
        raise RuntimeError(
            "Nessuna materia prima analizzata."
        )

    print_report(results)


if __name__ == "__main__":
    main()