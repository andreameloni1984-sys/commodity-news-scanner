from telegram.news_monitor import GDELT_MIN_INTERVAL_SECONDS, RSS_FEEDS


def test_energy_feed_added():
    assert dict(RSS_FEEDS)["EIA / TODAY IN ENERGY"].endswith("todayinenergy.xml")


def test_gdelt_interval_has_rate_limit_guard():
    assert GDELT_MIN_INTERVAL_SECONDS >= 900
