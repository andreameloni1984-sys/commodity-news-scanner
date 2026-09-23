# ============================================================
# SOYUZ GAGARIN v1.4
# COMMODITY UNIVERSE
# ============================================================
#
# Universo operativo principale.
#
# IMPORTANTE:
# I simboli qui sotto sono IDENTIFICATORI LOGICI.
# Non assumiamo che siano tutti disponibili sul piano
# Twelve Data corrente.
#
# La disponibilità reale viene verificata dal DATA ENGINE.
#
# ============================================================

from dataclasses import dataclass


# ============================================================
# COMMODITY
# ============================================================


@dataclass(frozen=True)
class Commodity:
    """
    Definizione canonica di una commodity.

    name:
        Nome utilizzato nei report Telegram.

    symbol:
        Identificatore primario richiesto al data adapter.

    category:
        Categoria della commodity.

    unit:
        Valuta/unità di riferimento.

    priority:
        Priorità interna dell'universo.
        Non è un punteggio di trading.

    enabled:
        Se False, la commodity non viene analizzata.
    """

    name: str
    symbol: str
    category: str
    unit: str = "USD"
    priority: int = 1
    enabled: bool = True


# ============================================================
# MAIN UNIVERSE
# ============================================================
#
# Manteniamo il paniere che abbiamo deciso per SOYUZ:
#
# METALLI
#   Oro
#   Argento
#   Platino
#   Palladio
#
# ENERGY
#   WTI
#   Brent
#
# AGRICOLTURA / FOOD
#   Riso
#   Zucchero
#   Cacao
#   Caffè
#
# ============================================================


COMMODITIES = [

    # --------------------------------------------------------
    # METALS
    # --------------------------------------------------------

    Commodity(
        name="Oro",
        symbol="XAU/USD",
        category="Metal",
        unit="USD",
        priority=1,
    ),

    Commodity(
        name="Argento",
        symbol="XAG/USD",
        category="Metal",
        unit="USD",
        priority=2,
    ),

    Commodity(
        name="Platino",
        symbol="XPT/USD",
        category="Metal",
        unit="USD",
        priority=3,
    ),

    Commodity(
        name="Palladio",
        symbol="XPD/USD",
        category="Metal",
        unit="USD",
        priority=4,
    ),

    # --------------------------------------------------------
    # ENERGY
    # --------------------------------------------------------

    Commodity(
        name="Petrolio WTI",
        symbol="WTI/USD",
        category="Energy",
        unit="USD",
        priority=5,
    ),

    Commodity(
        name="Petrolio Brent",
        symbol="BRENT/USD",
        category="Energy",
        unit="USD",
        priority=6,
    ),

    # --------------------------------------------------------
    # AGRICULTURE / FOOD
    # --------------------------------------------------------

    Commodity(
        name="Riso",
        symbol="RICE/USD",
        category="Agriculture",
        unit="USD",
        priority=7,
    ),

    Commodity(
        name="Zucchero",
        symbol="SUGAR/USD",
        category="Agriculture",
        unit="USD",
        priority=8,
    ),

    Commodity(
        name="Cacao",
        symbol="COCOA/USD",
        category="Agriculture",
        unit="USD",
        priority=9,
    ),

    Commodity(
        name="Caffè",
        symbol="COFFEE/USD",
        category="Agriculture",
        unit="USD",
        priority=10,
    ),
]


# ============================================================
# HELPERS
# ============================================================


def enabled_commodities() -> list[Commodity]:
    """
    Restituisce solamente le commodity abilitate.
    """

    return [
        commodity
        for commodity in COMMODITIES
        if commodity.enabled
    ]


def get_commodity_by_name(
    name: str,
) -> Commodity | None:
    """
    Cerca una commodity per nome.
    """

    normalized = (
        name.strip().lower()
        if name
        else ""
    )

    for commodity in COMMODITIES:

        if (
            commodity.name.lower()
            == normalized
        ):
            return commodity

    return None


def get_commodity_by_symbol(
    symbol: str,
) -> Commodity | None:
    """
    Cerca una commodity per simbolo.
    """

    normalized = (
        symbol.strip().upper()
        if symbol
        else ""
    )

    for commodity in COMMODITIES:

        if (
            commodity.symbol.upper()
            == normalized
        ):
            return commodity

    return None


def get_categories() -> list[str]:
    """
    Restituisce le categorie presenti
    nell'universo senza duplicati.
    """

    categories = []

    for commodity in COMMODITIES:

        if commodity.category not in categories:
            categories.append(
                commodity.category
            )

    return categories


def get_symbols() -> list[str]:
    """
    Restituisce tutti i simboli dell'universo.
    """

    return [
        commodity.symbol
        for commodity in enabled_commodities()
    ]


def universe_size() -> int:
    """
    Numero di commodity abilitate.
    """

    return len(
        enabled_commodities()
    )


# ============================================================
# VALIDATION
# ============================================================


def validate_universe() -> list[str]:
    """
    Controlla la consistenza dell'universo.

    NON verifica la disponibilità presso
    Twelve Data.

    Restituisce una lista di errori.
    Lista vuota = configurazione interna coerente.
    """

    errors = []

    names = set()
    symbols = set()

    for commodity in COMMODITIES:

        # ----------------------------------------------------
        # NAME
        # ----------------------------------------------------

        if not commodity.name.strip():

            errors.append(
                "EMPTY_COMMODITY_NAME"
            )

        # ----------------------------------------------------
        # SYMBOL
        # ----------------------------------------------------

        if not commodity.symbol.strip():

            errors.append(
                f"EMPTY_SYMBOL:{commodity.name}"
            )

        # ----------------------------------------------------
        # DUPLICATE NAME
        # ----------------------------------------------------

        name_key = (
            commodity.name.strip().lower()
        )

        if name_key in names:

            errors.append(
                f"DUPLICATE_NAME:{commodity.name}"
            )

        names.add(name_key)

        # ----------------------------------------------------
        # DUPLICATE SYMBOL
        # ----------------------------------------------------

        symbol_key = (
            commodity.symbol.strip().upper()
        )

        if symbol_key in symbols:

            errors.append(
                f"DUPLICATE_SYMBOL:{commodity.symbol}"
            )

        symbols.add(symbol_key)

        # ----------------------------------------------------
        # CATEGORY
        # ----------------------------------------------------

        if not commodity.category.strip():

            errors.append(
                f"EMPTY_CATEGORY:{commodity.name}"
            )

    return errors


# ============================================================
# MODULE VALIDATION
# ============================================================


_UNIVERSE_ERRORS = validate_universe()

if _UNIVERSE_ERRORS:

    raise ValueError(
        "Invalid SOYUZ commodity universe: "
        + ", ".join(
            _UNIVERSE_ERRORS
        )
    )