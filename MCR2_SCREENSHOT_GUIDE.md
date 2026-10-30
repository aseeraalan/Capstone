# MCR 2 screenshot guide

Run these from:

`C:\Users\Akash Seerqalan\Documents\Coding Projects\ThermoSense-AI-Student-C`

Activate the virtual environment first:

```powershell
.\.venv\Scripts\Activate.ps1
```

The packets in `sample_data/` were typed by hand. Do not caption any figure as an MLX90640 or BME688 measurement, and do not caption any figure as a Raspberry Pi test.

The elevated packet uses `delta_t` 20 C. Under the preliminary rule, `delta_t` of 30 C or more is high-risk, so 40 C would not be an elevated demonstration.

| Figure | Evidence | Command / File |
| --- | --- | --- |
| Figure 1 | Student C input and output schemas | `thermosense_c/schemas.py`, classes `SensorFeatures` (line 80) and `RiskAssessment` (line 120) |
| Figure 2 | Automated tests | `pytest -q` |
| Figure 3 | Normal simulated input | `python student_c_llm.py --mode mock --input sample_data/normal.json` |
| Figure 4 | Elevated simulated input | `python student_c_llm.py --mode mock --input sample_data/elevated.json` |
| Figure 5 | High-risk simulated input | `python student_c_llm.py --mode mock --input sample_data/high_risk.json` |
| Figure 6 | Invalid input handling | `python student_c_llm.py --mode mock --input sample_data/invalid.json` |
| Figure 7 | LLM unavailable handling | `python run_demo.py --mode ollama --input sample_data/normal.json` |
| Figure 8 | Local Llama test | Not available until Ollama is installed. Then run `ollama list` and `python run_demo.py --mode ollama --input sample_data/elevated.json` |

## Figure 1

Open `thermosense_c/schemas.py`. Fold the three methods inside `SensorFeatures` (`reject_non_numbers`, `reject_bad_timestamp`, `reject_inconsistent_features`) so `SensorFeatures` and `RiskAssessment` fit on one screen. Include the field lists, especially `data_quality` and `reason`.

Caption:

Figure 1. Student C structured input and output schemas used to validate processed sensor features and standardized LLM risk assessments. Only normal, elevated, and high-risk are accepted, and the explanation field is named reason.

## Figure 2

```powershell
pytest -q
```

On 23 October 2026 this printed `24 passed`. Capture your own terminal, including that pass line.

Caption:

Figure 2. Automated tests for the Student C interface, covering normal, elevated, and high-risk packets, plus missing fields, out-of-range values, extra fields, invalid data quality, and stale data quality. These tests do not call Ollama.

## Figure 3

```powershell
python student_c_llm.py --mode mock --input sample_data/normal.json
```

The output should show `"risk_category": "normal"`, `"mode": "mock"`, and `"model": "deterministic-test-double"`.

Caption:

Figure 3. Simulated normal processed-feature packet. The deterministic test double returns normal. These values were not measured by a thermal or gas sensor.

## Figure 4

```powershell
python student_c_llm.py --mode mock --input sample_data/elevated.json
```

The output should show `"risk_category": "elevated"` and `delta_t` 20.0.

Caption:

Figure 4. Simulated elevated processed-feature packet. Max temperature 65 C, rate 3 C/min, and delta_t 20 C meet the preliminary elevated band and stay below the high-risk band. This is a test double, not a live model result.

## Figure 5

```powershell
python student_c_llm.py --mode mock --input sample_data/high_risk.json
```

The output should show `"risk_category": "high-risk"`.

Caption:

Figure 5. Simulated high-risk processed-feature packet. Max temperature 85 C, rate 6 C/min, and delta_t 60 C meet the preliminary high-risk band. The recommendation states that this result does not operate the alarm.

## Figure 6

```powershell
python student_c_llm.py --mode mock --input sample_data/invalid.json
```

The output should show `"llm_status": "INPUT_INVALID"` and `"valid": false`, with no `risk_category`. PowerShell may then show an exit code of 1. That is the program finishing, not a crash. The same command with `sample_data/stale.json` rejects stale data.

Caption:

Figure 6. A packet marked data_quality invalid is rejected before any risk category is produced. Student D's local safety rules remain responsible for the alarm decision.

## Figure 7

Run this while Ollama is not running:

```powershell
python run_demo.py --mode ollama --input sample_data/normal.json
```

Wait for it to finish. It can take several seconds. The output should show `"llm_status": "LLM_UNAVAILABLE"` and `"valid": false`, with no `risk_category`. On 23 October 2026, Ollama was not installed (`ollama` was not found), the call to `http://localhost:11434/api/chat` was refused, and the program printed `LLM_UNAVAILABLE` with `latency_ms` 4087 and then exited. Capture your own run.

Caption:

Figure 7. With the local Ollama server unavailable, Student C returns LLM_UNAVAILABLE and does not invent a normal, elevated, or high-risk category. The program does not crash.

## Figure 8

Do not add this figure until both commands succeed on your machine.

```powershell
ollama list
python run_demo.py --mode ollama --input sample_data/elevated.json
```

`ollama list` must show `llama3.2:1b`. The ThermoSense command must show `"mode": "ollama"`, `"model": "llama3.2:1b"`, and a numeric `latency_ms`. If the status is `LLM_UNAVAILABLE`, `TIMEOUT`, or `INVALID_RESPONSE`, keep that screenshot as a failure result and do not relabel it as a successful Llama classification.

Caption, only after a real success:

Figure 8. One advisory reading from local llama3.2:1b through Ollama on this laptop. The reply was checked against the risk schema. This was not run on a Raspberry Pi, and the input packet is still the hand-written elevated example.

## Still requires the Raspberry Pi

- Install Ollama on the Pi, pull `llama3.2:1b`, and repeat Figure 7 or Figure 8 there.
- Record the Pi `latency_ms`. The 10 second reply timeout may need to be longer on the first model load.
- Pass a real feature file from Student B once the sensors are producing packets.
- Stop this Python process and confirm Student D's local rules still alarm.
- A schema-valid but incorrect category is still possible, so the model remains advisory only.
