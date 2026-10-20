"""Tests for the forex aggressive block in Soyuz Gagarin."""

import pytest

from soyuz_gagarin.config import GagarinConfig


PROFILE_OVERRIDE_KEYS = (
    "MIN_ENTRY_PROBABILITY",
    "MIN_ENTRY_QUALITY",
    "MIN_ENTRY_CONFIDENCE",
    "MIN_ENTRY_RR",
    "MAX_ENTRY_STOP_ATR",
)


@pytest.fixture
def clean_profile_env(monkeypatch):
    """Profile-default tests must not inherit workflow-level risk overrides."""
    for key in PROFILE_OVERRIDE_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_aggressive_profile_thresholds(clean_profile_env):
    cfg = GagarinConfig(profile_name="AGGRESSIVE")
    assert cfg.min_probability == 50
    assert cfg.min_quality == 40
    assert cfg.min_confidence == 45
    assert cfg.min_rr == 2.5


def test_aggressive_profile_timeframes(clean_profile_env):
    cfg = GagarinConfig(profile_name="AGGRESSIVE")
    assert "5M" in cfg.timeframes
    assert "15M" in cfg.timeframes


def test_soft_profile_thresholds(clean_profile_env):
    cfg = GagarinConfig(profile_name="SOFT")
    assert cfg.min_probability == 68
    assert cfg.min_quality == 60
    assert cfg.min_confidence == 65


def test_env_override_takes_precedence(monkeypatch, clean_profile_env):
    monkeypatch.setenv("MIN_ENTRY_PROBABILITY", "62")
    cfg = GagarinConfig(profile_name="AGGRESSIVE")
    assert cfg.min_probability == 62
