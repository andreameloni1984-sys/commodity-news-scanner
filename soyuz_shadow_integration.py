"""
SOYUZ GAGARIN — SHADOW INTEGRATION v1.0

Integrazione NON invasiva con commodity_bot.py.

Regole:
- SOYUZ non decide l'entry
- SOYUZ non modifica analysis
- SOYUZ non modifica operational_entry_allowed
- SOYUZ non invia Telegram
- SOYUZ non esegue ordini
- un errore SOYUZ non deve fermare commodity_bot.py
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from soyuz_shadow_bridge import (
    SoyuzShadowBridge,
)


_SHADOW_BRIDGE: Optional[SoyuzShadowBridge] = None


def _get_bridge() -> SoyuzShadowBridge:
    global _SHADOW_BRIDGE

    if _SHADOW_BRIDGE is None:
        _SHADOW_BRIDGE = SoyuzShadowBridge()

    return _SHADOW_BRIDGE


def run_shadow_safe(
    commodity: str,
    analysis: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    Esegue SOYUZ in modalità Shadow.

    In caso di errore restituisce None:
    il bot principale deve continuare normalmente.
    """

    try:

        bridge = _get_bridge()

        result = bridge.analyze(
            commodity=commodity,
            analysis=analysis,
        )

        return bridge.diagnostic(
            result
        )

    except Exception as exc:

        # IMPORTANTISSIMO:
        # mai propagare l'errore al motore principale.

        return {
            "commodity": commodity,
            "shadow_error": True,
            "error": type(exc).__name__,
            "message": str(exc),
        }


def shadow_enabled() -> bool:
    """
    Flag semplice per permettere al bot
    di sapere se l'integrazione è disponibile.
    """

    try:
        _get_bridge()
        return True

    except Exception:
        return False