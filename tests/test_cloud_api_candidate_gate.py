"""Regression tests for fail-closed paper-entry authorization in cloud_api."""
from cloud_api import _is_authorized_paper_candidate


def test_watch_and_wait_candidates_cannot_open_aggressive_paper_positions():
    assert not _is_authorized_paper_candidate({"action": "PAPER_WATCH"})
    assert not _is_authorized_paper_candidate({"action": "WAIT"})
    assert not _is_authorized_paper_candidate({})
    assert not _is_authorized_paper_candidate(None)


def test_only_governor_authorized_actions_can_enter_aggressive_paper_positions():
    assert _is_authorized_paper_candidate({"action": "PAPER_ENTRY"})
    assert _is_authorized_paper_candidate({"action": "PAPER_SIGNAL"})
    assert not _is_authorized_paper_candidate({"action": "paper_watch"})
