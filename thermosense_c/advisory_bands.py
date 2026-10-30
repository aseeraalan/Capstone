"""Preliminary bands shared by the mock stand-in and the model prompt.

These match Student D's current integration-test draft. They are not final
equipment safety limits, and this module does not operate alarms.
"""

from __future__ import annotations

from thermosense_c.schemas import SensorFeatures

# Checked in this order: any high-risk condition wins over elevated.
HIGH_MAX_TEMP = 80.0
HIGH_RATE_C_PER_MIN = 5.0
HIGH_DELTA_T = 30.0
ELEVATED_MAX_TEMP = 60.0
ELEVATED_RATE_C_PER_MIN = 2.0
ELEVATED_DELTA_T = 15.0


def advisory_category(features: SensorFeatures) -> str:
    """Return normal, elevated, or high-risk for a valid packet.

    Caller must reject invalid and stale packets before calling this.
    A schema-valid live-model answer is not rewritten to match these bands.
    """

    if features.data_quality != "valid":
        raise ValueError("invalid or stale data is not classified")

    if (
        features.max_temp >= HIGH_MAX_TEMP
        or features.temp_rate_of_change >= HIGH_RATE_C_PER_MIN
        or features.delta_t >= HIGH_DELTA_T
    ):
        return "high-risk"
    if (
        features.max_temp >= ELEVATED_MAX_TEMP
        or features.temp_rate_of_change >= ELEVATED_RATE_C_PER_MIN
        or features.delta_t >= ELEVATED_DELTA_T
    ):
        return "elevated"
    return "normal"
