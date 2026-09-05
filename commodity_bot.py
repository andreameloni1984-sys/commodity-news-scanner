import os
import math
import statistics
from datetime import datetime, timezone

import requests


# ============================================================
# COMMODITY TRADING BOT v4
# Adaptive Quantitative Model
# ============================================================

API_KEY = os.getenv("TWELVE_DATA_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "TWELVE_DATA_API_KEY non configurata nei GitHub Secrets."
    )


BASE_URL = "https://api.twelvedata.com/time_series"

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

HISTORY_SIZE = 4000
HORIZON = 5

FEATURE_NAMES = [
    "ret_1",
    "ret_5",
    "ret_20",
    "ret_60",
    "trend_20_50",
    "rsi",
    "macd",
    "atr_pct",
    "volatility",
    "pressure",
    "breakout",
    "seasonality",
]


# ============================================================
# UTILITIES
# ============================================================

def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def mean(values):
    values = [v for v in values if v is not None and math.isfinite(v)]
    if not values:
        return 0.0
    return sum(values) / len(values)


def std(values):
    values = [v for v in values if v is not None and math.isfinite(v)]

    if len(values) < 2:
        return 1.0

    m = mean(values)
    variance = sum((x - m) ** 2 for x in values) / (len(values) - 1)

    return max(math.sqrt(variance), 1e-8)


def sigmoid(x):
    x = max(-30.0, min(30.0, x))
    return 1.0 / (1.0 + math.exp(-x))


def clamp(x, low, high):
    return max(low, min(high, x))


# ============================================================
# DATA
# ============================================================

def get_daily_data(symbol):
    params = {
        "symbol": symbol,
        "interval": "1day",
        "outputsize": HISTORY_SIZE,
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

    if "status" in data and data["status"] == "error":
        raise RuntimeError(
            data.get("message", "Errore Twelve Data")
        )

    values = data.get("values", [])

    if not values:
        raise RuntimeError(
            f"Nessun dato disponibile per {symbol}"
        )

    candles = []

    for item in reversed(values):
        close = safe_float(item.get("close"))
        high = safe_float(item.get("high"))
        low = safe_float(item.get("low"))
        volume = safe_float(item.get("volume"))

        if close is None:
            continue

        candles.append({
            "datetime": item.get("datetime"),
            "open": safe_float(item.get("open")),
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        })

    candles.sort(key=lambda x: x["datetime"] or "")

    return candles


# ============================================================
# TECHNICAL INDICATORS
# ============================================================

def sma(values, period):
    if len(values) < period:
        return None

    return mean(values[-period:])


def ema(values, period):
    if len(values) < period:
        return None

    multiplier = 2.0 / (period + 1)

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

        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))

    avg_gain = mean(gains[-period:])
    avg_loss = mean(losses[-period:])

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss

    return 100.0 - (100.0 / (1.0 + rs))


def atr(candles, period=14):
    if len(candles) < period + 1:
        return None

    true_ranges = []

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

        true_ranges.append(tr)

    if len(true_ranges) < period:
        return None

    return mean(true_ranges[-period:])


def macd(values):
    if len(values) < 35:
        return 0.0

    fast = ema(values, 12)
    slow = ema(values, 26)

    if fast is None or slow is None:
        return 0.0

    return fast - slow


# ============================================================
# FEATURE ENGINEERING
# ============================================================

def return_pct(values, period):
    if len(values) <= period:
        return 0.0

    old = values[-period - 1]
    current = values[-1]

    if old == 0:
        return 0.0

    return (current / old) - 1.0


def pressure_score(candles, period=10):
    selected = candles[-period:]

    scores = []

    for candle in selected:
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

        body = close - open_price
        range_size = high - low

        scores.append(body / range_size)

    return mean(scores)


def volatility(values, period=20):
    if len(values) < period + 1:
        return 0.0

    returns = []

    for i in range(len(values) - period, len(values)):
        if i <= 0:
            continue

        previous = values[i - 1]

        if previous == 0:
            continue

        returns.append(
            (values[i] / previous) - 1.0
        )

    return std(returns)


def breakout_score(values, period=20):
    if len(values) < period + 1:
        return 0.0

    current = values[-1]

    previous = values[-period - 1:-1]

    highest = max(previous)
    lowest = min(previous)

    distance = highest - lowest

    if distance <= 0:
        return 0.0

    return (
        (current - lowest) / distance
    ) * 2.0 - 1.0


def seasonality_score(candles):
    """
    Measures historical tendency of the current calendar month.

    Only previous years are used for the current month.
    """

    if len(candles) < 250:
        return 0.0

    latest_date = candles[-1]["datetime"]

    try:
        month = int(latest_date.split("-")[1])
    except Exception:
        return 0.0

    monthly_returns = []

    for i in range(20, len(candles) - 5):
        date_string = candles[i]["datetime"]

        try:
            candle_month = int(date_string.split("-")[1])
        except Exception:
            continue

        if candle_month != month:
            continue

        start = candles[i]["close"]
        future = candles[i + 5]["close"]

        if start == 0:
            continue

        monthly_returns.append(
            (future / start) - 1.0
        )

    if len(monthly_returns) < 5:
        return 0.0

    return mean(monthly_returns)


def build_features(candles):
    closes = [
        c["close"]
        for c in candles
        if c["close"] is not None
    ]

    if len(closes) < 100:
        return None

    current = closes[-1]

    sma20 = sma(closes, 20)
    sma50 = sma(closes, 50)

    if sma20 is None:
        sma20 = current

    if sma50 is None:
        sma50 = current

    trend = (
        (sma20 / sma50) - 1.0
        if sma50 != 0
        else 0.0
    )

    current_atr = atr(candles, 14)

    if current_atr is None:
        atr_pct = 0.0
    else:
        atr_pct = current_atr / current

    current_macd = macd(closes)

    if current != 0:
        normalized_macd = current_macd / current
    else:
        normalized_macd = 0.0

    return [
        return_pct(closes, 1),
        return_pct(closes, 5),
        return_pct(closes, 20),
        return_pct(closes, 60),
        trend,
        (rsi(closes, 14) - 50.0) / 50.0,
        normalized_macd,
        atr_pct,
        volatility(closes, 20),
        pressure_score(candles, 10),
        breakout_score(closes, 20),
        seasonality_score(candles),
    ]


# ============================================================
# DATASET
# ============================================================

def build_dataset(candles):
    """
    Creates historical observations.

    X(t) only uses information available at t.
    y(t) uses the following HORIZON days.

    This prevents look-ahead leakage.
    """

    dataset = []

    minimum_history = 100

    for i in range(
        minimum_history,
        len(candles) - HORIZON
    ):

        history = candles[:i + 1]

        features = build_features(history)

        if features is None:
            continue

        current = candles[i]["close"]
        future = candles[i + HORIZON]["close"]

        if current == 0:
            continue

        future_return = (
            future / current
        ) - 1.0

        # Ignore extremely small movements.
        # They contain little directional information.
        if abs(future_return) < 0.002:
            continue

        label = 1 if future_return > 0 else 0

        dataset.append({
            "x": features,
            "y": label,
            "future_return": future_return,
        })

    return dataset


# ============================================================
# STANDARDIZATION
# ============================================================

def standardize_train_test(train_x, test_x):
    if not train_x:
        return [], []

    columns = len(train_x[0])

    means = []
    stds = []

    for j in range(columns):
        values = [
            row[j]
            for row in train_x
            if row[j] is not None
        ]

        m = mean(values)
        s = std(values)

        means.append(m)
        stds.append(s)

    def transform(row):
        result = []

        for j in range(columns):
            value = row[j]

            if value is None:
                value = means[j]

            result.append(
                (value - means[j]) / stds[j]
            )

        return result

    return (
        [transform(row) for row in train_x],
        [transform(row) for row in test_x],
        means,
        stds,
    )


# ============================================================
# LOGISTIC REGRESSION
# ============================================================

def fit_logistic(
    X,
    y,
    epochs=700,
    learning_rate=0.035,
    regularization=0.08,
):
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

            z = bias

            for j in range(feature_count):
                z += weights[j] * row[j]

            prediction = sigmoid(z)

            error = prediction - target

            bias_gradient += error

            for j in range(feature_count):
                gradients[j] += error * row[j]

        bias -= learning_rate * (
            bias_gradient / n
        )

        for j in range(feature_count):

            gradient = (
                gradients[j] / n
            )

            gradient += (
                regularization * weights[j]
            )

            weights[j] -= (
                learning_rate * gradient
            )

    return weights, bias


def predict_probability(
    row,
    weights,
    bias,
):
    z = bias

    for i in range(len(weights)):
        z += weights[i] * row[i]

    return sigmoid(z)


# ============================================================
# WALK-FORWARD BACKTEST
# ============================================================

def walk_forward_backtest(dataset):

    if len(dataset) < 500:
        return {
            "accuracy": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "trades": 0,
        }

    # Reserve the most recent 30% as out-of-sample.
    split = int(len(dataset) * 0.70)

    train_initial = dataset[:split]
    test_period = dataset[split:]

    predictions = []

    train_size = max(
        350,
        min(1000, len(train_initial))
    )

    step = 20

    for start in range(
        0,
        len(test_period),
        step
    ):

        training_start = max(
            0,
            split + start - train_size
        )

        training_end = split + start

        train = dataset[
            training_start:training_end
        ]

        test = test_period[
            start:start + step
        ]

        if len(train) < 250:
            continue

        X_train = [
            item["x"]
            for item in train
        ]

        y_train = [
            item["y"]
            for item in train
        ]

        X_test = [
            item["x"]
            for item in test
        ]

        (
            X_train_scaled,
            X_test_scaled,
            _,
            _,
        ) = standardize_train_test(
            X_train,
            X_test,
        )

        weights, bias = fit_logistic(
            X_train_scaled,
            y_train,
        )

        for item, row in zip(
            test,
            X_test_scaled,
        ):

            probability = predict_probability(
                row,
                weights,
                bias,
            )

            predictions.append({
                "probability": probability,
                "actual": item["y"],
                "return": item["future_return"],
            })

    if not predictions:
        return {
            "accuracy": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "trades": 0,
        }

    directional_correct = 0

    trades = []

    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0

    for prediction in predictions:

        probability = prediction["probability"]

        if probability >= 0.60:

            direction = 1

        elif probability <= 0.40:

            direction = -1

        else:

            continue

        actual_return = prediction["return"]

        trade_return = (
            actual_return
            if direction == 1
            else -actual_return
        )

        trades.append(trade_return)

        if (
            (direction == 1 and actual_return > 0)
            or
            (direction == -1 and actual_return < 0)
        ):
            directional_correct += 1

        equity *= (1.0 + trade_return)

        peak = max(peak, equity)

        drawdown = (
            equity / peak
        ) - 1.0

        max_drawdown = min(
            max_drawdown,
            drawdown,
        )

    total_predictions = len(predictions)

    accuracy = (
        sum(
            1
            for p in predictions
            if (
                (p["probability"] >= 0.5 and p["actual"] == 1)
                or
                (p["probability"] < 0.5 and p["actual"] == 0)
            )
        )
        / total_predictions
    )

    if trades:
        winning = [
            x for x in trades
            if x > 0
        ]

        losing = [
            x for x in trades
            if x < 0
        ]

        win_rate = (
            len(winning) / len(trades)
        )

        gross_profit = sum(winning)
        gross_loss = abs(sum(losing))

        if gross_loss > 0:
            profit_factor = (
                gross_profit / gross_loss
            )
        else:
            profit_factor = 99.0

    else:
        win_rate = 0.0
        profit_factor = 0.0

    return {
        "accuracy": accuracy,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "max_drawdown": max_drawdown,
        "trades": len(trades),
    }


# ============================================================
# FINAL MODEL
# ============================================================

def train_final_model(dataset):

    if len(dataset) < 250:
        return None

    X = [
        item["x"]
        for item in dataset
    ]

    y = [
        item["y"]
        for item in dataset
    ]

    (
        X_scaled,
        _,
        means,
        stds,
    ) = standardize_train_test(
        X,
        X[-1:],
    )

    weights, bias = fit_logistic(
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
        "stds": stds,
    }


def scale_features(features, model):

    result = []

    for i, value in enumerate(features):

        s = model["stds"][i]

        if s == 0:
            s = 1.0

        result.append(
            (value - model["means"][i]) / s
        )

    return result


# ============================================================
# MODEL QUALITY
# ============================================================

def model_quality(backtest):

    score = 50.0

    accuracy = backtest["accuracy"]
    win_rate = backtest["win_rate"]
    profit_factor = backtest["profit_factor"]
    drawdown = abs(backtest["max_drawdown"])

    score += (
        accuracy - 0.50
    ) * 100

    score += (
        win_rate - 0.50
    ) * 70

    if profit_factor > 1:
        score += (
            profit_factor - 1
        ) * 12

    score -= drawdown * 40

    return clamp(
        score,
        0,
        100,
    )


# ============================================================
# CURRENT SIGNAL
# ============================================================

def generate_signal(
    candles,
    dataset,
    model,
    backtest,
):

    features = build_features(candles)

    if features is None or model is None:
        return None

    scaled = scale_features(
        features,
        model,
    )

    probability = predict_probability(
        scaled,
        model["weights"],
        model["bias"],
    )

    quality = model_quality(
        backtest
    )

    # Model confidence combines:
    # probability distance from 50%
    # and historical robustness.
    directional_strength = (
        abs(probability - 0.50) * 200
    )

    confidence = (
        directional_strength * 0.60
        + quality * 0.40
    )

    # Weak model = no trade.
    if quality < 45:
        signal = "NO TRADE"
    elif probability >= 0.62:
        signal = "LONG"
    elif probability <= 0.38:
        signal = "SHORT"
    else:
        signal = "WAIT"

    current_price = candles[-1]["close"]

    current_atr = atr(
        candles,
        14,
    )

    if current_atr is None:
        current_atr = current_price * 0.01

    if signal == "LONG":

        entry = current_price
        stop = entry - (
            current_atr * 1.5
        )

        tp1 = entry + (
            current_atr * 1.5
        )

        tp2 = entry + (
            current_atr * 2.5
        )

    elif signal == "SHORT":

        entry = current_price
        stop = entry + (
            current_atr * 1.5
        )

        tp1 = entry - (
            current_atr * 1.5
        )

        tp2 = entry - (
            current_atr * 2.5
        )

    else:

        entry = current_price
        stop = None
        tp1 = None
        tp2 = None

    return {
        "signal": signal,
        "probability": probability,
        "confidence": confidence,
        "quality": quality,
        "entry": entry,
        "stop": stop,
        "tp1": tp1,
        "tp2": tp2,
        "features": features,
    }


# ============================================================
# RANKING
# ============================================================

def opportunity_score(result):

    if result is None:
        return -999

    signal = result["signal"]

    if signal == "NO TRADE":
        return -100

    probability = result["probability"]

    directional_probability = max(
        probability,
        1.0 - probability,
    )

    score = (
        directional_probability * 65
        + result["quality"] * 0.25
        + result["confidence"] * 0.10
    )

    if signal == "WAIT":
        score *= 0.70

    return score


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("🧠 COMMODITY TRADING BOT v4")
    print("ADAPTIVE QUANTITATIVE MODEL")
    print("=" * 70)
    print()

    now = datetime.now(
        timezone.utc
    )

    print(
        f"🕐 Aggiornamento UTC: "
        f"{now.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    print(
        "📚 Modello: dati storici + "
        "walk-forward validation"
    )

    print(
        "🎯 Orizzonte previsione: "
        f"{HORIZON} giorni"
    )

    print()

    results = []

    for name, symbol in COMMODITIES.items():

        print(
            f"🔎 Analizzo {name}..."
        )

        try:

            candles = get_daily_data(
                symbol
            )

            if len(candles) < 500:

                print(
                    f"⚠️ {name}: "
                    "dati insufficienti"
                )

                continue

            dataset = build_dataset(
                candles
            )

            if len(dataset) < 300:

                print(
                    f"⚠️ {name}: "
                    "dataset insufficiente"
                )

                continue

            backtest = walk_forward_backtest(
                dataset
            )

            model = train_final_model(
                dataset
            )

            signal = generate_signal(
                candles,
                dataset,
                model,
                backtest,
            )

            if signal is None:
                continue

            item = {
                "name": name,
                "symbol": symbol,
                "candles": candles,
                "dataset": dataset,
                "backtest": backtest,
                "signal": signal,
            }

            item["score"] = (
                opportunity_score(signal)
            )

            results.append(item)

            print(
                f"   → {signal['signal']} | "
                f"Probabilità: "
                f"{signal['probability'] * 100:.1f}% | "
                f"Qualità modello: "
                f"{signal['quality']:.1f}/100"
            )

        except Exception as error:

            print(
                f"❌ Errore {name}: {error}"
            )

    if not results:

        raise RuntimeError(
            "Nessuna materia prima analizzata correttamente."
        )

    results.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    # ========================================================
    # REPORT
    # ========================================================

    print()
    print("=" * 70)
    print("📊 RANKING DELLE MATERIE PRIME")
    print("=" * 70)

    for index, item in enumerate(
        results,
        start=1,
    ):

        signal = item["signal"]
        backtest = item["backtest"]

        probability = (
            signal["probability"] * 100
        )

        if signal["signal"] == "LONG":
            icon = "🟢"
        elif signal["signal"] == "SHORT":
            icon = "🔴"
        elif signal["signal"] == "WAIT":
            icon = "🟡"
        else:
            icon = "⚪"

        print(
            f"{index}. {icon} "
            f"{item['name']:<18} "
            f"{signal['signal']:<9} "
            f"Prob {probability:5.1f}% | "
            f"Conf {signal['confidence']:5.1f} | "
            f"BT {backtest['win_rate'] * 100:5.1f}%"
        )

    # ========================================================
    # BEST OPPORTUNITY
    # ========================================================

    best = results[0]

    signal = best["signal"]
    backtest = best["backtest"]

    print()
    print("=" * 70)
    print("🏆 MIGLIORE OPPORTUNITÀ")
    print("=" * 70)

    print(
        f"Materia prima: {best['name']}"
    )

    print(
        f"Simbolo: {best['symbol']}"
    )

    print(
        f"Segnale: {signal['signal']}"
    )

    print(
        f"Probabilità LONG: "
        f"{signal['probability'] * 100:.1f}%"
    )

    print(
        f"Confidenza modello: "
        f"{signal['confidence']:.1f}/100"
    )

    print(
        f"Qualità modello: "
        f"{signal['quality']:.1f}/100"
    )

    print()

    print("📈 BACKTEST OUT-OF-SAMPLE")

    print(
        f"Accuratezza: "
        f"{backtest['accuracy'] * 100:.1f}%"
    )

    print(
        f"Win rate: "
        f"{backtest['win_rate'] * 100:.1f}%"
    )

    print(
        f"Profit factor: "
        f"{backtest['profit_factor']:.2f}"
    )

    print(
        f"Max drawdown: "
        f"{backtest['max_drawdown'] * 100:.2f}%"
    )

    print(
        f"Trade simulati: "
        f"{backtest['trades']}"
    )

    print()

    print("💰 LIVELLI")

    print(
        f"Prezzo: "
        f"{signal['entry']:.4f}"
    )

    if signal["stop"] is not None:

        print(
            f"Stop Loss: "
            f"{signal['stop']:.4f}"
        )

        print(
            f"Take Profit 1: "
            f"{signal['tp1']:.4f}"
        )

        print(
            f"Take Profit 2: "
            f"{signal['tp2']:.4f}"
        )

    print()
    print("=" * 70)
    print("⚠️ Il segnale è un'analisi quantitativa, non una garanzia.")
    print("=" * 70)


if __name__ == "__main__":
    main()