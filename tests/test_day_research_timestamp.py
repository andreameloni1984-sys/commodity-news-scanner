import json

import engine.day_research as day_research


def test_unchanged_hourly_research_does_not_advance_timestamp(tmp_path, monkeypatch):
    output = tmp_path / "day_research.json"
    monkeypatch.setattr(day_research, "OUT", output)
    timestamps = iter(("2026-10-22T10:00:00Z", "2026-10-22T11:00:00Z"))
    monkeypatch.setattr(day_research, "_now", lambda: next(timestamps))

    first = day_research.run()
    first_timestamp = first["updated_at"]
    second = day_research.run()

    # The clock advanced by an hour, but identical research must keep its
    # original audit timestamp. This cannot pass merely because runs share a
    # timestamp at second-level precision.
    assert second["updated_at"] == first_timestamp == "2026-10-22T10:00:00Z"
    assert json.loads(output.read_text(encoding="utf-8"))["updated_at"] == first_timestamp


def test_changed_research_content_advances_timestamp(tmp_path, monkeypatch):
    output = tmp_path / "day_research.json"
    monkeypatch.setattr(day_research, "OUT", output)
    day_research.run()

    original_build = day_research.build

    def changed_build():
        report = original_build()
        report["notes"] = dict(report["notes"])
        report["notes"]["new_test_note"] = {"description": "changed"}
        report["updated_at"] = "2099-01-01T00:00:00Z"
        return report

    monkeypatch.setattr(day_research, "build", changed_build)
    second = day_research.run()

    assert second["updated_at"] == "2099-01-01T00:00:00Z"
    assert "new_test_note" in json.loads(output.read_text(encoding="utf-8"))["notes"]
