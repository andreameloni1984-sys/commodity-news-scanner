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


def test_dashboard_api_keys_are_not_persisted_in_browser_storage():
    html = (ROOT / "static" / "intelligence.html").read_text(encoding="utf-8")
    aggressive = (ROOT / "static" / "aggressive.html").read_text(encoding="utf-8")
    legacy_dashboard = (ROOT / "cloud_api.py").read_text(encoding="utf-8")

    assert 'id="apiKey" type="password"' in html
    assert 'autocomplete="off"' in html
    assert "localStorage" not in html
    assert "sessionStorage" not in html
    assert "$('apiKey').value='';" in html

    assert 'id="key" type="password"' in aggressive
    assert 'autocomplete="off"' in aggressive
    assert "localStorage" not in aggressive
    assert "sessionStorage" not in aggressive
    assert "pagehide" in aggressive

    # The unused legacy inline dashboard must not reintroduce browser key storage.
    assert "localStorage" not in legacy_dashboard
    assert "sessionStorage" not in legacy_dashboard


def test_every_static_html_application_requires_a_private_session():
    cloud_api = (ROOT / "cloud_api.py").read_text(encoding="utf-8")

    assert 'request.url.path.startswith("/static/") and request.url.path.lower().endswith(".html")' in cloud_api
    assert '_valid_app_session(request.cookies.get(_APP_COOKIE))' in cloud_api
    assert 'return RedirectResponse("/login", status_code=303)' in cloud_api


def test_inline_dashboard_javascript_parses():
    import re
    import shutil
    import subprocess
    import tempfile

    html = (ROOT / "static" / "intelligence.html").read_text(encoding="utf-8")
    scripts = [
        script
        for script in re.findall(
            r"<script\b[^>]*>(.*?)</script>", html, flags=re.IGNORECASE | re.DOTALL
        )
        if script.strip()
    ]

    assert scripts
    assert r"\n$('logout')" not in html

    node = shutil.which("node")
    if node:
        for script in scripts:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".js", encoding="utf-8"
            ) as source:
                source.write(script)
                source.flush()
                subprocess.run(
                    [node, "--check", source.name],
                    check=True,
                    capture_output=True,
                    text=True,
                )


def test_private_dashboard_environment_example_documents_secrets_without_values():
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    lines = [line.strip() for line in env_example.splitlines()]

    for name in ("APP_PASSWORD_HASH", "APP_SESSION_SECRET", "CLOUD_API_KEY"):
        assignments = [line for line in lines if line.startswith(f"{name}=")]
        assert assignments == [f"{name}="]

    assert "getpass.getpass" in env_example
    assert "secrets.token_urlsafe(48)" in env_example
    assert "200000..2000000" in env_example
    assert "backend Environment UI" in env_example


def test_ios_home_screen_icon_is_png_and_cached():
    import struct

    manifest = json.loads((ROOT / "static" / "manifest.webmanifest").read_text(encoding="utf-8"))
    html = (ROOT / "static" / "intelligence.html").read_text(encoding="utf-8")
    worker = (ROOT / "static" / "sw.js").read_text(encoding="utf-8")
    icon_path = ROOT / "static" / "apple-touch-icon.png"
    icon = icon_path.read_bytes()

    assert '<link rel="apple-touch-icon" href="/static/apple-touch-icon.png">' in html
    assert any(
        item.get("src") == "/static/apple-touch-icon.png"
        and item.get("sizes") == "180x180"
        and item.get("type") == "image/png"
        for item in manifest["icons"]
    )
    assert icon[:8] == bytes([137, 80, 78, 71, 13, 10, 26, 10])
    assert struct.unpack(">II", icon[16:24]) == (180, 180)
    assert '"/static/apple-touch-icon.png"' in worker
    assert "gagarin-personal-app-v2" in worker
