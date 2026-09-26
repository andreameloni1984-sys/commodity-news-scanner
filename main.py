"""
SOYUZ GAGARIN — MAIN RUNNER v2.2

Pipeline:
    UNIVERSE
        ↓
    GAGARIN ENGINE
        ↓
    SAFETY
        ↓
    PAPER JOURNAL
        ↓
    TELEGRAM

PAPER ONLY:
nessun ordine reale viene eseguito.
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

from paper_trade_journal import (
    record_entries,
)

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
        datetime.now(timezone.utc).isoformat(),
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
            age = f"{state.data_age_seconds:.1f}s"
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

        direction = (
            state.setup_direction
            if state.setup_direction
            in {"LONG", "SHORT"}
            else "—"
        )

        print(
            f"{index:>2}. "
            f"{state.commodity:<18} "
            f"{direction:<5} "
            f"Prob {state.probability:>5.1f} "
            f"Q {state.quality:>5.1f} "
            f"C {state.confidence:>5.1f} "
            f"{state.final_decision}"
        )

        if (
            state.final_decision != "ENTRY"
            and state.blockers
        ):
            print(
                "    └─ BLOCK: "
                + ", ".join(state.blockers)
            )

    print()


# ============================================================
# OPERATIONAL SECTION
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
        f"🟢 {len(entries)} ENTRATA/E "
        f"AUTORIZZATA/E"
    )

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
# PAPER TRADE JOURNAL
# ============================================================

def _print_paper_journal(results):

    print("🧪 PAPER JOURNAL")
    print("-" * 72)

    try:

        recorded = record_entries(results)

        print(
            f"Recorded entries: {recorded}"
        )

        if recorded:

            for state in results:

                if (
                    state.final_decision
                    == "ENTRY"
                ):

                    print(
                        f"  • "
                        f"{state.commodity} "
                        f"{state.setup_direction} "
                        f"Entry={state.entry} "
                        f"SL={state.stop} "
                        f"TP3={state.tp3}"
                    )

    except Exception as exc:

        print(
            "⚠️ PAPER JOURNAL ERROR"
        )

        print(
            f"{type(exc).__name__}: {exc}"
        )

    print()


# ============================================================
# MAIN RUN
# ============================================================

def run():

    _print_header()

    # --------------------------------------------------------
    # CONFIGURATION
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
    # UNIVERSE
    # --------------------------------------------------------

    commodities = enabled_commodities()

    if not commodities:

        print(
            "❌ Nessuna commodity abilitata."
        )

        return 1

    print(
        f"Universe: "
        f"{len(commodities)} commodity abilitate"
    )

    print()

    # --------------------------------------------------------
    # GAGARIN ENGINE
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
            f"{type(exc).__name__}: {exc}"
        )

        return 1

    # --------------------------------------------------------
    # REPORT
    # --------------------------------------------------------

    _print_data_summary(results)

    _print_ranking(results)

    _print_operational(results)

    # --------------------------------------------------------
    # PAPER JOURNAL
    # --------------------------------------------------------

    _print_paper_journal(results)

    # --------------------------------------------------------
    # TELEGRAM
    # --------------------------------------------------------

    report = format_report(results)

    if TELEGRAM_ENABLED:

        print("📨 TELEGRAM")

        try:

            send_telegram(report)

        except Exception as exc:

            print(
                "⚠️ TELEGRAM ERROR"
            )

            print(
                f"{type(exc).__name__}: {exc}"
            )

    else:

        print(
            "📨 TELEGRAM: DISABLED"
        )

    # --------------------------------------------------------
    # COMPLETED
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
    raise SystemExit(run())