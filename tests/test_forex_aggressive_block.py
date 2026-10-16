"""Tests for the forex aggressive block in Soyuz Gagarin."""

from soyuz_gagarin.config import GagarinConfig


def test_aggressive_profile_thresholds():
    cfg = GagarinConfig(profile_name="AGGRESSIVE")
    assert cfg.min_probability == 55
    assert cfg.min_quality == 45
    assert cfg.min_confidence == 50
    assert cfg.min_rr == 2.5


def test_aggressive_profile_timeframes():
    cfg = GagarinConfig(profile_name="AGGRESSIVE")
    assert "5M" in cfg.timeframes
    assert "15M" in cfg.timeframes
