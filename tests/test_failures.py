"""Failure-path tests. They use local sockets, not a running Ollama server."""

import json

import pytest
from pydantic import ValidationError

from thermosense_c.llm_client import DEFAULT_MODEL, DEFAULT_OLLAMA_URL, DEFAULT_TIMEOUT_S
from thermosense_c.local_checks import (
    check_malformed_response,
    check_timeout,
    check_unavailable,
    interpret_with_fake_ollama,
)
from thermosense_c.samples import normal_features
from thermosense_c.schemas import AssessmentStatus, InterfaceReport, RiskAssessment


def test_default_endpoint_model_and_timeout():
    assert DEFAULT_OLLAMA_URL == "http://localhost:11434/api/chat"
    assert DEFAULT_MODEL == "llama3.2:1b"
    assert DEFAULT_TIMEOUT_S == 10.0


def test_schema_lists_only_the_three_categories():
    schema = RiskAssessment.model_json_schema()
    category = schema["properties"]["risk_category"]
    values = category.get("enum")
    if values is None:
        values = [item["const"] for item in category["anyOf"]]
    assert values == ["normal", "elevated", "high-risk"]
    assert schema["additionalProperties"] is False
    assert "reason" in schema["properties"]
    assert "explanation" not in schema["properties"]


def test_disallowed_category_names_are_rejected():
    for name in ("low", "high", "very-high", "critical"):
        with pytest.raises(ValidationError):
            RiskAssessment.model_validate(
                {
                    "risk_category": name,
                    "reason": "Not an allowed category.",
                    "recommendation": "Do not use this label.",
                }
            )


def test_blank_reason_is_invalid():
    with pytest.raises(ValidationError):
        RiskAssessment(risk_category="normal", reason="   ", recommendation="Keep watching.")


def test_report_model_rejects_a_category_on_failure():
    with pytest.raises(ValidationError):
        InterfaceReport(
            llm_status=AssessmentStatus.TIMEOUT,
            valid=False,
            risk_category="normal",
            reason="Should not be attached.",
            recommendation="Should not be attached.",
            latency_ms=10,
            detail="timed out",
        )


def test_ollama_unavailable():
    report = check_unavailable()
    dumped = report.model_dump(mode="json", exclude_none=True)
    assert report.llm_status == AssessmentStatus.LLM_UNAVAILABLE
    assert report.valid is False
    assert report.risk_category is None
    assert "risk_category" not in dumped
    assert report.latency_ms is not None
    assert report.latency_ms >= 0


def test_timeout():
    report = check_timeout(timeout_s=0.4)
    assert report.llm_status == AssessmentStatus.TIMEOUT
    assert report.valid is False
    assert report.risk_category is None
    assert report.latency_ms is not None
    assert report.latency_ms >= 300


def test_malformed_model_response():
    report = check_malformed_response()
    assert report.llm_status == AssessmentStatus.INVALID_RESPONSE
    assert report.valid is False
    assert report.risk_category is None
    assert "risk_category" in (report.detail or "")


def test_non_json_model_text_is_invalid_response():
    report = interpret_with_fake_ollama("this is not json")
    assert report.llm_status == AssessmentStatus.INVALID_RESPONSE
    assert report.valid is False
    assert report.risk_category is None


def test_alarm_field_from_the_model_is_rejected():
    content = json.dumps(
        {
            "risk_category": "normal",
            "reason": "Quiet features.",
            "recommendation": "Continue monitoring.",
            "alarm": True,
        }
    )
    report = interpret_with_fake_ollama(content)
    assert report.llm_status == AssessmentStatus.INVALID_RESPONSE
    assert report.risk_category is None


def test_ollama_mode_keeps_a_valid_model_category():
    # The normal sample is "normal" in mock mode. Ollama mode must keep a
    # schema-valid category even when it disagrees with the preliminary bands.
    content = json.dumps(
        {
            "risk_category": "high-risk",
            "reason": "Model text from the test double.",
            "recommendation": "Follow the local safety procedure.",
        }
    )
    report = interpret_with_fake_ollama(content, features=normal_features())
    assert report.llm_status == AssessmentStatus.OK
    assert report.valid is True
    assert report.mode == "ollama"
    assert report.model == "llama3.2:1b"
    assert report.risk_category == "high-risk"
    assert report.latency_ms is not None


def test_request_uses_schema_temperature_zero_and_model():
    content = json.dumps(
        {
            "risk_category": "normal",
            "reason": "Supplied features are quiet.",
            "recommendation": "Keep monitoring.",
        }
    )
    capture: dict = {}
    report = interpret_with_fake_ollama(content, features=normal_features(), capture=capture)
    assert report.llm_status == AssessmentStatus.OK
    body = capture["body"]
    assert body["model"] == "llama3.2:1b"
    assert body["stream"] is False
    assert body["options"]["temperature"] == 0
    assert body["format"] == RiskAssessment.model_json_schema()
    assert "do not operate alarms" in body["messages"][0]["content"].lower()
    assert "35.0" in body["messages"][1]["content"]

    custom: dict = {}
    interpret_with_fake_ollama(content, model="llama3.2:3b", capture=custom)
    assert custom["body"]["model"] == "llama3.2:3b"
