"""Deterministic stand-in used only when the demo is started with --mode mock.

Results are labelled mode=mock and model=deterministic-test-double.
This is not an Ollama reply and it does not operate alarms.
"""

from __future__ import annotations

from thermosense_c.advisory_bands import advisory_category
from thermosense_c.schemas import RiskAssessment, SensorFeatures

MOCK_MODEL_NAME = "deterministic-test-double"

_RECOMMENDATIONS = {
    "normal": "Continue routine monitoring. Local safety rules stay in control.",
    "elevated": "Inspect the monitored area. Local safety rules stay in control.",
    "high-risk": "Follow the local safety procedure. This result does not operate the alarm.",
}


def mock_assessment(features: SensorFeatures) -> RiskAssessment:
    category = advisory_category(features)
    reason = (
        f"Test double: max {features.max_temp:g} C, "
        f"rate {features.temp_rate_of_change:g} C/min, "
        f"delta_t {features.delta_t:g} C."
    )
    return RiskAssessment(
        risk_category=category,
        reason=reason,
        recommendation=_RECOMMENDATIONS[category],
    )
