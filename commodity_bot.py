import os
import json
import math
from datetime import datetime, timezone

import requests


# ============================================================
# COMMODITY TRADING BOT v5.0
# QUANT MODEL + MULTI-TIMEFRAME + NEWS + USD + SEASONALITY
# + RANKING + POSITION MANAGEMENT
#
# Analitico/simulato: NON esegue ordini reali.
# ============================================================

API_KEY = os.getenv("TWELVE_DATA_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "8002086130")

if not API_KEY:
    raise RuntimeError(
        "TWELVE_DATA_API_KEY non configurata nei GitHub Secrets."
    )

BASE_URL = "https://api.twelvedata.com/time_series"
NEWS_URL = "https://newsapi.org/v2/everything"

POSITION_FILE = "position.json"

HISTORY_SIZE = 4000
HORIZON = 5

STOP_ATR = 1.5
TP1_ATR = 1.5
TP2_ATR = 2.5

LONG_THRESHOLD = 0.62
SHORT_THRESHOLD = 0.38

MIN_QUALITY = 45
MIN_CONFIDENCE = 58
MIN_SCORE = 65
MIN_RANK_MARGIN = 5

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
    "ret_1",
    "ret_5",
    "ret_20",
    "ret_60",
    "trend",
    "rsi",
    "macd",
    "atr_pct",
    "volatility",
    "pressure",
    "breakout",
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
    values = [
        x for x in values
        if x is not None and math.isfinite(x)
    ]

    return sum(values) / len(values) if values else 0.0


def std(values):
    values = [
        x for x in values
        if x is not None and math.isfinite(x)
    ]

    if len(values) < 2:
        return 1.0

    m = mean(values)

    variance = sum(
        (x - m) ** 2
        for x in values
    ) / (len(values) - 1)

    return max(
        math.sqrt(variance),
        1e-8
    )


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

        with open(
            POSITION_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        return data or None

    except Exception as error:

        print(
            f"⚠️ Impossibile leggere "
            f"{POSITION_FILE}: {error}"
        )

        return None


def save_position(position):

    with open(
        POSITION_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            position,
            file,
            indent=2,
            ensure_ascii=False
        )


def clear_position():

    if os.path.exists(POSITION_FILE):
        os.remove(POSITION_FILE)


# ============================================================
# TWELVE DATA
# ============================================================

def get_data(
    symbol,
    interval="1day",
    outputsize=4000
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
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    if data.get("status") == "error":

        raise RuntimeError(
            data.get(
                "message",
                "Errore Twelve Data"
            )
        )

    candles = []

    for item in data.get(
        "values",
        []
    ):

        close = safe_float(
            item.get("close")
        )

        if close is None:
            continue

        candles.append({

            "datetime":
                item.get("datetime"),

            "open":
                safe_float(
                    item.get("open")
                ),

            "high":
                safe_float(
                    item.get("high")
                ),

            "low":
                safe_float(
                    item.get("low")
                ),

            "close":
                close,

            "volume":
                safe_float(
                    item.get("volume")
                ),
        })

    candles.sort(
        key=lambda x:
        x["datetime"] or ""
    )

    return candles


def get_daily_data(symbol):

    return get_data(
        symbol,
        "1day",
        HISTORY_SIZE
    )


# ============================================================
# INDICATORS
# ============================================================

def sma(
    values,
    period
):

    if len(values) < period:
        return None

    return mean(
        values[-period:]
    )


def ema(
    values,
    period
):

    if len(values) < period:
        return None

    multiplier = 2 / (
        period + 1
    )

    result = mean(
        values[:period]
    )

    for value in values[period:]:

        result = (
            (value - result)
            * multiplier
            + result
        )

    return result


def rsi(
    values,
    period=14
):

    if len(values) < period + 1:
        return 50.0

    gains = []
    losses = []

    for i in range(
        1,
        len(values)
    ):

        change = (
            values[i]
            - values[i - 1]
        )

        gains.append(
            max(change, 0)
        )

        losses.append(
            max(-change, 0)
        )

    avg_gain = mean(
        gains[-period:]
    )

    avg_loss = mean(
        losses[-period:]
    )

    if avg_loss == 0:
        return 100.0

    rs = (
        avg_gain
        / avg_loss
    )

    return 100 - (
        100
        / (1 + rs)
    )


def atr(
    candles,
    period=14
):

    if len(candles) < period + 1:
        return None

    ranges = []

    for i in range(
        1,
        len(candles)
    ):

        high = candles[i]["high"]
        low = candles[i]["low"]
        previous = candles[i - 1]["close"]

        if high is None or low is None:
            continue

        ranges.append(
            max(
                high - low,
                abs(high - previous),
                abs(low - previous)
            )
        )

    if len(ranges) < period:
        return None

    return mean(
        ranges[-period:]
    )


def macd(values):

    if len(values) < 35:
        return 0.0

    fast = ema(
        values,
        12
    )

    slow = ema(
        values,
        26
    )

    if fast is None or slow is None:
        return 0.0

    return fast - slow


def return_pct(
    values,
    period
):

    if len(values) <= period:
        return 0.0

    old = values[
        -period - 1
    ]

    current = values[-1]

    if old == 0:
        return 0.0

    return (
        current / old
    ) - 1


def volatility(
    values,
    period=20
):

    if len(values) < period + 1:
        return 0.0

    returns = []

    start = (
        len(values)
        - period
    )

    for i in range(
        start,
        len(values)
    ):

        previous = values[
            i - 1
        ]

        if previous:
            returns.append(
                (
                    values[i]
                    / previous
                ) - 1
            )

    return std(returns)


def pressure(
    candles,
    period=10
):

    scores = []

    for candle in candles[-period:]:

        high = candle["high"]
        low = candle["low"]
        close = candle["close"]
        open_price = candle["open"]

        if (
            high is None
            or low is None
            or close is None
            or open_price is None
            or high == low
        ):
            continue

        scores.append(
            (
                close
                - open_price
            )
            / (
                high - low
            )
        )

    return mean(scores)


def breakout(
    values,
    period=20
):

    if len(values) < period + 1:
        return 0.0

    current = values[-1]

    previous = values[
        -period - 1:-1
    ]

    highest = max(previous)
    lowest = min(previous)

    distance = (
        highest
        - lowest
    )

    if distance == 0:
        return 0.0

    return (
        (
            current
            - lowest
        )
        / distance
    ) * 2 - 1
    # ============================================================
# MODEL QUALITY
# ============================================================

def quality_score(metrics):
    accuracy = metrics.get("accuracy", 0)
    win_rate = metrics.get("win_rate", 0)
    profit_factor = metrics.get("profit_factor", 0)
    drawdown = abs(metrics.get("drawdown", 0))

    pf_score = clamp(profit_factor / 2.0, 0, 1)

    drawdown_score = 1 - clamp(
        drawdown / 0.30,
        0,
        1
    )

    score = (
        accuracy * 0.30 +
        win_rate * 0.25 +
        pf_score * 0.30 +
        drawdown_score * 0.15
    )

    return score * 100


# ============================================================
# MULTI-TIMEFRAME
# ============================================================

def timeframe_direction(candles):
    if not candles or len(candles) < 60:
        return "NONE"

    closes = [c["close"] for c in candles]

    ema20 = ema(closes, 20)
    ema50 = ema(closes, 50)
    current = closes[-1]
    current_rsi = rsi(closes, 14)

    if ema20 is None or ema50 is None:
        return "NONE"

    bullish = (
        current > ema20 and
        ema20 > ema50 and
        current_rsi >= 52
    )

    bearish = (
        current < ema20 and
        ema20 < ema50 and
        current_rsi <= 48
    )

    if bullish:
        return "LONG"

    if bearish:
        return "SHORT"

    return "NONE"


def get_multitimeframe(symbol):
    timeframes = [
        ("4h", "4h"),
        ("1h", "1h"),
        ("15m", "15min"),
        ("5m", "5min"),
        ("1m", "1min"),
    ]

    result = {}

    for label, interval in timeframes:
        try:
            candles = get_data(
                symbol,
                interval,
                250
            )

            result[label] = timeframe_direction(
                candles
            )

        except Exception:
            result[label] = "NONE"

    return result


# ============================================================
# USD / DOLLAR
# ============================================================

def analyze_usd():
    try:
        candles = get_data(
            "UUP:NYSE",
            "1h",
            200
        )

        direction = timeframe_direction(
            candles
        )

        if direction == "LONG":
            return {
                "direction": "LONG",
                "impact": -1,
                "label": "SFAVOREVOLE",
            }

        if direction == "SHORT":
            return {
                "direction": "SHORT",
                "impact": 1,
                "label": "FAVOREVOLE",
            }

        return {
            "direction": "NONE",
            "impact": 0,
            "label": "NEUTRALE",
        }

    except Exception:
        return {
            "direction": "NONE",
            "impact": 0,
            "label": "N/D",
        }


# ============================================================
# NEWS
# ============================================================

def analyze_news(keyword):
    if not NEWS_API_KEY:
        return {
            "score": 0,
            "label": "N/D",
        }

    try:
        params = {
            "q": keyword,
            "apiKey": NEWS_API_KEY,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 20,
        }

        response = requests.get(
            NEWS_URL,
            params=params,
            timeout=15
        )

        response.raise_for_status()

        articles = response.json().get(
            "articles",
            []
        )

        if not articles:
            return {
                "score": 0,
                "label": "NEUTRALE",
            }

        positive_words = [
            "rise",
            "rises",
            "rising",
            "gain",
            "gains",
            "higher",
            "bullish",
            "surge",
            "surges",
            "strong",
            "increase",
            "increases",
            "demand",
            "shortage",
        ]

        negative_words = [
            "fall",
            "falls",
            "falling",
            "drop",
            "drops",
            "lower",
            "bearish",
            "decline",
            "declines",
            "weak",
            "decrease",
            "decreases",
            "oversupply",
            "selling",
        ]

        score = 0

        for article in articles:
            text = " ".join([
                str(article.get("title", "")),
                str(article.get("description", "")),
            ]).lower()

            positive = sum(
                text.count(word)
                for word in positive_words
            )

            negative = sum(
                text.count(word)
                for word in negative_words
            )

            score += positive - negative

        score = clamp(
            score / max(len(articles), 1),
            -3,
            3
        )

        if score > 0.5:
            label = "POSITIVE"

        elif score < -0.5:
            label = "NEGATIVE"

        else:
            label = "NEUTRALE"

        return {
            "score": score,
            "label": label,
        }

    except Exception:
        return {
            "score": 0,
            "label": "N/D",
        }


# ============================================================
# SIGNAL ANALYSIS
# ============================================================

def analyze(name, symbol):
    daily = get_daily_data(symbol)

    if len(daily) < 500:
        return {
            "name": name,
            "symbol": symbol,
            "signal": "WAIT",
            "direction": "NONE",
            "score": 0,
            "confidence": 0,
            "quality": 0,
            "price": daily[-1]["close"]
            if daily else 0,
            "reason": "Dati insufficienti",
        }

    features = build_features(daily)

    if features is None:
        raise RuntimeError(
            f"Features insufficienti per {name}"
        )

    dataset = build_dataset(daily)

    if len(dataset) < 300:
        return {
            "name": name,
            "symbol": symbol,
            "signal": "WAIT",
            "direction": "NONE",
            "score": 0,
            "confidence": 0,
            "quality": 0,
            "price": daily[-1]["close"],
            "reason": "Dataset insufficiente",
        }

    metrics = backtest(dataset)
    quality = quality_score(metrics)

    model = train_final(dataset)

    if model is None:
        raise RuntimeError(
            f"Modello non disponibile per {name}"
        )

    scaled = scale_current(
        features,
        model
    )

    probability = predict(
        scaled,
        model["weights"],
        model["bias"]
    )

    if probability >= LONG_THRESHOLD:
        direction = "LONG"
        model_strength = (
            probability - 0.5
        ) * 2

    elif probability <= SHORT_THRESHOLD:
        direction = "SHORT"
        model_strength = (
            0.5 - probability
        ) * 2

    else:
        direction = "NONE"
        model_strength = 0

    mtf = get_multitimeframe(symbol)

    repetition = historical_repetition(
        daily
    )

    usd = analyze_usd()

    news = analyze_news(
        NEWS_TERMS.get(
            name,
            name
        )
    )

    score = 0.0

    if direction == "LONG":
        score += model_strength * 40

    elif direction == "SHORT":
        score -= model_strength * 40

    score += (
        quality - 50
    ) * 0.35

    if repetition["direction"] == direction:
        score += (
            repetition["frequency"] * 20
        )

    elif (
        repetition["direction"] != "NEUTRALE"
        and repetition["direction"] != direction
    ):
        score -= (
            repetition["frequency"] * 15
        )

    score += (
        usd["impact"] * 5
    )

    score += (
        news["score"] * 3
    )

    main_tf = [
        mtf.get("4h"),
        mtf.get("1h"),
        mtf.get("15m"),
    ]

    fast_tf = [
        mtf.get("5m"),
        mtf.get("1m"),
    ]

    main_long = main_tf.count("LONG")
    main_short = main_tf.count("SHORT")

    fast_long = fast_tf.count("LONG")
    fast_short = fast_tf.count("SHORT")

    # Conferma principale
    if direction == "LONG":
        score += main_long * 5
        score -= main_short * 5

    elif direction == "SHORT":
        score += main_short * 5
        score -= main_long * 5

    # Conferma veloce
    if direction == "LONG":
        if fast_long == 2:
            score += 10

        elif fast_short == 2:
            score -= 12

    elif direction == "SHORT":
        if fast_short == 2:
            score -= 10

        elif fast_long == 2:
            score += 12

    score = clamp(
        score,
        -100,
        100
    )

    confidence = abs(score)

    fast_conflict = (
        direction == "LONG"
        and fast_short == 2
    ) or (
        direction == "SHORT"
        and fast_long == 2
    )

    main_conflict = (
        direction == "LONG"
        and main_short >= 2
    ) or (
        direction == "SHORT"
        and main_long >= 2
    )

    if direction == "NONE":
        signal = "WAIT"

    elif fast_conflict:
        signal = "WAIT"

    elif main_conflict:
        signal = "WAIT"

    elif direction == "LONG" and score >= 20:
        signal = "LONG"

    elif direction == "SHORT" and score <= -20:
        signal = "SHORT"

    else:
        signal = "WAIT"

    if signal == "LONG":
        grade = (
            "FORTE"
            if confidence >= 70
            else "MEDIA"
        )

    elif signal == "SHORT":
        grade = (
            "FORTE"
            if confidence >= 70
            else "MEDIA"
        )

    else:
        grade = "ATTENDERE"

    price = daily[-1]["close"]

    current_atr = atr(
        daily,
        14
    )

    if current_atr is None:
        current_atr = price * 0.01

    if signal == "LONG":
        stop = price - (
            current_atr * STOP_ATR
        )

        tp1 = price + (
            current_atr * TP1_ATR
        )

        tp2 = price + (
            current_atr * TP2_ATR
        )

    elif signal == "SHORT":
        stop = price + (
            current_atr * STOP_ATR
        )

        tp1 = price - (
            current_atr * TP1_ATR
        )

        tp2 = price - (
            current_atr * TP2_ATR
        )

    else:
        stop = None
        tp1 = None
        tp2 = None

    return {
        "name": name,
        "symbol": symbol,
        "price": price,
        "signal": signal,
        "direction": direction,
        "grade": grade,
        "score": score,
        "confidence": confidence,
        "probability": probability,
        "quality": quality,
        "metrics": metrics,
        "mtf": mtf,
        "repetition": repetition,
        "usd": usd,
        "news": news,
        "atr": current_atr,
        "stop": stop,
        "tp1": tp1,
        "tp2": tp2,
        "fast_conflict": fast_conflict,
        "main_conflict": main_conflict,
    }


# ============================================================
# POSITION MANAGEMENT
# ============================================================

def load_positions():
    if not os.path.exists(POSITION_FILE):
        return {}

    try:
        with open(
            POSITION_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)

    except Exception:
        return {}


def save_positions(data):
    with open(
        POSITION_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False
        )


def manage_position(result, positions):
    name = result["name"]
    signal = result["signal"]
    price = result["price"]

    position = positions.get(name)

    if not position:
        return None

    side = position.get("side")
    entry = position.get("entry")
    stop = position.get("stop")
    tp1 = position.get("tp1")
    tp2 = position.get("tp2")

    if side == "LONG":

        if price <= stop:
            del positions[name]

            return (
                f"🔴 EXIT LONG — {name}\n"
                f"Prezzo: {price:.4f}\n"
                f"Motivo: STOP"
            )

        if price >= tp2:
            del positions[name]

            return (
                f"🟢 EXIT LONG — {name}\n"
                f"Prezzo: {price:.4f}\n"
                f"Motivo: TP2"
            )

        if (
            price >= tp1
            and signal == "SHORT"
        ):
            del positions[name]

            return (
                f"🟠 EXIT LONG — {name}\n"
                f"Prezzo: {price:.4f}\n"
                f"Motivo: INVERSIONE"
            )

    elif side == "SHORT":

        if price >= stop:
            del positions[name]

            return (
                f"🔴 EXIT SHORT — {name}\n"
                f"Prezzo: {price:.4f}\n"
                f"Motivo: STOP"
            )

        if price <= tp2:
            del positions[name]

            return (
                f"🟢 EXIT SHORT — {name}\n"
                f"Prezzo: {price:.4f}\n"
                f"Motivo: TP2"
            )

        if (
            price <= tp1
            and signal == "LONG"
        ):
            del positions[name]

            return (
                f"🟠 EXIT SHORT — {name}\n"
                f"Prezzo: {price:.4f}\n"
                f"Motivo: INVERSIONE"
            )

    return None
    # ============================================================
# TELEGRAM
# ============================================================

def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN:
        return

    url = (
        "https://api.telegram.org/bot"
        f"{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
    }

    try:
        requests.post(
            url,
            json=payload,
            timeout=15
        )
    except Exception as e:
        print(
            f"Telegram error: {e}"
        )


# ============================================================
# FORMATTAZIONE
# ============================================================

def fmt_price(value):
    if value is None:
        return "N/D"

    if abs(value) >= 100:
        return f"{value:.2f}"

    if abs(value) >= 10:
        return f"{value:.3f}"

    return f"{value:.4f}"


def direction_icon(direction):
    if direction == "LONG":
        return "🟢"

    if direction == "SHORT":
        return "🔴"

    return "⚪"


def signal_icon(signal):
    if signal == "LONG":
        return "🟢"

    if signal == "SHORT":
        return "🔴"

    return "🟡"


def format_result(result):
    return (
        f"{direction_icon(result['direction'])} "
        f"{result['name']} — "
        f"{result['signal']}\n"
        f"Score: {result['score']:.0f} | "
        f"Prob: {result['probability'] * 100:.0f}% | "
        f"Qualità: {result['quality']:.0f}%"
    )


# ============================================================
# RANKING
# ============================================================

def ranking_score(result):
    signal = result.get(
        "signal",
        "WAIT"
    )

    score = abs(
        result.get("score", 0)
    )

    quality = result.get(
        "quality",
        0
    )

    confidence = result.get(
        "confidence",
        0
    )

    value = (
        score * 0.60 +
        quality * 0.25 +
        confidence * 0.15
    )

    if signal == "WAIT":
        value *= 0.70

    return value


def rank_results(results):
    return sorted(
        results,
        key=ranking_score,
        reverse=True
    )


# ============================================================
# SCELTA DEL MIGLIOR SETUP
# ============================================================

def choose_best(results):
    ranked = rank_results(
        results
    )

    if not ranked:
        return None, []

    best = ranked[0]

    second = (
        ranked[1]
        if len(ranked) > 1
        else None
    )

    best_rank = ranking_score(
        best
    )

    second_rank = (
        ranking_score(second)
        if second
        else 0
    )

    margin = (
        best_rank - second_rank
    )

    best["ranking_score"] = best_rank
    best["ranking_margin"] = margin

    # Per evitare di scegliere automaticamente
    # un setup debole.
    if best["signal"] == "WAIT":
        return None, ranked

    if best_rank < 65:
        return None, ranked

    if best["quality"] < 45:
        return None, ranked

    if best["confidence"] < 58:
        return None, ranked

    if margin < 5:
        return None, ranked

    if best.get("fast_conflict"):
        return None, ranked

    if best.get("main_conflict"):
        return None, ranked

    return best, ranked


# ============================================================
# APERTURA POSIZIONE
# ============================================================

def open_position(result, positions):
    name = result["name"]

    if name in positions:
        return None

    if result["signal"] not in (
        "LONG",
        "SHORT"
    ):
        return None

    position = {
        "side": result["signal"],
        "entry": result["price"],
        "stop": result["stop"],
        "tp1": result["tp1"],
        "tp2": result["tp2"],
        "opened_at": datetime.utcnow().isoformat(),
        "score": result["score"],
        "probability": result["probability"],
    }

    positions[name] = position

    return position


# ============================================================
# MESSAGGIO TELEGRAM
# ============================================================

def build_telegram_message(
    best,
    ranked,
    exits
):
    lines = []

    lines.append(
        "🌍 COMMODITIES BOT"
    )
    lines.append("")

    if best:
        lines.append(
            "🏆 MIGLIOR SETUP"
        )

        lines.append(
            f"{direction_icon(best['direction'])} "
            f"{best['name']}"
        )

        lines.append(
            f"🎯 {best['signal']} | "
            f"{best['grade']}"
        )

        lines.append(
            f"📊 Score: "
            f"{best['score']:.0f}/100"
        )

        lines.append(
            f"💰 Prezzo: "
            f"{fmt_price(best['price'])}"
        )

        lines.append(
            f"🎲 Probabilità: "
            f"{best['probability'] * 100:.0f}%"
        )

        lines.append(
            f"🧠 Qualità modello: "
            f"{best['quality']:.0f}%"
        )

        rep = best["repetition"]

        if rep["samples"] > 0:
            avg = (
                rep["avg_return"] * 100
            )

            lines.append(
                f"📅 Ricorrenza: "
                f"{rep['direction']} "
                f"{rep['frequency'] * 100:.0f}%"
            )

            lines.append(
                f"📈 Media 5g storica: "
                f"{avg:+.2f}%"
            )

        lines.append(
            f"📰 News: "
            f"{best['news']['label']}"
        )

        lines.append(
            f"💵 Dollaro: "
            f"{best['usd']['label']}"
        )

        lines.append("")

        lines.append(
            f"👉 ENTRY: "
            f"{fmt_price(best['price'])}"
        )

        lines.append(
            f"🛑 SL: "
            f"{fmt_price(best['stop'])}"
        )

        lines.append(
            f"🎯 TP1: "
            f"{fmt_price(best['tp1'])}"
        )

        lines.append(
            f"🎯 TP2: "
            f"{fmt_price(best['tp2'])}"
        )

        lines.append("")

        mtf = best["mtf"]

        lines.append(
            "⏱️ TF: "
            f"4H {mtf.get('4h', 'NONE')} | "
            f"1H {mtf.get('1h', 'NONE')} | "
            f"15m {mtf.get('15m', 'NONE')} | "
            f"5m {mtf.get('5m', 'NONE')} | "
            f"1m {mtf.get('1m', 'NONE')}"
        )

        lines.append(
            "👉 FOCUS: "
            f"{best['name']}"
        )

    else:
        lines.append(
            "🟡 NESSUN SETUP ABBASTANZA FORTE"
        )

        if ranked:
            lines.append("")

            for i, result in enumerate(
                ranked[:5],
                start=1
            ):
                icon = (
                    "🥇"
                    if i == 1
                    else "🥈"
                    if i == 2
                    else "🥉"
                    if i == 3
                    else "▫️"
                )

                lines.append(
                    f"{icon} "
                    f"{result['name']} — "
                    f"{result['signal']} "
                    f"({result['score']:.0f})"
                )

    if exits:
        lines.append("")
        lines.append(
            "📌 GESTIONE POSIZIONI"
        )

        for exit_message in exits:
            lines.append(
                exit_message
            )

    lines.append("")
    lines.append(
        "⚠️ Segnale algoritmico, "
        "non garanzia di profitto."
    )

    return "\n".join(lines)


# ============================================================
# MAIN
# ============================================================

def main():
    print(
        "🌍 COMMODITIES BOT v5.0"
    )

    if not TWELVE_DATA_API_KEY:
        raise RuntimeError(
            "TWELVE_DATA_API_KEY "
            "non configurata."
        )

    positions = load_positions()

    results = []
    exits = []

    # --------------------------------------------------------
    # ANALISI COMMODITIES
    # --------------------------------------------------------

    for name, symbol in COMMODITIES.items():

        try:
            print(
                f"Analisi: {name} "
                f"({symbol})"
            )

            result = analyze(
                name,
                symbol
            )

            # Gestione di eventuale posizione
            exit_message = manage_position(
                result,
                positions
            )

            if exit_message:
                exits.append(
                    exit_message
                )

            results.append(
                result
            )

        except Exception as e:
            print(
                f"Errore {name}: {e}"
            )

    # --------------------------------------------------------
    # RANKING
    # --------------------------------------------------------

    best, ranked = choose_best(
        results
    )

    # --------------------------------------------------------
    # APERTURA POSIZIONE
    # --------------------------------------------------------

    if best:
        position = open_position(
            best,
            positions
        )

        if position:
            print(
                f"Nuova posizione: "
                f"{best['name']} "
                f"{best['signal']}"
            )

    # --------------------------------------------------------
    # SALVATAGGIO
    # --------------------------------------------------------

    save_positions(
        positions
    )

    # --------------------------------------------------------
    # TELEGRAM
    # --------------------------------------------------------

    message = build_telegram_message(
        best,
        ranked,
        exits
    )

    send_telegram(
        message
    )

    # --------------------------------------------------------
    # CONSOLE
    # --------------------------------------------------------

    print("")
    print(message)
    print("")

    # --------------------------------------------------------
    # RANKING COMPLETO
    # --------------------------------------------------------

    print(
        "========== RANKING =========="
    )

    for i, result in enumerate(
        ranked,
        start=1
    ):
        print(
            f"{i}. "
            f"{result['name']} | "
            f"{result['signal']} | "
            f"Score {result['score']:.1f} | "
            f"Quality {result['quality']:.1f}"
        )


if __name__ == "__main__":
    main()
    