import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_personal_dashboard_is_configured_as_installable_pwa():
    manifest = json.loads((ROOT / "static" / "manifest.webmanifest").read_text(encoding="utf-8"))
    html = (ROOT / "static" / "intelligence.html").read_text(encoding="utf-8")

    assert manifest["start_url"] == "/static/intelligence.html"
    assert manifest["scope"] == "/static/"
    assert manifest["display"] == "standalone"
    assert manifest["short_name"] == "Gagarin"
    assert '<link rel="manifest" href="/static/manifest.webmanifest">' in html
    assert "apple-mobile-web-app-capable" in html
    assert "serviceWorker.register('/static/sw.js'" in html


def test_service_worker_never_caches_private_api_responses():
    worker = (ROOT / "static" / "sw.js").read_text(encoding="utf-8")

    api_bypass = re.search(
        r'if\\s*\\(\\s*url\\.pathname\\.startsWith\\(\\s*["\\\']/api/["\\\']\\s*\\)\\s*\\)\\s*return\\s*;',
        worker,
    )
    assert api_bypass is not None, "API requests must bypass the service worker cache handler"

    first_cache_handler = worker.find("event.respondWith")
    assert first_cache_handler >= 0
    assert api_bypass.end() < first_cache_handler, (
        "The private API bypass must run before any cache-backed response handler"
    )
    assert '"/static/intelligence.html"' not in worker
