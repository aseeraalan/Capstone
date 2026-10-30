"""Turn Student B's features into a report for Student D.

Order of work:
1. Validate the packet. A bad record never reaches the model.
2. If data_quality is invalid or stale, return INPUT_INVALID. Do not classify it.
3. In mock mode, use the deterministic test double and label it as mock.
4. In ollama mode, call the local server, time that call, then validate the reply.
5. On timeout, unavailability, or a bad reply, return a failure and no category.
"""

from __future__ import annotations

import json
import math

from pydantic import ValidationError

from thermosense_c.llm_client import (
    DEFAULT_MODEL,
    DEFAULT_OLLAMA_URL,
    DEFAULT_TIMEOUT_S,
    LlmCallError,
    chat_completion,
)
from thermosense_c.mock_interpreter import MOCK_MODEL_NAME, mock_assessment
from thermosense_c.prompts import build_messages
from thermosense_c.schemas import (
    AssessmentStatus,
    InterfaceReport,
    RiskAssessment,
    SensorFeatures,
    summarize_validation_error,
)

_STATUS_FROM_KIND = {
    "timeout": AssessmentStatus.TIMEOUT,
    "unavailable": AssessmentStatus.LLM_UNAVAILABLE,
    "invalid_response": AssessmentStatus.INVALID_RESPONSE,
}


def interpret(
    features: object,
    *,
    mode: str,
    model: str = DEFAULT_MODEL,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    ollama_url: str = DEFAULT_OLLAMA_URL,
) -> InterfaceReport:
    if mode not in ("mock", "ollama"):
        raise ValueError("mode must be 'mock' or 'ollama'")
    _check_timeout(timeout_s)

    try:
        parsed = features if isinstance(features, SensorFeatures) else SensorFeatures.model_validate(features)
    except ValidationError as exc:
        return _rejected("Input rejected before any model call. " + summarize_validation_error(exc))

    if parsed.data_quality != "valid":
        return _rejected(
            f"data_quality is {parsed.data_quality}. "
            "No risk category was produced. Student D's local rules remain in control."
        )

    if mode == "mock":
        assessment = mock_assessment(parsed)
        return _ok(assessment, mode="mock", model=MOCK_MODEL_NAME, latency_ms=None)

    if not isinstance(model, str) or not model.strip():
        raise ValueError("model must be a non-empty string")

    try:
        content, latency_ms = chat_completion(
            url=ollama_url,
            model=model,
            messages=build_messages(parsed),
            timeout_s=float(timeout_s),
            response_schema=RiskAssessment.model_json_schema(),
        )
    except LlmCallError as exc:
        status = _STATUS_FROM_KIND[exc.kind]
        return _failed(status, _failure_detail(status, exc.detail, timeout_s), exc.latency_ms)

    try:
        assessment = RiskAssessment.model_validate(json.loads(content))
    except json.JSONDecodeError:
        problem = "The model response was not a JSON object."
    except ValidationError as exc:
        problem = summarize_validation_error(exc)
    else:
        return _ok(assessment, mode="ollama", model=model, latency_ms=latency_ms)

    return _failed(
        AssessmentStatus.INVALID_RESPONSE,
        "The model reply failed validation. No risk category was accepted. " + problem,
        latency_ms,
    )


def _ok(assessment: RiskAssessment, *, mode: str, model: str, latency_ms: int | None) -> InterfaceReport:
    return InterfaceReport(
        llm_status=AssessmentStatus.OK,
        valid=True,
        mode=mode,  # type: ignore[arg-type]
        model=model,
        risk_category=assessment.risk_category,
        reason=assessment.reason,
        recommendation=assessment.recommendation,
        latency_ms=latency_ms,
    )


def _rejected(detail: str) -> InterfaceReport:
    return InterfaceReport(llm_status=AssessmentStatus.INPUT_INVALID, valid=False, detail=detail)


def _failed(status: AssessmentStatus, detail: str, latency_ms: int) -> InterfaceReport:
    return InterfaceReport(llm_status=status, valid=False, detail=detail, latency_ms=latency_ms)


def _failure_detail(status: AssessmentStatus, reason: str, timeout_s: float) -> str:
    if status == AssessmentStatus.TIMEOUT:
        lead = f"Ollama did not answer within {timeout_s:g} seconds. No risk category was produced."
    elif status == AssessmentStatus.LLM_UNAVAILABLE:
        lead = "The local Ollama server could not be used. No risk category was produced."
    else:
        lead = "The model reply could not be read. No risk category was produced."
    return f"{lead} {reason}"


def _check_timeout(timeout_s: float) -> None:
    if isinstance(timeout_s, bool) or not isinstance(timeout_s, (int, float)):
        raise ValueError("timeout_s must be a positive number of seconds")
    if not math.isfinite(float(timeout_s)) or float(timeout_s) <= 0:
        raise ValueError("timeout_s must be a positive number of seconds")
