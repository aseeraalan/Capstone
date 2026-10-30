"""Pipeline tests for the Student B / Student D contract. Ollama is not required."""

import pytest

from thermosense_c import AssessmentStatus, interpret
from thermosense_c.samples import (
    elevated_features,
    high_risk_features,
    invalid_features,
    load_sample,
    normal_features,
    stale_features,
)
from thermosense_c.schemas import SensorFeatures


def _mock(features: dict):
    return interpret(features, mode="mock")


def test_normal_input_returns_normal():
    report = _mock(normal_features())
    assert report.llm_status == AssessmentStatus.OK
    assert report.valid is True
    assert report.mode == "mock"
    assert report.model == "deterministic-test-double"
    assert report.risk_category == "normal"
    assert report.latency_ms is None


def test_elevated_input_returns_elevated():
    features = elevated_features()
    # 20 C is inside the elevated delta_t band and below the 30 C high-risk band.
    assert features["max_temp"] < 80
    assert features["temp_rate_of_change"] < 5
    assert 15 <= features["delta_t"] < 30
    report = _mock(features)
    assert report.llm_status == AssessmentStatus.OK
    assert report.risk_category == "elevated"
    assert report.model == "deterministic-test-double"


def test_high_risk_input_returns_high_risk():
    report = _mock(high_risk_features())
    assert report.llm_status == AssessmentStatus.OK
    assert report.risk_category == "high-risk"


def test_missing_field_is_input_invalid():
    features = normal_features()
    del features["timestamp"]
    report = _mock(features)
    assert report.llm_status == AssessmentStatus.INPUT_INVALID
    assert report.valid is False
    assert report.risk_category is None
    assert "timestamp" in (report.detail or "")


def test_invalid_numeric_range_is_input_invalid():
    features = normal_features()
    features["max_temp"] = 500
    report = _mock(features)
    assert report.llm_status == AssessmentStatus.INPUT_INVALID
    assert report.valid is False
    assert report.risk_category is None
    assert "max_temp" in (report.detail or "")


def test_extra_field_is_input_invalid():
    features = normal_features()
    features["humidity_pct"] = 40
    report = _mock(features)
    assert report.llm_status == AssessmentStatus.INPUT_INVALID
    assert report.risk_category is None
    assert "humidity_pct" in (report.detail or "")


def test_invalid_data_quality_is_not_classified():
    features = invalid_features()
    SensorFeatures.model_validate(features)
    report = _mock(features)
    dumped = report.model_dump(mode="json", exclude_none=True)
    assert report.llm_status == AssessmentStatus.INPUT_INVALID
    assert report.valid is False
    assert "risk_category" not in dumped
    assert "invalid" in (report.detail or "")


def test_stale_data_quality_is_not_classified():
    features = stale_features()
    report = _mock(features)
    dumped = report.model_dump(mode="json", exclude_none=True)
    assert report.llm_status == AssessmentStatus.INPUT_INVALID
    assert report.valid is False
    assert "risk_category" not in dumped
    assert "stale" in (report.detail or "")


def test_extra_packets_follow_the_preliminary_bands():
    expected = {
        "cool_room.json": "normal",
        "near_normal.json": "normal",
        "elevated_by_rate.json": "elevated",
        "elevated_by_delta.json": "elevated",
        "high_risk_by_rate.json": "high-risk",
        "high_risk_by_delta.json": "high-risk",
    }
    for filename, category in expected.items():
        report = _mock(load_sample(filename))
        assert report.llm_status == AssessmentStatus.OK
        assert report.risk_category == category

    for filename in ("missing_timestamp.json", "extra_field.json", "out_of_range.json"):
        report = _mock(load_sample(filename))
        assert report.llm_status == AssessmentStatus.INPUT_INVALID
        assert report.risk_category is None


def test_unknown_mode_is_a_programming_error():
    with pytest.raises(ValueError):
        interpret(normal_features(), mode="cloud")
