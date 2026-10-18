from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from research.intraday_windows import calculate_window_statistics, format_intraday_window_report


def _bars_for_window(day, start_hour, start_minute, count, price=100.0):
    rows = []
    start = datetime(2026, 10, day, start_hour, start_minute, tzinfo=ZoneInfo("Europe/Rome"))
    for i in range(count):
        local = start.timestamp() + i * 300
        rows.append({
            "timestamp": local,
            "open": price,
            "high": price + 0.5,
            "low": price - 0.5,
            "close": price + 0.1,
        })
    return rows


def test_calculate_window_statistics_returns_descriptive_metrics_only():
    rows = []
    rows += _bars_for_window(12, 8, 0, 36)
    rows += _bars_for_window(12, 14, 0, 48)
    rows += _bars_for_window(12, 15, 30, 30)
    stats = calculate_window_statistics(rows)
    assert [item["window"] for item in stats] == ["08:00–11:00", "14:00–18:00", "15:30–18:00"]
    assert all(item["n"] == 1 for item in stats)
    assert all(item["mean_range_pct"] is not None for item in stats)
    assert all(item["mean_close_open_pct"] is not None for item in stats)
    assert not any("win_rate" in item or "profit_factor" in item for item in stats)


def test_format_report_disclaims_profitability():
    report = {
        "assets": {
            name: {
                "symbol": symbol,
                "windows": [
                    {"window": label, "n": 2, "mean_range_pct": 0.4,
                     "median_range_pct": 0.3, "mean_close_open_pct": -0.1,
                     "median_close_open_pct": -0.05}
                    for label in ("08:00–11:00", "14:00–18:00", "15:30–18:00")
                ],
            }
            for name, symbol in (("Oro", "GC=F"), ("Argento", "SI=F"), ("WTI", "CL=F"), ("Brent", "BZ=F"))
        }
    }
    text = format_intraday_window_report(report)
    assert "non è un backtest" in text.lower()
    assert "Europe/Rome" in text
    assert "win rate" in text.lower()
