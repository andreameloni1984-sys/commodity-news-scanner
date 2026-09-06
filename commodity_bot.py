import os
import json
import math
import re
from datetime import datetime, timezone

import requests


# ============================================================
# COMMODITY TRADING BOT v6.1
# QUANT MODEL + MULTI-TIMEFRAME + WEB NEWS + USD
# + SEASONALITY + RANKING + POSITION MANAGEMENT
#
# ANALITICO/SIMULATO - NON ESEGUE ORDINI REALI
# ============================================================

API_KEY = os.getenv("TWELVE_DATA_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "8002086130")

if not API_KEY:
    raise RuntimeError(
        "TWELVE_DATA_API_KEY non configurata nei GitHub Secrets."
    )

BASE_URL = "https://api.twelvedata.com/time_series"

# GDELT DOC 2.0
GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CommoditiesBot/6.1)"
}

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
# NEWS
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

MACRO_TERMS = (
    'Federal Reserve OR Fed OR inflation OR CPI OR PPI OR '
    'NFP OR jobs OR "interest rates" OR "Treasury yields" OR '
    'dollar OR USD OR OPEC OR China'
)


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
}


# ============================================================
# UTILITY
# ============================================================

def safe_float(value):
    try:
        return float(value)
    except Exception:
        return None


def mean(values):
    values = [x for x in values if x is not None]
    if not values:
        return 0.0
    return sum(values) / len(values)


def std(values):
    values = [x for x in values if x is not None]
    if len(values) < 2:
        return 0.0

    m = mean(values)
    variance = sum((x - m) ** 2 for x in values) / len(values)

    return math.sqrt(variance)


def sigmoid(x):
    x = max(-60, min(60, x))
    return 1.0 / (1.0 + math.exp(-x))


def clamp(value, low, high):
    return max(low, min(high, value))


def pct(a, b):
    if b in (None, 0):
        return 0.0
    return ((a - b) / b) * 100.0


def clean_words(text):
    return re.findall(
        r"[a-zA-ZÀ-ÿ]+",
        str(text).lower()
    )


# ============================================================
# POSITION MEMORY
# ============================================================

def load_position():
    if not os.path.exists(POSITION_FILE):
        return None

    try:
        with open(POSITION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_position(position):
    with open(POSITION_FILE, "w", encoding="utf-8") as f:
        json.dump(position, f, indent=2)


def clear_position():
    if os.path.exists(POSITION_FILE):
        try:
            os.remove(POSITION_FILE)
        except Exception:
            pass


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

    response = requests.get(
        BASE_URL,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    if data.get("status") == "error":
        raise RuntimeError(
            data.get("message", "Errore Twelve Data")
        )

    values = data.get("values", [])

    candles = []

    for item in values:

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

    value = mean(values[:period])

    for price in values[period:]:
        value = (
            price - value
        ) * multiplier + value

    return value


def rsi(values, period=14):

    if len(values) <= period:
        return None

    gains = []
    losses = []

    for i in range(1, len(values)):
        change = values[i] - values[i - 1]

        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    avg_gain = mean(gains[:period])
    avg_loss = mean(losses[:period])

    for i in range(period, len(gains)):
        avg_gain = (
            avg_gain * (period - 1)
            + gains[i]
        ) / period

        avg_loss = (
            avg_loss * (period - 1)
            + losses[i]
        ) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss

    return 100 - (100 / (1 + rs))


def atr(candles, period=14):

    if len(candles) <= period:
        return None

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

    if len(trs) < period:
        return None

    return mean(trs[-period:])


def macd(values):

    ema12 = ema(values, 12)
    ema26 = ema(values, 26)

    if ema12 is None or ema26 is None:
        return 0.0

    return ema12 - ema26


def return_pct(values, period):

    if len(values) <= period:
        return 0.0

    old = values[-period - 1]

    if old == 0:
        return 0.0

    return (
        (values[-1] - old)
        / old
        * 100
    )


def volatility(values, period=20):

    if len(values) < period + 1:
        return 0.0

    returns = []

    for i in range(
        len(values) - period,
        len(values)
    ):
        old = values[i - 1]

        if old != 0:
            returns.append(
                (values[i] - old) / old
            )

    return std(returns)


def pressure(candles, period=10):

    if len(candles) < period:
        return 0.0

    recent = candles[-period:]

    scores = []

    for candle in recent:

        high = candle["high"]
        low = candle["low"]
        close = candle["close"]

        if (
            high is None
            or low is None
            or close is None
            or high == low
        ):
            continue

        position = (
            (close - low)
            / (high - low)
        )

        scores.append(
            (position - 0.5) * 2
        )

    return mean(scores)


def breakout(candles, period=20):

    if len(candles) <= period:
        return 0.0

    recent = candles[-period - 1:-1]

    high = max(
        c["high"]
        for c in recent
        if c["high"] is not None
    )

    low = min(
        c["low"]
        for c in recent
        if c["low"] is not None
    )

    close = candles[-1]["close"]

    if close > high:
        return 1.0

    if close < low:
        return -1.0

    return 0.0


# ============================================================
# SEASONALITY
# ============================================================

def historical_repetition(candles):

    if len(candles) < 300:
        return {
            "score": 0.0,
            "frequency": 0.0,
            "avg_return": 0.0,
            "samples": 0,
            "years": 0,
            "direction": "NONE",
        }

    try:
        current_date = datetime.fromisoformat(
            candles[-1]["datetime"]
        )
    except Exception:
        return {
            "score": 0.0,
            "frequency": 0.0,
            "avg_return": 0.0,
            "samples": 0,
            "years": 0,
            "direction": "NONE",
        }

    current_doy = current_date.timetuple().tm_yday

    matches = []

    for i in range(
        20,
        len(candles) - HORIZON
    ):

        dt_string = candles[i]["datetime"]

        try:
            dt = datetime.fromisoformat(dt_string)
        except Exception:
            continue

        doy = dt.timetuple().tm_yday

        distance = abs(doy - current_doy)

        distance = min(
            distance,
            365 - distance
        )

        if distance <= 22:

            start = candles[i]["close"]
            future = candles[i + HORIZON]["close"]

            if start:
                future_return = (
                    future - start
                ) / start

                matches.append(
                    future_return
                )

    if len(matches) < 5:
        return {
            "score": 0.0,
            "frequency": 0.0,
            "avg_return": 0.0,
            "samples": len(matches),
            "years": 0,
            "direction": "NONE",
        }

    positives = sum(
        1 for x in matches
        if x > 0
    )

    frequency = positives / len(matches)

    avg_return = mean(matches)

    score = clamp(
        (frequency - 0.5) * 2,
        -1,
        1
    )

    if score > 0.15:
        direction = "LONG"
    elif score < -0.15:
        direction = "SHORT"
    else:
        direction = "NEUTRALE"

    years = len(
        set(
            candles[i]["datetime"][:4]
            for i in range(
                max(0, len(candles) - 1000),
                len(candles)
            )
            if candles[i].get("datetime")
        )
    )

    return {
        "score": score,
        "frequency": frequency,
        "avg_return": avg_return,
        "samples": len(matches),
        "years": years,
        "direction": direction,
    }


def seasonality(candles):

    result = historical_repetition(
        candles
    )

    return result["score"]


# ============================================================
# FEATURES
# ============================================================

def build_features(candles):

    closes = [
        c["close"]
        for c in candles
        if c["close"] is not None
    ]

    if len(closes) < 100:
        return None

    ema20 = ema(closes, 20)
    ema50 = ema(closes, 50)
    ema100 = ema(closes, 100)

    current = closes[-1]

    return [
        clamp(
            (current - ema20)
            / current
            * 100,
            -10,
            10
        ),

        clamp(
            (current - ema50)
            / current
            * 100,
            -10,
            10
        ),

        clamp(
            (current - ema100)
            / current
            * 100,
            -10,
            10
        ),

        clamp(
            (rsi(closes) - 50) / 50,
            -1,
            1
        ),

        clamp(
            macd(closes) / current * 100,
            -10,
            10
        ),

        clamp(
            return_pct(closes, 5),
            -10,
            10
        ),

        clamp(
            return_pct(closes, 20),
            -20,
            20
        ),

        clamp(
            volatility(closes) * 100,
            0,
            10
        ),

        pressure(candles),

        breakout(candles),

        seasonality(candles),

        clamp(
            return_pct(closes, 60),
            -30,
            30
        ),
    ]


# ============================================================
# DATASET
# ============================================================

def build_dataset(candles):

    dataset = []

    for i in range(
        120,
        len(candles) - HORIZON
    ):

        subset = candles[:i + 1]

        features = build_features(
            subset
        )

        if features is None:
            continue

        current = candles[i]["close"]
        future = candles[
            i + HORIZON
        ]["close"]

        if current == 0:
            continue

        future_return = (
            future - current
        ) / current

        if abs(future_return) < 0.002:
            continue

        label = 1 if future_return > 0 else 0

        dataset.append(
            (features, label)
        )

    return dataset


# ============================================================
# STANDARDIZATION
# ============================================================

def standardize(X, current=None):

    if not X:
        return [], None

    cols = list(zip(*X))

    means = [
        mean(col)
        for col in cols
    ]

    stds = [
        std(col) or 1.0
        for col in cols
    ]

    scaled = []

    for row in X:

        scaled.append([
            (value - m) / s
            for value, m, s
            in zip(row, means, stds)
        ])

    current_scaled = None

    if current is not None:

        current_scaled = [
            (value - m) / s
            for value, m, s
            in zip(
                current,
                means,
                stds
            )
        ]

    return scaled, current_scaled


# ============================================================
# LOGISTIC MODEL
# ============================================================

def fit_model(X, y):

    if not X:
        return None

    weights = [
        0.0
        for _ in X[0]
    ]

    bias = 0.0

    learning_rate = 0.03

    epochs = 120

    for _ in range(epochs):

        gradients = [
            0.0
            for _ in weights
        ]

        bias_gradient = 0.0

        for row, target in zip(X, y):

            z = bias

            for w, value in zip(
                weights,
                row
            ):
                z += w * value

            prediction = sigmoid(z)

            error = (
                prediction - target
            )

            for j in range(
                len(weights)
            ):
                gradients[j] += (
                    error * row[j]
                )

            bias_gradient += error

        n = len(X)

        for j in range(
            len(weights)
        ):
            weights[j] -= (
                learning_rate
                * gradients[j]
                / n
            )

        bias -= (
            learning_rate
            * bias_gradient
            / n
        )

    return {
        "weights": weights,
        "bias": bias,
    }


def predict(model, row):

    if model is None:
        return 0.5

    z = model["bias"]

    for w, value in zip(
        model["weights"],
        row
    ):
        z += w * value

    return sigmoid(z)


# ============================================================
# BACKTEST
# ============================================================

def backtest(dataset):

    if len(dataset) < 500:
        return {
            "accuracy": 0.5,
            "win_rate": 0.5,
            "profit_factor": 1.0,
            "drawdown": 0.0,
            "trades": 0,
        }

    split = int(
        len(dataset) * 0.70
    )

    wins = 0
    losses = 0

    gross_profit = 0.0
    gross_loss = 0.0

    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0

    trades = 0

    for i in range(
        split,
        len(dataset),
        20
    ):

        train_start = max(
            0,
            i - 1000
        )

        train = dataset[
            train_start:i
        ]

        if len(train) < 100:
            continue

        X = [
            x[0]
            for x in train
        ]

        y = [
            x[1]
            for x in train
        ]

        X_scaled, _ = standardize(X)

        model = fit_model(
            X_scaled,
            y
        )

        test_features = dataset[i][0]

        _, test_scaled = standardize(
            X + [test_features]
        )

        probability = predict(
            model,
            test_scaled
        )

        actual = dataset[i][1]

        if probability >= 0.62:

            trades += 1

            if actual == 1:
                wins += 1
                gross_profit += 1.0
                equity *= 1.01
            else:
                losses += 1
                gross_loss += 1.0
                equity *= 0.99

        elif probability <= 0.38:

            trades += 1

            if actual == 0:
                wins += 1
                gross_profit += 1.0
                equity *= 1.01
            else:
                losses += 1
                gross_loss += 1.0
                equity *= 0.99

        peak = max(
            peak,
            equity
        )

        dd = (
            peak - equity
        ) / peak

        max_drawdown = max(
            max_drawdown,
            dd
        )

    accuracy = (
        wins / trades
        if trades
        else 0.5
    )

    profit_factor = (
        gross_profit / gross_loss
        if gross_loss
        else 1.0
    )

    return {
        "accuracy": accuracy,
        "win_rate": accuracy,
        "profit_factor": profit_factor,
        "drawdown": max_drawdown,
        "trades": trades,
    }


# ============================================================
# FINAL MODEL
# ============================================================

def train_final(dataset):

    if len(dataset) < 100:
        return None, None

    X = [
        x[0]
        for x in dataset
    ]

    y = [
        x[1]
        for x in dataset
    ]

    X_scaled, scaler_current = standardize(
        X,
        X[-1]
    )

    model = fit_model(
        X_scaled,
        y
    )

    return model, scaler_current


def scale_current(dataset, current):

    X = [
        x[0]
        for x in dataset
    ]

    if not X:
        return current

    _, current_scaled = standardize(
        X,
        current
    )

    return current_scaled


# ============================================================
# QUALITY
# ============================================================

def quality_score(
    probability,
    backtest_result,
    volatility_value
):

    model_quality = (
        abs(probability - 0.5)
        * 200
    )

    backtest_quality = (
        backtest_result["win_rate"]
        * 100
    )

    volatility_penalty = clamp(
        volatility_value * 500,
        0,
        20
    )

    score = (
        model_quality * 0.45
        + backtest_quality * 0.45
        - volatility_penalty * 0.10
    )

    return clamp(
        score,
        0,
        100
    )


# ============================================================
# MULTI TIMEFRAME
# ============================================================

def timeframe_direction(candles):

    if len(candles) < 60:
        return {
            "direction": "NONE",
            "score": 0,
        }

    closes = [
        c["close"]
        for c in candles
    ]

    ema20 = ema(
        closes,
        20
    )

    ema50 = ema(
        closes,
        50
    )

    current = closes[-1]

    rsi_value = rsi(
        closes
    )

    score = 0

    if current > ema20:
        score += 1
    else:
        score -= 1

    if ema20 > ema50:
        score += 1
    else:
        score -= 1

    if rsi_value is not None:

        if rsi_value > 55:
            score += 1

        elif rsi_value < 45:
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
                250
            )

            result[name] = (
                timeframe_direction(
                    candles
                )
            )

        except Exception as error:

            print(
                f"MTF {symbol} {name}: "
                f"{error}"
            )

            result[name] = {
                "direction": "NONE",
                "score": 0,
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
            120
        )

        if len(candles) < 30:
            return {
                "direction": "NONE",
                "score": 0,
            }

        closes = [
            c["close"]
            for c in candles
        ]

        ema20 = ema(
            closes,
            20
        )

        current = closes[-1]

        if current > ema20:

            return {
                "direction": "LONG",
                "score": -1,
            }

        return {
            "direction": "SHORT",
            "score": 1,
        }

    except Exception as error:

        print(
            f"USD ERROR: {error}"
        )

        return {
            "direction": "NONE",
            "score": 0,
        }


# ============================================================
# GDELT
# ============================================================

def gdelt_query_candidates(query):

    candidates = [
        query
    ]

    simplified = query

    simplified = simplified.replace(
        "(",
        " "
    )

    simplified = simplified.replace(
        ")",
        " "
    )

    simplified = re.sub(
        r"\s+",
        " ",
        simplified
    ).strip()

    if simplified != query:
        candidates.append(
            simplified
        )

    if " AND " in simplified:

        fallback = simplified.replace(
            " AND ",
            " "
        )

        candidates.append(
            fallback
        )

    clean = []

    for item in candidates:

        if item and item not in clean:
            clean.append(item)

    return clean


def gdelt_search(
    query,
    max_records=20,
    timespan="72h"
):

    last_error = None

    for candidate in gdelt_query_candidates(
        query
    ):

        params = {
            "query": candidate,
            "mode": "artlist",
            "maxrecords": max_records,
            "format": "json",
            "sort": "datedesc",
            "timespan": timespan,
        }

        try:

            response = requests.get(
                GDELT_URL,
                params=params,
                headers=REQUEST_HEADERS,
                timeout=30
            )

            response.raise_for_status()

            try:
                data = response.json()
            except Exception:
                data = {}

            if not isinstance(
                data,
                dict
            ):
                continue

            articles = data.get(
                "articles",
                []
            )

            if not isinstance(
                articles,
                list
            ):
                articles = []

            articles = [
                article
                for article in articles
                if isinstance(
                    article,
                    dict
                )
            ]

            return articles, None

        except requests.exceptions.HTTPError as error:

            code = (
                error.response.status_code
                if error.response is not None
                else "?"
            )

            last_error = (
                f"GDELT HTTP {code}"
            )

            print(
                f"{last_error} "
                f"query={candidate}"
            )

        except Exception as error:

            last_error = (
                f"GDELT {type(error).__name__}: "
                f"{error}"
            )

            print(
                f"{last_error} "
                f"query={candidate}"
            )

    return [], last_error


def get_macro_news():

    articles, error = gdelt_search(
        MACRO_TERMS,
        max_records=20,
        timespan="72h"
    )

    if articles:
        return articles, None

    # Query molto semplice come fallback
    fallback_query = (
        'Fed OR inflation OR '
        '"interest rates" OR dollar OR '
        'OPEC OR China'
    )

    articles, fallback_error = gdelt_search(
        fallback_query,
        max_records=20,
        timespan="72h"
    )

    if articles:
        return articles, None

    return [], fallback_error or error


# ============================================================
# NEWS SENTIMENT
# ============================================================

def article_sentiment(
    commodity,
    title,
    description="",
    tone=None
):

    text = (
        f"{title} {description}"
    ).lower()

    score = 0.0

    # --------------------------------------------------------
    # Prezzo
    # --------------------------------------------------------

    positive_price = [
        r"price.{0,20}(rise|rises|rising|higher|gain|gains|surge|rally|jump)",
        r"prices.{0,20}(rise|rises|rising|higher|gain|gains|surge|rally|jump)",
    ]

    negative_price = [
        r"price.{0,20}(fall|falls|falling|lower|drop|drops|decline|slump|crash)",
        r"prices.{0,20}(fall|falls|falling|lower|drop|drops|decline|slump|crash)",
    ]

    for pattern in positive_price:

        if re.search(pattern, text):
            score += 1.0

    for pattern in negative_price:

        if re.search(pattern, text):
            score -= 1.0

    # --------------------------------------------------------
    # Offerta / produzione
    # --------------------------------------------------------

    supply_positive = [
        r"supply.{0,25}(cut|cuts|disruption|disrupted|shortage)",
        r"production.{0,25}(cut|cuts|disruption|disrupted)",
        r"output.{0,25}(cut|cuts|disruption|disrupted)",
        r"tight supply",
        r"supply shortage",
    ]

    supply_negative = [
        r"supply.{0,25}(increase|increased|surplus|oversupply)",
        r"production.{0,25}(increase|increased|surge)",
        r"output.{0,25}(increase|increased|surge)",
        r"oversupply",
        r"supply surplus",
    ]

    for pattern in supply_positive:

        if re.search(pattern, text):
            score += 1.0

    for pattern in supply_negative:

        if re.search(pattern, text):
            score -= 1.0

    # --------------------------------------------------------
    # Domanda
    # --------------------------------------------------------

    demand_positive = [
        r"demand.{0,25}(strong|rises|rise|increase|increased|boost)",
        r"strong demand",
        r"rising demand",
    ]

    demand_negative = [
        r"demand.{0,25}(weak|falls|fall|decline|decrease|decreased)",
        r"weak demand",
        r"falling demand",
    ]

    for pattern in demand_positive:

        if re.search(pattern, text):
            score += 1.0

    for pattern in demand_negative:

        if re.search(pattern, text):
            score -= 1.0

    # --------------------------------------------------------
    # Parole generiche
    # --------------------------------------------------------

    words = clean_words(text)

    positive_count = sum(
        1
        for word in words
        if word in POSITIVE_WORDS
    )

    negative_count = sum(
        1
        for word in words
        if word in NEGATIVE_WORDS
    )

    score += (
        positive_count
        - negative_count
    ) * 0.15

    # --------------------------------------------------------
    # GDELT TONE
    # --------------------------------------------------------

    tone_value = safe_float(
        tone
    )

    if tone_value is not None:

        tone_component = clamp(
            tone_value / 10.0,
            -1,
            1
        )

        score = (
            score * 0.75
            + tone_component * 0.25
        )

    return clamp(
        score / 2.0,
        -1,
        1
    )


def macro_sentiment_for_commodity(
    commodity,
    title,
    description=""
):

    text = (
        f"{title} {description}"
    ).lower()

    score = 0.0

    # --------------------------------------------------------
    # ORO / ARGENTO
    # --------------------------------------------------------

    if commodity in (
        "Oro",
        "Argento"
    ):

        positive = [
            "rate cut",
            "rate cuts",
            "lower rates",
            "dovish",
            "weaker dollar",
            "dollar falls",
            "dollar weak",
            "safe haven",
            "geopolitical tension",
        ]

        negative = [
            "rate hike",
            "rate hikes",
            "higher rates",
            "hawkish",
            "strong dollar",
            "dollar rises",
            "yields rise",
        ]

        for phrase in positive:
            if phrase in text:
                score += 1

        for phrase in negative:
            if phrase in text:
                score -= 1

    # --------------------------------------------------------
    # PETROLIO
    # --------------------------------------------------------

    elif commodity in (
        "Petrolio WTI",
        "Petrolio Brent"
    ):

        positive = [
            "opec cut",
            "production cut",
            "output cut",
            "supply disruption",
            "strong demand",
            "china demand",
            "stimulus",
        ]

        negative = [
            "opec increase",
            "output increase",
            "supply surplus",
            "weak demand",
            "recession",
            "economic slowdown",
        ]

        for phrase in positive:
            if phrase in text:
                score += 1

        for phrase in negative:
            if phrase in text:
                score -= 1

    # --------------------------------------------------------
    # RAME
    # --------------------------------------------------------

    elif commodity == "Rame":

        positive = [
            "china stimulus",
            "strong demand",
            "manufacturing growth",
            "supply disruption",
            "mine disruption",
            "production cut",
        ]

        negative = [
            "china slowdown",
            "weak demand",
            "recession",
            "manufacturing contraction",
            "supply surplus",
        ]

        for phrase in positive:
            if phrase in text:
                score += 1

        for phrase in negative:
            if phrase in text:
                score -= 1

    # --------------------------------------------------------
    # GRANO / MAIS / CAFFÈ / GAS
    # --------------------------------------------------------

    else:

        positive = [
            "drought",
            "frost",
            "freeze",
            "flood",
            "crop damage",
            "supply disruption",
            "shortage",
        ]

        negative = [
            "bumper crop",
            "favorable weather",
            "surplus",
            "oversupply",
            "harvest increase",
        ]

        for phrase in positive:
            if phrase in text:
                score += 1

        for phrase in negative:
            if phrase in text:
                score -= 1

    return clamp(
        score / 3.0,
        -1,
        1
    )


# ============================================================
# ANALISI NEWS
# ============================================================

def analyze_news(
    name,
    macro_articles=None
):

    if macro_articles is None:
        macro_articles = []

    commodity_query = NEWS_TERMS.get(
        name,
        name
    )

    commodity_articles, error = gdelt_search(
        commodity_query,
        max_records=20,
        timespan="72h"
    )

    # Fallback semplicissimo
    if not commodity_articles:

        fallback_map = {
            "Oro": "gold",
            "Argento": "silver",
            "Petrolio WTI": "oil",
            "Petrolio Brent": "Brent",
            "Gas Naturale": '"natural gas"',
            "Rame": "copper",
            "Grano": "wheat",
            "Mais": "corn",
            "Caffè": "coffee",
        }

        fallback = fallback_map.get(
            name,
            name
        )

        fallback_articles, fallback_error = gdelt_search(
            fallback,
            max_records=20,
            timespan="72h"
        )

        if fallback_articles:
            commodity_articles = (
                fallback_articles
            )
            error = None
        elif fallback_error:
            error = fallback_error

    # --------------------------------------------------------
    # Deduplica
    # --------------------------------------------------------

    merged = {}

    for article in commodity_articles:

        key = (
            article.get("url")
            or article.get("title")
            or ""
        )

        if key:
            merged[key] = article

    commodity_articles = list(
        merged.values()
    )

    # --------------------------------------------------------
    # Sentiment commodity
    # --------------------------------------------------------

    scores = []

    positive_count = 0
    negative_count = 0

    for article in commodity_articles:

        title = (
            article.get("title")
            or ""
        )

        description = (
            article.get("description")
            or article.get("snippet")
            or ""
        )

        tone = article.get(
            "tone"
        )

        sentiment = article_sentiment(
            name,
            title,
            description,
            tone
        )

        scores.append(
            sentiment
        )

        if sentiment > 0.15:
            positive_count += 1

        elif sentiment < -0.15:
            negative_count += 1

    commodity_score = mean(
        scores
    )

    # --------------------------------------------------------
    # Macro news
    # --------------------------------------------------------

    macro_scores = []

    for article in macro_articles:

        title = (
            article.get("title")
            or ""
        )

        description = (
            article.get("description")
            or article.get("snippet")
            or ""
        )

        macro_score = (
            macro_sentiment_for_commodity(
                name,
                title,
                description
            )
        )

        if abs(macro_score) > 0:
            macro_scores.append(
                macro_score
            )

    macro_score = mean(
        macro_scores
    )

    # --------------------------------------------------------
    # Score finale news
    # --------------------------------------------------------

    if scores:

        if macro_scores:

            final_score = (
                commodity_score * 0.75
                + macro_score * 0.25
            )

        else:

            final_score = commodity_score

    else:

        final_score = macro_score

    if final_score > 0.15:
        label = "POSITIVE"

    elif final_score < -0.15:
        label = "NEGATIVE"

    else:
        label = "NEUTRALE"

    # --------------------------------------------------------
    # Ultima notizia
    # --------------------------------------------------------

    headline = ""

    source = ""

    if commodity_articles:

        first = commodity_articles[0]

        headline = (
            first.get("title")
            or ""
        )

        source = (
            first.get("domain")
            or ""
        )

        if not source:

            url = first.get(
                "url",
                ""
            )

            match = re.search(
                r"https?://([^/]+)",
                url
            )

            if match:
                source = match.group(1)

    status = "OK"

    if (
        not commodity_articles
        and not macro_scores
    ):

        if error:
            status = "ERRORE"
        else:
            status = "NESSUNA"

    return {
        "label": label,
        "score": final_score,
        "positive": positive_count,
        "negative": negative_count,
        "count": len(commodity_articles),
        "headline": headline,
        "source": source,
        "status": status,
        "error": error,
    }


# ============================================================
# ANALISI PRINCIPALE
# ============================================================

def analyze(
    candles,
    dataset,
    model,
    bt,
    usd,
    news,
    timeframes
):

    closes = [
        c["close"]
        for c in candles
    ]

    current_price = closes[-1]

    current_features = build_features(
        candles
    )

    current_scaled = scale_current(
        dataset,
        current_features
    )

    probability = predict(
        model,
        current_scaled
    )

    model_signal = "NEUTRALE"

    if probability >= LONG_THRESHOLD:
        model_signal = "LONG"

    elif probability <= SHORT_THRESHOLD:
        model_signal = "SHORT"

    # --------------------------------------------------------
    # Timeframe score
    # --------------------------------------------------------

    tf_score = 0

    for value in timeframes.values():

        direction = value["direction"]

        if direction == "LONG":
            tf_score += 1

        elif direction == "SHORT":
            tf_score -= 1

    # --------------------------------------------------------
    # Fast timeframe
    # --------------------------------------------------------

    fast_score = (
        timeframes["5m"]["score"]
        + timeframes["1m"]["score"]
    )

    fast_conflict = (
        timeframes["5m"]["direction"]
        not in ("NONE", "LONG")
        and timeframes["1m"]["direction"]
        == "LONG"
    ) or (
        timeframes["5m"]["direction"]
        not in ("NONE", "SHORT")
        and timeframes["1m"]["direction"]
        == "SHORT"
    )

    # --------------------------------------------------------
    # Historical
    # --------------------------------------------------------

    repetition = historical_repetition(
        candles
    )

    # --------------------------------------------------------
    # News
    # --------------------------------------------------------

    news_score = news["score"]

    # --------------------------------------------------------
    # USD
    # --------------------------------------------------------

    usd_score = usd["score"]

    # --------------------------------------------------------
    # Probability score
    # --------------------------------------------------------

    probability_score = (
        probability * 100
    )

    # --------------------------------------------------------
    # Direction score
    # --------------------------------------------------------

    direction_score = (
        50
        + tf_score * 7
        + fast_score * 3
        + usd_score * 4
        + news_score * 10
        + repetition["score"] * 5
    )

    direction_score = clamp(
        direction_score,
        0,
        100
    )

    # --------------------------------------------------------
    # Final score
    # --------------------------------------------------------

    final_score = (
        probability_score * 0.45
        + direction_score * 0.55
    )

    final_score = clamp(
        final_score,
        0,
        100
    )

    # --------------------------------------------------------
    # Direction
    # --------------------------------------------------------

    if final_score >= 62:

        signal = "LONG"

    elif final_score <= 38:

        signal = "SHORT"

    else:

        signal = "NEUTRALE"

    # --------------------------------------------------------
    # Confidence
    # --------------------------------------------------------

    confidence = (
        abs(final_score - 50)
        * 2
    )

    confidence = clamp(
        confidence,
        0,
        100
    )

    # --------------------------------------------------------
    # Quality
    # --------------------------------------------------------

    vol = volatility(
        closes
    )

    quality = quality_score(
        probability,
        bt,
        vol
    )

    # --------------------------------------------------------
    # ATR
    # --------------------------------------------------------

    atr_value = atr(
        candles
    )

    stop_loss = None
    tp1 = None
    tp2 = None

    if atr_value:

        if signal == "LONG":

            stop_loss = (
                current_price
                - atr_value * STOP_ATR
            )

            tp1 = (
                current_price
                + atr_value * TP1_ATR
            )

            tp2 = (
                current_price
                + atr_value * TP2_ATR
            )

        elif signal == "SHORT":

            stop_loss = (
                current_price
                + atr_value * STOP_ATR
            )

            tp1 = (
                current_price
                - atr_value * TP1_ATR
            )

            tp2 = (
                current_price
                - atr_value * TP2_ATR
            )

    # --------------------------------------------------------
    # Grade
    # --------------------------------------------------------

    if final_score >= 75:
        grade = "A"

    elif final_score >= 65:
        grade = "B"

    elif final_score >= 55:
        grade = "C"

    else:
        grade = "D"

    # --------------------------------------------------------
    # Operational signal
    # --------------------------------------------------------

    operational_signal = signal

    if (
        quality < MIN_QUALITY
        or confidence < MIN_CONFIDENCE
        or final_score < MIN_SCORE
        or fast_conflict
    ):

        operational_signal = (
            "NO TRADE"
        )

    return {
        "price": current_price,
        "probability": probability,
        "signal": signal,
        "operational_signal": operational_signal,
        "score": final_score,
        "confidence": confidence,
        "quality": quality,
        "grade": grade,
        "atr": atr_value,
        "sl": stop_loss,
        "tp1": tp1,
        "tp2": tp2,
        "timeframes": timeframes,
        "repetition": repetition,
        "fast_conflict": fast_conflict,
    }


# ============================================================
# POSITION MANAGEMENT
# ============================================================

def manage_position(
    position,
    result
):

    if not position:
        return None

    price = result["price"]

    direction = position.get(
        "direction"
    )

    sl = position.get(
        "sl"
    )

    tp1 = position.get(
        "tp1"
    )

    tp2 = position.get(
        "tp2"
    )

    if direction == "LONG":

        if sl and price <= sl:
            return "STOP"

        if tp2 and price >= tp2:
            return "TP2"

        if (
            tp1
            and price >= tp1
            and not position.get(
                "tp1_hit"
            )
        ):
            position["tp1_hit"] = True

            # Trailing stop
            position["sl"] = (
                position["entry"]
            )

            return "TP1"

    elif direction == "SHORT":

        if sl and price >= sl:
            return "STOP"

        if tp2 and price <= tp2:
            return "TP2"

        if (
            tp1
            and price <= tp1
            and not position.get(
                "tp1_hit"
            )
        ):
            position["tp1_hit"] = True

            position["sl"] = (
                position["entry"]
            )

            return "TP1"

    return None


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(message):

    if not TELEGRAM_BOT_TOKEN:
        print(
            "TELEGRAM_BOT_TOKEN non configurato."
        )
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

        response = requests.post(
            url,
            json=payload,
            timeout=30
        )

        response.raise_for_status()

    except Exception as error:

        print(
            f"Telegram error: {error}"
        )


def icon_for_signal(signal):

    if signal == "LONG":
        return "🟢"

    if signal == "SHORT":
        return "🔴"

    if signal == "NO TRADE":
        return "🟡"

    return "⚪"


def compact_tf(timeframes):

    values = []

    for key in [
        "4H",
        "1H",
        "15m",
        "5m",
        "1m"
    ]:

        values.append(
            f"{key} "
            f"{timeframes[key]['direction']}"
        )

    return " | ".join(values)


def confirmation_text(result):

    if result["operational_signal"] == "LONG":

        return (
            "👉 Setup LONG sufficientemente forte."
        )

    if result["operational_signal"] == "SHORT":

        return (
            "👉 Setup SHORT sufficientemente forte."
        )

    return (
        "👉 Nessun setup principale "
        "sufficientemente forte."
    )


def build_telegram(
    ranked,
    best,
    usd
):

    signal = best["result"][
        "operational_signal"
    ]

    icon = icon_for_signal(
        signal
    )

    result = best["result"]
    news = best["news"]

    repetition = result[
        "repetition"
    ]

    timeframes = result[
        "timeframes"
    ]

    message = (
        "🌍 COMMODITIES BOT\n\n"
        "🏆 MIGLIOR SETUP\n"
        f"{icon} {best['name']}\n"
        f"🎯 {signal} | "
        f"Score: {result['score']:.0f}/100\n"
        f"📊 Qualità: "
        f"{result['quality']:.0f}/100\n\n"
        f"💰 Prezzo: "
        f"{result['price']:.4f}\n"
        f"🧠 Modello: "
        f"{result['probability'] * 100:.1f}%\n"
        f"📈 {compact_tf(timeframes)}\n"
        f"{confirmation_text(result)}\n\n"
        f"📰 News: "
        f"{news['label']} "
        f"({news['count']})\n"
        f"🟢 News positive: "
        f"{news['positive']}\n"
        f"🔴 News negative: "
        f"{news['negative']}\n"
    )

    if news.get("headline"):

        headline = (
            news["headline"]
            .replace("\n", " ")
            .strip()
        )

        if len(headline) > 180:
            headline = (
                headline[:177]
                + "..."
            )

        message += (
            f"🗞️ {headline}\n"
        )

        if news.get("source"):

            message += (
                f"🌐 Fonte: "
                f"{news['source']}\n"
            )

    if news.get("status") == "ERRORE":

        message += (
            "\n⚠️ Errore web:\n"
            f"{news.get('error') or 'GDELT errore sconosciuto'}\n"
        )

    message += (
        f"\n💵 Dollaro: "
        f"{'FORTE / SFAVOREVOLE' if usd['direction'] == 'LONG' else 'DEBOLE / FAVOREVOLE' if usd['direction'] == 'SHORT' else 'NEUTRALE'}\n"
        f"🔄 Storico: "
        f"{repetition['direction']} "
        f"({repetition['frequency'] * 100:.0f}% "
        f"su {repetition['samples']} casi)\n"
    )

    if signal == "NO TRADE" or signal == "NEUTRALE":

        message += (
            "\n🟡 NESSUNA ENTRATA.\n"
        )

    else:

        message += (
            "\n🚨 SETUP OPERATIVO.\n"
        )

        if result["sl"] is not None:

            message += (
                f"🛡️ SL: "
                f"{result['sl']:.4f}\n"
            )

        if result["tp1"] is not None:

            message += (
                f"🎯 TP1: "
                f"{result['tp1']:.4f}\n"
            )

        if result["tp2"] is not None:

            message += (
                f"🎯 TP2: "
                f"{result['tp2']:.4f}\n"
            )

    message += (
        f"\n👉 FOCUS: {best['name']}\n\n"
        "🌐 News analizzate dal web "
        "nelle ultime 72h.\n\n"
        "⚠️ Segnale algoritmico, "
        "non garanzia di profitto."
    )

    return message


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "===================================="
    )

    print(
        "COMMODITY BOT v6.1"
    )

    print(
        "Avvio..."
    )

    print(
        "===================================="
    )

    position = load_position()

    usd = analyze_usd()

    print(
        f"USD: {usd}"
    )

    # --------------------------------------------------------
    # NEWS MACRO UNA SOLA VOLTA
    # --------------------------------------------------------

    macro_articles, macro_error = (
        get_macro_news()
    )

    if macro_articles:

        print(
            f"Macro news: "
            f"{len(macro_articles)}"
        )

    else:

        print(
            f"Macro news non disponibili: "
            f"{macro_error}"
        )

    ranked = []

    # --------------------------------------------------------
    # ANALISI COMMODITIES
    # --------------------------------------------------------

    for name, symbol in COMMODITIES.items():

        print(
            f"\nAnalizzo {name} "
            f"({symbol})..."
        )

        try:

            candles = get_daily_data(
                symbol
            )

            if len(candles) < 150:

                print(
                    f"{name}: "
                    "dati insufficienti"
                )

                continue

            dataset = build_dataset(
                candles
            )

            if len(dataset) < 100:

                print(
                    f"{name}: "
                    "dataset insufficiente"
                )

                continue

            bt = backtest(
                dataset
            )

            model, _ = train_final(
                dataset
            )

            if model is None:

                print(
                    f"{name}: "
                    "modello non disponibile"
                )

                continue

            current_features = (
                build_features(
                    candles
                )
            )

            current_scaled = scale_current(
                dataset,
                current_features
            )

            # MTF
            timeframes = (
                get_multitimeframe(
                    symbol
                )
            )

            # NEWS
            news = analyze_news(
                name,
                macro_articles
            )

            result = analyze(
                candles,
                dataset,
                model,
                bt,
                usd,
                news,
                timeframes
            )

            ranked.append({
                "name": name,
                "symbol": symbol,
                "result": result,
                "news": news,
                "backtest": bt,
            })

            print(
                f"{name}: "
                f"{result['operational_signal']} "
                f"score={result['score']:.1f} "
                f"news={news['label']}"
            )

        except Exception as error:

            print(
                f"❌ {name}: {error}"
            )

            continue

    # --------------------------------------------------------
    # NESSUN RISULTATO
    # --------------------------------------------------------

    if not ranked:

        message = (
            "🌍 COMMODITIES BOT\n\n"
            "⚠️ Nessuna commodity "
            "analizzabile in questo ciclo.\n\n"
            "Controllare i simboli "
            "Twelve Data e i dati disponibili.\n\n"
            "⚠️ Segnale algoritmico, "
            "non garanzia di profitto."
        )

        send_telegram(
            message
        )

        print(message)

        return

    # --------------------------------------------------------
    # RANKING
    # --------------------------------------------------------

    ranked.sort(
        key=lambda x: x["result"]["score"],
        reverse=True
    )

    best = ranked[0]

    # --------------------------------------------------------
    # POSITION MANAGEMENT
    # --------------------------------------------------------

    if position:

        position_result = manage_position(
            position,
            best["result"]
        )

        if position_result:

            print(
                f"POSITION EVENT: "
                f"{position_result}"
            )

            if position_result in (
                "STOP",
                "TP2"
            ):

                clear_position()

                position = None

            else:

                save_position(
                    position
                )

    # --------------------------------------------------------
    # NUOVA POSIZIONE SIMULATA
    # --------------------------------------------------------

    if position is None:

        best_result = best["result"]

        eligible = (
            best_result[
                "operational_signal"
            ]
            in (
                "LONG",
                "SHORT"
            )
            and best_result["score"]
            >= MIN_SCORE
            and best_result["quality"]
            >= MIN_QUALITY
            and best_result["confidence"]
            >= MIN_CONFIDENCE
            and not best_result[
                "fast_conflict"
            ]
        )

        if len(ranked) >= 2:

            margin = (
                ranked[0]["result"]["score"]
                - ranked[1]["result"]["score"]
            )

        else:

            margin = 999

        eligible = (
            eligible
            and margin >= MIN_RANK_MARGIN
        )

        if eligible:

            direction = (
                best_result[
                    "operational_signal"
                ]
            )

            new_position = {
                "commodity": best["name"],
                "symbol": best["symbol"],
                "direction": direction,
                "entry": best_result["price"],
                "sl": best_result["sl"],
                "tp1": best_result["tp1"],
                "tp2": best_result["tp2"],
                "tp1_hit": False,
                "opened_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

            save_position(
                new_position
            )

            print(
                "NUOVA POSIZIONE SIMULATA:",
                new_position
            )

    # --------------------------------------------------------
    # TELEGRAM
    # --------------------------------------------------------

    message = build_telegram(
        ranked,
        best,
        usd
    )

    send_telegram(
        message
    )

    # --------------------------------------------------------
    # CONSOLE RANKING
    # --------------------------------------------------------

    print(
        "\n===================================="
    )

    print(
        "RANKING COMMODITIES"
    )

    print(
        "===================================="
    )

    for index, item in enumerate(
        ranked,
        start=1
    ):

        result = item["result"]

        print(
            f"{index}. "
            f"{item['name']} | "
            f"{result['operational_signal']} | "
            f"score={result['score']:.1f} | "
            f"news={item['news']['label']}"
        )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()