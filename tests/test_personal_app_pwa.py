import json
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

    assert 'url.pathname.startsWith("/api/")' in worker
    assert "Never cache API responses" in worker
    assert "/static/intelligence.html" not in worker
