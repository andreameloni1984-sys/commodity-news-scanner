"""Tests for the forex aggressive block in Soyuz Gagarin."""

from soyuz_gagarin.config import GagarinConfig


def test_aggressive_profile_thresholds():
    cfg = GagarinConfig(profile_name="AGGRESSIVE")
    assert cfg.min_probability == 50
    assert cfg.min_quality == 40
    assert cfg.min_confidence == 45
    assert cfg.min_rr == 2.5


def test_aggressive_profile_timeframes():
    cfg = GagarinConfig(profile_name="AGGRESSIVE")
    assert "5M" in cfg.timeframes
    assert "15M" in cfg.timeframes


def test_soft_profile_thresholds():
    cfg = GagarinConfig(profile_name="SOFT")
    assert cfg.min_probability == 68
    assert cfg.min_quality == 60
    assert cfg.min_confidence == 65


def test_env_override_takes_precedence():
    import os
    os.environ["MIN_ENTRY_PROBABILITY"] = "62"
    try:
        cfg = GagarinConfig(profile_name="AGGRESSIVE")
        assert cfg.min_probability == 62
    finally:
        del os.environ["MIN_ENTRY_PROBABILITY"]
