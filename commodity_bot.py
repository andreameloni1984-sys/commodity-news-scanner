# ============================================================
# CORREZIONE DATA ENGINE v4.1
# Sostituisce twelve_price() e twelve_series()
# ============================================================

def twelve_request(endpoint, params):
    """
    Richiesta Twelve Data con diagnostica esplicita.
    Non nasconde gli errori API.
    """
    if not TWELVE_KEY:
        print("Twelve Data: API key assente")
        return None

    try:
        url = f"https://api.twelvedata.com/{endpoint}"

        response = requests.get(
            url,
            params=params,
            timeout=int(
                os.getenv(
                    "TWELVE_DATA_TIMEOUT_SECONDS",
                    "20"
                )
            )
        )

        if response.status_code != 200:
            print(
                f"Twelve Data HTTP {response.status_code}: "
                f"{response.text[:500]}"
            )
            return None

        data = response.json()

        if data.get("status") == "error":
            print(
                "Twelve Data API error:",
                data.get("code"),
                data.get("message")
            )
            return None

        return data

    except requests.RequestException as exc:
        print("Twelve Data connection error:", repr(exc))
        return None

    except Exception as exc:
        print("Twelve Data unexpected error:", repr(exc))
        return None


def twelve_price(symbol):
    data = twelve_request(
        "price",
        {
            "symbol": symbol,
            "apikey": TWELVE_KEY
        }
    )

    if not data:
        return None

    return safe_float(data.get("price"))


def twelve_series(symbol, interval="15min", outputsize=100):
    data = twelve_request(
        "time_series",
        {
            "symbol": symbol,
            "interval": interval,
            "outputsize": outputsize,
            "apikey": TWELVE_KEY
        }
    )

    if not data:
        return []

    rows = data.get("values", [])

    values = []

    for row in rows:
        close = safe_float(row.get("close"))

        if close is not None:
            values.append(close)

    return list(reversed(values))


def resolve_twelve_symbol(symbol, name):
    """
    Prova prima il simbolo configurato.
    Se non è accettato, interroga /commodities per cercare
    una corrispondenza reale senza inventare simboli.
    """

    price = twelve_price(symbol)

    if price is not None:
        return symbol

    print(
        f"{name}: simbolo {symbol} non disponibile, "
        "cerco nella lista commodity Twelve Data..."
    )

    data = twelve_request(
        "commodities",
        {
            "apikey": TWELVE_KEY
        }
    )

    if not data:
        return None

    candidates = []

    if isinstance(data, dict):
        candidates = (
            data.get("data")
            or data.get("commodities")
            or data.get("values")
            or []
        )

    target = name.lower()

    for item in candidates:

        if not isinstance(item, dict):
            continue

        item_name = str(
            item.get("name")
            or item.get("commodity")
            or item.get("symbol")
            or ""
        )

        item_symbol = str(
            item.get("symbol")
            or item.get("code")
            or ""
        )

        combined = (
            item_name + " " + item_symbol
        ).lower()

        if target in combined:
            print(
                f"{name}: trovato simbolo Twelve Data "
                f"{item_symbol}"
            )
            return item_symbol

    return None
