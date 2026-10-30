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
