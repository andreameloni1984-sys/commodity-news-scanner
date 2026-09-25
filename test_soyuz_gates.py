"""
SOYUZ GAGARIN — INTEGRATION TEST v1.0

Testa insieme:
1. data_freshness.py
2. ranking_gate.py
3. gagarin_gate.py

NON modifica il bot.
NON invia Telegram.
NON esegue ordini.
"""

from datetime import datetime, timezone

from data_freshness import operational_data_gate
from ranking_gate import evaluate_candidate
from gagarin_gate import evaluate


def now_ts():
    return datetime.now(timezone.utc).timestamp()


def print_header(title):
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def test_freshness():

    print_header("TEST 1 — DATA FRESHNESS")

    now = now_ts()

    tests = [
        ("M5", now - 30),
        ("M5", now - 180),
        ("M15", now - 180),
        ("H1", now - 600),
    ]

    for timeframe, timestamp in tests:

        result = operational_data_gate(
            timestamp=timestamp,
            timeframe=timeframe,
            now_timestamp=now,
        )

        age = (
            f"{result.age_seconds:.1f}s"
            if result.age_seconds is not None
            else "N/A"
        )

        print(
            f"{timeframe:>4} | "
            f"{result.status:<7} | "
            f"AGE={age:<8} | "
            f"{result.reason}"
        )


def test_ranking():

    print_header("TEST 2 — RANKING GATE")

    candidates = [

        {
            "symbol": "COCOA",
            "direction": "SHORT",
            "probability": 63,
            "quality": 51,
            "confidence": 55,
            "rr": 0,
            "data_status": "STALE",
            "setup_valid": False,
            "trigger_confirmed": False,
            "entry_present": False,
            "stop_present": False,
            "tp_present": False,
        },

        {
            "symbol": "WTI",
            "direction": "NONE",
            "probability": 63,
            "quality": 40,
            "confidence": 45,
            "rr": 0,
            "data_status": "LIVE",
            "setup_valid": False,
            "trigger_confirmed": False,
            "entry_present": False,
            "stop_present": False,
            "tp_present": False,
        },

        {
            "symbol": "VALID_TEST",
            "direction": "LONG",
            "probability": 72,
            "quality": 70,
            "confidence": 75,
            "rr": 3.0,
            "data_status": "LIVE",
            "setup_valid": True,
            "trigger_confirmed": True,
            "entry_present": True,
            "stop_present": True,
            "tp_present": True,
        },
    ]

    for candidate in candidates:

        result = evaluate_candidate(candidate)

        print(
            f"{candidate['symbol']:<15} "
            f"→ {result.state:<8} "
            f"rankable={result.rankable}"
        )


def test_final_gate():

    print_header("TEST 3 — FINAL GAGARIN GATE")

    # --------------------------------------------------------
    # STALE
    # --------------------------------------------------------

    stale = {
        "symbol": "COCOA",
        "data_status": "STALE",

        "mtf_confirmed": True,

        "setup_valid": True,
        "direction": "SHORT",

        "trigger_confirmed": True,
        "trigger_direction": "SHORT",

        "entry": 5576,
        "stop": 5600,

        "tp1": 5520,
        "tp2": 5480,
        "tp3": 5440,

        "atr": 23.5,

        "probability": 70,
        "quality": 70,
        "confidence": 70,
    }

    result = evaluate(stale)

    print("COCOA:")
    print(f"  STATE = {result.state}")
    print(f"  FINAL = {result.final_confluence}")
    print(
        f"  BLOCKERS = "
        f"{', '.join(result.blockers)}"
    )

    # --------------------------------------------------------
    # WATCH
    # --------------------------------------------------------

    watch = {
        "symbol": "WTI",
        "data_status": "LIVE",

        "mtf_confirmed": True,

        "setup_valid": False,
        "direction": "NONE",

        "trigger_confirmed": False,

        "entry": 0,
        "stop": 0,

        "tp1": 0,
        "tp2": 0,
        "tp3": 0,

        "atr": 0,

        "probability": 63,
        "quality": 40,
        "confidence": 45,
    }

    result = evaluate(watch)

    print()
    print("WTI:")
    print(f"  STATE = {result.state}")
    print(f"  FINAL = {result.final_confluence}")
    print(
        f"  BLOCKERS = "
        f"{', '.join(result.blockers)}"
    )

    # --------------------------------------------------------
    # VALID ENTRY
    # --------------------------------------------------------

    valid = {
        "symbol": "VALID_TEST",
        "data_status": "LIVE",

        "mtf_confirmed": True,

        "setup_valid": True,
        "direction": "LONG",

        "trigger_confirmed": True,
        "trigger_direction": "LONG",

        "entry": 100.0,
        "stop": 98.0,

        "tp1": 106.0,
        "tp2": 108.0,
        "tp3": 110.0,

        "atr": 1.0,

        "probability": 72,
        "quality": 70,
        "confidence": 75,
    }

    result = evaluate(valid)

    print()
    print("VALID_TEST:")
    print(f"  STATE = {result.state}")
    print(f"  FINAL = {result.final_confluence}")
    print(f"  RR = {result.rr:.2f}")
    print(f"  STOP ATR = {result.stop_atr:.2f}")

    # --------------------------------------------------------
    # ASSERTIONS
    # --------------------------------------------------------

    assert result.state == "ENTRY"
    assert result.final_confluence is True
    assert result.rr >= 2.5
    assert result.stop_atr <= 2.5

    print()
    print("✅ VALID ENTRY TEST PASSED")


def main():

    print_header(
        "SOYUZ GAGARIN — INTEGRATION TEST v1.0"
    )

    test_freshness()
    test_ranking()
    test_final_gate()

    print()
    print("=" * 72)
    print("✅ TUTTI I TEST COMPLETATI")
    print("=" * 72)


if __name__ == "__main__":
    main()