"""Command-line demo tests."""

from run_demo import main


def test_mock_command_prints_one_clean_case(capsys):
    code = main(["--mode", "mock", "--input", "sample_data/normal.json"])
    output = capsys.readouterr().out
    assert code == 0
    assert "THERMOSENSE-AI - STUDENT C LLM INTERFACE" in output
    assert "TEST CASE: Normal Thermal Condition" in output
    assert "INPUT FROM STUDENT B" in output
    assert "STUDENT C OUTPUT" in output
    assert '"llm_status": "OK"' in output
    assert '"valid": true' in output
    assert '"mode": "mock"' in output
    assert '"model": "deterministic-test-double"' in output
    assert '"risk_category": "normal"' in output
    assert '"reason":' in output


def test_invalid_command_does_not_classify(capsys):
    code = main(["--mode", "mock", "--input", "sample_data/invalid.json"])
    output = capsys.readouterr().out
    assert code == 1
    assert '"llm_status": "INPUT_INVALID"' in output
    assert '"valid": false' in output
    assert '"risk_category":' not in output


def test_failure_check_command(capsys):
    code = main(["--mode", "failure-check"])
    output = capsys.readouterr().out
    assert code == 0
    assert output.count('"llm_status": "LLM_UNAVAILABLE"') == 1
    assert output.count('"llm_status": "TIMEOUT"') == 1
    assert output.count('"llm_status": "INVALID_RESPONSE"') == 1
    assert '"llm_status": "OK"' not in output
    assert '"risk_category":' not in output
