"""Runtime profile selector for Gagarin. Defaults to SOFT and persists locally."""
import json
import os
from pathlib import Path

_STATE_PATH = Path(os.getenv("GAGARIN_PROFILE_STATE", "gagarin_profile_state.json"))
_VALID = {"SOFT", "AGGRESSIVE"}
_runtime_profile = None


def get_profile() -> str:
    if _runtime_profile in _VALID:
        return _runtime_profile
    try:
        value = json.loads(_STATE_PATH.read_text(encoding="utf-8")).get("profile", "SOFT")
        value = str(value).upper()
        return value if value in _VALID else "SOFT"
    except (OSError, ValueError, AttributeError):
        return "SOFT"


def set_profile(profile: str) -> str:
    global _runtime_profile
    value = str(profile).strip().upper()
    if value not in _VALID:
        raise ValueError("Profile must be SOFT or AGGRESSIVE")
    _runtime_profile = value
    try:
        _STATE_PATH.write_text(json.dumps({"profile": value}, indent=2), encoding="utf-8")
    except OSError:
        # The selected profile remains active for this process.
        pass
    return value
