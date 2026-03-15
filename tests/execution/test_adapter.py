from unittest.mock import patch, MagicMock
from conveyor.execution.adapter import ClaudeCodeAdapter, AgentResult


def test_agent_result_success():
    r = AgentResult(output="done", exit_code=0, duration_seconds=5.0)
    assert r.success is True


def test_agent_result_failure():
    r = AgentResult(output="error", exit_code=1, duration_seconds=5.0)
    assert r.success is False


@patch("conveyor.execution.adapter.subprocess.run")
def test_adapter_calls_claude_code(mock_run, tmp_path):
    mock_run.return_value = MagicMock(
        stdout="Agent output here",
        returncode=0,
    )
    adapter = ClaudeCodeAdapter()
    result = adapter.execute("Do something", workdir=str(tmp_path), timeout=60)

    mock_run.assert_called_once()
    call_args = mock_run.call_args
    cmd = call_args[0][0]
    assert "claude" in cmd[0]
    assert "--print" in cmd
    assert result.output == "Agent output here"
    assert result.exit_code == 0
    assert result.success is True


@patch("conveyor.execution.adapter.subprocess.run")
def test_adapter_handles_timeout(mock_run, tmp_path):
    import subprocess
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=60)

    adapter = ClaudeCodeAdapter()
    result = adapter.execute("Do something", workdir=str(tmp_path), timeout=60)

    assert result.success is False
    assert "timeout" in result.output.lower()


@patch("conveyor.execution.adapter.subprocess.run")
def test_adapter_handles_nonzero_exit(mock_run, tmp_path):
    mock_run.return_value = MagicMock(
        stdout="partial output",
        returncode=1,
    )
    adapter = ClaudeCodeAdapter()
    result = adapter.execute("Do something", workdir=str(tmp_path), timeout=60)

    assert result.success is False
    assert result.exit_code == 1
