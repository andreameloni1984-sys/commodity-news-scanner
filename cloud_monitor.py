from __future__ import annotations

import os
from urllib.parse import urlsplit

import requests


def _monitor_config(environ=None) -> tuple[str, str]:
    """Load an explicitly configured HTTPS endpoint and API key.

    There is deliberately no provider-specific default. In particular, an
    unset URL must never send credentials to a legacy hosting endpoint.
    """
    env = os.environ if environ is None else environ
    base_url = str(env.get("GAGARIN_CLOUD_URL", "")).strip().rstrip("/")
    if not base_url:
        raise SystemExit(
            "GAGARIN_CLOUD_URL is required; no default endpoint is configured"
        )

    parsed = urlsplit(base_url)
    if (
        parsed.scheme.lower() != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise SystemExit(
            "GAGARIN_CLOUD_URL must be an HTTPS base URL without credentials, "
            "query, or fragment"
        )

    api_key = str(env.get("CLOUD_API_KEY", "")).strip()
    if not api_key:
        raise SystemExit("CLOUD_API_KEY is required")
    return base_url, api_key


def main(environ=None, post=None) -> dict:
    base_url, api_key = _monitor_config(environ)
    request_post = requests.post if post is None else post
    response = request_post(
        f"{base_url}/api/run",
        headers={"X-API-Key": api_key},
        timeout=180,
        allow_redirects=False,
    )
    if 300 <= response.status_code < 400:
        raise RuntimeError(
            "GAGARIN cloud endpoint returned a redirect; request was not followed"
        )
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise RuntimeError("GAGARIN cloud endpoint returned an invalid response")

    portfolio = data.get("portfolio", {})
    if not isinstance(portfolio, dict):
        portfolio = {}
    signals = data.get("signals", [])
    if not isinstance(signals, list):
        signals = []
    print(
        "GAGARIN MONITOR | "
        f"{data.get('timestamp_utc')} | "
        f"signals={len(signals)} | "
        f"cash={portfolio.get('cash')} | "
        f"equity={portfolio.get('equity')}"
    )
    return data


if __name__ == "__main__":
    main()
