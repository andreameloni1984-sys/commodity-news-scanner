from __future__ import annotations

import os
import requests

BASE_URL = os.getenv("GAGARIN_CLOUD_URL", "https://gagarin-cloud.onrender.com").rstrip("/")
API_KEY = os.getenv("CLOUD_API_KEY", "").strip()

if not API_KEY:
    raise SystemExit("CLOUD_API_KEY is required")

response = requests.post(
    f"{BASE_URL}/api/run",
    headers={"X-API-Key": API_KEY},
    timeout=180,
)
response.raise_for_status()
data = response.json()

portfolio = data.get("portfolio", {})
signals = data.get("signals", [])
print(
    "GAGARIN MONITOR | "
    f"{data.get('timestamp_utc')} | "
    f"signals={len(signals)} | "
    f"cash={portfolio.get('cash')} | "
    f"equity={portfolio.get('equity')}"
)
