"""Student C advisory interface for ThermoSense-AI.

Validates processed features, asks a local model for a risk reading, and
returns either that reading or a failure status. It does not operate alarms.
"""

from thermosense_c.assess import interpret
from thermosense_c.schemas import (
    AssessmentStatus,
    InterfaceReport,
    RiskAssessment,
    SensorFeatures,
)

__all__ = [
    "AssessmentStatus",
    "InterfaceReport",
    "RiskAssessment",
    "SensorFeatures",
    "interpret",
]
