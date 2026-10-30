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
    operational_commodities,
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
    record_forecasts as record_feedback_forecasts,
    summarize as summarize_feedback,
    format_summary as format_feedback_summary,
    update_open_outcomes,
)

from telegram.bot import send_telegram
from telegram.signals import format_signal_board, format_watch_board
from soyuz_gagarin.adapter import evaluate_states
from execution.router import execute_state


OPERATIONAL_SYMBOLS = frozenset(
    item.symbol.strip().upper()
    for item in operational_commodities()
)


def _is_operational_state(state) -> bool:
    return str(getattr(state, "symbol", "") or "").strip().upper() in OPERATIONAL_SYMBOLS


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

def _provider_error_label(error):

    value = str(error or "").upper()

    if not value:
        return "NO_DATA"

    if "429" in value or "RATE LIMIT" in value or "TOO MANY REQUEST" in value:
        return "RATE_LIMIT"

    if "401" in value or "403" in value or "INVALID API KEY" in value or "API KEY" in value:
        return "AUTH"

    if "TIMEOUT" in value or "TIMED OUT" in value:
        return "TIMEOUT"

    if "SYMBOL_NOT_FOUND" in value or "NOT_MAPPED" in value or "NOT FOUND" in value:
        return "SYMBOL_UNAVAILABLE"

    if "INSUFFICIENT_CANDLES" in value:
        return "INSUFFICIENT_CANDLES"

    if "STALE_DATA" in value:
        return "STALE"

    if any(token in value for token in ("NO_DATA", "NO_CANDLES", "NO_BARS", "EMPTY")):
        return "EMPTY_RESPONSE"

    if "HTTP" in value:
        return "HTTP_ERROR"

    return "PROVIDER_ERROR"


def _format_provider_attempts(attempts):

    if not isinstance(attempts, (list, tuple)):
        return ""

    details = []

    for attempt in attempts:
        if not isinstance(attempt, dict):
            continue

        provider = str(attempt.get("provider") or "UNKNOWN").strip().upper()
        freshness = str(attempt.get("freshness_status") or "").strip().upper()
        accepted = attempt.get("accepted_for_live") is True
        success = bool(attempt.get("success"))

        if freshness == "STALE":
            label = f"{provider}:STALE"
        elif accepted:
            label = f"{provider}:LIVE"
        elif not success:
            label = f"{provider}:{_provider_error_label(attempt.get('error'))}"
        else:
            label = f"{provider}:DATA"

        age = attempt.get("age_seconds")
        if isinstance(age, (int, float)) and not isinstance(age, bool):
            label += f"@{age:.0f}s"

        details.append(label)

    return " | ".join(details)


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

        metadata = getattr(state, "metadata", {}) or {}
        if not isinstance(metadata, dict):
            metadata = {}

        status = metadata.get(
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

        provider_checks = _format_provider_attempts(
            metadata.get("provider_attempts")
        )
        if provider_checks:
            print(f"    └─ PROVIDER CHECKS: {provider_checks}")

        fallback_reason = metadata.get("freshness_fallback_reason")
        if fallback_reason:
            print(f"    └─ FALLBACK REASON: {str(fallback_reason)[:80]}")

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

        action_label = (
            "CONTESTO FX — NON OPERATIVO"
            if not _is_operational_state(state)
            else str((getattr(state, "metadata", {}) or {}).get(
                "gagarin_action", state.final_decision
            ))
        )
        print(
            f"{index:>2}. "
            f"{state.commodity:<18} "
            f"{direction:<5} "
            f"Prob {state.probability:>5.1f} "
            f"Q {state.quality:>5.1f} "
            f"C {state.confidence:>5.1f} "
            f"{action_label}"
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

def _print_feedback(results, operational_results=None):

    print("🧪 SOYUZ FEEDBACK")
    print("-" * 72)

    try:

        operational_results = (
            list(operational_results)
            if operational_results is not None
            else list(results)
        )
        updated = update_open_outcomes(results)

        # Existing outcomes may still be updated for every tracked symbol,
        # but new forecasts and entries are restricted to the eight commodities.
        recorded = record_feedback_entries(
            operational_results
        )

        # Track valid live directional WATCH setups as forecasts too.
        # Approved entries are already recorded above and are deduplicated by
        # signal_id inside record_forecasts().
        recorded_forecasts = record_feedback_forecasts(
            operational_results
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
            f"New additional live forecasts (WATCH/other): "
            f"{recorded_forecasts}"
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
        return False

    print()
    return True


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

    instruments = filter_by_session(
        enabled_commodities(), on_demand=False
    )
    operational_instruments = [
        item for item in instruments
        if str(getattr(item, "symbol", "")).strip().upper() in OPERATIONAL_SYMBOLS
    ]
    auxiliary_instruments = [
        item for item in instruments
        if str(getattr(item, "symbol", "")).strip().upper() not in OPERATIONAL_SYMBOLS
    ]

    print(
        "SESSION FILTER: 8 commodities operative; EUR/USD e GBP/USD restano ausiliari "
        "e vengono analizzati nelle rispettive finestre (Europe/Rome)."
    )

    if not instruments:

        print(
            "⏭️ SKIP: nessuno strumento previsto nella finestra oraria corrente."
        )
        print(
            "Run pianificato completato senza analisi; non è un errore del motore."
        )

        return 0

    print(
        f"Universe: {len(instruments)} strumenti analizzati "
        f"({len(operational_instruments)} commodities operative, "
        f"{len(auxiliary_instruments)} Forex ausiliari in finestra)"
    )

    print()

    # --------------------------------------------------------
    # GAGARIN ENGINE
    # --------------------------------------------------------

    try:

        results = analyze_universe(
            instruments
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

    operational_results = [
        state for state in results if _is_operational_state(state)
    ]
    decisions = evaluate_states(operational_results)
    decisions_by_symbol = {
        decision.symbol: decision
        for decision in decisions
    }
    for state in results:
        symbol = str(getattr(state, "symbol", "")).strip().upper()
        decision = decisions_by_symbol.get(symbol)
        metadata = getattr(state, "metadata", None)
        if not isinstance(metadata, dict):
            metadata = {}
            state.metadata = metadata
        if not _is_operational_state(state):
            metadata["gagarin_action"] = "AUXILIARY_ONLY"
            metadata["gagarin_reason"] = "FOREX_CONTEXT_ONLY"
        else:
            metadata["gagarin_action"] = (
                decision.action if decision is not None else "WAIT"
            )
            metadata["gagarin_reason"] = (
                decision.reason if decision is not None else "NO_DECISION"
            )

    # --------------------------------------------------------
    # EXPLAINABLE ANALYST LAYER
    # --------------------------------------------------------
    from engine.analyst_reasoning import build_reasoning
    for state in results:
        decision = decisions_by_symbol.get(
            str(getattr(state, "symbol", "")).upper()
        )
        state.metadata["analyst_reasoning"] = build_reasoning(state, decision)

    # --------------------------------------------------------
    # EXECUTION LAYER
    # --------------------------------------------------------
    print("EXECUTION LAYER")
    print("-" * 72)
    execution_results = []
    for state in operational_results:
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
        operational_results
    )

    # --------------------------------------------------------
    # PAPER JOURNAL
    # --------------------------------------------------------

    _print_paper_journal(
        operational_results
    )

    # --------------------------------------------------------
    # FEEDBACK
    # --------------------------------------------------------

    feedback_ok = _print_feedback(
        results, operational_results
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
        for state in operational_results
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
                watch_msg = format_watch_board(operational_results, min_score=40.0)
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

    # A failed feedback write/summary must not leave a green monitor run.
    # Telegram processing above is still allowed; the workflow's always()
    # persistence step can then save any local CSV before the job fails.
    if not feedback_ok:
        print("❌ FEEDBACK INCOMPLETE: monitor run marked failed; journal must be checked.")
        return 1

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
