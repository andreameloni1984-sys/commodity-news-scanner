"""Regression test for the production runner's import graph."""


def test_main_runner_imports_and_exposes_run():
    import main

    assert callable(main.run)


def test_provider_attempt_summary_exposes_stale_age_and_safe_failure_class():
    import main

    summary = main._format_provider_attempts([
        {
            "provider": "YAHOO",
            "success": True,
            "freshness_status": "STALE",
            "age_seconds": 603.2,
            "accepted_for_live": False,
        },
        {
            "provider": "TWELVE_DATA",
            "success": False,
            "error": "HTTP 429 Too Many Requests; api_key=DO_NOT_PRINT",
            "candles": 0,
        },
    ])

    assert summary == "YAHOO:STALE@603s | TWELVE_DATA:RATE_LIMIT"
    assert "DO_NOT_PRINT" not in summary


def test_data_summary_prints_provider_attempts_and_fallback_reason(capsys):
    from types import SimpleNamespace
    import main

    state = SimpleNamespace(
        commodity="Grano",
        data_age_seconds=613.8,
        data_source="YAHOO",
        metadata={
            "data_status": "STALE",
            "provider_attempts": [
                {
                    "provider": "YAHOO",
                    "success": True,
                    "freshness_status": "STALE",
                    "age_seconds": 613.8,
                    "accepted_for_live": False,
                },
                {
                    "provider": "TWELVE_DATA",
                    "success": False,
                    "error": "AGRI_SYMBOL_NOT_FOUND",
                    "candles": 0,
                },
            ],
            "freshness_fallback_reason": "NO_FRESH_PROVIDER_AVAILABLE",
        },
    )

    main._print_data_summary([state])
    output = capsys.readouterr().out

    assert "Grano" in output
    assert "YAHOO:STALE@614s" in output
    assert "TWELVE_DATA:SYMBOL_UNAVAILABLE" in output
    assert "NO_FRESH_PROVIDER_AVAILABLE" in output
