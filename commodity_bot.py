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
    raise RuntimeError("TWELVE_DATA_API_KEY non configurata nei GitHub Secrets.")

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

def get_data(symbol, interval="1day", outputsize=4000):
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


def get_daily_data(symbol):
    return get_data(symbol, "1day", HISTORY_SIZE)


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
    if len(candles) < 300:
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

    if len(closes) < 100:
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
    minimum_history = 100

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
    if len(dataset) < 500:
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
    if len(dataset) < 300:
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
    if not NEWS_API_KEY:
        return {
            "score": 0,
            "label": "NON DISPONIBILI",
            "count": 0,
        }

    query = NEWS_TERMS.get(name, name)

    params = {
        "q": query,
        "apiKey": NEWS_API_KEY,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 20,
    }

    try:
        response = requests.get(NEWS_URL, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()

        articles = data.get("articles", [])
        if not articles:
            return {
                "score": 0,
                "label": "NEUTRALI",
                "count": 0,
            }

        positive_words = {
            "rise", "rises", "rising", "gain", "gains", "bullish",
            "surge", "surges", "strong", "higher", "increase",
            "increases", "shortage", "demand", "support",
        }

        negative_words = {
            "fall", "falls", "falling", "drop", "drops", "bearish",
            "weak", "lower", "decrease", "decreases", "oversupply",
            "collapse", "concern", "concerns", "recession",
        }

        total = 0

        for article in articles:
            text = (
                f"{article.get('title', '')} "
                f"{article.get('description', '')}"
            ).lower()

            words = set(text.split())
            pos = len(words & positive_words)
            neg = len(words & negative_words)

            if pos > neg:
                total += 1
            elif neg > pos:
                total -= 1

        normalized = clamp(total / max(len(articles), 1), -1, 1)

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
        print(f"   ⚠️ News {name}: {error}")
        return {
            "score": 0,
            "label": "ERRORE",
            "count": 0,
        }


# ============================================================
# SIGNAL
# ============================================================

def analyze(candles, dataset, model, bt, usd, news, timeframes):
    features = build_features(candles)

    if features is None:
        return None

    scaled = scale_current(features, model)

    probability = predict(
        scaled,
        model["weights"],
        model["bias"],
    )

    quality = quality_score(bt)

    strength = abs(probability - 0.50) * 200
    confidence = strength * 0.60 + quality * 0.40

    if quality < MIN_QUALITY:
        model_signal = "NO TRADE"
    elif probability >= LONG_THRESHOLD:
        model_signal = "LONG"
    elif probability <= SHORT_THRESHOLD:
        model_signal = "SHORT"
    else:
        model_signal = "WAIT"

    main_direction = (
        "LONG" if probability >= 0.50
        else "SHORT"
    )

    tf_score = 0
    for tf in ("4H", "1H", "15m"):
        direction = timeframes[tf]["direction"]
        if direction == main_direction:
            tf_score += 1
        elif direction not in ("NONE", main_direction):
            tf_score -= 1

    fast_confirmations = 0
    fast_conflicts = 0

    for tf in ("5m", "1m"):
        direction = timeframes[tf]["direction"]
        if direction == main_direction:
            fast_confirmations += 1
        elif direction not in ("NONE", main_direction):
            fast_conflicts += 1

    # Fattore storico: positivo se concorda col modello,
    # negativo se va contro.
    repetition = historical_repetition(candles)

    repetition_impact = 0
    if repetition["direction"] == main_direction:
        repetition_impact = repetition["frequency"] * 8
    elif repetition["direction"] not in ("NEUTRALE", main_direction):
        repetition_impact = -repetition["frequency"] * 8

    # Score 0-100.
    direction_score = abs(probability - 0.50) * 200

    score = (
        direction_score * 0.40
        + quality * 0.20
        + confidence * 0.15
        + max(tf_score, -3) * 5
        + fast_confirmations * 5
        + repetition_impact
        + news["score"] * 6
        + usd["impact"] * 3
    )

    score = clamp(score, 0, 100)

    # Non permettiamo un LONG/SHORT operativo se i timeframe
    # principali sono completamente contrari o i veloci mostrano
    # un conflitto netto.
    operational_signal = model_signal

    if model_signal in ("LONG", "SHORT"):
        if tf_score <= -2:
            operational_signal = "WAIT"
        elif fast_conflicts == 2:
            operational_signal = "WAIT"

    # Grado del setup.
    if operational_signal in ("LONG", "SHORT"):
        if (
            confidence >= 70
            and fast_confirmations == 2
            and tf_score >= 1
            and score >= 75
        ):
            grade = "FORTE"
        elif confidence >= 58 and score >= 65:
            grade = "IN FORMAZIONE"
        else:
            grade = "DEBOLE"
    elif model_signal in ("LONG", "SHORT"):
        grade = "CONFLITTO" if fast_conflicts else "IN FORMAZIONE"
    else:
        grade = "NEUTRALE"

    price = candles[-1]["close"]
    current_atr = atr(candles, 14) or price * 0.01

    if operational_signal == "LONG":
        stop = price - current_atr * STOP_ATR
        tp1 = price + current_atr * TP1_ATR
        tp2 = price + current_atr * TP2_ATR
    elif operational_signal == "SHORT":
        stop = price + current_atr * STOP_ATR
        tp1 = price - current_atr * TP1_ATR
        tp2 = price - current_atr * TP2_ATR
    else:
        stop = tp1 = tp2 = None

    return {
        "signal": operational_signal,
        "model_signal": model_signal,
        "grade": grade,
        "probability": probability,
        "confidence": confidence,
        "quality": quality,
        "score": score,
        "price": price,
        "atr": current_atr,
        "stop": stop,
        "tp1": tp1,
        "tp2": tp2,
        "timeframes": timeframes,
        "usd": usd,
        "news": news,
        "repetition": repetition,
        "tf_score": tf_score,
        "fast_confirmations": fast_confirmations,
        "fast_conflicts": fast_conflicts,
    }


# ============================================================
# POSITION MANAGEMENT
# ============================================================

def manage_position(position, current_analysis, current_price):
    direction = position["direction"]
    entry = position["entry"]
    stop = position["stop"]
    tp1 = position["tp1"]
    tp2 = position["tp2"]

    probability = current_analysis["probability"]
    signal = current_analysis["signal"]

    if direction == "LONG":
        if current_price <= stop:
            return {"action": "EXIT", "reason": "STOP LOSS", "new_stop": stop}

        if current_price >= tp2:
            return {"action": "EXIT", "reason": "TAKE PROFIT 2", "new_stop": stop}

        if probability <= 0.38 or signal == "SHORT":
            return {
                "action": "EXIT",
                "reason": "INVERSIONE CONFERMATA",
                "new_stop": stop,
            }

        if probability < 0.48:
            return {
                "action": "WARNING",
                "reason": "LONG INDEBOLITO",
                "new_stop": stop,
            }

        if current_price >= tp1:
            trailing_stop = current_price - current_analysis["atr"]
            new_stop = max(stop, entry, trailing_stop)
            return {
                "action": "HOLD",
                "reason": "TP1 RAGGIUNTO - TRAILING STOP",
                "new_stop": new_stop,
            }

        return {
            "action": "HOLD",
            "reason": "TREND LONG ANCORA VALIDO",
            "new_stop": stop,
        }

    if direction == "SHORT":
        if current_price >= stop:
            return {"action": "EXIT", "reason": "STOP LOSS", "new_stop": stop}

        if current_price <= tp2:
            return {"action": "EXIT", "reason": "TAKE PROFIT 2", "new_stop": stop}

        if probability >= 0.62 or signal == "LONG":
            return {
                "action": "EXIT",
                "reason": "INVERSIONE CONFERMATA",
                "new_stop": stop,
            }

        if probability > 0.52:
            return {
                "action": "WARNING",
                "reason": "SHORT INDEBOLITO",
                "new_stop": stop,
            }

        if current_price <= tp1:
            trailing_stop = current_price + current_analysis["atr"]
            new_stop = min(stop, entry, trailing_stop)
            return {
                "action": "HOLD",
                "reason": "TP1 RAGGIUNTO - TRAILING STOP",
                "new_stop": new_stop,
            }

        return {
            "action": "HOLD",
            "reason": "TREND SHORT ANCORA VALIDO",
            "new_stop": stop,
        }

    return {
        "action": "EXIT",
        "reason": "DIREZIONE NON RICONOSCIUTA",
        "new_stop": stop,
    }


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
    signal = analysis["model_signal"]
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


def build_telegram(ranked, best, position_message=None):
    a = best["analysis"]

    lines = [
        "🌍 COMMODITIES BOT",
        "",
        f"🏆 MIGLIOR SETUP",
        f"{icon_for_signal(a['signal'])} {best['name']}",
        f"🎯 {a['signal']} | {a['grade']}",
        f"📊 Score: {a['score']:.0f}/100",
        "",
        f"💰 Prezzo: {a['price']:.4f}",
        f"🧠 Modello: {pct(a['probability'])}",
        f"📈 {compact_tf(a['timeframes'])}",
        confirmation_text(a),
        "",
        f"📰 News: {a['news']['label']}",
        f"💵 Dollaro: {a['usd']['label']}",
        f"🔄 Storico: {a['repetition']['direction']} "
        f"({a['repetition']['frequency'] * 100:.0f}% "
        f"su {a['repetition']['samples']} casi)",
        "",
    ]

    if a["signal"] in ("LONG", "SHORT"):
        lines.extend([
            f"👉 ENTRY: {a['price']:.4f}",
            f"🛑 SL: {a['stop']:.4f}",
            f"🎯 TP1: {a['tp1']:.4f}",
            f"🎯 TP2: {a['tp2']:.4f}",
            "",
        ])

    for i, item in enumerate(ranked[:3], 1):
        if item["name"] == best["name"]:
            continue

        x = item["analysis"]
        lines.append(
            f"{'🥈' if i == 2 else '🥉'} {item['name']} — "
            f"{x['signal']} | {x['score']:.0f}/100"
        )

    if position_message:
        lines.extend(["", position_message])

    lines.extend([
        "",
        f"👉 FOCUS: {best['name']}",
        "",
        "⚠️ Segnale algoritmico, non garanzia di profitto.",
    ])

    return "\n".join(lines)


# ============================================================
# MAIN
# ============================================================

def main():
    print()
    print("=" * 70)
    print("🌍 COMMODITY TRADING BOT v5.0")
    print("QUANT + MTF + NEWS + USD + RIPETIZIONE STORICA")
    print("=" * 70)
    print()

    position = load_position()
    usd = analyze_usd()

    results = []

    for name, symbol in COMMODITIES.items():
        print(f"🔎 Analizzo {name}...")

        try:
            candles = get_daily_data(symbol)

            if len(candles) < 500:
                print("   ⚠️ Dati insufficienti")
                continue

            dataset = build_dataset(candles)

            if len(dataset) < 300:
                print("   ⚠️ Dataset insufficiente")
                continue

            bt = backtest(dataset)
            model = train_final(dataset)

            if model is None:
                continue

            timeframes = get_multitimeframe(symbol)
            news = analyze_news(name)

            analysis = analyze(
                candles,
                dataset,
                model,
                bt,
                usd,
                news,
                timeframes,
            )

            if analysis is None:
                continue

            results.append({
                "name": name,
                "symbol": symbol,
                "candles": candles,
                "analysis": analysis,
                "backtest": bt,
            })

            print(
                f"   → MODELLO {analysis['model_signal']} | "
                f"OPERATIVO {analysis['signal']} | "
                f"Score {analysis['score']:.0f}"
            )

        except Exception as error:
            print(f"   ❌ {error}")

    if not results:
        raise RuntimeError("Nessuna materia prima analizzata.")

    # ========================================================
    # RANKING
    # ========================================================

    ranked = sorted(
        results,
        key=lambda x: x["analysis"]["score"],
        reverse=True,
    )

    best = ranked[0]

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

            elif management["action"] == "WARNING":
                position["stop"] = management["new_stop"]
                save_position(position)
                position_message = (
                    f"🟠 POSIZIONE {position['direction']} — ATTENZIONE\n"
                    f"{management['reason']}"
                )

            else:
                if management["new_stop"] != position["stop"]:
                    position["stop"] = management["new_stop"]
                    save_position(position)

                position_message = (
                    f"🟢 POSIZIONE {position['direction']} — MANTIENI\n"
                    f"{management['reason']}"
                )

    # ========================================================
    # NUOVA POSIZIONE
    # ========================================================

    if not position and best["analysis"]["signal"] in ("LONG", "SHORT"):
        second_score = ranked[1]["analysis"]["score"] if len(ranked) > 1 else 0
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
            and a["score"] - second_score >= MIN_RANK_MARGIN
            and a["fast_conflicts"] == 0
        ):
            position = {
                "name": best["name"],
                "symbol": best["symbol"],
                "direction": a["signal"],
                "entry": a["price"],
                "stop": a["stop"],
                "tp1": a["tp1"],
                "tp2": a["tp2"],
                "opened_at": datetime.now(timezone.utc).isoformat(),
            }

            save_position(position)

            position_message = (
                f"🚨 NUOVA POSIZIONE {a['signal']}\n"
                f"Entry {a['price']:.4f} | "
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
        print(
            f"{i}. {icon_for_signal(x['signal'])} "
            f"{item['name']} | "
            f"{x['signal']} | "
            f"{x['score']:.0f}/100 | "
            f"model {x['probability'] * 100:.1f}% | "
            f"storico {x['repetition']['direction']}"
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
