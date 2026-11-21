from datetime import datetime, timedelta, timezone
from io import BytesIO
from urllib.parse import parse_qs

from invest_v2 import gagarin_runner
from invest_v2.gagarin import Bar
from invest_v3.engine import evaluate
from invest_v3.macro import bls_release, compare, gdp_reading, rate_readings
from invest_v3.news import classify, reviews
from invest_v3.scan import build_rows, check_market

NOW = datetime(2026, 11, 20, 15, 5, tzinfo=timezone.utc)


def test_catalyst_direction_requires_evidence_for_the_linked_issuer():
    assert classify("IR", "Example posts third quarter financial results", "", "EXM")[:2] == ("Trimestrale", None)
    assert classify("IR", "Example EPS beats analyst estimates", "", "EXM")[:2] == ("Trimestrale", "LONG")
    assert classify("IR", "Example EPS beats estimates but cuts its full-year guidance", "", "EXM")[1] is None
    assert classify("IR", "Example wins a $40 million contract", "", "EXM")[:2] == ("Contratto", "LONG")
    assert classify("IR", "Example to acquire Contoso", "", "EXM")[:2] == ("Acquisizione", None)
    assert classify("IR", "Example (NYSE: EXM) to be acquired at a 21% premium", "", "EXM")[:2] == ("Acquisizione", "LONG")
    assert classify("FDA", "FDA approves Example therapy", "", "EXM")[:2] == ("Decisione FDA", "LONG")
    assert classify("SEC EDGAR", "8-K", "Item 2.02: Results of Operations", "EXM")[:2] == ("Trimestrale", None)
    assert classify("SEC EDGAR", "8-K", "Item 1.03: Bankruptcy or Receivership", "EXM")[1] == "SHORT"


def test_macro_keeps_official_readings_expectations_and_revisions_separate():
    data = b"""<pre>Transmission of material in this news release is embargoed until USDL-26-1632
    8:30 a.m. (ET) Friday, November 6, 2026
    THE EMPLOYMENT SITUATION - OCTOBER 2026
    Total nonfarm payroll employment rose by 165,000 in October, and the unemployment rate changed
    little at 4.1 percent. The change in total nonfarm payroll employment for August was revised up
    by 53,000, from +133,000 to +186,000, and the change for September was revised up by 31,000,
    from +29,000 to +60,000.</pre>"""
    published, figures = bls_release(data, cpi=False)
    assert published.astimezone(timezone.utc).isoformat() == "2026-11-06T13:30:00+00:00"
    nfp, unemployment = figures
    assert unemployment["actual"] == 4.1
    forecast = {"series": "NFP", "period": "2026-10", "unit": "jobs", "value": 150000,
                "source": "https://example.com/forecast", "as_of": "2026-11-06T13:20:00Z"}
    result = compare(nfp, published, [forecast, {**forecast, "as_of": "2026-11-06T13:31:00Z", "value": 1},
                                      {**forecast, "unit": "pct", "value": 1}])
    assert (result["actual"], result["expected"]["value"], result["surprise"]) == (165000, 150000, 15000)
    assert [(item["period"], item["delta"]) for item in result["revision_deltas"]] == [
        ("2026-08", 53000), ("2026-09", 31000),
    ]
    assert result["direction"] is None and compare(nfp, published, [])["surprise"] is None


def test_cpi_gdp_and_fomc_basis_and_vintages():
    cpi = b"""<p>Transmission of material in this release is embargoed until
    8:30 a.m. (ET) Tuesday, November 10, 2026</p>
    <h2>CONSUMER PRICE INDEX - OCTOBER 2026</h2>
    <p>The Consumer Price Index for All Urban Consumers (CPI-U) decreased 0.4 percent on a
    seasonally adjusted basis in October after rising 0.6 percent in September.</p>"""
    _, cpi_figures = bls_release(cpi, cpi=True)
    assert cpi_figures[0]["actual"] == -0.4
    assert cpi_figures[0]["revisions"] == []
    gdp = gdp_reading("GDP (Second Estimate), 3rd Quarter 2026",
                      "Real gross domestic product (GDP) increased at an annual rate of 3.4 percent. "
                      "The increase in real GDP was revised down 0.2 percentage point.")
    actual = compare(gdp, NOW, [{"series": "GDP", "period": "2026-Q3", "unit": "pct_qoq_annualized",
                                 "edition": "advance estimate", "as_of": "2026-11-19T14:00:00Z",
                                 "source": "https://example.com", "value": 3.1}])
    assert actual["expected"] is None
    assert actual["revisions"] == [{"period": "2026-Q3", "previous": 3.6, "revised": 3.4}]
    lower, upper = rate_readings(b"maintain the target range for the federal funds rate at 3-3/4 to 4 percent", NOW)
    assert (lower["actual"], upper["actual"]) == (3.75, 4)


def test_scan_explains_missing_catalog_ambiguous_macro_and_stale_bars():
    feed = b"""<rss><channel><item><title>Example raises guidance (NYSE: EXM)</title>
    <link>https://example.com/release</link>
    <pubDate>Fri, 20 Nov 2026 15:00:00 GMT</pubDate></item></channel></rss>"""
    detected = list(reviews(feed, source="IR", now=NOW, directory={}))
    args = {"market": None, "opened": NOW, "clock": lambda: NOW}
    missing = build_rows(detected, universe=None, **args)[0]
    excluded = build_rows(detected, universe={}, **args)[0]
    assert missing["selected"] is None and "non verificabile" in missing["exclusion"]
    assert not excluded["selected"] and "non presente" in excluded["exclusion"]
    macro = list(reviews(feed, source="BLS", now=NOW, directory={}))[0]
    assert not macro[0].direction and "nessuna direzione" in macro[1]
    event = detected[0][0]
    assert evaluate(event, [], NOW)[1] == "barre concluse assenti"
    assert evaluate(event, [Bar(100, 101, 99, 4000, NOW - timedelta(minutes=4))], NOW)[1].startswith("ultima barra scaduta")


def test_closed_market_preflight_distinguishes_history_from_freshness():
    class Market:
        feed = "iex"

        def bars(self, symbols, *, start, end):
            assert start < end
            return {symbols[0]: [Bar(100, 101, 99, 4000, end)]}

    premarket = NOW.replace(hour=9)
    report = check_market(Market(), {}, premarket, None)
    assert report["stato"] == "storico / scaduto"
    assert report["eta_secondi"] > 120


def test_telegram_transport_requires_confirmed_message(monkeypatch):
    responses = iter([b'{"ok":false}', b'{"ok":true,"result":{"message_id":42}}'])

    def opened(request, timeout):
        assert parse_qs(request.data.decode()) == {"chat_id": ["test-chat"], "text": ["segnale paper"]}
        return BytesIO(next(responses))

    monkeypatch.setattr(gagarin_runner, "urlopen", opened)
    assert not gagarin_runner.send_telegram("segnale paper", token="test-token", chat_id="test-chat")
    assert gagarin_runner.send_telegram("segnale paper", token="test-token", chat_id="test-chat")
