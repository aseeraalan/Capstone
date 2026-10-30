"""Build the chat messages. This module does not call Ollama."""

from __future__ import annotations

import json

from thermosense_c.advisory_bands import (
    ELEVATED_DELTA_T,
    ELEVATED_MAX_TEMP,
    ELEVATED_RATE_C_PER_MIN,
    HIGH_DELTA_T,
    HIGH_MAX_TEMP,
    HIGH_RATE_C_PER_MIN,
)
from thermosense_c.schemas import SensorFeatures


def system_prompt() -> str:
    # The prompt asks for the shape and the preliminary bands.
    # llm_client.py also sends the JSON Schema. assess.py checks the reply again.
    # These bands are integration-test guidance, not alarm setpoints.
    return (
        "You interpret processed thermal features for ThermoSense-AI. "
        "You do not operate alarms, relays, or shutdowns. Another part of the system owns the safety rules. "
        "Use only the numbers in the user message. Do not invent measurements, and do not say a fire is confirmed. "
        "Return one JSON object with exactly these keys: risk_category, reason, recommendation. "
        "risk_category must be exactly one of: normal, elevated, high-risk. "
        "Do not use low, high, or very-high. "
        "Preliminary bands, which are not final safety limits: "
        f"high-risk if max_temp is at least {HIGH_MAX_TEMP:g}, "
        f"or temp_rate_of_change is at least {HIGH_RATE_C_PER_MIN:g}, "
        f"or delta_t is at least {HIGH_DELTA_T:g}. "
        f"Otherwise elevated if max_temp is at least {ELEVATED_MAX_TEMP:g}, "
        f"or temp_rate_of_change is at least {ELEVATED_RATE_C_PER_MIN:g}, "
        f"or delta_t is at least {ELEVATED_DELTA_T:g}. "
        "Otherwise normal. "
        "reason and recommendation must each be one short sentence."
    )


def user_message(features: SensorFeatures) -> str:
    body = json.dumps(features.model_dump(mode="json"), indent=2)
    return (
        "Units: temperatures and delta_t are degrees Celsius; "
        "temp_rate_of_change is degrees Celsius per minute.\n"
        "Interpret this processed feature summary.\n" + body
    )


def build_messages(features: SensorFeatures) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": system_prompt()},
        {"role": "user", "content": user_message(features)},
    ]
