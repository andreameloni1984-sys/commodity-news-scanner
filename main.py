"""
SOYUZ GAGARIN — MAIN RUNNER v2.1

Entry point operativo del progetto.

Pipeline unica:
    UNIVERSE
        ↓
    GAGARIN ENGINE
        ↓
    SAFETY
        ↓
    TELEGRAM

IMPORTANTE:
- main.py NON contiene self-test.
- main.py NON crea una seconda decision authority.
- La decisione ENTRY/WAIT resta in engine/gagarin.py + engine/safety.py.
- PAPER ONLY: nessun ordine viene eseguito.
- Telegram gestisce autonomamente il proprio esito di invio.
"""

from __future__ import annotations

from datetime import datetime, timezone

from commodities.universe import (
    enabled_commodities,
    validate_universe,
)

from config import (
    PAPER_TRADING_ONLY,
    TELEGRAM_ENABLED,
)

from engine.gagarin import analyze_universe

from telegram.bot import (
    format_report,
    send_telegram,
)


# ============================================================
# HEADER
# ============================================================

def _print_header():

    print()

    print("=" * 72)
    print("🚀 SOYUZ GAGARIN")
    print("=" * 72)

    print(
        "DATA → REGIME → STRUCTURE → SETUP → "
        "TRIGGER → RISK → SAFETY"
    )

    if PAPER_TRADING_ONLY:
        print("MODE: PAPER ONLY")
    else:
        print("MODE: UNSAFE CONFIGURATION")

    print(
        "UTC:",
        datetime.now(
            timezone.utc
        ).isoformat(),
    )

    print()


# ============================================================
# CONFIGURATION VALIDATION
# ============================================================

def _validate():

    errors = validate_universe()

    if not PAPER_TRADING_ONLY:
        errors.append(
            "PAPER_TRADING_ONLY_MUST_BE_TRUE"
        )

    return errors


# ============================================================
# DATA SUMMARY
# ============================================================

def _print_data_summary(results):

    print("📡 DATA / ENGINE")
    print("-" * 72)

    for state in results:

        if state.data_age_seconds is not None:

            age = (
                f"{state.data_age_seconds:.1f}s"
            )

        else:

            age = "N/A"

        status = state.metadata.get(
            "data_status",
            "UNKNOWN",
        )

        provider = (
            state.data_source
            if state.data_source
            else "N/A"
        )

        print(
            f"{state.commodity:<18} "
            f"{status:<7} "
            f"age={age:<9} "
            f"provider={provider}"
        )

    print()


# ============================================================
# GAGARIN RANKING
# ============================================================

def _print_ranking(results):

    print("📊 CLASSIFICA GAGARIN")
    print("-" * 72)

    if not results:

        print("Nessun risultato.")
        print()

        return

    for index, state in enumerate(
        results,
        start=1,
    ):

        if state.setup_direction in {
            "LONG",
            "SHORT",
        }:

            direction = (
                state.setup_direction
            )

        else:

            direction = "—"

        print(
            f"{index:>2}. "
            f"{state.commodity:<18} "
            f"{direction:<5} "
            f"Prob {state.probability:>5.1f} "
            f"Q {state.quality:>5.1f} "
            f"C {state.confidence:>5.1f} "
            f"{state.final_decision}"
        )

    print()


# ============================================================
# OPERATIONAL RESULTS
# ============================================================

def _print_operational(results):

    entries = [
        state
        for state in results
        if state.final_decision == "ENTRY"
    ]

    print("🎯 OPERATIVITÀ")
    print("-" * 72)

    if not entries:

        print(
            "🟡 NESSUNA ENTRATA AUTORIZZATA"
        )

        print()

        return

    print(
        f"🟢 {len(entries)} "
        "ENTRATA/E AUTORIZZATA/E"
    )

    # Mostriamo al massimo le prime 3,
    # coerentemente con il report Telegram.

    for state in entries[:3]:

        print()

        print(
            f"🟢 {state.commodity} "
            f"{state.setup_direction}"
        )

        print(
            f"Prob:       "
            f"{state.probability:.1f}%"
        )

        print(
            f"Quality:    "
            f"{state.quality:.1f}"
        )

        print(
            f"Confidence: "
            f"{state.confidence:.1f}"
        )

        if state.entry is not None:

            print(
                f"Entry:      "
                f"{state.entry:.6g}"
            )

        if state.stop is not None:

            print(
                f"SL:         "
                f"{state.stop:.6g}"
            )

        if state.tp1 is not None:

            print(
                f"TP1:        "
                f"{state.tp1:.6g}"
            )

        if state.tp2 is not None:

            print(
                f"TP2:        "
                f"{state.tp2:.6g}"
            )

        if state.tp3 is not None:

            print(
                f"TP3:        "
                f"{state.tp3:.6g}"
            )

        if state.rr3 is not None:

            print(
                f"RR3:        "
                f"{state.rr3:.2f}"
            )

        if state.stop_atr is not None:

            print(
                f"SL ATR:     "
                f"{state.stop_atr:.2f}"
            )

    print()


# ============================================================
# MAIN RUNNER
# ============================================================

def run():

    # --------------------------------------------------------
    # 1. HEADER
    # --------------------------------------------------------

    _print_header()

    # --------------------------------------------------------
    # 2. CONFIGURATION
    # --------------------------------------------------------

    errors = _validate()

    if errors:

        print(
            "❌ CONFIGURAZIONE BLOCCATA"
        )

        for error in errors:

            print(
                f" - {error}"
            )

        return 1

    # --------------------------------------------------------
    # 3. UNIVERSE
    # --------------------------------------------------------

    commodities = (
        enabled_commodities()
    )

    if not commodities:

        print(
            "❌ Nessuna commodity abilitata."
        )

        return 1

    print(
        f"Universe: "
        f"{len(commodities)} "
        "commodity abilitate"
    )

    print()

    # --------------------------------------------------------
    # 4. GAGARIN ENGINE
    # --------------------------------------------------------

    try:

        results = analyze_universe(
            commodities
        )

    except Exception as exc:

        print()
        print(
            "❌ GAGARIN ENGINE ERROR"
        )

        print(
            f"{type(exc).__name__}: "
            f"{exc}"
        )

        return 1

    # --------------------------------------------------------
    # 5. DATA STATUS
    # --------------------------------------------------------

    _print_data_summary(
        results
    )

    # --------------------------------------------------------
    # 6. RANKING
    # --------------------------------------------------------

    _print_ranking(
        results
    )

    # --------------------------------------------------------
    # 7. OPERATIONAL GATE
    # --------------------------------------------------------

    _print_operational(
        results
    )

    # --------------------------------------------------------
    # 8. TELEGRAM
    # --------------------------------------------------------

    report = format_report(
        results
    )

    if TELEGRAM_ENABLED:

        print(
            "📨 TELEGRAM"
        )

        # send_telegram() stampa già
        # Telegram API: OK / FAILED.
        #
        # Non lo ristampiamo qui per
        # evitare il doppio messaggio.

        send_telegram(
            report
        )

    else:

        print(
            "📨 TELEGRAM: DISABLED"
        )

    # --------------------------------------------------------
    # 9. COMPLETED
    # --------------------------------------------------------

    print()

    print("=" * 72)
    print(
        "✅ SOYUZ GAGARIN RUN COMPLETED"
    )
    print("=" * 72)

    return 0


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    raise SystemExit(
        run()
    )