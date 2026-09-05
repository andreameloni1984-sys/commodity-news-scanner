import os
import math
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# ============================================================
# CONFIGURAZIONE
# ============================================================

API_KEY = os.getenv("TWELVE_DATA_API_KEY")

if not API_KEY:
    raise RuntimeError("TWELVE_DATA_API_KEY non configurata nei GitHub Secrets.")


BASE_URL = "https://api.twelvedata.com"

# Materie prime principali.
# Se una commodity non è disponibile sul tuo piano/account,
# il bot la salta automaticamente.
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
# FUNZIONI API
# ============================================================

def api_get(endpoint, params):
    params["apikey"] = API_KEY

    response = requests.get(
        BASE_URL + endpoint,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    if data.get("status") == "error":
        raise RuntimeError(data.get("message", "Errore Twelve Data"))

    return data


def get_time_series(symbol, interval="1day", outputsize=None,
                    start_date=None, end_date=None):

    params = {
        "symbol": symbol,
        "interval": interval
    }

    if outputsize is not None:
        params["outputsize"] = outputsize

    if start_date:
        params["start_date"] = start_date

    if end_date:
        params["end_date"] = end_date

    data = api_get("/time_series", params)

    values = data.get("values", [])

    if not values:
        raise RuntimeError(f"Nessun dato ricevuto per {symbol}")

    # Twelve Data restituisce normalmente i dati dal più recente
    # al più vecchio. Li riportiamo in ordine cronologico.
    values = list(reversed(values))

    candles = []

    for x in values:
        try:
            candles.append({
                "datetime": x.get("datetime"),
                "open": float(x["open"]),
                "high": float(x["high"]),
                "low": float(x["low"]),
                "close": float(x["close"]),
                "volume": float(x.get("volume", 0) or 0)
            })
        except (ValueError, TypeError, KeyError):
            continue

    if len(candles) < 30:
        raise RuntimeError(f"Dati insufficienti per {symbol}")

    return candles


# ============================================================
# INDICATORI
# ============================================================

def sma(values, period):
    if len(values) < period:
        return None

    return sum(values[-period:]) / period


def momentum(values, periods):
    if len(values) <= periods:
        return 0

    old = values[-periods - 1]

    if old == 0:
        return 0

    return ((values[-1] / old) - 1) * 100


def volatility(values, period=20):
    if len(values) < period + 1:
        return 0

    returns = []

    start = len(values) - period

    for i in range(start, len(values)):
        previous = values[i - 1]

        if previous != 0:
            returns.append((values[i] / previous) - 1)

    if len(returns) < 2:
        return 0

    mean = sum(returns) / len(returns)

    variance = sum(
        (x - mean) ** 2 for x in returns
    ) / (len(returns) - 1)

    return math.sqrt(variance) * 100


def atr(candles, period=14):
    if len(candles) < period + 1:
        return 0

    true_ranges = []

    for i in range(1, len(candles)):
        high = candles[i]["high"]
        low = candles[i]["low"]
        previous_close = candles[i - 1]["close"]

        tr = max(
            high - low,
            abs(high - previous_close),
            abs(low - previous_close)
        )

        true_ranges.append(tr)

    if len(true_ranges) < period:
        return 0

    return sum(true_ranges[-period:]) / period


def pressure(candles, period=20):
    """
    Misura dove il prezzo chiude rispetto al range della candela.

    +100 = forte pressione compratrice
    -100 = forte pressione venditrice
    """

    if len(candles) < period:
        return 0

    values = []

    for candle in candles[-period:]:
        high = candle["high"]
        low = candle["low"]
        close = candle["close"]

        if high == low:
            continue

        location = ((close - low) / (high - low)) * 2 - 1
        values.append(location)

    if not values:
        return 0

    return (sum(values) / len(values)) * 100


def volume_score(candles, period=20):
    volumes = [
        x["volume"]
        for x in candles[-period:]
        if x["volume"] > 0
    ]

    if len(volumes) < 5:
        return 0

    average = sum(volumes[:-1]) / max(1, len(volumes) - 1)
    current = volumes[-1]

    if average == 0:
        return 0

    ratio = current / average

    if ratio >= 1.5:
        return 15

    if ratio >= 1.2:
        return 8

    if ratio >= 0.9:
        return 3

    return -3


# ============================================================
# CICLO STORICO
# ============================================================

def normalize_pattern(values):
    """
    Trasforma una sequenza di prezzi in variazioni percentuali
    rispetto al primo valore.
    """

    if not values or values[0] == 0:
        return []

    first = values[0]

    return [
        (x / first) - 1
        for x in values
    ]


def pattern_distance(a, b):
    """
    Distanza tra due configurazioni.
    Più è bassa, più sono simili.
    """

    if len(a) != len(b) or not a:
        return float("inf")

    squared = [
        (x - y) ** 2
        for x, y in zip(a, b)
    ]

    return math.sqrt(sum(squared) / len(squared))


def historical_cycle_analysis(symbol, years=10, pattern_days=20):
    """
    Cerca negli ultimi ~10 anni configurazioni simili a quella attuale.

    Poi verifica cosa è successo dopo 1, 7 e 30 giorni.
    """

    end = datetime.utcnow().date()
    start = end - timedelta(days=years * 365 + pattern_days + 60)

    candles = get_time_series(
        symbol,
        interval="1day",
        start_date=start.isoformat(),
        end_date=end.isoformat()
    )

    closes = [x["close"] for x in candles]

    minimum_needed = pattern_days + 35

    if len(closes) < minimum_needed:
        return {
            "matches": 0,
            "prob_1d": None,
            "prob_7d": None,
            "prob_30d": None,
            "avg_1d": None,
            "avg_7d": None,
            "avg_30d": None,
            "bias": "NEUTRALE",
            "confidence": "BASSA"
        }

    current_pattern = normalize_pattern(
        closes[-pattern_days:]
    )

    candidates = []

    # Cerchiamo configurazioni passate.
    # Lasciamo almeno 35 giorni dopo ogni configurazione
    # per poter misurare il comportamento successivo.
    last_possible = len(closes) - 30

    for end_index in range(
        pattern_days,
        last_possible
    ):

        start_index = end_index - pattern_days

        historical_values = closes[
            start_index:end_index
        ]

        historical_pattern = normalize_pattern(
            historical_values
        )

        distance = pattern_distance(
            current_pattern,
            historical_pattern
        )

        candidates.append({
            "distance": distance,
            "index": end_index
        })

    if not candidates:
        return {
            "matches": 0,
            "prob_1d": None,
            "prob_7d": None,
            "prob_30d": None,
            "avg_1d": None,
            "avg_7d": None,
            "avg_30d": None,
            "bias": "NEUTRALE",
            "confidence": "BASSA"
        }

    # Prendiamo le configurazioni più simili.
    candidates.sort(key=lambda x: x["distance"])

    # Evitiamo di usare un numero eccessivo di casi.
    matches = candidates[:20]

    results_1d = []
    results_7d = []
    results_30d = []

    for match in matches:
        idx = match["index"]

        base = closes[idx - 1]

        if base == 0:
            continue

        if idx < len(closes):
            results_1d.append(
                ((closes[idx] / base) - 1) * 100
            )

        if idx + 7 < len(closes):
            results_7d.append(
                ((closes[idx + 7] / base) - 1) * 100
            )

        if idx + 30 < len(closes):
            results_30d.append(
                ((closes[idx + 30] / base) - 1) * 100
            )

    def probability_positive(values):
        if not values:
            return None

        return (
            sum(1 for x in values if x > 0)
            / len(values)
        ) * 100

    def average(values):
        if not values:
            return None

        return sum(values) / len(values)

    prob_1d = probability_positive(results_1d)
    prob_7d = probability_positive(results_7d)
    prob_30d = probability_positive(results_30d)

    avg_1d = average(results_1d)
    avg_7d = average(results_7d)
    avg_30d = average(results_30d)

    probabilities = [
        x for x in [
            prob_1d,
            prob_7d,
            prob_30d
        ]
        if x is not None
    ]

    if not probabilities:
        bias = "NEUTRALE"
    else:
        average_probability = sum(probabilities) / len(probabilities)

        if average_probability >= 60:
            bias = "RIALZISTA"
        elif average_probability <= 40:
            bias = "RIBASSISTA"
        else:
            bias = "NEUTRALE"

    if len(matches) >= 15:
        confidence = "ALTA"
    elif len(matches) >= 8:
        confidence = "MEDIA"
    else:
        confidence = "BASSA"

    return {
        "matches": len(matches),
        "prob_1d": prob_1d,
        "prob_7d": prob_7d,
        "prob_30d": prob_30d,
        "avg_1d": avg_1d,
        "avg_7d": avg_7d,
        "avg_30d": avg_30d,
        "bias": bias,
        "confidence": confidence
    }


# ============================================================
# NOTIZIE
# ============================================================

def get_news(symbol_name):
    """
    Usa Google News RSS come fonte di titoli.
    Il sentiment è basato su parole chiave.
    """

    query_map = {
        "Oro": "gold price gold market",
        "Argento": "silver price silver market",
        "Petrolio WTI": "WTI oil crude oil",
        "Petrolio Brent": "Brent oil crude oil",
        "Gas Naturale": "natural gas price",
        "Rame": "copper price copper market",
        "Grano": "wheat price wheat market",
        "Mais": "corn price corn market",
        "Caffè": "coffee price coffee market"
    }

    query = query_map.get(
        symbol_name,
        symbol_name
    )

    url = "https://news.google.com/rss/search"

    try:
        response = requests.get(
            url,
            params={
                "q": query,
                "hl": "en-US",
                "gl": "US",
                "ceid": "US:en"
            },
            timeout=20
        )

        response.raise_for_status()

        text = response.text

    except Exception:
        return {
            "score": 0,
            "headlines": []
        }

    import xml.etree.ElementTree as ET

    try:
        root = ET.fromstring(text)
    except Exception:
        return {
            "score": 0,
            "headlines": []
        }

    positive_words = [
        "surge",
        "rally",
        "rise",
        "rises",
        "higher",
        "bullish",
        "strong",
        "demand",
        "shortage",
        "supply cut",
        "support",
        "gain",
        "gains",
        "record"
    ]

    negative_words = [
        "fall",
        "falls",
        "drop",
        "drops",
        "lower",
        "bearish",
        "weak",
        "weakness",
        "oversupply",
        "surplus",
        "selloff",
        "decline",
        "declines",
        "loss"
    ]

    score = 0
    headlines = []

    for item in root.findall(".//item")[:10]:

        title_element = item.find("title")

        if title_element is None:
            continue

        title = title_element.text or ""
        lower = title.lower()

        positive = sum(
            1 for word in positive_words
            if word in lower
        )

        negative = sum(
            1 for word in negative_words
            if word in lower
        )

        news_score = positive - negative

        score += news_score

        if news_score > 0:
            label = "🟢"
        elif news_score < 0:
            label = "🔴"
        else:
            label = "🟡"

        headlines.append(
            f"{label} {title}"
        )

    score = max(-15, min(15, score))

    return {
        "score": score,
        "headlines": headlines[:5]
    }


# ============================================================
# ANALISI SINGOLA COMMODITY
# ============================================================

def analyze_commodity(name, symbol):

    # Dati recenti intraday
    candles = get_time_series(
        symbol,
        interval="1h",
        outputsize=100
    )

    closes = [x["close"] for x in candles]

    price = closes[-1]

    sma20 = sma(closes, 20)
    sma50 = sma(closes, 50)

    momentum_6h = momentum(closes, 6)
    momentum_24h = momentum(closes, 24)

    vol = volatility(closes, 20)
    atr_value = atr(candles, 14)

    pressure_value = pressure(candles, 20)

    vol_score = volume_score(candles, 20)

    # --------------------------------------------------------
    # TREND
    # --------------------------------------------------------

    trend_score = 0

    if sma20 and sma50:

        if price > sma20:
            trend_score += 15
        else:
            trend_score -= 15

        if sma20 > sma50:
            trend_score += 15
        else:
            trend_score -= 15

    # --------------------------------------------------------
    # MOMENTUM
    # --------------------------------------------------------

    momentum_score = 0

    if momentum_6h > 0:
        momentum_score += 10
    else:
        momentum_score -= 10

    if momentum_24h > 0:
        momentum_score += 10
    else:
        momentum_score -= 10

    # --------------------------------------------------------
    # PRESSIONE
    # --------------------------------------------------------

    pressure_score = pressure_value * 0.20

    # --------------------------------------------------------
    # NOTIZIE
    # --------------------------------------------------------

    news = get_news(name)

    news_score = news["score"]

    # --------------------------------------------------------
    # CICLO STORICO
    # --------------------------------------------------------

    try:
        history = historical_cycle_analysis(
            symbol,
            years=10,
            pattern_days=20
        )
    except Exception as e:
        print(
            f"⚠️ Storico non disponibile per {name}: {e}"
        )

        history = {
            "matches": 0,
            "prob_1d": None,
            "prob_7d": None,
            "prob_30d": None,
            "avg_1d": None,
            "avg_7d": None,
            "avg_30d": None,
            "bias": "NEUTRALE",
            "confidence": "BASSA"
        }

    history_score = 0

    if history["bias"] == "RIALZISTA":
        history_score = 12

    elif history["bias"] == "RIBASSISTA":
        history_score = -12

    # --------------------------------------------------------
    # PUNTEGGIO TOTALE
    # --------------------------------------------------------

    raw_score = (
        50
        + trend_score * 0.45
        + momentum_score * 0.50
        + pressure_score
        + vol_score * 0.30
        + news_score * 0.80
        + history_score * 0.50
    )

    score = max(0, min(100, raw_score))

    # --------------------------------------------------------
    # DIREZIONE
    # --------------------------------------------------------

    if score >= 65:
        direction = "🟢 LONG"

    elif score <= 35:
        direction = "🔴 SHORT"

    else:
        direction = "🟡 ASPETTARE"

    # --------------------------------------------------------
    # CONTROLLO CONFLITTI
    # --------------------------------------------------------

    bullish_components = 0
    bearish_components = 0

    if trend_score > 0:
        bullish_components += 1
    elif trend_score < 0:
        bearish_components += 1

    if momentum_score > 0:
        bullish_components += 1
    elif momentum_score < 0:
        bearish_components += 1

    if pressure_value > 10:
        bullish_components += 1
    elif pressure_value < -10:
        bearish_components += 1

    if news_score > 2:
        bullish_components += 1
    elif news_score < -2:
        bearish_components += 1

    if history["bias"] == "RIALZISTA":
        bullish_components += 1
    elif history["bias"] == "RIBASSISTA":
        bearish_components += 1

    conflict = (
        bullish_components >= 2
        and bearish_components >= 2
    )

    if conflict:
        direction = "🟡 ASPETTARE"

    # --------------------------------------------------------
    # FORZA
    # --------------------------------------------------------

    if score >= 80 or score <= 20:
        strength = "🔥 MOLTO FORTE"

    elif score >= 70 or score <= 30:
        strength = "💪 FORTE"

    elif score >= 60 or score <= 40:
        strength = "⚠️ MODERATA"

    else:
        strength = "🟡 DEBOLE"

    # --------------------------------------------------------
    # FILTRO VOLATILITÀ
    # --------------------------------------------------------

    abnormal_volatility = vol > 3.5

    if abnormal_volatility:
        direction = "🟡 ASPETTARE"

    # --------------------------------------------------------
    # LIVELLI
    # --------------------------------------------------------

    entry = price

    if atr_value <= 0:
        sl = None
        tp1 = None
        tp2 = None
    else:

        if direction == "🟢 LONG":

            sl = entry - (1.5 * atr_value)

            risk = entry - sl

            tp1 = entry + (1.5 * risk)

            tp2 = entry + (2.5 * risk)

        elif direction == "🔴 SHORT":

            sl = entry + (1.5 * atr_value)

            risk = sl - entry

            tp1 = entry - (1.5 * risk)

            tp2 = entry - (2.5 * risk)

        else:

            sl = None
            tp1 = None
            tp2 = None

    # --------------------------------------------------------
    # RAGIONI
    # --------------------------------------------------------

    reasons = []

    if trend_score > 0:
        reasons.append("trend rialzista")

    elif trend_score < 0:
        reasons.append("trend ribassista")

    if momentum_score > 0:
        reasons.append("momentum positivo")

    elif momentum_score < 0:
        reasons.append("momentum negativo")

    if pressure_value > 15:
        reasons.append("pressione compratrice")

    elif pressure_value < -15:
        reasons.append("pressione venditrice")

    if news_score > 3:
        reasons.append("notizie favorevoli")

    elif news_score < -3:
        reasons.append("notizie sfavorevoli")

    if history["bias"] == "RIALZISTA":
        reasons.append("storico favorevole al rialzo")

    elif history["bias"] == "RIBASSISTA":
        reasons.append("storico favorevole al ribasso")

    if abnormal_volatility:
        reasons.append("volatilità anomala")

    if conflict:
        reasons.append("indicatori in conflitto")

    return {
        "name": name,
        "symbol": symbol,
        "price": price,
        "score": score,
        "direction": direction,
        "strength": strength,
        "trend_score": trend_score,
        "momentum_score": momentum_score,
        "pressure": pressure_value,
        "volume_score": vol_score,
        "news_score": news_score,
        "momentum_6h": momentum_6h,
        "momentum_24h": momentum_24h,
        "volatility": vol,
        "atr": atr_value,
        "entry": entry,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "history": history,
        "reasons": reasons,
        "news_headlines": news["headlines"],
        "conflict": conflict,
        "abnormal_volatility": abnormal_volatility
    }


# ============================================================
# FORMATO PREZZI
# ============================================================

def fmt(value):

    if value is None:
        return "-"

    if abs(value) >= 100:
        return f"{value:.2f}"

    if abs(value) >= 10:
        return f"{value:.3f}"

    return f"{value:.4f}"


def fmt_percent(value):

    if value is None:
        return "-"

    return f"{value:+.2f}%"


# ============================================================
# REPORT
# ============================================================

def print_report(results):

    print("\n")
    print("=" * 70)
    print("🥇 COMMODITY TRADING BOT v3")
    print("=" * 70)

    now = datetime.now(
        ZoneInfo("Europe/Rome")
    )

    print(
        f"🕒 Ora analisi: "
        f"{now.strftime('%d/%m/%Y %H:%M')} "
        f"Europe/Rome"
    )

    print(
        "🔄 Storico utilizzato: circa 10 anni"
    )

    print("=" * 70)

    results = sorted(
        results,
        key=lambda x: x["score"],
        reverse=True
    )

    print("\n🏆 CLASSIFICA\n")

    for i, r in enumerate(results, 1):

        print(
            f"{i}. {r['name']:<18} "
            f"{r['direction']:<15} "
            f"{r['score']:.0f}/100 "
            f"{r['strength']}"
        )

    print("\n" + "=" * 70)

    # --------------------------------------------------------
    # MIGLIORE OPPORTUNITÀ
    # --------------------------------------------------------

    tradable = [
        r for r in results
        if r["direction"] in [
            "🟢 LONG",
            "🔴 SHORT"
        ]
        and not r["conflict"]
        and not r["abnormal_volatility"]
    ]

    if not tradable:

        print("🛑 NESSUN TRADE")
        print()
        print(
            "Nessuna materia prima presenta "
            "un setup sufficientemente affidabile."
        )

        print("=" * 70)

        return

    best = tradable[0]

    print(
        f"\n🎯 MIGLIORE OPPORTUNITÀ: "
        f"{best['name']}"
    )

    print(
        f"📌 SEGNALE: {best['direction']}"
    )

    print(
        f"💪 FORZA: {best['strength']}"
    )

    print(
        f"📊 PUNTEGGIO: "
        f"{best['score']:.0f}/100"
    )

    print(
        f"💰 PREZZO: "
        f"{fmt(best['price'])}"
    )

    print("\n--- ANALISI ---")

    print(
        f"📈 Trend: "
        f"{best['trend_score']:+.1f}"
    )

    print(
        f"🚀 Momentum 6h: "
        f"{fmt_percent(best['momentum_6h'])}"
    )

    print(
        f"🚀 Momentum 24h: "
        f"{fmt_percent(best['momentum_24h'])}"
    )

    print(
        f"💰 Pressione acquisti/vendite: "
        f"{best['pressure']:+.1f}"
    )

    print(
        f"📰 News score: "
        f"{best['news_score']:+.1f}"
    )

    print(
        f"📊 Volatilità: "
        f"{best['volatility']:.2f}%"
    )

    print(
        f"📐 ATR: "
        f"{fmt(best['atr'])}"
    )

    # --------------------------------------------------------
    # STORICO
    # --------------------------------------------------------

    history = best["history"]

    print("\n--- 🔄 CICLO STORICO ---")

    print(
        f"📚 Configurazioni simili: "
        f"{history['matches']}"
    )

    print(
        f"📅 Probabilità positiva 1 giorno: "
        f"{'-' if history['prob_1d'] is None else f'{history['prob_1d']:.0f}%'}"
    )

    print(
        f"📅 Probabilità positiva 7 giorni: "
        f"{'-' if history['prob_7d'] is None else f'{history['prob_7d']:.0f}%'}"
    )

    print(
        f"📅 Probabilità positiva 30 giorni: "
        f"{'-' if history['prob_30d'] is None else f'{history['prob_30d']:.0f}%'}"
    )

    print(
        f"📈 Media 1 giorno: "
        f"{fmt_percent(history['avg_1d'])}"
    )

    print(
        f"📈 Media 7 giorni: "
        f"{fmt_percent(history['avg_7d'])}"
    )

    print(
        f"📈 Media 30 giorni: "
        f"{fmt_percent(history['avg_30d'])}"
    )

    print(
        f"🔄 Bias storico: "
        f"{history['bias']}"
    )

    print(
        f"🎯 Affidabilità storico: "
        f"{history['confidence']}"
    )

    # --------------------------------------------------------
    # LIVELLI
    # --------------------------------------------------------

    print("\n--- 🎯 LIVELLI ---")

    if best["entry"] is not None:

        print(
            f"ENTRY: {fmt(best['entry'])}"
        )

        print(
            f"STOP LOSS: {fmt(best['sl'])}"
        )

        print(
            f"TAKE PROFIT 1: {fmt(best['tp1'])}"
        )

        print(
            f"TAKE PROFIT 2: {fmt(best['tp2'])}"
        )

    # --------------------------------------------------------
    # PERCHÉ
    # --------------------------------------------------------

    print("\n--- 🧠 PERCHÉ QUESTA COMMODITY ---")

    if best["reasons"]:

        for reason in best["reasons"]:
            print(f"• {reason}")

    else:
        print("• Nessun fattore dominante.")

    # --------------------------------------------------------
    # NOTIZIE
    # --------------------------------------------------------

    print("\n--- 📰 NOTIZIE ---")

    for headline in best["news_headlines"]:
        print(headline)

    # --------------------------------------------------------
    # AVVERTIMENTO
    # --------------------------------------------------------

    print("\n" + "=" * 70)

    print(
        "⚠️ NOTA: il ciclo storico misura configurazioni "
        "passate simili. Non garantisce il futuro."
    )

    print(
        "⚠️ ENTRY, SL e TP sono calcoli automatici "
        "basati principalmente sull'ATR."
    )

    print("=" * 70)


# ============================================================
# PROGRAMMA PRINCIPALE
# ============================================================

def main():

    print("\n")
    print("🚀 Avvio Commodity Trading Bot v3...")
    print(
        "🔎 Analisi tecnica + news + pressione + "
        "storico/cicli"
    )

    results = []

    for name, symbol in COMMODITIES.items():

        print(
            f"\n🔍 Analizzo {name} ({symbol})..."
        )

        try:

            result = analyze_commodity(
                name,
                symbol
            )

            results.append(result)

            print(
                f"✅ {name}: "
                f"{result['score']:.0f}/100 "
                f"{result['direction']}"
            )

        except Exception as e:

            print(
                f"⚠️ {name} saltata: {e}"
            )

    if not results:

        raise RuntimeError(
            "Nessuna commodity è stata analizzata."
        )

    print_report(results)


if __name__ == "__main__":
    main()