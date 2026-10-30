"""Pydantic contracts for Student B's features, the model reply, and Student D.

schemas.py does not open a network connection. The Ollama client lives in
llm_client.py. assess.py is the only module that connects the two.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

# Sanity bounds for garbled packets. They are not alarm thresholds.
# Student D still applies local safety rules on the parallel path.
TEMP_MIN_C = -40.0
TEMP_MAX_C = 300.0
RATE_MIN_C_PER_MIN = -60.0
RATE_MAX_C_PER_MIN = 60.0

HotspotLocation = Literal[
    "none",
    "centre",
    "upper-left",
    "upper-right",
    "lower-left",
    "lower-right",
]
DataQuality = Literal["valid", "invalid", "stale"]
RiskCategory = Literal["normal", "elevated", "high-risk"]

_NUMERIC_FIELDS = (
    "max_temp",
    "mean_temp",
    "temp_rate_of_change",
    "ambient_temp",
    "delta_t",
)


class AssessmentStatus(str, Enum):
    """Status returned to Student D. Only OK carries a risk category."""

    OK = "OK"
    INPUT_INVALID = "INPUT_INVALID"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    TIMEOUT = "TIMEOUT"
    LLM_UNAVAILABLE = "LLM_UNAVAILABLE"


def _finite_number(value: object) -> float:
    # Reject strings and booleans before Pydantic can coerce them.
    # True is an int subclass, so the bool check has to come first.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("must be finite")
    return number


def _timestamp(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("must be a string")
    text = value.strip()
    normalized = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("must be ISO-8601, for example 2026-10-23T11:00:00-04:00") from exc
    if parsed.tzinfo is None:
        raise ValueError("must include a timezone")
    if parsed > datetime.now(timezone.utc) + timedelta(hours=24):
        raise ValueError("is more than 24 hours in the future")
    return text


class SensorFeatures(BaseModel):
    """Processed feature packet from Student B. Extra keys are rejected.

    data_quality may be valid, invalid, or stale. invalid and stale are
    legal values here, and assess.py refuses to classify them.
    """

    model_config = ConfigDict(extra="forbid")

    timestamp: str = Field(description="ISO-8601 time with a timezone.")
    max_temp: float = Field(ge=TEMP_MIN_C, le=TEMP_MAX_C, description="Highest temperature, degrees Celsius.")
    mean_temp: float = Field(ge=TEMP_MIN_C, le=TEMP_MAX_C, description="Mean temperature, degrees Celsius.")
    hotspot_location: HotspotLocation = Field(description="Region label. Use centre, not center.")
    temp_rate_of_change: float = Field(
        ge=RATE_MIN_C_PER_MIN,
        le=RATE_MAX_C_PER_MIN,
        description="Temperature rate, degrees Celsius per minute.",
    )
    ambient_temp: float = Field(ge=TEMP_MIN_C, le=TEMP_MAX_C, description="Ambient temperature, degrees Celsius.")
    delta_t: float = Field(ge=TEMP_MIN_C, le=TEMP_MAX_C, description="Temperature difference, degrees Celsius.")
    data_quality: DataQuality

    @field_validator(*_NUMERIC_FIELDS, mode="before")
    @classmethod
    def reject_non_numbers(cls, value: object) -> float:
        return _finite_number(value)

    @field_validator("timestamp")
    @classmethod
    def reject_bad_timestamp(cls, value: object) -> str:
        return _timestamp(value)

    @model_validator(mode="after")
    def reject_inconsistent_features(self) -> SensorFeatures:
        # 0.05 C covers ordinary rounding. It is not an alarm deadband.
        if self.mean_temp > self.max_temp + 0.05:
            raise ValueError("mean_temp cannot be greater than max_temp")
        return self


class RiskAssessment(BaseModel):
    """The only model reply Student C will forward.

    The same schema is sent to Ollama in the format field. Categories such as
    low, high, and very-high are rejected, as is any extra alarm field.
    """

    model_config = ConfigDict(extra="forbid")

    risk_category: RiskCategory
    reason: str = Field(min_length=1, max_length=400)
    recommendation: str = Field(min_length=1, max_length=400)

    @field_validator("reason", "recommendation")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped


class InterfaceReport(BaseModel):
    """Flat report printed for Student D and for the MCR screenshots."""

    model_config = ConfigDict(extra="forbid")

    llm_status: AssessmentStatus
    valid: bool
    mode: Literal["mock", "ollama"] | None = None
    model: str | None = None
    risk_category: RiskCategory | None = None
    reason: str | None = None
    recommendation: str | None = None
    detail: str | None = None
    latency_ms: int | None = None

    @model_validator(mode="after")
    def keep_failures_free_of_a_category(self) -> InterfaceReport:
        # A failed call must not look like a normal, elevated, or high-risk result.
        if self.llm_status == AssessmentStatus.OK:
            if not self.valid:
                raise ValueError("OK must be valid")
            if self.risk_category is None or not self.reason or not self.recommendation:
                raise ValueError("OK report is missing the risk assessment")
            if self.mode not in ("mock", "ollama") or not self.model:
                raise ValueError("OK report must name the mode and model")
        else:
            if self.valid:
                raise ValueError("A failure must not be marked valid")
            if self.risk_category is not None or self.reason is not None or self.recommendation is not None:
                raise ValueError("A failed call must not include a risk classification")

        if self.llm_status == AssessmentStatus.INPUT_INVALID and self.latency_ms is not None:
            raise ValueError("Invalid input is rejected before a model call")
        if self.mode == "mock":
            if self.model != "deterministic-test-double":
                raise ValueError("Mock mode must use the deterministic test double")
            if self.latency_ms is not None:
                raise ValueError("Mock mode must not report an LLM latency")
        if self.mode == "ollama" and self.latency_ms is None:
            raise ValueError("An Ollama call must report latency_ms")
        return self


def summarize_validation_error(exc: ValidationError) -> str:
    """Turn a Pydantic error into one short string for Student D's log."""

    parts: list[str] = []
    for err in exc.errors():
        loc = ".".join(str(item) for item in err.get("loc", ())) or "input"
        parts.append(f"{loc}: {err.get('msg', 'invalid')}")
    return "; ".join(parts) if parts else "invalid input"
