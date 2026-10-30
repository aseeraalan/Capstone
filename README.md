# ThermoSense-AI Student C: LLM interface

This folder is Student C's part of COE/ELE 70A ThermoSense-AI. It checks a processed feature packet from Student B, asks a local model for an advisory reading when the packet is valid, and returns either that reading or a failure status to Student D.

The language model does not operate alarms. If the model is unavailable, times out, or returns a bad reply, this module does not invent a risk category. Student D's local rules stay in control.

The JSON files in `sample_data/` were typed by hand for a Windows laptop. They were not measured by an MLX90640, a BME688, or any other sensor. This folder has not been run on a Raspberry Pi.

Screenshot commands and captions are in `MCR2_SCREENSHOT_GUIDE.md`.

## Setup

From this folder in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

`pytest` and `--mode mock` do not need Ollama. There is no cloud LLM package.

## Commands

```powershell
pytest -q
python run_demo.py --mode mock
python student_c_llm.py --mode mock --input sample_data/normal.json
python student_c_llm.py --mode mock --input sample_data/invalid.json
python run_demo.py --mode ollama --input sample_data/normal.json
```

`student_c_llm.py` and `run_demo.py` are the same program. The default Ollama URL is `http://localhost:11434/api/chat`. The default model is `llama3.2:1b`. The reply timeout is 10 seconds. Temperature is 0. The request sends the `RiskAssessment` JSON schema in Ollama's `format` field.

Opening the connection is capped at 5 seconds. If nothing accepts it, the status is `LLM_UNAVAILABLE` and the program exits without a traceback.

## Input from Student B

| Field | Accepted values |
| --- | --- |
| `timestamp` | ISO-8601 string with a timezone |
| `max_temp`, `mean_temp`, `ambient_temp` | Finite numbers from -40 to 300. Mean cannot exceed max by more than 0.05 C |
| `hotspot_location` | `none`, `centre`, `upper-left`, `upper-right`, `lower-left`, `lower-right` |
| `temp_rate_of_change` | Finite number from -60 to 60, degrees Celsius per minute |
| `delta_t` | Finite number from -40 to 300, degrees Celsius |
| `data_quality` | `valid`, `invalid`, or `stale` |

Missing fields, extra fields, strings where numbers belong, and out-of-range numbers become `INPUT_INVALID`. `invalid` and `stale` are legal flag values, and the module still refuses to classify those packets.

These ranges are sanity checks, not alarm setpoints.

## Mock bands

Used only by the deterministic test double, and repeated in the model prompt as guidance. They follow Student D's current preliminary draft. They are not final equipment limits.

- high-risk if `max_temp >= 80` or `temp_rate_of_change >= 5` or `delta_t >= 30`
- otherwise elevated if `max_temp >= 60` or `temp_rate_of_change >= 2` or `delta_t >= 15`
- otherwise normal

The elevated sample uses `delta_t` 20 C. A value of 40 C would meet the high-risk rule.

Mock output is labelled `"mode": "mock"` and `"model": "deterministic-test-double"`. A schema-valid Ollama reply is not rewritten to match these bands.

## Output

A successful reading has `llm_status` `OK`, `valid` true, and `risk_category` of `normal`, `elevated`, or `high-risk`, plus `reason` and `recommendation`.

Failure readings use `INPUT_INVALID`, `INVALID_RESPONSE`, `TIMEOUT`, or `LLM_UNAVAILABLE`, with `valid` false and no risk category.

## Source files

| File | Role |
| --- | --- |
| `thermosense_c/schemas.py` | Input, model-reply, and report models |
| `thermosense_c/assess.py` | Validate, reject bad quality, call mock or Ollama, validate the reply |
| `thermosense_c/prompts.py` | Chat text. No network call |
| `thermosense_c/llm_client.py` | HTTP call to local Ollama, 10 second reply timeout, temperature 0 |
| `thermosense_c/mock_interpreter.py` | Deterministic test double |
| `thermosense_c/advisory_bands.py` | Preliminary band numbers |
| `sample_data/` | Hand-written packets |
| `run_demo.py`, `student_c_llm.py` | Terminal demo |
| `tests/test_pipeline.py` | The eight contract checks |
| `tests/test_failures.py` | Unavailable, timeout, and bad model replies, without a real Ollama server |
