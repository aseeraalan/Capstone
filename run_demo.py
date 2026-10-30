"""Laptop demo for the Student C interface.

Examples, from this folder:
  python run_demo.py --mode mock
  python student_c_llm.py --mode mock --input sample_data/normal.json
  python run_demo.py --mode ollama --input sample_data/normal.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from thermosense_c import AssessmentStatus, interpret
from thermosense_c.llm_client import DEFAULT_MODEL, DEFAULT_OLLAMA_URL, DEFAULT_TIMEOUT_S
from thermosense_c.local_checks import run_failure_checks
from thermosense_c.samples import classification_cases, extra_cases
from thermosense_c.schemas import InterfaceReport, RiskAssessment, SensorFeatures

_TITLES = {
    "normal": "Normal Thermal Condition",
    "elevated": "Elevated Thermal Condition",
    "high-risk": "High-risk Thermal Condition",
    "high_risk": "High-risk Thermal Condition",
    "invalid": "Invalid Data Quality",
    "stale": "Stale Data Quality",
    "cool_room": "Cool Room",
    "near_normal": "Just Below Elevated",
    "elevated_by_rate": "Elevated By Rate Only",
    "elevated_by_delta": "Elevated By Delta T Only",
    "high_risk_by_rate": "High-risk By Rate Only",
    "high_risk_by_delta": "High-risk By Delta T Only",
    "missing_timestamp": "Missing Timestamp",
    "extra_field": "Unexpected Extra Field",
    "out_of_range": "Temperature Out Of Range",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Student C advisory interface. This program does not operate safety alarms.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--mode", required=True, choices=["mock", "ollama", "failure-check", "schema"])
    parser.add_argument(
        "--case",
        choices=[
            "normal",
            "elevated",
            "high-risk",
            "invalid",
            "stale",
            "all",
            "more",
            "cool_room",
            "near_normal",
            "elevated_by_rate",
            "elevated_by_delta",
            "high_risk_by_rate",
            "high_risk_by_delta",
            "missing_timestamp",
            "extra_field",
            "out_of_range",
        ],
        default="all",
        help="Built-in simulated case. 'more' runs the extra packets. Ignored when --input is set.",
    )
    parser.add_argument(
        "--input",
        dest="input_path",
        help="JSON file of processed features. If omitted, built-in simulated cases are used.",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("THERMOSENSE_OLLAMA_MODEL", DEFAULT_MODEL),
        help="Ollama model name. Override with THERMOSENSE_OLLAMA_MODEL.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=_timeout_default(),
        help="Seconds to wait for an Ollama reply after the connection opens.",
    )
    parser.add_argument(
        "--ollama-url",
        default=os.environ.get("THERMOSENSE_OLLAMA_URL", DEFAULT_OLLAMA_URL),
        help="Local Ollama chat endpoint. Override with THERMOSENSE_OLLAMA_URL.",
    )
    args = parser.parse_args(argv)

    if args.mode == "schema":
        _print_schemas()
        return 0
    if args.mode == "failure-check":
        return _print_failure_checks()

    try:
        cases = _cases(args.case, args.input_path)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Could not read input file: {exc}")
        return 1

    exit_code = 0
    for title, features in cases:
        report = interpret(
            features,
            mode=args.mode,
            model=args.model,
            timeout_s=args.timeout,
            ollama_url=args.ollama_url,
        )
        _print_case(title, features, report)
        if report.llm_status != AssessmentStatus.OK:
            exit_code = 2 if args.mode == "ollama" else 1
    return exit_code


def _cases(case: str, input_path: str | None) -> list[tuple[str, object]]:
    if input_path:
        payload = json.loads(Path(input_path).read_text(encoding="utf-8"))
        return [(_title_for(Path(input_path).stem), payload)]
    selected = {name: (title, features) for name, title, features in classification_cases()}
    extras = {name: (title, features) for name, title, features in extra_cases()}
    if case == "all":
        return [(title, features) for title, features in selected.values()]
    if case == "more":
        return [(title, features) for title, features in extras.values()]
    if case in extras:
        return [extras[case]]
    if case in ("invalid", "stale"):
        from thermosense_c.samples import invalid_features, stale_features

        features = invalid_features() if case == "invalid" else stale_features()
        return [(_TITLES[case], features)]
    return [selected[case]]


def _title_for(stem: str) -> str:
    return _TITLES.get(stem, stem.replace("_", " ").title())


def _print_case(title: str, features: object, report: InterfaceReport) -> None:
    print("=" * 60)
    print("THERMOSENSE-AI - STUDENT C LLM INTERFACE")
    print(f"TEST CASE: {title}")
    print("=" * 60)
    print()
    print("INPUT FROM STUDENT B")
    print()
    print(json.dumps(features, indent=2))
    print()
    print("STUDENT C OUTPUT")
    print()
    print(json.dumps(report.model_dump(mode="json", exclude_none=True), indent=2))
    print()


def _print_schemas() -> None:
    print("SensorFeatures schema (Student B -> Student C)")
    print(json.dumps(SensorFeatures.model_json_schema(), indent=2))
    print("RiskAssessment schema (sent to Ollama as format, then checked again)")
    print(json.dumps(RiskAssessment.model_json_schema(), indent=2))


def _print_failure_checks() -> int:
    expected = [
        AssessmentStatus.LLM_UNAVAILABLE,
        AssessmentStatus.TIMEOUT,
        AssessmentStatus.INVALID_RESPONSE,
    ]
    labels = ("Ollama unavailable", "Timeout", "Malformed model response")
    reports = run_failure_checks()
    for label, report in zip(labels, reports):
        _print_case(label, {"note": "Simulated normal packet used only as a valid carrier."}, report)
    matched = [report.llm_status for report in reports] == expected
    empty = all(report.risk_category is None and report.valid is False for report in reports)
    return 0 if matched and empty else 1


def _timeout_default() -> float:
    raw = os.environ.get("THERMOSENSE_OLLAMA_TIMEOUT")
    if raw is None or not raw.strip():
        return DEFAULT_TIMEOUT_S
    return float(raw)


if __name__ == "__main__":
    sys.exit(main())
