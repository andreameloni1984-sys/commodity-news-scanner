import os
import json
import math
import re
from datetime import datetime, timezone

import requests


# ============================================================
# COMMODITY TRADING BOT v6.0
# QUANT MODEL + MULTI-TIMEFRAME + WEB NEWS + USD
# + SEASONALITY + RANKING + POSITION MANAGEMENT
#
# Analitico/simulato: NON esegue ordini reali.
# ============================================================

API_KEY = os.getenv("TWELVE_DATA_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "8002086130")

if not API_KEY:
    raise RuntimeError(
        "TWELVE_DATA_API_KEY non configurata nei GitHub Secrets."
    )

BASE_URL = "https://api.twelvedata.com/time_series"

# GDELT: ricerca notizie dal web senza API key
GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

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


# ============================================================
# COMMODITIES
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
# TERMINI DI RICERCA WEB
# ============================================================

NEWS_TERMS = {
    "Oro": (
        'gold OR bullion OR XAU OR "gold price" OR '
        '"gold market" OR "precious metals"'
    ),

    "Argento": (
        'silver OR XAG OR "silver price" OR '
        '"silver market"'
    ),

    "Petrolio WTI": (
        'oil OR crude OR WTI OR "oil price" OR '
        '"crude oil" OR OPEC'
    ),

    "Petrolio Brent": (
        'oil OR crude OR Brent OR "Brent crude" OR '
        '"oil price" OR OPEC'
    ),

    "Gas Naturale": (
        '"natural gas" OR LNG OR "gas prices" OR '
        '"gas market"'
    ),

    "Rame": (
        'copper OR "copper price" OR '
        '"copper market" OR China'
    ),

    "Grano": (
        'wheat OR grain OR "wheat price" OR '
        '"wheat market" OR crops'
    ),

    "Mais": (
        'corn OR maize OR "corn price" OR '
        '"corn market" OR crops'
    ),

    "Caffè": (
        'coffee OR "coffee price" OR '
        '"coffee market" OR arabica OR robusta'
    ),
}


# ============================================================
# EVENTI MACRO CHE POSSONO INFLUENZARE LE COMMODITIES
# ============================================================

MACRO_TERMS = (
    'Federal Reserve OR Fed OR interest rates OR '
    'inflation OR CPI OR PPI OR NFP OR jobs OR '
    'Treasury yields OR dollar OR USD OR '
    'geopolitical OR sanctions OR tariffs OR '
    'China OR OPEC'
)


# ============================================================
# PAROLE POSITIVE / NEGATIVE
# ============================================================

POSITIVE_WORDS = {
    "rise",
    "rises",
    "rising",
    "gain",
    "gains",
    "bullish",
    "surge",
    "surges",
    "soar",
    "soars",
    "strong",
    "higher",
    "increase",
    "increases",
    "jump",
    "jumps",
    "rally",
    "rallies",
    "support",
    "demand",
    "shortage",
    "tight",
    "tighter",
    "boost",
    "boosts",
    "upside",
    "record",
    "rebound",
    "recovery",
    "hawkish",
}

NEGATIVE_WORDS = {
    "fall",
    "falls",
    "falling",
    "drop",
    "drops",
    "bearish",
    "weak",
    "weaker",
    "lower",
    "decrease",
    "decreases",
    "decline",
    "declines",
    "collapse",
    "oversupply",
    "surplus",
    "concern",
    "concerns",
    "recession",
    "downside",
    "slump",
    "slumps",
    "crash",
    "cuts",
    "cut",
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

    return max(math.sqrt(variance), 1e-8)


def sigmoid(x):
    x = max(-30, min(30, x))
    return 1 / (1 + math.exp(-x))


def clamp(value, low, high):
    return max(low, min(high, value))


def pct(value):
    return f"{value * 100:.1f}%"


def clean_words(text):
    return set(
        re.findall(
            r"[a-zA-Z]+",
            text.lower()
        )
    )


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

    for item in data.get("values", []):

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


def get_daily_data(symbol):

    return get_data(
        symbol,
        "1day",
        HISTORY_SIZE
    )


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

    result = mean(
        values[:period]
    )

    for value in values[period:]:

        result = (
            (value - result) * multiplier
            + result
        )

    return result


def rsi(values, period=14):

    if len(values) < period + 1:
        return 50.0

    gains = []
    losses = []

    for i in range(1, len(values)):

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

    rs = avg_gain / avg_loss

    return 100 - (
        100 / (1 + rs)
    )


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

        ranges.append(
            max(
                high - low,
                abs(high - previous),
                abs(low - previous)
            )
        )

    return (
        mean(ranges[-period:])
        if len(ranges) >= period
        else None
    )


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
            returns.append(
                values[i] / previous - 1
            )

    return std(returns)


def pressure(candles, period=10):

    scores = []

    for candle in candles[-period:]:

        high = candle["high"]
        low = candle["low"]
        close = candle["close"]
        open_price = candle["open"]

        if None in (
            high,
            low,
            close,
            open_price
        ):
            continue

        if high == low:
            continue

        scores.append(
            (close - open_price)
            / (high - low)
        )

    return mean(scores)


def breakout(values, period=20):

    if len(values) < period + 1:
        return 0.0

    current = values[-1]

    previous = values[
        -period - 1:-1
    ]

    highest = max(previous)
    lowest = min(previous)

    distance = highest - lowest

    if distance == 0:
        return 0.0

    return (
        (current - lowest)
        / distance
    ) * 2 - 1


# ============================================================
# STAGIONALITÀ
# ============================================================

def historical_repetition(candles):

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
            candles[-1]["datetime"]
            .replace("Z", "+00:00")
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

    target_day = (
        current_date.timetuple().tm_yday
    )

    samples = []

    for i in range(
        100,
        len(candles) - HORIZON
    ):

        try:

            d = datetime.fromisoformat(
                candles[i]["datetime"]
                .replace("Z", "+00:00")
            )

            day = d.timetuple().tm_yday

        except Exception:
            continue

        distance = abs(
            day - target_day
        )

        distance = min(
            distance,
            366 - distance
        )

        if distance <= 22:

            current = candles[i]["close"]
            future = candles[
                i + HORIZON
            ]["close"]

            if current:

                samples.append(
                    future / current - 1
                )

    if len(samples) < 5:

        return {
            "score": 0.0,
            "frequency": 0.0,
            "avg_return": 0.0,
            "samples": len(samples),
            "years": 0,
            "direction": "NEUTRALE",
        }

    positive = sum(
        1 for x in samples
        if x > 0
    )

    negative = sum(
        1 for x in samples
        if x < 0
    )

    frequency = (
        max(positive, negative)
        / len(samples)
    )

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

    magnitude_factor = clamp(
        abs(avg_return) / 0.01,
        0.0,
        1.0
    )

    score = (
        raw_score
        * magnitude_factor
    )

    years = len({
        candles[i]["datetime"][:4]
        for i in range(
            100,
            len(candles) - HORIZON
        )
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

    return historical_repetition(
        candles
    )["score"]


# ============================================================
# FEATURES
# ============================================================

def build_features(candles):

    closes = [
        c["close"]
        for c in candles
    ]

    if len(closes) < 100:
        return None

    current = closes[-1]

    sma20 = (
        sma(closes, 20)
        or current
    )

    sma50 = (
        sma(closes, 50)
        or current
    )

    trend = (
        sma20 / sma50 - 1
        if sma50
        else 0.0
    )

    current_atr = atr(
        candles,
        14
    )

    atr_pct = (
        current_atr / current
        if current_atr and current
        else 0.0
    )

    current_macd = macd(
        closes
    )

    macd_normalized = (
        current_macd / current
        if current
        else 0.0
    )

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

    for i in range(
        minimum_history,
        len(candles) - HORIZON
    ):

        history = candles[
            :i + 1
        ]

        features = build_features(
            history
        )

        if features is None:
            continue

        current = candles[i]["close"]

        future = candles[
            i + HORIZON
        ]["close"]

        if not current:
            continue

        future_return = (
            future / current - 1
        )

        if abs(future_return) < 0.002:
            continue

        dataset.append({
            "x": features,
            "y": (
                1
                if future_return > 0
                else 0
            ),
            "return": future_return,
        })

    return dataset


# ============================================================
# STANDARDIZATION
# ============================================================

def standardize(
    train_x,
    other_x
):

    if not train_x:
        return [], [], [], []

    count = len(
        train_x[0]
    )

    means = []
    deviations = []

    for j in range(count):

        values = [
            row[j]
            for row in train_x
        ]

        means.append(
            mean(values)
        )

        deviations.append(
            std(values)
        )

    def transform(row):

        return [
            (
                row[j]
                - means[j]
            )
            / deviations[j]
            for j in range(count)
        ]

    return (
        [
            transform(row)
            for row in train_x
        ],

        [
            transform(row)
            for row in other_x
        ],

        means,
        deviations,
    )


# ============================================================
# LOGISTIC MODEL
# ============================================================

def fit_model(
    X,
    y,
    epochs=700,
    learning_rate=0.035,
    regularization=0.08
):

    if not X:
        return [], 0.0

    feature_count = len(
        X[0]
    )

    weights = [
        0.0
        for _ in range(feature_count)
    ]

    bias = 0.0
    n = len(X)

    for _ in range(epochs):

        gradients = [
            0.0
            for _ in range(feature_count)
        ]

        bias_gradient = 0.0

        for row, target in zip(
            X,
            y
        ):

            z = (
                bias
                + sum(
                    weights[j]
                    * row[j]
                    for j in range(
                        feature_count
                    )
                )
            )

            prediction = sigmoid(z)

            error = (
                prediction
                - target
            )

            bias_gradient += error

            for j in range(
                feature_count
            ):

                gradients[j] += (
                    error
                    * row[j]
                )

        bias -= (
            learning_rate
            * bias_gradient
            / n
        )

        for j in range(
            feature_count
        ):

            gradient = (
                gradients[j] / n
            )

            gradient += (
                regularization
                * weights[j]
            )

            weights[j] -= (
                learning_rate
                * gradient
            )

    return weights, bias


def predict(
    row,
    weights,
    bias
):

    return sigmoid(
        bias
        + sum(
            weights[i]
            * row[i]
            for i in range(
                len(weights)
            )
        )
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

    split = int(
        len(dataset) * 0.70
    )

    test = dataset[split:]

    predictions = []

    train_size = 1000
    step = 20