"""
SOYUZ GAGARIN — MAIN RUNNER v2.3

Pipeline:
    UNIVERSE
        ↓
    GAGARIN ENGINE
        ↓
    SAFETY
        ↓
    PAPER JOURNAL
        ↓
    FEEDBACK
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
from engine.session_filter import filter_by_session

from paper_trade_journal import (
    record_entries,
)

from engine.feedback import (
    record_entries as record_feedback_entries,
    summarize as summarize_feedback,
    format_summary as format_feedback_summary,
    update_open_outcomes,
)

from telegram.bot import send_telegram
from telegram.signals import format_signal_board, format_watch_board
from soyuz_gagarin.adapter import evaluate_states
from execution.router import execute_state


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
        "TRIGGER → RISK → SAFETY → FEEDBACK"
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
            f"{status:<14} "
            f"age={age:<10} "
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

        print(
            "Nessun risultato."
        )

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
                + ", ".join(
                    state.blockers
                )
            )

    print()


# ============================================================
# OPERATIONAL SECTION
# ============================================================

def _print_operational(results):

    entries = [
        state
        for state in results
        if str(
            (getattr(state, "metadata", {}) or {}).get(
                "gagarin_action", ""
            )
        ).upper() in {"PAPER_ENTRY", "PAPER_SIGNAL"}
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

        recorded = record_entries(
            results
        )

        print(
            f"Recorded entries: "
            f"{recorded}"
        )

        if recorded:

            for state in results:

                if str(
                    (getattr(state, "metadata", {}) or {}).get(
                        "gagarin_action", ""
                    )
                ).upper() in {"PAPER_ENTRY", "PAPER_SIGNAL"}:

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
            f"{type(exc).__name__}: "
            f"{exc}"
        )

    print()


# ============================================================
# FEEDBACK ENGINE
# ============================================================

def _print_feedback(results):

    print("🧪 SOYUZ FEEDBACK")
    print("-" * 72)

    try:

        updated = update_open_outcomes(results)

        recorded = record_feedback_entries(
            results
        )

        summary = summarize_feedback()

        print(
            f"Updated open outcomes: {updated}"
        )

        print(
            f"New feedback signals: "
            f"{recorded}"
        )

        print(
            format_feedback_summary(
                summary
            )
        )

    except Exception as exc:

        print(
            "⚠️ FEEDBACK ERROR"
        )

        print(
            f"{type(exc).__name__}: "
            f"{exc}"
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

    ALLOWED = {
        "XAU/USD", "XAG/USD", "COPPER/USD",
        "WTI/USD", "BRENT/USD",
        "WHEAT/USD", "CORN/USD", "SOYBEAN/USD",
        "EUR/USD", "GBP/USD",
    }
    commodities = [
        c for c in filter_by_session(enabled_commodities(), on_demand=False)
        if str(getattr(c, "symbol", "")).upper() in ALLOWED
    ]

    print(
        "SESSION FILTER: orari esatti per i 10 strumenti (Europe/Rome). "
        "Run manuali/on-demand bypassano il filtro."
    )

    if not commodities:

        print(
            "⏭️ SKIP: nessuna commodity prevista nella finestra oraria corrente."
        )
        print(
            "Run pianificato completato senza analisi; non è un errore del motore."
        )

        return 0

    print(
        f"Universe: "
        f"{len(commodities)} commodity abilitate (filtrate per orario)"
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
            f"{type(exc).__name__}: "
            f"{exc}"
        )

        return 1

    # --------------------------------------------------------
    # CANONICAL GAGARIN GOVERNOR
    # --------------------------------------------------------

    decisions = evaluate_states(results)
    decisions_by_symbol = {
        decision.symbol: decision
        for decision in decisions
    }
    for state in results:
        decision = decisions_by_symbol.get(
            str(getattr(state, "symbol", "")).upper()
        )
        metadata = getattr(state, "metadata", None)
        if not isinstance(metadata, dict):
            metadata = {}
            state.metadata = metadata
        metadata["gagarin_action"] = (
            decision.action if decision is not None else "WAIT"
        )
        metadata["gagarin_reason"] = (
            decision.reason if decision is not None else "NO_DECISION"
        )

    # --------------------------------------------------------
    # EXECUTION LAYER
    # --------------------------------------------------------
    print("EXECUTION LAYER")
    print("-" * 72)
    execution_results = []
    for state in results:
        try:
            result = execute_state(state)
            execution_results.append(result)
            if result.accepted:
                print("  " + result.mode + ": " + result.symbol + " -> " + result.order_id)
        except Exception as exc:
            print("  EXECUTION ERROR " + str(getattr(state, "symbol", "")) + ": " + type(exc).__name__ + ": " + str(exc))
    if not execution_results:
        print("  No execution decisions.")
    print()

    # --------------------------------------------------------
    # REPORT
    # --------------------------------------------------------

    _print_data_summary(
        results
    )

    _print_ranking(
        results
    )

    _print_operational(
        results
    )

    # --------------------------------------------------------
    # PAPER JOURNAL
    # --------------------------------------------------------

    _print_paper_journal(
        results
    )

    # --------------------------------------------------------
    # FEEDBACK
    # --------------------------------------------------------

    _print_feedback(
        results
    )

    # --------------------------------------------------------
    # TELEGRAM
    # --------------------------------------------------------

    approved_symbols = {
        decision.symbol
        for decision in decisions
        if decision.action == "PAPER_SIGNAL"
    }

    signal_results = [
        state
        for state in results
        if (
            (
                str(getattr(state, "symbol", "")).upper() in approved_symbols
                or str((getattr(state, "metadata", {}) or {}).get("gagarin_action", "")).upper() in {"PAPER_ENTRY", "PAPER_SIGNAL"}
            )
            and str(getattr(state, "setup_direction", "")).upper() in {"LONG", "SHORT"}
        )
    ]

    if TELEGRAM_ENABLED:

        print("📨 TELEGRAM")

        try:

            if signal_results:
                delivered = send_telegram(
                    format_signal_board(signal_results)
                )
                if not delivered:
                    print("❌ TELEGRAM DELIVERY FAILED: signal message was not accepted by Telegram.")
                    return 1
                print(
                    f"📡 SIGNAL CHANNEL: Telegram accepted {len(signal_results)} signal(s)"
                )
            else:
                # Send WATCH pre-alert for near-threshold setups
                watch_msg = format_watch_board(results, min_score=40.0)
                if "Nessun setup vicino" not in watch_msg:
                    delivered = send_telegram(watch_msg)
                    if not delivered:
                        print("❌ TELEGRAM DELIVERY FAILED: WATCH message was not accepted by Telegram.")
                        return 1
                    print("🟡 WATCH pre-alert accepted by Telegram")
                else:
                    print("No signals and no watch candidates")

        except Exception as exc:

            print(
                "⚠️ TELEGRAM ERROR"
            )

            print(
                f"{type(exc).__name__}: "
                f"{exc}"
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

    raise SystemExit(
        run()
    )
