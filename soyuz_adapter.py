"""
SOYUZ GAGARIN — Adapter v1.0

Ponte tra commodity_bot.py e soyuz_motors.py.

IMPORTANTE:
- non esegue ordini
- non invia Telegram
- non modifica la decisione del bot esistente
- non bypassa Gagarin
- se un gate di sicurezza non è esplicitamente disponibile,
  il gate resta FALSE
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from soyuz_motors import SoyuzFusion, SoyuzDecision


# ============================================================
# HELPERS
# ============================================================

def _num(
    value: Any,
    default: float = 0.0,
) -> float:
    try:
        number = float(value)

        if number != number:
            return default

        return number

    except (TypeError, ValueError):
        return default


def _bool(
    value: Any,
    default: bool = False,
) -> bool:
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.strip().lower() in {
            "1",
            "true",
            "yes",
            "y",
            "ok",
            "confirmed",
            "authorized",
        }

    return bool(value)


def _first(
    data: Dict[str, Any],
    *keys: str,
    default: Any = None,
) -> Any:
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]

    return default


# ============================================================
# ADAPTER
# ============================================================

class SoyuzAdapter:
    """
    Traduce i dati già prodotti dal bot nel formato richiesto
    dai tre motori SOYUZ.
    """

    def __init__(
        self,
        fusion: Optional[SoyuzFusion] = None,
    ) -> None:
        self.fusion = fusion or SoyuzFusion()

    # ========================================================
    # MOTOR 1 — MACRO / FUNDAMENTAL
    # ========================================================

    def build_macro_data(
        self,
        analysis: Dict[str, Any],
    ) -> Dict[str, Any]:

        return {
            "regime": _first(
                analysis,
                "regime",
                "market_regime",
                "regime_name",
                default="UNKNOWN",
            ),

            "inflation_bias": _num(
                _first(
                    analysis,
                    "inflation_bias",
                    default=0,
                )
            ),

            "rates_bias": _num(
                _first(
                    analysis,
                    "rates_bias",
                    "interest_rates_bias",
                    default=0,
                )
            ),

            "dollar_bias": _num(
                _first(
                    analysis,
                    "dollar_bias",
                    "usd_bias",
                    default=0,
                )
            ),

            "energy_bias": _num(
                _first(
                    analysis,
                    "energy_bias",
                    default=0,
                )
            ),

            "geopolitical_bias": _num(
                _first(
                    analysis,
                    "geopolitical_bias",
                    "political_bias",
                    "political_impact",
                    default=0,
                )
            ),

            "fundamentals_bias": _num(
                _first(
                    analysis,
                    "fundamentals_bias",
                    "fundamental_bias",
                    default=0,
                )
            ),

            "confidence": _num(
                _first(
                    analysis,
                    "macro_confidence",
                    "fundamental_confidence",
                    default=0,
                )
            ),

            "reasons": _first(
                analysis,
                "macro_reasons",
                "fundamental_reasons",
                default=[],
            ),
        }

    # ========================================================
    # MOTOR 2 — MARKET INTELLIGENCE
    # ========================================================

    def build_intelligence_data(
        self,
        analysis: Dict[str, Any],
    ) -> Dict[str, Any]:

        return {
            "direction": str(
                _first(
                    analysis,
                    "direction",
                    "bias",
                    "signal",
                    default="WAIT",
                )
                or "WAIT"
            ).upper(),

            "mtf_score": _num(
                _first(
                    analysis,
                    "mtf_score",
                    "mtf",
                    default=0,
                )
            ),

            "correlation_score": _num(
                _first(
                    analysis,
                    "correlation_score",
                    "cross_commodity_score",
                    default=0,
                )
            ),

            "news_score": _num(
                _first(
                    analysis,
                    "news_score",
                    "intelligence_score",
                    default=0,
                )
            ),

            "futures_score": _num(
                _first(
                    analysis,
                    "futures_score",
                    "futures_structure_score",
                    default=0,
                )
            ),

            "anomaly_score": _num(
                _first(
                    analysis,
                    "anomaly_score",
                    "anomaly",
                    default=0,
                )
            ),

            "reasons": _first(
                analysis,
                "intelligence_reasons",
                "market_intelligence_reasons",
                default=[],
            ),
        }

    # ========================================================
    # MOTOR 3 — GAGARIN
    # ========================================================

    def build_gagarin_data(
        self,
        analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Non inventiamo un gate TRUE.

        Se il bot non fornisce esplicitamente l'informazione,
        il gate rimane FALSE.

        Questo impedisce all'adapter di creare artificialmente
        un'ENTRY.
        """

        return {
            "regime_ok": _bool(
                _first(
                    analysis,
                    "gagarin_regime_ok",
                    "regime_ok",
                    default=False,
                )
            ),

            "structure_ok": _bool(
                _first(
                    analysis,
                    "gagarin_structure_ok",
                    "structure_ok",
                    default=False,
                )
            ),

            "setup_ok": _bool(
                _first(
                    analysis,
                    "gagarin_setup_ok",
                    "setup_ok",
                    default=False,
                )
            ),

            "trigger_ok": _bool(
                _first(
                    analysis,
                    "gagarin_trigger_ok",
                    "trigger_ok",
                    default=False,
                )
            ),

            "risk_ok": _bool(
                _first(
                    analysis,
                    "gagarin_risk_ok",
                    "risk_ok",
                    default=False,
                )
            ),

            "safety_ok": _bool(
                _first(
                    analysis,
                    "gagarin_safety_ok",
                    "safety_ok",
                    default=False,
                )
            ),

            "reasons": _first(
                analysis,
                "gagarin_reasons",
                "gagarin_blockers",
                default=[],
            ),
        }

    # ========================================================
    # FINAL FUSION
    # ========================================================

    def evaluate(
        self,
        commodity: str,
        analysis: Dict[str, Any],
    ) -> SoyuzDecision:

        macro_data = self.build_macro_data(
            analysis
        )

        intelligence_data = (
            self.build_intelligence_data(
                analysis
            )
        )

        gagarin_data = (
            self.build_gagarin_data(
                analysis
            )
        )

        return self.fusion.evaluate(
            commodity=commodity,
            macro_data=macro_data,
            intelligence_data=intelligence_data,
            gagarin_data=gagarin_data,
        )


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================

def evaluate_with_soyuz(
    commodity: str,
    analysis: Dict[str, Any],
) -> SoyuzDecision:
    """
    Funzione semplice da usare successivamente dentro
    commodity_bot.py.
    """

    adapter = SoyuzAdapter()

    return adapter.evaluate(
        commodity=commodity,
        analysis=analysis,
    )


# ============================================================
# DEBUG / HUMAN READABLE
# ============================================================

def decision_summary(
    decision: SoyuzDecision,
) -> str:

    reasons = "; ".join(
        decision.reasons[:5]
    )

    return (
        f"SOYUZ | "
        f"{decision.commodity} | "
        f"{decision.direction} | "
        f"{decision.state} | "
        f"MACRO={decision.macro_bias:.1f} | "
        f"INTEL={decision.intelligence_score:.1f} | "
        f"GAGARIN="
        f"{'AUTHORIZED' if decision.gagarin_authorized else 'BLOCKED'}"
        + (
            f" | {reasons}"
            if reasons
            else ""
        )
    )