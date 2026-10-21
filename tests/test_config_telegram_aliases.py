import os
import subprocess
import sys


def _load_token_with_env(env):
    result = subprocess.run(
        [sys.executable, "-c", "import config; print(config.TELEGRAM_BOT_TOKEN)"],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return result.stdout.strip()


def test_canonical_telegram_token_takes_precedence_over_aliases():
    env = os.environ.copy()
    for key in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_TOKEN", "BOT_TOKEN"):
        env.pop(key, None)
    env["TELEGRAM_BOT_TOKEN"] = "canonical-value"
    env["TELEGRAM_TOKEN"] = "legacy-value"
    assert _load_token_with_env(env) == "canonical-value"


def test_existing_telegram_token_alias_is_accepted():
    env = os.environ.copy()
    for key in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_TOKEN", "BOT_TOKEN"):
        env.pop(key, None)
    env["TELEGRAM_TOKEN"] = "existing-render-value"
    assert _load_token_with_env(env) == "existing-render-value"


def test_bot_token_alias_is_accepted():
    env = os.environ.copy()
    for key in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_TOKEN", "BOT_TOKEN"):
        env.pop(key, None)
    env["BOT_TOKEN"] = "existing-bot-value"
    assert _load_token_with_env(env) == "existing-bot-value"
