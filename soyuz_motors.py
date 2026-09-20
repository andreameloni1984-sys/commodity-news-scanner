"""
SOYUZ GAGARIN — THREE MOTORS v1.0

Motor 1: Macro / Fundamental
Motor 2: Market Intelligence
Motor 3: Gagarin Final Authority

Questo modulo NON esegue ordini.
È un contratto decisionale separato dal vecchio commodity_bot.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List


# ============================================================
# HELPERS
# ============================================================

def _bounded(
    value: Any,
    low: float = -100.0,
    high: float = 100.0,
) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0

    if number != number:  # NaN
        return 0.0

    return max(low, min(high, number))


def _clean_reasons(values: Iterable[Any]) -> List[str]:
    if isinstance(values, str):
        values = [values]

    result: List[str] = []

    for value in values or []:
        text = str(value).strip()

        if text and text not in result:
            result.append(text)

    return result[:20]


# ============================================================
# MOTOR 1 — MACRO / FUNDAMENTAL
# ============================================================

@dataclass
class MacroSnapshot:
    regime: str = "UNKNOWN"

    inflation_bias: float = 0.0
    rates_bias: float = 0.0
    dollar_bias: float = 0.0
    energy_bias: float = 0.0
    geopolitical_bias: float = 0.0
    fundamentals_bias: float = 0.0

    confidence: float = 0.0

    reasons: List[str] = field(default_factory=list)

    @property
    def composite_bias(self) -> float:
        values = [
            self.inflation_bias,
            self.rates_bias,
            self.dollar_bias,
            self.energy_bias,
            self.geopolitical_bias,
            self.fundamentals_bias,
        ]

        return max(
            -100.0,
            min(100.0, sum(values) / len(values)),
        )


class MacroFundamentalMotor:
    """
    MOTOR 1

    Riceve informazioni macro/fondamentali già raccolte dal bot
    e le normalizza in un unico snapshot.

    Non genera direttamente ENTRY.
    """

    def evaluate(self, data: Dict[str, Any]) -> MacroSnapshot:

        snapshot = MacroSnapshot(
            regime=str(
                data.get("regime") or "UNKNOWN"
            ).upper(),

            inflation_bias=_bounded(
                data.get("inflation_bias")
            ),

            rates_bias=_bounded(
                data.get("rates_bias")
            ),

            dollar_bias=_bounded(
                data.get("dollar_bias")
            ),

            energy_bias=_bounded(
                data.get("energy_bias")
            ),

            geopolitical_bias=_bounded(
                data.get("geopolitical_bias")
            ),

            fundamentals_bias=_bounded(
                data.get("fundamentals_bias")
            ),

            confidence=_bounded(
                data.get("confidence"),
                0.0,
                100.0,
            ),

            reasons=_clean_reasons(
                data.get("reasons", [])
            ),
        )

        return snapshot


# ============================================================
# MOTOR 2 — MARKET INTELLIGENCE
# ============================================================

@dataclass
class IntelligenceSnapshot:
    direction: str = "WAIT"

    score: float = 0.0

    mtf_score: float = 0.0
    correlation_score: float = 0.0
    news_score: float = 0.0
    futures_score: float = 0.0
    anomaly_score: float = 0.0

    reasons: List[str] = field(default_factory=list)


class MarketIntelligenceMotor:
    """
    MOTOR 2

    Unisce:

    - MTF
    - correlazioni intermarket
    - news
    - futures structure
    - anomalie

    Non può autorizzare autonomamente un'operazione.
    """

    def evaluate(
        self,
        data: Dict[str, Any],
    ) -> IntelligenceSnapshot:

        direction = str(
            data.get("direction") or "WAIT"
        ).upper()

        if direction not in {
            "LONG",
            "SHORT",
            "WAIT",
        }:
            direction = "WAIT"

        scores = [
            _bounded(
                data.get("mtf_score"),
                0.0,
                100.0,
            ),

            _bounded(
                data.get("correlation_score"),
                0.0,
                100.0,
            ),

            _bounded(
                data.get("news_score"),
                0.0,
                100.0,
            ),

            _bounded(
                data.get("futures_score"),
                0.0,
                100.0,
            ),

            _bounded(
                data.get("anomaly_score"),
                0.0,
                100.0,
            ),
        ]

        score = sum(scores) / len(scores)

        return IntelligenceSnapshot(
            direction=direction,

            score=score,

            mtf_score=scores[0],
            correlation_score=scores[1],
            news_score=scores[2],
            futures_score=scores[3],
            anomaly_score=scores[4],

            reasons=_clean_reasons(
                data.get("reasons", [])
            ),
        )


# ============================================================
# MOTOR 3 — GAGARIN
# ============================================================

@dataclass
class GagarinGate:

    regime_ok: bool = False
    structure_ok: bool = False
    setup_ok: bool = False
    trigger_ok: bool = False
    risk_ok: bool = False
    safety_ok: bool = False

    reasons: List[str] = field(default_factory=list)

    @property
    def authorized(self) -> bool:
        """
        ENTRY possibile SOLO se tutti i gate sono TRUE.
        """

        return all(
            (
                self.regime_ok,
                self.structure_ok,
                self.setup_ok,
                self.trigger_ok,
                self.risk_ok,
                self.safety_ok,
            )
        )


class GagarinMotor:
    """
    MOTOR 3

    Gagarin mantiene l'autorità finale.

    Nessun altro motore può bypassarlo.
    """

    def evaluate(
        self,
        data: Dict[str, Any],
    ) -> GagarinGate:

        return GagarinGate(

            regime_ok=bool(
                data.get("regime_ok")
            ),

            structure_ok=bool(
                data.get("structure_ok")
            ),

            setup_ok=bool(
                data.get("setup_ok")
            ),

            trigger_ok=bool(
                data.get("trigger_ok")
            ),

            risk_ok=bool(
                data.get("risk_ok")
            ),

            safety_ok=bool(
                data.get("safety_ok")
            ),

            reasons=_clean_reasons(
                data.get("reasons", [])
            ),
        )


# ============================================================
# FINAL DECISION
# ============================================================

@dataclass
class SoyuzDecision:

    commodity: str

    direction: str

    state: str

    macro_bias: float

    intelligence_score: float

    gagarin_authorized: bool

    reasons: List[str] = field(
        default_factory=list
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )


# ============================================================
# SOYUZ FUSION
# ============================================================

class SoyuzFusion:
    """
    Punto di fusione dei tre motori.

    Flusso:

    MACRO
       ↓
    INTELLIGENCE
       ↓
    GAGARIN
       ↓
    FINAL DECISION
    """

    def __init__(self) -> None:

        self.macro = MacroFundamentalMotor()

        self.intelligence = (
            MarketIntelligenceMotor()
        )

        self.gagarin = GagarinMotor()

    def evaluate(
        self,
        commodity: str,
        macro_data: Dict[str, Any],
        intelligence_data: Dict[str, Any],
        gagarin_data: Dict[str, Any],
    ) -> SoyuzDecision:

        macro = self.macro.evaluate(
            macro_data
        )

        intelligence = (
            self.intelligence.evaluate(
                intelligence_data
            )
        )

        gagarin = self.gagarin.evaluate(
            gagarin_data
        )

        direction = intelligence.direction

        reasons: List[str] = []

        reasons.extend(
            macro.reasons
        )

        reasons.extend(
            intelligence.reasons
        )

        reasons.extend(
            gagarin.reasons
        )

        # ====================================================
        # FINAL AUTHORITY
        # ====================================================

        if (
            gagarin.authorized
            and direction in {
                "LONG",
                "SHORT",
            }
        ):

            state = "ENTRY_AUTHORIZED"

        elif direction in {
            "LONG",
            "SHORT",
        }:

            state = "WAIT_GAGARIN"

            reasons.append(
                "GAGARIN_FINAL_AUTHORITY_NOT_AUTHORIZED"
            )

        else:

            state = "NO_SETUP"

            reasons.append(
                "NO_DIRECTIONAL_SETUP"
            )

        return SoyuzDecision(

            commodity=commodity,

            direction=direction,

            state=state,

            macro_bias=macro.composite_bias,

            intelligence_score=(
                intelligence.score
            ),

            gagarin_authorized=(
                gagarin.authorized
            ),

            reasons=_clean_reasons(
                reasons
            ),

            metadata={

                "macro_regime":
                    macro.regime,

                "macro_confidence":
                    macro.confidence,

                "mtf_score":
                    intelligence.mtf_score,

                "correlation_score":
                    intelligence.correlation_score,

                "news_score":
                    intelligence.news_score,

                "futures_score":
                    intelligence.futures_score,

                "anomaly_score":
                    intelligence.anomaly_score,
            },
        )