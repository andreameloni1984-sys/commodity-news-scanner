import os
import json
import math
from datetime import datetime, timezone

import requests


# ============================================================
# COMMODITY TRADING BOT v4.1
# QUANT MODEL + POSITION MANAGEMENT
# ============================================================

API_KEY = os.getenv("TWELVE_DATA_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "TWELVE_DATA_API_KEY non configurata nei GitHub Secrets."
    )

BASE_URL = "https://api.twelvedata.com/time_series"

POSITION_FILE = "position.json"

HISTORY_SIZE = 4000
HORIZON = 5

STOP_ATR = 1.5
TP1_ATR = 1.5
TP2_ATR = 2.5

LONG_THRESHOLD = 0.62
SHORT_THRESHOLD = 0.38

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
# UTILITIES
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

    if not values:
        return 0.0

    return sum(values) / len(values)


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

        if not data:
            return None

        return data

    except Exception as error:

        print(
            f"⚠️ Impossibile leggere {POSITION_FILE}: "
            f"{error}"
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
# MARKET DATA
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

    values = data.get(
        "values",
        []
    )

    if not values:
        raise RuntimeError(
            f"Nessun dato disponibile per {symbol}"
        )

    candles = []

    for item in values:

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


# ============================================================
# INDICATORS
# ============================================================

def sma(values, period):

    if len(values) < period:
        return None

    return mean(
        values[-period:]
    )


def ema(values, period):

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

        true_range = max(
            high - low,
            abs(high - previous),
            abs(low - previous)
        )

        ranges.append(
            true_range
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


def return_pct(values, period):

    if len(values) <= period:
        return 0.0

    old = values[-period - 1]
    current = values[-1]

    if old == 0:
        return 0.0

    return (
        current / old
    ) - 1


def volatility(values, period=20):

    if len(values) < period + 1:
        return 0.0

    returns = []

    start = len(values) - period

    for i in range(
        start,
        len(values)
    ):

        if i <= 0:
            continue

        previous = values[i - 1]

        if previous == 0:
            continue

        returns.append(
            (values[i] / previous) - 1
        )

    return std(returns)


def pressure(candles, period=10):

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

    distance = (
        highest - lowest
    )

    if distance == 0:
        return 0.0

    return (
        (
            current - lowest
        ) / distance
    ) * 2 - 1


def seasonality(candles):

    if len(candles) < 300:
        return 0.0

    try:
        current_month = int(
            candles[-1]["datetime"]
            .split("-")[1]
        )
    except Exception:
        return 0.0

    returns = []

    for i in range(
        100,
        len(candles) - 5
    ):

        try:
            month = int(
                candles[i]["datetime"]
                .split("-")[1]
            )
        except Exception:
            continue

        if month != current_month:
            continue

        current = candles[i]["close"]
        future = candles[i + 5]["close"]

        if current == 0:
            continue

        returns.append(
            (future / current) - 1
        )

    if len(returns) < 5:
        return 0.0

    return mean(returns)


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

    sma20 = sma(
        closes,
        20
    )

    sma50 = sma(
        closes,
        50
    )

    if sma20 is None:
        sma20 = current

    if sma50 is None:
        sma50 = current

    if sma50 != 0:

        trend = (
            sma20 / sma50
        ) - 1

    else:
        trend = 0.0

    current_atr = atr(
        candles,
        14
    )

    if current_atr is None:
        atr_pct = 0.0
    else:
        atr_pct = (
            current_atr
            / current
        )

    current_macd = macd(
        closes
    )

    if current != 0:
        macd_normalized = (
            current_macd
            / current
        )
    else:
        macd_normalized = 0.0

    return [
        return_pct(
            closes,
            1
        ),

        return_pct(
            closes,
            5
        ),

        return_pct(
            closes,
            20
        ),

        return_pct(
            closes,
            60
        ),

        trend,

        (
            rsi(
                closes,
                14
            ) - 50
        ) / 50,

        macd_normalized,

        atr_pct,

        volatility(
            closes,
            20
        ),

        pressure(
            candles,
            10
        ),

        breakout(
            closes,
            20
        ),

        seasonality(
            candles
        ),
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

        if current == 0:
            continue

        future_return = (
            future / current
        ) - 1

        # Ignora movimenti troppo piccoli.
        if abs(future_return) < 0.002:
            continue

        label = (
            1
            if future_return > 0
            else 0
        )

        dataset.append({
            "x": features,
            "y": label,
            "return": future_return
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

        result = []

        for j in range(count):

            result.append(
                (
                    row[j]
                    - means[j]
                )
                / deviations[j]
            )

        return result

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
        deviations
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
        for _ in range(
            feature_count
        )
    ]

    bias = 0.0

    n = len(X)

    for _ in range(epochs):

        gradients = [
            0.0
            for _ in range(
                feature_count
            )
        ]

        bias_gradient = 0.0

        for row, target in zip(
            X,
            y
        ):

            z = bias

            for j in range(
                feature_count
            ):

                z += (
                    weights[j]
                    * row[j]
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

    z = bias

    for i in range(
        len(weights)
    ):

        z += (
            weights[i]
            * row[i]
        )

    return sigmoid(z)


# ============================================================
# WALK FORWARD BACKTEST
# ============================================================

def backtest(dataset):

    if len(dataset) < 500:

        return {
            "accuracy": 0,
            "win_rate": 0,
            "profit_factor": 0,
            "drawdown": 0,
            "trades": 0
        }

    split = int(
        len(dataset)
        * 0.70
    )

    test = dataset[
        split:
    ]

    predictions = []

    train_size = 1000

    step = 20

    for start in range(
        0,
        len(test),
        step
    ):

        end = split + start

        training_start = max(
            0,
            end - train_size
        )

        training = dataset[
            training_start:end
        ]

        testing = test[
            start:start + step
        ]

        if len(training) < 300:
            continue

        X_train = [
            x["x"]
            for x in training
        ]

        y_train = [
            x["y"]
            for x in training
        ]

        X_test = [
            x["x"]
            for x in testing
        ]

        (
            X_train_scaled,
            X_test_scaled,
            _,
            _
        ) = standardize(
            X_train,
            X_test
        )

        weights, bias = fit_model(
            X_train_scaled,
            y_train
        )

        for item, row in zip(
            testing,
            X_test_scaled
        ):

            probability = predict(
                row,
                weights,
                bias
            )

            predictions.append({
                "probability": probability,
                "return": item["return"],
                "actual": item["y"]
            })

    if not predictions:

        return {
            "accuracy": 0,
            "win_rate": 0,
            "profit_factor": 0,
            "drawdown": 0,
            "trades": 0
        }

    correct = 0

    trades = []

    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0

    for item in predictions:

        p = item["probability"]

        predicted = (
            1
            if p >= 0.50
            else 0
        )

        if predicted == item["actual"]:
            correct += 1

        if p >= LONG_THRESHOLD:

            trade_return = (
                item["return"]
            )

        elif p <= SHORT_THRESHOLD:

            trade_return = (
                -item["return"]
            )

        else:

            continue

        trades.append(
            trade_return
        )

        equity *= (
            1 + trade_return
        )

        peak = max(
            peak,
            equity
        )

        drawdown = (
            equity / peak
        ) - 1

        max_drawdown = min(
            max_drawdown,
            drawdown
        )

    accuracy = (
        correct
        / len(predictions)
    )

    if trades:

        winners = [
            x for x in trades
            if x > 0
        ]

        losers = [
            x for x in trades
            if x < 0
        ]

        win_rate = (
            len(winners)
            / len(trades)
        )

        gross_profit = sum(
            winners
        )

        gross_loss = abs(
            sum(losers)
        )

        if gross_loss > 0:

            profit_factor = (
                gross_profit
                / gross_loss
            )

        else:

            profit_factor = 99

    else:

        win_rate = 0
        profit_factor = 0

    return {
        "accuracy": accuracy,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "drawdown": max_drawdown,
        "trades": len(trades)
    }


# ============================================================
# FINAL MODEL
# ============================================================

def train_final(dataset):

    if len(dataset) < 300:
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
        deviations
    ) = standardize(
        X,
        X[-1:]
    )

    weights, bias = fit_model(
        X_scaled,
        y,
        epochs=900,
        learning_rate=0.03,
        regularization=0.10
    )

    return {
        "weights": weights,
        "bias": bias,
        "means": means,
        "deviations": deviations
    }


def scale_current(
    features,
    model
):

    result = []

    for i, value in enumerate(
        features
    ):

        deviation = (
            model["deviations"][i]
        )

        if deviation == 0:
            deviation = 1

        result.append(
            (
                value
                - model["means"][i]
            )
            / deviation
        )

    return result


# ============================================================
# MODEL QUALITY
# ============================================================

def quality_score(bt):

    score = 50

    score += (
        bt["accuracy"]
        - 0.50
    ) * 100

    score += (
        bt["win_rate"]
        - 0.50
    ) * 70

    if bt["profit_factor"] > 1:

        score += (
            bt["profit_factor"]
            - 1
        ) * 12

    score -= (
        abs(bt["drawdown"])
        * 40
    )

    return clamp(
        score,
        0,
        100
    )


# ============================================================
# SIGNAL
# ============================================================

def analyze(
    candles,
    dataset,
    model,
    bt
):

    features = build_features(
        candles
    )

    if features is None:
        return None

    scaled = scale_current(
        features,
        model
    )

    probability = predict(
        scaled,
        model["weights"],
        model["bias"]
    )

    quality = quality_score(
        bt
    )

    strength = (
        abs(
            probability
            - 0.50
        )
        * 200
    )

    confidence = (
        strength * 0.60
        + quality * 0.40
    )

    if quality < 45:

        signal = "NO TRADE"

    elif probability >= LONG_THRESHOLD:

        signal = "LONG"

    elif probability <= SHORT_THRESHOLD:

        signal = "SHORT"

    else:

        signal = "WAIT"

    price = candles[-1]["close"]

    current_atr = atr(
        candles,
        14
    )

    if current_atr is None:

        current_atr = (
            price * 0.01
        )

    if signal == "LONG":

        stop = (
            price
            - current_atr
            * STOP_ATR
        )

        tp1 = (
            price
            + current_atr
            * TP1_ATR
        )

        tp2 = (
            price
            + current_atr
            * TP2_ATR
        )

    elif signal == "SHORT":

        stop = (
            price
            + current_atr
            * STOP_ATR
        )

        tp1 = (
            price
            - current_atr
            * TP1_ATR
        )

        tp2 = (
            price
            - current_atr
            * TP2_ATR
        )

    else:

        stop = None
        tp1 = None
        tp2 = None

    return {
        "signal": signal,
        "probability": probability,
        "confidence": confidence,
        "quality": quality,
        "price": price,
        "atr": current_atr,
        "stop": stop,
        "tp1": tp1,
        "tp2": tp2
    }


# ============================================================
# POSITION MANAGEMENT
# ============================================================

def manage_position(
    position,
    current_analysis,
    current_price
):

    direction = position["direction"]

    entry = position["entry"]

    stop = position["stop"]

    tp1 = position["tp1"]

    tp2 = position["tp2"]

    probability = (
        current_analysis["probability"]
    )

    signal = (
        current_analysis["signal"]
    )

    # --------------------------------------------------------
    # LONG
    # --------------------------------------------------------

    if direction == "LONG":

        if current_price <= stop:

            return {
                "action": "EXIT",
                "reason": "STOP LOSS",
                "new_stop": stop
            }

        if current_price >= tp2:

            return {
                "action": "EXIT",
                "reason": "TAKE PROFIT 2",
                "new_stop": stop
            }

        if (
            probability <= 0.38
            or signal == "SHORT"
        ):

            return {
                "action": "EXIT",
                "reason": "INVERSIONE CONFERMATA",
                "new_stop": stop
            }

        if probability < 0.48:

            return {
                "action": "WARNING",
                "reason": "LONG INDEBOLITO",
                "new_stop": stop
            }

        # Trailing stop dopo TP1
        if current_price >= tp1:

            atr_value = (
                current_analysis["atr"]
            )

            trailing_stop = (
                current_price
                - atr_value * 1.0
            )

            new_stop = max(
                stop,
                entry,
                trailing_stop
            )

            return {
                "action": "HOLD",
                "reason": "TP1 RAGGIUNTO - TRAILING STOP",
                "new_stop": new_stop
            }

        return {
            "action": "HOLD",
            "reason": "TREND LONG ANCORA VALIDO",
            "new_stop": stop
        }

    # --------------------------------------------------------
    # SHORT
    # --------------------------------------------------------

    if direction == "SHORT":

        if current_price >= stop:

            return {
                "action": "EXIT",
                "reason": "STOP LOSS",
                "new_stop": stop
            }

        if current_price <= tp2:

            return {
                "action": "EXIT",
                "reason": "TAKE PROFIT 2",
                "new_stop": stop
            }

        if (
            probability >= 0.62
            or signal == "LONG"
        ):

            return {
                "action": "EXIT",
                "reason": "INVERSIONE CONFERMATA",
                "new_stop": stop
            }

        if probability > 0.52:

            return {
                "action": "WARNING",
                "reason": "SHORT INDEBOLITO",
                "new_stop": stop
            }

        if current_price <= tp1:

            atr_value = (
                current_analysis["atr"]
            )

            trailing_stop = (
                current_price
                + atr_value
            )

            new_stop = min(
                stop,
                entry,
                trailing_stop
            )

            return {
                "action": "HOLD",
                "reason": "TP1 RAGGIUNTO - TRAILING STOP",
                "new_stop": new_stop
            }

        return {
            "action": "HOLD",
            "reason": "TREND SHORT ANCORA VALIDO",
            "new_stop": stop
        }

    return {
        "action": "EXIT",
        "reason": "DIREZIONE NON RICONOSCIUTA",
        "new_stop": stop
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("🧠 COMMODITY TRADING BOT v4.1")
    print("QUANT MODEL + POSITION MANAGEMENT")
    print("=" * 70)
    print()

    position = load_position()

    if position:

        print("📌 POSIZIONE MEMORIZZATA")
        print(
            f"Materia prima: "
            f"{position['name']}"
        )
        print(
            f"Direzione: "
            f"{position['direction']}"
        )
        print(
            f"Entrata: "
            f"{position['entry']}"
        )
        print()

    else:

        print(
            "📭 Nessuna posizione aperta."
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
                    "   ⚠️ Dati insufficienti"
                )

                continue

            dataset = build_dataset(
                candles
            )

            if len(dataset) < 300:

                print(
                    "   ⚠️ Dataset insufficiente"
                )

                continue

            bt = backtest(
                dataset
            )

            model = train_final(
                dataset
            )

            if model is None:
                continue

            analysis = analyze(
                candles,
                dataset,
                model,
                bt
            )

            if analysis is None:
                continue

            results.append({
                "name": name,
                "symbol": symbol,
                "candles": candles,
                "analysis": analysis,
                "backtest": bt
            })

            print(
                f"   → {analysis['signal']} | "
                f"{analysis['probability'] * 100:.1f}%"
            )

        except Exception as error:

            print(
                f"   ❌ {error}"
            )

    if not results:

        raise RuntimeError(
            "Nessuna materia prima analizzata."
        )

    # ========================================================
    # SE C'È UNA POSIZIONE
    # ========================================================

    if position:

        matching = [
            x for x in results
            if x["name"]
            == position["name"]
        ]

        if matching:

            current = matching[0]

            current_price = (
                current["analysis"]["price"]
            )

            management = manage_position(
                position,
                current["analysis"],
                current_price
            )

            print()
            print("=" * 70)
            print("📌 GESTIONE POSIZIONE")
            print("=" * 70)

            print(
                f"Materia prima: "
                f"{position['name']}"
            )

            print(
                f"Direzione: "
                f"{position['direction']}"
            )

            print(
                f"Entrata: "
                f"{position['entry']:.4f}"
            )

            print(
                f"Prezzo attuale: "
                f"{current_price:.4f}"
            )

            print(
                f"Probabilità modello: "
                f"{current['analysis']['probability'] * 100:.1f}%"
            )

            print()

            action = management["action"]

            if action == "EXIT":

                print(
                    "🚨 USCITA"
                )

                print(
                    f"Motivo: "
                    f"{management['reason']}"
                )

                clear_position()

                print(
                    "🗑️ Posizione rimossa dalla memoria."
                )

            elif action == "WARNING":

                print(
                    "🟠 ATTENZIONE"
                )

                print(
                    f"Motivo: "
                    f"{management['reason']}"
                )

                position["stop"] = (
                    management["new_stop"]
                )

                save_position(
                    position
                )

            else:

                print(
                    "🟢 MANTIENI"
                )

                print(
                    f"Motivo: "
                    f"{management['reason']}"
                )

                if (
                    management["new_stop"]
                    != position["stop"]
                ):

                    position["stop"] = (
                        management["new_stop"]
                    )

                    print(
                        f"🔒 Nuovo trailing stop: "
                        f"{position['stop']:.4f}"
                    )

                    save_position(
                        position
                    )

        else:

            print(
                "⚠️ Impossibile aggiornare "
                "la posizione."
            )

        return

    # ========================================================
    # NUOVA OPERAZIONE
    # ========================================================

    ranked = []

    for item in results:

        probability = (
            item["analysis"]["probability"]
        )

        quality = (
            item["analysis"]["quality"]
        )

        confidence = (
            item["analysis"]["confidence"]
        )

        if (
            probability >= 0.50
        ):

            direction_strength = (
                probability
            )

        else:

            direction_strength = (
                1 - probability
            )

        score = (
            direction_strength * 60
            + quality * 0.25
            + confidence * 0.15
        )

        if item["analysis"]["signal"] == "WAIT":
            score *= 0.70

        if item["analysis"]["signal"] == "NO TRADE":
            score = -1

        item["score"] = score

        ranked.append(item)

    ranked.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    best = ranked[0]

    analysis = best["analysis"]
    bt = best["backtest"]

    print()
    print("=" * 70)
    print("🏆 MIGLIORE OPPORTUNITÀ")
    print("=" * 70)

    print(
        f"Materia prima: "
        f"{best['name']}"
    )

    print(
        f"Segnale: "
        f"{analysis['signal']}"
    )

    print(
        f"Probabilità: "
        f"{analysis['probability'] * 100:.1f}%"
    )

    print(
        f"Confidenza: "
        f"{analysis['confidence']:.1f}/100"
    )

    print(
        f"Qualità modello: "
        f"{analysis['quality']:.1f}/100"
    )

    print()

    print(
        f"Win rate backtest: "
        f"{bt['win_rate'] * 100:.1f}%"
    )

    print(
        f"Profit factor: "
        f"{bt['profit_factor']:.2f}"
    )

    print(
        f"Max drawdown: "
        f"{bt['drawdown'] * 100:.2f}%"
    )

    # ========================================================
    # APRI POSIZIONE SOLO CON SEGNALE FORTE
    # ========================================================

    if analysis["signal"] in (
        "LONG",
        "SHORT"
    ):

        direction = (
            analysis["signal"]
        )

        position = {
            "name": best["name"],
            "symbol": best["symbol"],
            "direction": direction,
            "entry": analysis["price"],
            "stop": analysis["stop"],
            "tp1": analysis["tp1"],
            "tp2": analysis["tp2"],
            "opened_at": datetime.now(
                timezone.utc
            ).isoformat()
        }

        save_position(
            position
        )

        print()
        print("=" * 70)
        print("🚨 NUOVA POSIZIONE")
        print("=" * 70)

        print(
            f"Direzione: {direction}"
        )

        print(
            f"Entrata: "
            f"{analysis['price']:.4f}"
        )

        print(
            f"Stop Loss: "
            f"{analysis['stop']:.4f}"
        )

        print(
            f"Take Profit 1: "
            f"{analysis['tp1']:.4f}"
        )

        print(
            f"Take Profit 2: "
            f"{analysis['tp2']:.4f}"
        )

        print()
        print(
            "💾 Posizione salvata."
        )

    else:

        print()
        print(
            "🟡 NESSUNA ENTRATA."
        )

        print(
            "Il modello non vede "
            "un vantaggio sufficiente."
        )

    # ========================================================
    # RANKING
    # ========================================================

    print()
    print("=" * 70)
    print("📊 RANKING")
    print("=" * 70)

    for i, item in enumerate(
        ranked,
        1
    ):

        a = item["analysis"]

        if a["signal"] == "LONG":
            icon = "🟢"
        elif a["signal"] == "SHORT":
            icon = "🔴"
        elif a["signal"] == "WAIT":
            icon = "🟡"
        else:
            icon = "⚪"

        print(
            f"{i}. {icon} "
            f"{item['name']} | "
            f"{a['signal']} | "
            f"{a['probability'] * 100:.1f}%"
        )

    print()
    print("=" * 70)
    print(
        "⚠️ Analisi quantitativa, "
        "non garanzia di profitto."
    )
    print("=" * 70)


if __name__ == "__main__":
    main()