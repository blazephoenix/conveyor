from unittest.mock import patch, MagicMock
from pathlib import Path

from conveyor.core.orchestrator import run_orchestrator
from conveyor.tracking.models import AgentResult


@patch("conveyor.core.orchestrator.ClaudeCodeAdapter")
def test_orchestrator_calls_claude_code(MockAdapter, tmp_path):
    mock_adapter = MagicMock()
    mock_adapter.execute.return_value = AgentResult(
        output="""Analysis here.

```
CONVEYOR_PLAN_START
[
  {
    "task_number": 1,
    "title": "Add hello endpoint",
    "agent": "backend",
    "files_allowed": ["src/app.py"],
    "files_forbidden": [],
    "depends_on": [],
    "risk": "low",
    "acceptance_criteria": ["GET /hello returns 200"]
  }
]
CONVEYOR_PLAN_END
```""",
        exit_code=0,
        duration_seconds=5.0,
    )
    MockAdapter.return_value = mock_adapter

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("# app")

    graph = run_orchestrator(
        intent_message="Add a hello world endpoint",
        repo_dir=tmp_path,
        claude_md="",
    )
    assert len(graph.tasks) == 1
    assert graph.tasks[0]["title"] == "Add hello endpoint"
    mock_adapter.execute.assert_called_once()
