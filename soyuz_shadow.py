"""
SOYUZ GAGARIN — SHADOW MODE v1.0

Scopo:
    Confrontare la decisione del bot esistente con SOYUZ.

SICUREZZA:
    - nessun ordine
    - nessun Telegram
    - nessuna modifica all'analisi originale
    - nessun bypass di Gagarin
    - nessuna modifica alla decisione operativa esistente

SOYUZ lavora esclusivamente in osservazione.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict

from soyuz_real_adapter import (
    SoyuzRealAdapter,
)


# ============================================================
# RESULT
# ============================================================

@dataclass
class ShadowResult:
    commodity: str

    bot_direction: str
    soyuz_direction: str

    bot_authorized: bool
    soyuz_authorized: bool

    direction_agreement: bool
    authorization_agreement: bool

    soyuz_state: str

    divergence: bool

    reasons: list[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================
# HELPERS
# ============================================================

def _direction(value: Any) -> str:

    value = str(
        value or "WAIT"
    ).upper().strip()

    if value in {
        "BUY",
        "LONG",
        "CALL",
    }:
        return "LONG"

    if value in {
        "SELL",
        "SHORT",
        "PUT",
    }:
        return "SHORT"

    return "WAIT"


def _bool(value: Any) -> bool:

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.strip().lower() in {
            "1",
            "true",
            "yes",
            "y",
            "ok",
            "authorized",
            "confirmed",
        }

    return bool(value)


# ============================================================
# SHADOW ENGINE
# ============================================================

class SoyuzShadow:

    def __init__(
        self,
        adapter: SoyuzRealAdapter | None = None,
    ) -> None:

        self.adapter = (
            adapter
            or SoyuzRealAdapter()
        )

    def evaluate(
        self,
        commodity: str,
        analysis: Dict[str, Any],
    ) -> ShadowResult:

        result = self.adapter.evaluate(
            commodity=commodity,
            analysis=analysis,
        )

        soyuz = result.get(
            "soyuz",
            {},
        )

        existing = result.get(
            "existing_bot",
            {},
        )

        bot_direction = _direction(
            existing.get(
                "setup_direction",
                "WAIT",
            )
        )

        soyuz_direction = _direction(
            soyuz.get(
                "direction",
                "WAIT",
            )
        )

        bot_authorized = _bool(
            existing.get(
                "operational_entry_allowed",
                False,
            )
        )

        soyuz_authorized = _bool(
            soyuz.get(
                "gagarin_authorized",
                False,
            )
        )

        direction_agreement = (
            bot_direction
            == soyuz_direction
        )

        authorization_agreement = (
            bot_authorized
            == soyuz_authorized
        )

        divergence = not (
            direction_agreement
            and authorization_agreement
        )

        reasons = []

        if not direction_agreement:

            reasons.append(
                "DIRECTION_DIVERGENCE"
            )

        if not authorization_agreement:

            reasons.append(
                "AUTHORIZATION_DIVERGENCE"
            )

        if soyuz_direction == "WAIT":

            reasons.append(
                "SOYUZ_NO_DIRECTION"
            )

        if soyuz_authorized:

            reasons.append(
                "SOYUZ_GAGARIN_AUTHORIZED"
            )

        if bot_authorized:

            reasons.append(
                "EXISTING_BOT_AUTHORIZED"
            )

        return ShadowResult(
            commodity=commodity,

            bot_direction=bot_direction,
            soyuz_direction=soyuz_direction,

            bot_authorized=bot_authorized,
            soyuz_authorized=soyuz_authorized,

            direction_agreement=direction_agreement,
            authorization_agreement=authorization_agreement,

            soyuz_state=str(
                soyuz.get(
                    "state",
                    "UNKNOWN",
                )
            ),

            divergence=divergence,

            reasons=reasons,
        )


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================

def evaluate_shadow(
    commodity: str,
    analysis: Dict[str, Any],
) -> ShadowResult:

    engine = SoyuzShadow()

    return engine.evaluate(
        commodity=commodity,
        analysis=analysis,
    )


# ============================================================
# TELEGRAM-SAFE SUMMARY
# ============================================================

def shadow_summary(
    result: ShadowResult,
) -> str:

    return (
        f"SOYUZ SHADOW | "
        f"{result.commodity} | "
        f"BOT={result.bot_direction} | "
        f"SOYUZ={result.soyuz_direction} | "
        f"BOT_AUTH="
        f"{'YES' if result.bot_authorized else 'NO'} | "
        f"SOYUZ_AUTH="
        f"{'YES' if result.soyuz_authorized else 'NO'} | "
        f"STATE={result.soyuz_state} | "
        f"DIVERGENCE="
        f"{'YES' if result.divergence else 'NO'}"
    )