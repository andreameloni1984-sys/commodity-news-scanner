"""Test in SOLA LETTURA del conto Trading 212 Invest DEMO: python -m cfdbot.t212_demo_check

Legge saldo e posizioni. Non inserisce, modifica o cancella ordini.
Le chiavi non vengono mai stampate.
"""
from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.request

from . import notify

DEMO_BASE = "https://demo.trading212.com/api/v0"


def _headers(key: str, secret: str) -> list[tuple[str, dict]]:
    """Prova prima l'autenticazione chiave+segreto (Basic), poi la vecchia con la sola chiave."""
    out = []
    if key and secret:
        token = base64.b64encode(f"{key}:{secret}".encode()).decode()
        out.append(("chiave + segreto", {"Authorization": f"Basic {token}"}))
    if key:
        out.append(("sola chiave", {"Authorization": key}))
    return out


def _get(path: str, headers: dict) -> tuple[int, object]:
    req = urllib.request.Request(DEMO_BASE + path, headers={**headers, "User-Agent": "Gagarin-demo-check"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read().decode("utf-8")
            return r.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:  # noqa: BLE001
        return 0, type(e).__name__


def split_credentials(key: str, secret: str) -> tuple[str, str, str]:
    """Gestisce chiave e segreto incollati insieme nello stesso secret (su due righe o con ':')."""
    key, secret = key.strip(), secret.strip()
    note = ""
    parts = [p.strip() for p in key.replace("\r", "\n").split("\n") if p.strip()]
    if len(parts) >= 2:
        note = "il secret della chiave contiene più righe: uso la prima come chiave e la seconda come segreto"
        key = parts[0]
        secret = secret or parts[1]
    elif not secret and ":" in key:
        note = "il secret della chiave contiene 'chiave:segreto': li separo"
        key, secret = (x.strip() for x in key.split(":", 1))
    key = "".join(key.split())
    secret = "".join(secret.split())
    return key, secret, note


def describe(value: str) -> str:
    return f"{len(value)} caratteri" if value else "assente"


def run() -> tuple[bool, str]:
    raw_key = os.getenv("T212_API_KEY", "")
    raw_secret = os.getenv("T212_API_SECRET", "")
    source = os.getenv("T212_KEY_SOURCE", "non trovato")
    key, secret, note = split_credentials(raw_key, raw_secret)
    if not key:
        return False, ("🧪 TEST TRADING 212 DEMO — ❌ chiavi non trovate\n"
                       "Nessun secret T212_API_KEY / GAGARIN_DEMO_KEY / TRADING212_DEMO_API_KEY nel repository.")
    attempts = []
    for label, headers in _headers(key, secret):
        status, cash = _get("/equity/account/cash", headers)
        if status == 200 and isinstance(cash, dict):
            _, info = _get("/equity/account/info", headers)
            pstatus, positions = _get("/equity/portfolio", headers)
            currency = info.get("currencyCode", "") if isinstance(info, dict) else ""
            lines = [
                "🧪 TEST TRADING 212 DEMO — ✅ collegamento riuscito",
                f"Chiavi lette da: {source} · autenticazione: {label}",
                *( [f"Nota: {note}"] if note else [] ),
                "",
                f"Valore totale: {cash.get('total', 'n.d.')} {currency}",
                f"Liquidità disponibile: {cash.get('free', 'n.d.')} {currency}",
                f"Investito: {cash.get('invested', 'n.d.')} {currency}",
                f"Profitto/perdita aperti: {cash.get('ppl', 'n.d.')} {currency}",
            ]
            if pstatus == 200 and isinstance(positions, list):
                lines.append(f"Posizioni aperte: {len(positions)}")
                for p in positions[:5]:
                    lines.append(f"• {p.get('ticker')} · quantità {p.get('quantity')} · P/L {p.get('ppl')}")
            lines += ["", "Test in sola lettura: nessun ordine inserito. Conto DEMO, nessun denaro reale."]
            return True, "\n".join(lines)
        attempts.append(f"{label}: HTTP {status}" if status else f"{label}: errore ({cash})")
    hint = ("Controlla che la chiave sia del conto DEMO (non reale), che abbia i permessi di lettura "
            "account/portafoglio e che non sia limitata a indirizzi IP specifici.")
    return False, "\n".join([
        "🧪 TEST TRADING 212 DEMO — ❌ accesso rifiutato",
        f"Chiavi lette da: {source} · chiave {describe(key)} · segreto {describe(secret)}",
        *( [f"Nota: {note}"] if note else [] ),
        "Tentativi: " + "; ".join(attempts),
        hint,
    ])


def main() -> int:
    ok, text = run()
    print(text)
    if notify.configured():
        notify.send(text)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
