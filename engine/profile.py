"""Runtime profile selector for Gagarin. Defaults to SOFT and persists locally."""
import json
import os
from pathlib import Path

_STATE_PATH = Path(os.getenv("GAGARIN_PROFILE_STATE", "gagarin_profile_state.json"))
_VALID = {"SOFT", "AGGRESSIVE"}

def get_profile() -> str:
    try:
        value = json.loads(_STATE_PATH.read_text(encoding="utf-8")).get("profile", "SOFT")
        value = str(value).upper()
        return value if value in _VALID else "SOFT"
    except (OSError, ValueError, AttributeError):
        return "SOFT"

def set_profile(profile: str) -> str:
    value = str(profile).strip().upper()
    if value not in _VALID:
        raise ValueError("Profile must be SOFT or AGGRESSIVE")
    try:
        _STATE_PATH.write_text(json.dumps({"profile": value}, indent=2), encoding="utf-8")
    except OSError:
        # The process still applies the selected profile for this run.
        global _runtime_profile
        _runtime_profile = value
    else:
        global _runtime_profile
        _runtime_profile = value
    return value

_runtime_profile = None
_original_get_profile = get_profile
def get_profile() -> str:
    if _runtime_profile in _VALID:
        return _runtime_profile
    return _original_get_profile()
