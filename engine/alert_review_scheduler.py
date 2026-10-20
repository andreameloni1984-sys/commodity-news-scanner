"""Daily Telegram alert-review scheduler (21:00 Europe/Rome)."""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def daily_alert_review_tick(send_fn, *, now=None, marker_path=None) -> bool:
    """Deliver at most one review per local day; return True only when sent."""
    now = now or datetime.now(ZoneInfo("Europe/Rome"))
    if now.tzinfo is None:
        now = now.replace(tzinfo=ZoneInfo("Europe/Rome"))
    local_now = now.astimezone(ZoneInfo("Europe/Rome"))
    if local_now.hour != 21:
        return False

    day = local_now.date().isoformat()
    marker_path = Path(marker_path or os.getenv(
        "GAGARIN_ALERT_REVIEW_SCHEDULE_FILE",
        "data/gagarin_alert_review_schedule.json",
    ))
    last_day = None
    try:
        if os.getenv("DATABASE_URL", "").strip():
            from state_store import ensure_schema, load_state
            if ensure_schema():
                last_day = load_state("gagarin_alert_review_last_day")
        if not last_day and marker_path.exists():
            last_day = json.loads(marker_path.read_text(encoding="utf-8")).get("last_day")
    except Exception as exc:
        print("GAGARIN ALERT REVIEW SCHEDULE READ ERROR | %s: %s" % (type(exc).__name__, exc), flush=True)
    if last_day == day:
        return False

    from engine.feedback import format_alert_review
    message = format_alert_review(limit=10, day=day)
    if not send_fn(message):
        print("GAGARIN ALERT REVIEW | delivery failed; retrying during 21:00 hour", flush=True)
        return False

    saved = False
    try:
        if os.getenv("DATABASE_URL", "").strip():
            from state_store import ensure_schema, save_state
            if ensure_schema():
                saved = save_state("gagarin_alert_review_last_day", day)
        if not saved:
            marker_path.parent.mkdir(parents=True, exist_ok=True)
            temp = marker_path.with_suffix(marker_path.suffix + ".tmp")
            temp.write_text(json.dumps({"last_day": day}), encoding="utf-8")
            temp.replace(marker_path)
            saved = True
    except Exception as exc:
        print("GAGARIN ALERT REVIEW SCHEDULE SAVE ERROR | %s: %s" % (type(exc).__name__, exc), flush=True)
    print("GAGARIN ALERT REVIEW | delivered=YES | date=%s | marker_saved=%s" % (day, saved), flush=True)
    return True
