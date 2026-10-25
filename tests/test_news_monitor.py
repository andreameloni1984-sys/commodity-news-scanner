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
    assert matches[0]["rr_tp1"] == (83.0 - 80.1) / (80.1 - 78.5)
    assert matches[0]["risk_pct"] > 0
    assert matches[0]["tp1_pct"] > 0

    from telegram.news_monitor import _format_news_alert
    message = _format_news_alert(
        {"title": "OPEC announces production cut", "source": "Test RSS",
         "published_at": "2026-10-18T13:59:00+00:00",
         "first_seen_at": "2026-10-18T14:00:00+00:00",
         "catalyst_timing": "FRESH_CATALYST", "catalyst_age_minutes": 6.0,
         "url": "https://example.test/opec-cut"},
        matches[0],
    )
    assert "Stop Loss: 78.5" in message
    assert "Take Profit 1: 83" in message
    assert "Rapporto R/R su TP1:" in message
    assert "PAPER/DEMO — NESSUN ORDINE" in message
    assert "slippage o gap" in message
    assert "non è una previsione anticipata" in message


def test_telegram_alert_rejects_invalid_stop_or_target_geometry():
    from telegram.news_monitor import _confirmed_setups

    event = {"title": "OPEC announces production cut", "baseline_prices": {"WTI": 80.0}}
    base = dict(
        commodity="Petrolio WTI", symbol="WTI/USD", setup_direction="LONG",
        final_decision="PAPER_SIGNAL", trigger_confirmed=True, live=True,
        price=80.1, entry=80.1, stop=81.0, tp1=83.0, data_source="TEST_FEED",
    )
    assert _confirmed_setups(event, [SimpleNamespace(**base)]) == []

    base["stop"] = float("nan")
    assert _confirmed_setups(event, [SimpleNamespace(**base)]) == []

    base["stop"] = 78.5
    base["tp1"] = 79.0
    assert _confirmed_setups(event, [SimpleNamespace(**base)]) == []



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
    journal_rows = []
    monkeypatch.setattr(monitor, "_journal", lambda row: journal_rows.append(dict(row)))

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
    assert "Variazione dal rilevamento" in messages[0]
    assert "PAPER/DEMO" in messages[0]
    assert "Timing fonte: FRESH_CATALYST | età alla conferma: 6.0 min" in messages[0]

    detected = next(row for row in journal_rows if row.get("kind") == "NEWS_DETECTED")
    sent_row = next(row for row in journal_rows if row.get("kind") == "NEWS_ALERT_SENT")
    assert detected["catalyst_timing"] == "FRESH_CATALYST"
    assert detected["catalyst_age_minutes"] == 1.0
    assert detected["catalyst_future_skew_minutes"] == 0.0
    assert sent_row["catalyst_timing"] == "FRESH_CATALYST"
    assert sent_row["catalyst_age_minutes"] == 6.0
    assert sent_row["catalyst_future_skew_minutes"] == 0.0

    # The observation window starts when Telegram delivery succeeds.
    import json
    saved = json.loads((tmp_path / "news_state.json").read_text(encoding="utf-8"))
    sent_event = next(event for event in saved["pending"] if event.get("alert_sent"))
    assert sent_event["alert_sent_at"] == (now + timedelta(minutes=5)).isoformat()
    assert sent_event["expires_at"] == (now + timedelta(minutes=5, hours=4)).isoformat()
    assert sent_event["catalyst_timing"] == "FRESH_CATALYST"
    assert sent_event["catalyst_age_minutes"] == 6.0



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


def test_selected_agricultural_commodities_are_classified_by_crop_catalyst():
    coffee = classify_event("Brazil drought threatens Arabica coffee harvest")
    cocoa = classify_event("Cocoa crop disease reduces production forecast")
    rice = classify_event("Rice export ban disrupts supply")
    sugar = classify_event("Sugar production rises after bumper harvest")
    assert coffee["impact"]["Caffè"] == "RIALZISTA"
    assert cocoa["impact"]["Cacao"] == "RIALZISTA"
    assert rice["impact"]["Riso"] == "RIALZISTA"
    assert sugar["impact"]["Zucchero"] == "RIBASSISTA"


def test_platinum_and_silver_are_supported_in_selected_universe():
    result = classify_event("Platinum rises as the Federal Reserve signals rate cuts")
    assert "Platino" in result["assets"]
    assert "Argento" in result["assets"]


def test_agricultural_mixed_catalysts_remain_mixed():
    result = classify_event("Coffee harvest improves but drought threatens supply")
    assert result["impact"]["Caffè"] == "MISTA"


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


def test_alert_scorecard_reports_adverse_and_favorable_excursions_not_only_final_return():
    from datetime import datetime, timedelta, timezone
    from telegram.news_monitor import build_alert_scorecard

    sent = datetime(2026, 10, 21, 18, 0, tzinfo=timezone.utc)
    rows = [
        {"kind": "NEWS_ALERT_SENT", "event_id": "evt-excursion", "asset": "WTI",
         "direction": "LONG", "price": 100.0, "stop": 95.0, "tp1": 105.0,
         "sent_at": sent.isoformat()},
        {"kind": "NEWS_REACTION", "event_id": "evt-excursion", "asset": "WTI",
         "current_price": 98.0, "observed_at": (sent + timedelta(minutes=20)).isoformat()},
        {"kind": "NEWS_REACTION", "event_id": "evt-excursion", "asset": "WTI",
         "current_price": 103.0, "observed_at": (sent + timedelta(minutes=30)).isoformat()},
        {"kind": "NEWS_REACTION", "event_id": "evt-excursion", "asset": "WTI",
         "current_price": 101.0, "observed_at": (sent + timedelta(minutes=40)).isoformat()},
    ]

    report = build_alert_scorecard(rows, now=sent + timedelta(hours=1))

    assert report["scored"] == 1
    assert report["correct"] == 1  # final observation is positive
    assert report["mean_directional_return_pct"] == 1.0
    assert report["mean_max_adverse_excursion_pct"] == -2.0
    assert report["mean_max_favorable_excursion_pct"] == 3.0


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


def test_asset_matches_support_silver_and_palladium_symbols():
    from telegram.news_monitor import _asset_matches

    assert _asset_matches("Argento", SimpleNamespace(commodity="Silver", symbol="XAGUSD"))
    assert _asset_matches("Argento", SimpleNamespace(commodity="Argento spot", symbol=""))
    assert _asset_matches("Palladio", SimpleNamespace(commodity="Palladium", symbol="XPDUSD"))
    assert _asset_matches("Palladio", SimpleNamespace(commodity="Palladio spot", symbol=""))

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



def test_alert_scorecard_rejects_non_finite_prices_and_levels():
    from datetime import datetime, timedelta, timezone
    from telegram.news_monitor import build_alert_scorecard

    sent = datetime(2026, 10, 21, 18, 0, tzinfo=timezone.utc)
    rows = [
        {"kind": "NEWS_ALERT_SENT", "event_id": "bad-alert-price", "asset": "WTI",
         "direction": "LONG", "price": float("inf"), "sent_at": sent.isoformat()},
        {"kind": "NEWS_ALERT_SENT", "event_id": "bad-reaction", "asset": "Oro",
         "direction": "LONG", "price": 4000.0, "stop": float("nan"),
         "tp1": 4100.0, "sent_at": sent.isoformat()},
        {"kind": "NEWS_REACTION", "event_id": "bad-reaction", "asset": "Oro",
         "current_price": float("inf"),
         "observed_at": (sent + timedelta(minutes=20)).isoformat()},
    ]
    report = build_alert_scorecard(rows, now=sent + timedelta(hours=1))
    assert report["alerts"] == 1
    assert report["scored"] == 0
    assert report["pending"] == 1


def test_alert_scorecard_treats_naive_now_as_utc():
    from datetime import datetime, timezone
    from telegram.news_monitor import build_alert_scorecard

    sent = datetime(2026, 10, 21, 18, 0, tzinfo=timezone.utc)
    rows = [{
        "kind": "NEWS_ALERT_SENT", "event_id": "naive-now", "asset": "WTI",
        "direction": "LONG", "price": 80.0, "sent_at": sent.isoformat(),
    }]
    # Naive input is explicitly interpreted as 18:10 UTC, regardless of host TZ.
    report = build_alert_scorecard(rows, now=datetime(2026, 10, 21, 18, 10))
    assert report["alerts"] == 1
    assert report["scored"] == 0
    assert report["pending"] == 1
    assert report["unscored_expired"] == 0


def test_title_cluster_dedupes_syndication_within_utc_day_but_allows_later_recurrence():
    from telegram.news_monitor import _title_cluster

    first = {
        "title": "OPEC announces production decision",
        "url": "https://feed-a.example/story/1",
        "published_at": "2026-10-22T23:50:00+00:00",
    }
    same_day_syndication = {
        "title": "OPEC announces production decision",
        "url": "https://feed-b.example/story/2",
        "published_at": "2026-10-22T23:58:00+00:00",
    }
    later_recurrence = {
        "title": "OPEC announces production decision",
        "url": "https://feed-c.example/story/3",
        "published_at": "2026-10-23T09:00:00+00:00",
    }

    assert _title_cluster(first) == _title_cluster(same_day_syndication)
    assert _title_cluster(first) != _title_cluster(later_recurrence)


def test_title_cluster_uses_normalized_utc_publication_day():
    from telegram.news_monitor import _title_cluster

    utc_item = {
        "title": "Fed announces rate decision",
        "published_at": "2026-10-23T00:30:00+00:00",
    }
    offset_item = {
        "title": "Fed announces rate decision",
        # Same instant expressed as the previous local calendar date.
        "published_at": "2026-10-22T20:30:00-04:00",
    }

    assert _title_cluster(utc_item) == _title_cluster(offset_item)


def test_multi_asset_catalyst_alerts_once_per_asset_across_rechecks(tmp_path, monkeypatch):
    import json
    from datetime import datetime, timedelta, timezone
    import telegram.news_monitor as monitor

    monkeypatch.setattr(monitor, "STATE_PATH", tmp_path / "news_state.json")
    now = datetime(2026, 10, 23, 14, 0, tzinfo=timezone.utc)
    item = {
        "source": "Test RSS",
        "title": "OPEC announces production cut",
        "url": "https://example.test/opec-cut-multi",
        "published_at": (now - timedelta(minutes=1)).isoformat(),
    }
    wti = SimpleNamespace(
        commodity="Petrolio WTI", symbol="WTI/USD", setup_direction="LONG",
        final_decision="PAPER_SIGNAL", trigger_confirmed=True, live=True,
        price=80.0, entry=80.1, stop=78.5, tp1=83.0, tp2=84.0,
        data_source="TEST_FEED",
    )
    brent = SimpleNamespace(
        commodity="Petrolio Brent", symbol="BRENT/USD", setup_direction="LONG",
        final_decision="PAPER_SIGNAL", trigger_confirmed=True, live=True,
        price=85.0, entry=85.1, stop=83.5, tp1=88.0, tp2=89.0,
        data_source="TEST_FEED",
    )
    states = [wti, brent]
    messages, journal_rows = [], []
    monkeypatch.setattr(monitor, "_journal", lambda row: journal_rows.append(dict(row)))

    def analyze():
        return states

    first = monitor.poll_news_once(
        lambda message: messages.append(message) or True, analyze,
        fetcher=lambda: [item], now=now,
    )
    assert first["alerts"] == 0  # first pass captures baselines only

    wti.price = 80.2
    brent.price = 85.2
    second = monitor.poll_news_once(
        lambda message: messages.append(message) or True, analyze,
        fetcher=lambda: [item], now=now + timedelta(minutes=5),
    )
    assert second["alerts"] == 2
    assert len(messages) == 2
    sent_assets = [row["asset"] for row in journal_rows if row.get("kind") == "NEWS_ALERT_SENT"]
    assert set(sent_assets) == {"WTI", "Brent"}

    third = monitor.poll_news_once(
        lambda message: messages.append(message) or True, analyze,
        fetcher=lambda: [item], now=now + timedelta(minutes=10),
    )
    assert third["alerts"] == 0
    assert len(messages) == 2
    saved = json.loads((tmp_path / "news_state.json").read_text(encoding="utf-8"))
    event = next(row for row in saved["pending"] if row.get("event_id"))
    assert set(event["alerted_assets"]) == {"brent", "wti"}

def test_confirmed_setup_rejects_non_finite_catalyst_baselines():
    from telegram.news_monitor import _confirmed_setups

    bearish_event = {
        "title": "Federal Reserve signals hawkish policy and a rate hike",
        "baseline_prices": {"Oro": float("inf")},
    }
    state = SimpleNamespace(
        commodity="Gold", symbol="XAUUSD", setup_direction="SHORT",
        final_decision="PAPER_SIGNAL", trigger_confirmed=True, live=True,
        price=3990.0, entry=3990.0, stop=4010.0, tp1=3950.0,
        data_source="TEST_FEED",
    )
    assert _confirmed_setups(bearish_event, [state]) == []

    bearish_event["baseline_prices"]["Oro"] = float("nan")
    assert _confirmed_setups(bearish_event, [state]) == []


def test_capture_baseline_skips_non_finite_live_prices():
    from telegram.news_monitor import _capture_baseline

    states = [
        SimpleNamespace(commodity="Gold", symbol="XAUUSD", live=True, price=float("inf")),
        SimpleNamespace(commodity="Gold", symbol="XAUUSD", live=True, price=float("nan")),
    ]
    assert _capture_baseline({"assets": ["Oro"]}, states) == {}

def test_alert_scorecard_ignores_future_dated_reactions_until_they_are_observable():
    from datetime import datetime, timedelta, timezone
    from telegram.news_monitor import build_alert_scorecard

    sent = datetime(2026, 10, 23, 18, 0, tzinfo=timezone.utc)
    now = sent + timedelta(minutes=30)
    rows = [
        {
            "kind": "NEWS_ALERT_SENT",
            "event_id": "future-reaction",
            "asset": "WTI",
            "direction": "LONG",
            "price": 80.0,
            "sent_at": sent.isoformat(),
        },
        {
            "kind": "NEWS_REACTION",
            "event_id": "future-reaction",
            "asset": "WTI",
            "current_price": 84.0,
            "observed_at": (sent + timedelta(minutes=40)).isoformat(),
        },
    ]

    report = build_alert_scorecard(rows, now=now)

    assert report["alerts"] == 1
    assert report["scored"] == 0
    assert report["pending"] == 1
    assert report["unscored_expired"] == 0



def test_alert_scorecard_excludes_conflicting_prices_at_same_reaction_timestamp():
    from datetime import datetime, timedelta, timezone
    from telegram.news_monitor import build_alert_scorecard

    sent = datetime(2026, 10, 23, 18, 0, tzinfo=timezone.utc)
    ambiguous_at = sent + timedelta(minutes=20)
    clean_at = sent + timedelta(minutes=30)
    alert = {
        "kind": "NEWS_ALERT_SENT", "event_id": "duplicate-reaction-time",
        "asset": "WTI", "direction": "LONG", "price": 80.0,
        "stop": 79.0, "tp1": 82.0, "sent_at": sent.isoformat(),
    }
    conflicting = [
        {"kind": "NEWS_REACTION", "event_id": "duplicate-reaction-time",
         "asset": "WTI", "current_price": 78.0, "observed_at": ambiguous_at.isoformat()},
        {"kind": "NEWS_REACTION", "event_id": "duplicate-reaction-time",
         "asset": "WTI", "current_price": 83.0, "observed_at": ambiguous_at.isoformat()},
    ]
    later = {
        "kind": "NEWS_REACTION", "event_id": "duplicate-reaction-time",
        "asset": "WTI", "current_price": 81.0, "observed_at": clean_at.isoformat(),
    }

    # Reversing insertion order must not change the outcome. The conflicting
    # same-time prices could otherwise label either SL or TP1 depending on order.
    reports = [
        build_alert_scorecard([alert, *conflicting, later], now=sent + timedelta(hours=1)),
        build_alert_scorecard([alert, *reversed(conflicting), later], now=sent + timedelta(hours=1)),
    ]
    for report in reports:
        assert report["alerts"] == 1
        assert report["scored"] == 1
        assert report["ambiguous_reaction_groups"] == 1
        assert report["sl_observed"] == 0
        assert report["tp1_observed"] == 0
    assert reports[0] == reports[1]
    assert reports[0]["open_at_last_check"] == 1

def test_alert_scorecard_assigns_reactions_only_to_latest_event_asset_alert():
    from datetime import datetime, timedelta, timezone
    from telegram.news_monitor import build_alert_scorecard

    sent_first = datetime(2026, 10, 23, 18, 0, tzinfo=timezone.utc)
    sent_second = sent_first + timedelta(minutes=30)
    rows = [
        {
            "kind": "NEWS_ALERT_SENT", "event_id": "same-catalyst",
            "asset": "WTI", "direction": "LONG", "price": 80.0,
            "stop": 79.0, "tp1": 82.0, "sent_at": sent_first.isoformat(),
        },
        {
            "kind": "NEWS_ALERT_SENT", "event_id": "same-catalyst",
            "asset": "WTI", "direction": "LONG", "price": 81.0,
            "stop": 80.0, "tp1": 83.0, "sent_at": sent_second.isoformat(),
        },
        {
            "kind": "NEWS_REACTION", "event_id": "same-catalyst",
            "asset": "WTI", "current_price": 81.0,
            "observed_at": (sent_first + timedelta(minutes=20)).isoformat(),
        },
        {
            "kind": "NEWS_REACTION", "event_id": "same-catalyst",
            "asset": "WTI", "current_price": 83.0,
            "observed_at": (sent_second + timedelta(minutes=15)).isoformat(),
        },
    ]

    report = build_alert_scorecard(rows, now=sent_second + timedelta(minutes=30))

    assert report["alerts"] == 2
    assert report["scored"] == 2
    assert report["ambiguous_alert_groups"] == 0
    # If the second reaction leaked into the first alert's window, both alerts
    # would be reported as TP1 hits. The boundary must leave one open and one TP1.
    assert report["tp1_observed"] == 1
    assert report["open_at_last_check"] == 1

def test_news_reaction_journal_rejects_non_finite_live_price(tmp_path, monkeypatch):
    from datetime import datetime, timedelta, timezone
    import telegram.news_monitor as monitor

    monkeypatch.setattr(monitor, "STATE_PATH", tmp_path / "news_state.json")
    now = datetime(2026, 10, 23, 14, 0, tzinfo=timezone.utc)
    item = {
        "source": "Test RSS",
        "title": "OPEC announces production cut",
        "url": "https://example.test/opec-cut-invalid-reaction",
        "published_at": (now - timedelta(minutes=1)).isoformat(),
    }
    wti = SimpleNamespace(
        commodity="Petrolio WTI", symbol="WTI/USD", setup_direction="LONG",
        final_decision="PAPER_SIGNAL", trigger_confirmed=True, live=True,
        price=80.0, entry=80.1, stop=78.5, tp1=83.0, tp2=84.0,
        data_source="TEST_FEED",
    )
    journal_rows = []
    monkeypatch.setattr(monitor, "_journal", lambda row: journal_rows.append(dict(row)))

    first = monitor.poll_news_once(
        lambda _message: True, lambda: [wti],
        fetcher=lambda: [item], now=now,
    )
    assert first["alerts"] == 0  # capture a finite baseline only

    wti.price = float("inf")
    second = monitor.poll_news_once(
        lambda _message: True, lambda: [wti],
        fetcher=lambda: [item], now=now + timedelta(minutes=5),
    )

    reactions = [row for row in journal_rows if row.get("kind") == "NEWS_REACTION"]
    assert second["alerts"] == 0
    assert reactions == []
    assert second["pending"] == 1

def test_alert_scorecard_does_not_score_tp_sl_with_directionally_invalid_brackets():
    from datetime import datetime, timedelta, timezone
    from telegram.news_monitor import build_alert_scorecard

    sent = datetime(2026, 10, 24, 8, 0, tzinfo=timezone.utc)
    observed = sent + timedelta(minutes=20)
    rows = [
        # LONG stop is incorrectly above the reference price.
        {"kind": "NEWS_ALERT_SENT", "event_id": "bad-long-bracket", "asset": "WTI",
         "direction": "LONG", "price": 80.0, "stop": 81.0, "tp1": 82.0,
         "sent_at": sent.isoformat()},
        {"kind": "NEWS_REACTION", "event_id": "bad-long-bracket", "asset": "WTI",
         "current_price": 81.5, "observed_at": observed.isoformat()},
        # SHORT stop is incorrectly below the reference price.
        {"kind": "NEWS_ALERT_SENT", "event_id": "bad-short-bracket", "asset": "Gold",
         "direction": "SHORT", "price": 4000.0, "stop": 3990.0, "tp1": 3950.0,
         "sent_at": sent.isoformat()},
        {"kind": "NEWS_REACTION", "event_id": "bad-short-bracket", "asset": "Gold",
         "current_price": 3995.0, "observed_at": observed.isoformat()},
    ]

    report = build_alert_scorecard(rows, now=sent + timedelta(hours=1))

    assert report["alerts"] == 2
    assert report["scored"] == 2
    assert report["invalid_level_alerts"] == 2
    assert report["tp1_observed"] == 0
    assert report["sl_observed"] == 0
    assert report["open_at_last_check"] == 2

def test_alert_scorecard_coverage_uses_eligible_alerts_not_raw_journal_rows():
    from datetime import datetime, timedelta, timezone
    from telegram.news_monitor import build_alert_scorecard

    sent = datetime(2026, 10, 21, 18, 0, tzinfo=timezone.utc)
    rows = [
        {"kind": "NEWS_ALERT_SENT", "event_id": "ambiguous", "asset": "WTI",
         "direction": "LONG", "price": 80.0, "stop": 79.0, "tp1": 81.0,
         "sent_at": sent.isoformat()},
        {"kind": "NEWS_ALERT_SENT", "event_id": "ambiguous", "asset": "WTI",
         "direction": "SHORT", "price": 80.0, "stop": 81.0, "tp1": 79.0,
         "sent_at": sent.isoformat()},
        {"kind": "NEWS_ALERT_SENT", "event_id": "valid", "asset": "Brent",
         "direction": "LONG", "price": 80.0, "sent_at": sent.isoformat()},
        {"kind": "NEWS_REACTION", "event_id": "valid", "asset": "Brent",
         "current_price": 80.2, "observed_at": (sent + timedelta(minutes=20)).isoformat()},
    ]

    report = build_alert_scorecard(rows, now=sent + timedelta(hours=1))

    assert report["alerts"] == 3
    assert report["eligible_alerts"] == 1
    assert report["scored"] == 1
    assert report["ambiguous_alert_groups"] == 1
    assert report["coverage_pct"] == 100.0

def test_alert_scorecard_flags_tp_sl_path_ambiguous_after_long_observation_gap():
    from datetime import datetime, timedelta, timezone
    from telegram.news_monitor import build_alert_scorecard

    sent = datetime(2026, 10, 24, 8, 0, tzinfo=timezone.utc)
    rows = [
        {"kind": "NEWS_ALERT_SENT", "event_id": "gap-tp", "asset": "WTI",
         "direction": "LONG", "price": 80.0, "stop": 79.0, "tp1": 81.0,
         "sent_at": sent.isoformat()},
        {"kind": "NEWS_REACTION", "event_id": "gap-tp", "asset": "WTI",
         "current_price": 80.2, "observed_at": (sent + timedelta(minutes=20)).isoformat()},
        # The 30-minute gap is greater than the scorecard's 15-minute floor.
        {"kind": "NEWS_REACTION", "event_id": "gap-tp", "asset": "WTI",
         "current_price": 81.1, "observed_at": (sent + timedelta(minutes=50)).isoformat()},
    ]

    report = build_alert_scorecard(rows, now=sent + timedelta(hours=1))

    assert report["scored"] == 1
    assert report["tp1_observed"] == 1
    assert report["sl_observed"] == 0
    assert report["path_ambiguous_alerts"] == 1
    assert report["observation_gap_limit_minutes"] == 15.0
