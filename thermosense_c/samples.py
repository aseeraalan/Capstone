"""Hand-written feature packets loaded from sample_data.

These files were typed for the laptop demo. They were not measured by an
MLX90640, a BME688, or any other sensor.

The elevated packet uses delta_t 20 C. A draft example used 40 C, but Student
D's preliminary rule treats delta_t of 30 C or more as high-risk. 20 C stays
inside the elevated band.
"""

from __future__ import annotations

import json
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / "sample_data"

SIMULATED_NOTICE = (
    "These feature records are hand-written examples for a laptop demo. "
    "They were not measured by an MLX90640, a BME688, or any other sensor. "
    "This laptop run is not a Raspberry Pi test."
)


def load_sample(filename: str) -> dict:
    return json.loads((_DATA_DIR / filename).read_text(encoding="utf-8"))


def normal_features() -> dict:
    return load_sample("normal.json")


def elevated_features() -> dict:
    return load_sample("elevated.json")


def high_risk_features() -> dict:
    return load_sample("high_risk.json")


def invalid_features() -> dict:
    return load_sample("invalid.json")


def stale_features() -> dict:
    return load_sample("stale.json")


def classification_cases() -> list[tuple[str, str, dict]]:
    """The three simulated conditions used by --mode mock with no --input."""

    return [
        ("normal", "Normal Thermal Condition", normal_features()),
        ("elevated", "Elevated Thermal Condition", elevated_features()),
        ("high-risk", "High-risk Thermal Condition", high_risk_features()),
    ]


def extra_cases() -> list[tuple[str, str, dict]]:
    """Extra hand-written packets. Each valid one trips at most one band."""

    return [
        ("cool_room", "Cool Room", load_sample("cool_room.json")),
        ("near_normal", "Just Below Elevated", load_sample("near_normal.json")),
        ("elevated_by_rate", "Elevated By Rate Only", load_sample("elevated_by_rate.json")),
        ("elevated_by_delta", "Elevated By Delta T Only", load_sample("elevated_by_delta.json")),
        ("high_risk_by_rate", "High-risk By Rate Only", load_sample("high_risk_by_rate.json")),
        ("high_risk_by_delta", "High-risk By Delta T Only", load_sample("high_risk_by_delta.json")),
        ("missing_timestamp", "Missing Timestamp", load_sample("missing_timestamp.json")),
        ("extra_field", "Unexpected Extra Field", load_sample("extra_field.json")),
        ("out_of_range", "Temperature Out Of Range", load_sample("out_of_range.json")),
    ]
