from types import SimpleNamespace

from telegram.news_monitor import classify_event, _confirmed_setups  # selected commodity universe is authoritative


def test_oil_inventory_draw_is_provisional_bullish_for_crude():
    result = classify_event("EIA reports crude oil inventories fell sharply")
    assert result["relevant"] is True
    assert result["assets"] == ["WTI", "Brent"]
    assert result["impact"]["WTI"] == "RIALZISTA"
    assert result["impact"]["Brent"] == "RIALZISTA"


def test_hawkish_fed_headline_is_provisional_bearish_for_metals():
    result = classify_event("Federal Reserve signals hawkish policy and a rate hike")
    assert "Oro" in result["assets"]
    assert "Argento" in result["assets"]
    assert result["impact"]["Oro"] == "RIBASSISTA"


def test_ambiguous_macro_headline_does_not_force_direction():
    result = classify_event("Trump comments on tariffs")
    assert result["relevant"] is True
    assert result["impact"]["Oro"] == "MISTA"


def test_alert_requires_existing_live_confirmed_aligned_setup():
    event = {"title": "OPEC announces production cut", "baseline_prices": {"WTI": 80.0}}
    good = SimpleNamespace(
        commodity="Petrolio WTI",
        symbol="WTI/USD",
        setup_direction="LONG",
        final_decision="PAPER_SIGNAL",
        trigger_confirmed=True,
        live=True,
        price=80.1,
        entry=80.1,
        stop=78.5,
        tp1=83.0,
        tp2=84.0,
        data_source="TEST_FEED",
    )
    not_live = SimpleNamespace(
        commodity="Petrolio Brent",
        symbol="BRENT/USD",
        setup_direction="LONG",
        final_decision="PAPER_SIGNAL",
        trigger_confirmed=True,
        live=False,
        price=85.0,
        entry=85.1,
        stop=83.5,
        tp1=88.0,
    )
    matches = _confirmed_setups(event, [good, not_live])
    assert len(matches) == 1
    assert matches[0]["asset"] == "WTI"
    assert matches[0]["direction"] == "LONG"
    assert matches[0]["move_pct"] >= 0.05



def test_new_news_triggers_immediate_analysis_then_waits_for_price_confirmation(tmp_path, monkeypatch):
    import telegram.news_monitor as monitor
    from datetime import datetime, timedelta, timezone

    monkeypatch.setattr(monitor, "STATE_PATH", tmp_path / "news_state.json")
    now = datetime(2026, 10, 18, 14, 0, tzinfo=timezone.utc)
    item = {
        "source": "Test RSS",
        "title": "OPEC announces production cut",
        "url": "https://example.test/opec-cut",
        "published_at": (now - timedelta(minutes=1)).isoformat(),
    }
    state = SimpleNamespace(
        commodity="Petrolio WTI",
        symbol="WTI/USD",
        setup_direction="LONG",
        final_decision="PAPER_SIGNAL",
        trigger_confirmed=True,
        live=True,
        price=80.0,
        entry=80.1,
        stop=78.5,
        tp1=83.0,
        tp2=84.0,
        data_source="TEST_FEED",
    )
    analysis_calls = []
    messages = []

    def analyze():
        analysis_calls.append(1)
        return [state]

    first = monitor.poll_news_once(
        lambda message: messages.append(message) or True,
        analyze,
        fetcher=lambda: [item],
        now=now,
    )
    assert first["analysis"] == 1
    assert first["alerts"] == 0
    assert len(analysis_calls) == 1

    state.price = 80.1
    second = monitor.poll_news_once(
        lambda message: messages.append(message) or True,
        analyze,
        fetcher=lambda: [item],
        now=now + timedelta(minutes=5),
    )
    assert second["analysis"] == 1
    assert second["alerts"] == 1
    assert len(messages) == 1
    assert "Reazione dal rilevamento" in messages[0]
    assert "PAPER/DEMO" in messages[0]

    # The observation window starts when Telegram delivery succeeds.
    import json
    saved = json.loads((tmp_path / "news_state.json").read_text(encoding="utf-8"))
    sent_event = next(event for event in saved["pending"] if event.get("alert_sent"))
    assert sent_event["alert_sent_at"] == (now + timedelta(minutes=5)).isoformat()
    assert sent_event["expires_at"] == (now + timedelta(minutes=5, hours=4)).isoformat()



def test_oil_supply_risk_headlines_are_classified_bullish():
    for title in (
        "Tanker attacks raise oil supply risk",
        "Iran sanctions threaten crude exports",
        "Oilfield shutdown disrupts production",
    ):
        result = classify_event(title)
        assert result["impact"]["Brent"] == "RIALZISTA"
        assert result["impact"]["WTI"] == "RIALZISTA"
        assert result["matched_terms"]["Brent"]["bullish"]


def test_mixed_oil_catalysts_stay_neutral_and_explain_why():
    result = classify_event(
        "OPEC production cut as weak demand outlook raises oversupply concerns"
    )
    assert result["impact"]["Brent"] == "MISTA"
    assert result["matched_terms"]["Brent"]["bullish"]
    assert result["matched_terms"]["Brent"]["bearish"]
    assert 0 <= result["confidence_score"] <= 100


def test_selected_grains_are_classified_by_crop_catalyst():
    wheat = classify_event("Drought damages wheat crop and threatens harvest")
    corn = classify_event("Corn crop disease threatens production")
    soybean = classify_event("Soybean harvest improves after bumper harvest")
    assert wheat["impact"]["Grano"] == "RIALZISTA"
    assert corn["impact"]["Mais"] == "RIALZISTA"
    assert soybean["impact"]["Soia"] == "RIBASSISTA"
    assert not {"Caffè", "Cacao", "Riso", "Zucchero"} & set(wheat["assets"])


def test_copper_and_silver_are_supported_in_selected_universe():
    copper = classify_event("Copper supply disruption raises industrial metal prices")
    silver = classify_event("Silver bullion demand rises")
    assert "Rame" in copper["assets"]
    assert "Argento" in silver["assets"]
    assert "Platino" not in copper["assets"]
    assert "Palladio" not in copper["assets"]


def test_agricultural_mixed_catalysts_remain_mixed():
    result = classify_event("Coffee harvest improves but drought threatens supply")
    assert result["impact"]["Caffè"] == "MISTA"


def test_inactive_commodities_do_not_create_selected_universe_assets():
    assert classify_event("Coffee prices rise after a routine harvest update")["relevant"] is False
    assert classify_event("Platinum futures rise in a quiet session")["relevant"] is False


def test_sputnik_historical_action_reaction_is_attached_to_gagarin_news():
    result = classify_event("Trump threatens massive increase in China tariffs")
    historical = result["historical_action_reaction"]
    assert historical["event_type"] == "TRADE_ESCALATION"
    assert historical["historical_matches"] == ["china_tariff_escalation_2025_10"]
    assert historical["historical_directions"]["NASDAQ"] == "DOWN"
    assert historical["evidence"] == "HISTORICAL_ANALOGUE"
    assert result["sputnik_watch_candidates"]
    assert all(row["status"] == "WATCH" for row in result["sputnik_watch_candidates"])


def test_sputnik_does_not_invent_historical_direction_without_analogue():
    result = classify_event("OPEC announces routine production meeting with no oil price change")
    historical = result["historical_action_reaction"]
    assert historical["evidence"] == "NO_ANALOGUE"
    assert historical["historical_directions"] == {}

def test_sputnik_does_not_match_broad_china_headline_to_trade_analogue():
    from sputnik_action_reaction import match_historical_reactions

    matches = match_historical_reactions(
        "China discusses semiconductor exports at a routine meeting"
    )
    assert matches == []

def test_sputnik_tariff_pause_does_not_match_escalation_pattern():
    from sputnik_action_reaction import match_historical_reactions

    matches = match_historical_reactions("Trump announces a 90 days pause on tariffs")
    assert [item["id"] for item in matches] == ["tariff_pause_2025_04"]


def test_alert_scorecard_scores_only_prices_observed_after_alert():
    from datetime import datetime, timedelta, timezone
    from telegram.news_monitor import build_alert_scorecard

    sent = datetime(2026, 10, 21, 18, 0, tzinfo=timezone.utc)
    rows = [
        {"kind": "NEWS_ALERT_SENT", "event_id": "evt-1", "asset": "WTI", "direction": "LONG",
         "price": 80.0, "sent_at": sent.isoformat()},
        {"kind": "NEWS_REACTION", "event_id": "evt-1", "asset": "WTI",
         "current_price": 80.2, "observed_at": (sent + timedelta(minutes=20)).isoformat()},
        {"kind": "NEWS_ALERT_SENT", "event_id": "evt-2", "asset": "Oro", "direction": "SHORT",
         "price": 4000.0, "sent_at": sent.isoformat()},
        {"kind": "NEWS_REACTION", "event_id": "evt-2", "asset": "Oro",
         "current_price": 4010.0, "observed_at": (sent + timedelta(minutes=20)).isoformat()},
        {"kind": "NEWS_REACTION", "event_id": "evt-2", "asset": "Oro",
         "current_price": 3990.0, "observed_at": (sent + timedelta(minutes=5)).isoformat()},
    ]
    report = build_alert_scorecard(rows, now=sent + timedelta(hours=1))
    assert report["alerts"] == 2
    assert report["scored"] == 2
    assert report["correct"] == 1
    assert report["incorrect"] == 1
    assert report["accuracy_pct"] == 50.0
    assert report["pending"] == 0


def test_alert_scorecard_marks_alert_pending_without_later_observation():
    from datetime import datetime, timezone
    from telegram.news_monitor import build_alert_scorecard

    sent = datetime(2026, 10, 21, 18, 0, tzinfo=timezone.utc)
    report = build_alert_scorecard([{
        "kind": "NEWS_ALERT_SENT", "event_id": "evt-1", "asset": "WTI",
        "direction": "LONG", "price": 80.0, "sent_at": sent.isoformat(),
    }], now=sent)
    assert report["alerts"] == 1
    assert report["scored"] == 0
    assert report["pending"] == 1


def test_alert_scorecard_tracks_observed_tp1_and_stop_loss():
    from datetime import datetime, timedelta, timezone
    from telegram.news_monitor import build_alert_scorecard

    sent = datetime(2026, 10, 21, 18, 0, tzinfo=timezone.utc)
    rows = [
        {"kind": "NEWS_ALERT_SENT", "event_id": "tp", "asset": "WTI", "direction": "LONG",
         "price": 80.0, "stop": 79.0, "tp1": 81.0, "sent_at": sent.isoformat()},
        {"kind": "NEWS_REACTION", "event_id": "tp", "asset": "WTI",
         "current_price": 81.1, "observed_at": (sent + timedelta(minutes=20)).isoformat()},
        {"kind": "NEWS_ALERT_SENT", "event_id": "sl", "asset": "Oro", "direction": "SHORT",
         "price": 4000.0, "stop": 4050.0, "tp1": 3900.0, "sent_at": sent.isoformat()},
        {"kind": "NEWS_REACTION", "event_id": "sl", "asset": "Oro",
         "current_price": 4060.0, "observed_at": (sent + timedelta(minutes=20)).isoformat()},
    ]
    report = build_alert_scorecard(rows, now=sent + timedelta(hours=1))
    assert report["tp1_observed"] == 1
    assert report["sl_observed"] == 1
    assert report["open_at_last_check"] == 0


def test_asset_matches_support_silver_and_copper_symbols():
    from telegram.news_monitor import _asset_matches

    assert _asset_matches("Argento", SimpleNamespace(commodity="Silver", symbol="XAG/USD"))
    assert _asset_matches("Argento", SimpleNamespace(commodity="Argento spot", symbol=""))
    assert _asset_matches("Rame", SimpleNamespace(commodity="Copper", symbol="COPPER/USD"))
    assert _asset_matches("Rame", SimpleNamespace(commodity="Rame spot", symbol=""))


def test_alert_scorecard_does_not_miss_stop_hit_in_first_15_minutes():
    from datetime import datetime, timedelta, timezone
    from telegram.news_monitor import build_alert_scorecard

    sent = datetime(2026, 10, 21, 18, 0, tzinfo=timezone.utc)
    rows = [
        {"kind": "NEWS_ALERT_SENT", "event_id": "early-sl", "asset": "WTI", "direction": "LONG",
         "price": 80.0, "stop": 79.0, "tp1": 81.0, "sent_at": sent.isoformat()},
        {"kind": "NEWS_REACTION", "event_id": "early-sl", "asset": "WTI",
         "current_price": 78.9, "observed_at": (sent + timedelta(minutes=5)).isoformat()},
        {"kind": "NEWS_REACTION", "event_id": "early-sl", "asset": "WTI",
         "current_price": 80.1, "observed_at": (sent + timedelta(minutes=20)).isoformat()},
    ]
    report = build_alert_scorecard(rows, now=sent + timedelta(hours=1))
    assert report["scored"] == 1
    assert report["sl_observed"] == 1
    assert report["tp1_observed"] == 0


def test_eia_press_release_feed_uses_published_rss_endpoint():
    from telegram.news_monitor import RSS_FEEDS

    feeds = dict(RSS_FEEDS)
    assert feeds["EIA"] == "https://www.eia.gov/rss/press_rss.xml"

def test_alert_scorecard_marks_closed_window_without_prices_unscored():
    from datetime import datetime, timedelta, timezone
    from telegram.news_monitor import build_alert_scorecard

    sent = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)
    report = build_alert_scorecard([{
        "kind": "NEWS_ALERT_SENT", "event_id": "missing-data", "asset": "WTI",
        "direction": "LONG", "price": 80.0, "sent_at": sent.isoformat(),
    }], now=sent + timedelta(hours=5))
    assert report["alerts"] == 1
    assert report["scored"] == 0
    assert report["pending"] == 0
    assert report["unscored_expired"] == 1
    assert report["coverage_pct"] == 0.0

def test_news_monitor_prefers_durable_state_and_event_journal(tmp_path, monkeypatch):
    import json
    import state_store
    import telegram.news_monitor as monitor

    local_state = tmp_path / "local_state.json"
    local_journal = tmp_path / "local_journal.jsonl"
    monkeypatch.setattr(monitor, "STATE_PATH", local_state)
    monkeypatch.setattr(monitor, "JOURNAL_PATH", local_journal)

    durable_state = {"seen": ["durable-fingerprint"], "clusters": [], "pending": [], "initialized": True}
    saved_states = []
    journal_records = []
    monkeypatch.setattr(state_store, "load_state", lambda key: durable_state if key == "gagarin_news_monitor" else None)
    monkeypatch.setattr(state_store, "save_state", lambda key, value: saved_states.append((key, value)) or True)
    monkeypatch.setattr(state_store, "append_event_journal", lambda record: journal_records.append(record) or True)
    monkeypatch.setattr(state_store, "load_event_journal", lambda limit=20000: [{"kind": "DURABLE_TEST"}])

    assert monitor._load_state()["seen"] == ["durable-fingerprint"]
    monitor._save_state({"seen": ["updated"], "clusters": [], "pending": []})
    monitor._journal({"kind": "TEST_EVENT"})
    assert saved_states[0][0] == "gagarin_news_monitor"
    assert journal_records[0]["kind"] == "TEST_EVENT"
    assert not local_journal.exists()
    assert state_store.load_event_journal(limit=10) == [{"kind": "DURABLE_TEST"}]




def test_forbidden_news_source_is_cooled_down_for_six_hours(monkeypatch):
    from types import SimpleNamespace
    import telegram.news_monitor as monitor

    source = "TEST_FORBIDDEN_SOURCE"
    monkeypatch.setitem(monitor._SOURCE_FAILURES, source, 0)
    monkeypatch.setitem(monitor._SOURCE_RETRY_AT, source, 0.0)
    error = RuntimeError("forbidden")
    error.response = SimpleNamespace(status_code=403, headers={})
    delay = monitor._source_failed(source, error)

    assert delay == 6 * 60 * 60
    assert monitor._SOURCE_RETRY_AT[source] > 0
    assert not monitor._source_allowed(source)



def test_valid_signal_levels_enforces_directional_order_and_finite_values():
    from telegram.news_monitor import _valid_signal_levels

    assert _valid_signal_levels("LONG", 80.1, 80.1, 78.5, 83.0, 84.0)
    assert _valid_signal_levels("SHORT", 79.9, 80.0, 81.0, 78.0, 77.0)
    assert not _valid_signal_levels("LONG", float("nan"), 80.1, 78.5, 83.0, 84.0)
    assert not _valid_signal_levels("LONG", 80.1, float("inf"), 78.5, 83.0, 84.0)
    assert not _valid_signal_levels("LONG", 80.1, 80.1, 80.2, 83.0, 84.0)
    assert not _valid_signal_levels("LONG", 80.1, 80.1, 78.5, 80.0, 84.0)
    assert not _valid_signal_levels("LONG", 80.1, 80.1, 78.5, 83.0, 82.0)
    assert not _valid_signal_levels("SHORT", 79.9, 80.0, 81.0, 82.0, 77.0)


def test_confirmed_setups_rejects_nonfinite_and_inverted_levels():
    from telegram.news_monitor import _confirmed_setups

    event = {"title": "OPEC announces production cut", "baseline_prices": {"WTI": 80.0}}
    base = dict(
        commodity="Petrolio WTI", symbol="WTI/USD", setup_direction="LONG",
        final_decision="PAPER_SIGNAL", trigger_confirmed=True, live=True,
        price=80.1, entry=80.1, stop=78.5, tp1=83.0, tp2=84.0,
        data_source="TEST_FEED",
    )
    invalid_variants = [
        {"price": float("nan")},
        {"entry": float("inf")},
        {"stop": 80.2},
        {"tp1": 80.0},
        {"tp2": 82.0},
    ]
    for override in invalid_variants:
        state_data = {**base, **override}
        assert _confirmed_setups(event, [SimpleNamespace(**state_data)]) == []


def test_stale_pending_catalyst_is_suppressed_before_telegram(tmp_path, monkeypatch):
    import json
    from datetime import datetime, timedelta, timezone
    import telegram.news_monitor as monitor

    now = datetime(2026, 10, 26, 10, 0, tzinfo=timezone.utc)
    state_path = tmp_path / "news_state.json"
    monkeypatch.setattr(monitor, "STATE_PATH", state_path)
    monkeypatch.setattr(monitor, "_maybe_send_daily_scorecard", lambda *args, **kwargs: None)

    event = {
        "event_id": "stale-opec-event",
        "source": "Test RSS",
        "title": "OPEC announces production cut",
        "url": "https://example.test/opec-cut",
        "published_at": (now - timedelta(hours=5)).isoformat(),
        "first_seen_at": (now - timedelta(minutes=10)).isoformat(),
        "baseline_at": (now - timedelta(minutes=5)).isoformat(),
        "baseline_prices": {"WTI": 80.0},
        "expires_at": (now + timedelta(minutes=10)).isoformat(),
    }
    state_path.write_text(json.dumps({
        "seen": [],
        "clusters": [],
        "pending": [event],
        "last_analysis_at": now.timestamp() - monitor.RECHECK_SECONDS - 1,
        "initialized": True,
    }), encoding="utf-8")

    wti = SimpleNamespace(
        commodity="Petrolio WTI", symbol="WTI/USD", setup_direction="LONG",
        final_decision="PAPER_SIGNAL", trigger_confirmed=True, live=True,
        price=80.1, entry=80.1, stop=78.5, tp1=83.0, tp2=84.0,
        data_source="TEST_FEED", metadata={},
    )
    messages = []
    journal_rows = []
    monkeypatch.setattr(monitor, "_journal", lambda row: journal_rows.append(dict(row)))

    result = monitor.poll_news_once(
        lambda message: messages.append(message) or True,
        lambda: [wti],
        fetcher=lambda: [],
        now=now,
    )

    assert result["analysis"] == 1
    assert result["alerts"] == 0
    assert messages == []
    suppressed = [row for row in journal_rows if row.get("kind") == "NEWS_ALERT_SUPPRESSED"]
    assert len(suppressed) == 1
    assert suppressed[0]["event_id"] == "stale-opec-event"
    assert suppressed[0]["catalyst_timing"] == "STALE_CATALYST"
    saved = json.loads(state_path.read_text(encoding="utf-8"))
    assert saved["pending"] == []


def test_retry_after_header_rejects_nonfinite_and_negative_values(monkeypatch):
    from types import SimpleNamespace
    import telegram.news_monitor as monitor

    for header in ("NaN", "Infinity", "-Infinity", "-10", "not-a-number"):
        source = "TEST_RETRY_AFTER_INVALID"
        monkeypatch.setitem(monitor._SOURCE_FAILURES, source, 0)
        monkeypatch.setitem(monitor._SOURCE_RETRY_AT, source, 0.0)
        error = RuntimeError("upstream unavailable")
        error.response = SimpleNamespace(status_code=503, headers={"Retry-After": header})

        delay = monitor._source_failed(source, error)

        assert delay == 120
        assert not monitor._source_allowed(source)


def test_retry_after_header_is_capped_to_maximum_backoff(monkeypatch):
    from types import SimpleNamespace
    import telegram.news_monitor as monitor

    source = "TEST_RETRY_AFTER_LARGE"
    monkeypatch.setitem(monitor._SOURCE_FAILURES, source, 0)
    monkeypatch.setitem(monitor._SOURCE_RETRY_AT, source, 0.0)
    error = RuntimeError("upstream busy")
    error.response = SimpleNamespace(status_code=503, headers={"Retry-After": "999999"})

    delay = monitor._source_failed(source, error)

    assert delay == monitor.SOURCE_BACKOFF_MAX_SECONDS
    assert not monitor._source_allowed(source)


def test_alert_scorecard_rejects_non_finite_prices_and_invalid_levels():
    from datetime import datetime, timedelta, timezone
    from telegram.news_monitor import build_alert_scorecard

    sent = datetime(2026, 10, 21, 18, 0, tzinfo=timezone.utc)
    rows = [
        {"kind": "NEWS_ALERT_SENT", "event_id": "bad-nan", "asset": "WTI", "direction": "LONG",
         "price": float("nan"), "sent_at": sent.isoformat()},
        {"kind": "NEWS_ALERT_SENT", "event_id": "bad-inf", "asset": "WTI", "direction": "LONG",
         "price": float("inf"), "sent_at": sent.isoformat()},
        {"kind": "NEWS_ALERT_SENT", "event_id": "bad-levels", "asset": "WTI", "direction": "LONG",
         "price": 80.0, "stop": float("nan"), "tp1": 82.0, "sent_at": sent.isoformat()},
        {"kind": "NEWS_REACTION", "event_id": "bad-levels", "asset": "WTI",
         "current_price": float("inf"), "observed_at": (sent + timedelta(minutes=20)).isoformat()},
        {"kind": "NEWS_REACTION", "event_id": "bad-levels", "asset": "WTI",
         "current_price": 80.2, "observed_at": (sent + timedelta(minutes=25)).isoformat()},
    ]
    report = build_alert_scorecard(rows, now=sent + timedelta(hours=1))
    assert report["alerts"] == 1
    assert report["scored"] == 1
    assert report["correct"] == 1
    assert report["tp1_observed"] == 0
    assert report["sl_observed"] == 0
    assert report["open_at_last_check"] == 1
