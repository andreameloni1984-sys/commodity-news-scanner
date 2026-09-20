"""
SOYUZ GAGARIN — SHADOW BRIDGE v1.0

Ponte passivo tra commodity_bot.py e SOYUZ.

SICUREZZA:
- non modifica l'analysis originale
- non modifica operational_entry_allowed
- non invia Telegram
- non esegue ordini
- non cambia la decisione del bot
- SOYUZ lavora esclusivamente in osservazione
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, List, Optional

from soyuz_shadow import SoyuzShadow, ShadowResult


class SoyuzShadowBridge:

    def __init__(
        self,
        engine: Optional[SoyuzShadow] = None,
    ) -> None:

        self.engine = engine or SoyuzShadow()

    # ========================================================
    # SINGLE ANALYSIS
    # ========================================================

    def analyze(
        self,
        commodity: str,
        analysis: Dict[str, Any],
    ) -> ShadowResult:

        if not isinstance(analysis, dict):
            raise TypeError(
                "analysis must be a dictionary"
            )

        # Copia difensiva:
        # SOYUZ non riceve mai il riferimento
        # all'oggetto originale del bot.
        safe_analysis = deepcopy(
            analysis
        )

        return self.engine.evaluate(
            commodity=commodity,
            analysis=safe_analysis,
        )

    # ========================================================
    # MULTI COMMODITY
    # ========================================================

    def analyze_many(
        self,
        analyses: Dict[str, Dict[str, Any]],
    ) -> List[ShadowResult]:

        results: List[ShadowResult] = []

        for commodity, analysis in analyses.items():

            if not isinstance(analysis, dict):
                continue

            result = self.analyze(
                commodity,
                analysis,
            )

            results.append(
                result
            )

        return results

    # ========================================================
    # SAFE SUMMARY
    # ========================================================

    @staticmethod
    def summary(
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

    # ========================================================
    # DIAGNOSTIC EXPORT
    # ========================================================

    @staticmethod
    def diagnostic(
        result: ShadowResult,
    ) -> Dict[str, Any]:

        return {
            "commodity": result.commodity,

            "bot": {
                "direction": result.bot_direction,
                "authorized": result.bot_authorized,
            },

            "soyuz": {
                "direction": result.soyuz_direction,
                "authorized": result.soyuz_authorized,
                "state": result.soyuz_state,
            },

            "comparison": {
                "direction_agreement":
                    result.direction_agreement,

                "authorization_agreement":
                    result.authorization_agreement,

                "divergence":
                    result.divergence,
            },

            "reasons": list(
                result.reasons
            ),
        }


# ============================================================
# SAFE CONVENIENCE FUNCTION
# ============================================================

def run_soyuz_shadow(
    commodity: str,
    analysis: Dict[str, Any],
) -> ShadowResult:

    bridge = SoyuzShadowBridge()

    return bridge.analyze(
        commodity=commodity,
        analysis=analysis,
    )


def run_soyuz_shadow_many(
    analyses: Dict[str, Dict[str, Any]],
) -> List[ShadowResult]:

    bridge = SoyuzShadowBridge()

    return bridge.analyze_many(
        analyses
    )