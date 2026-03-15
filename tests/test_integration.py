"""
Full end-to-end integration test.
Mocks Claude Code subprocess but validates the complete flow:
  init -> intent -> orchestrator -> plan -> execute -> validate -> merge
"""
import subprocess
from unittest.mock import patch, MagicMock, call
from pathlib import Path

from conveyor.core.init import run_init
from conveyor.core.orchestrator import run_orchestrator
from conveyor.core.planner import parse_plan
from conveyor.config import load_config
from conveyor.execution.runner import Runner
from conveyor.tracking.markdown import MarkdownStore
from conveyor.tracking.models import (
    Intent, Issue, IssueStatus, RiskLevel, AgentResult,
)


MOCK_ORCHESTRATOR_OUTPUT = AgentResult(
    output="""Analysis: The repo needs a new hello endpoint.

```
CONVEYOR_PLAN_START
[
  {
    "task_number": 1,
    "title": "Create hello module",
    "agent": "backend",
    "files_allowed": ["src/hello.py"],
    "files_forbidden": [],
    "depends_on": [],
    "risk": "low",
    "acceptance_criteria": ["src/hello.py exists with hello() function"]
  }
]
CONVEYOR_PLAN_END
```""",
    exit_code=0,
    duration_seconds=3.0,
)

MOCK_WORKER_OUTPUT = AgentResult(
    output="""I created the hello module.

CONVEYOR_REPORT_START
files_created: src/hello.py
files_modified:
lines_added: 5
tests_added: 0
tests_passing: true
notes: Created hello() function
CONVEYOR_REPORT_END""",
    exit_code=0,
    duration_seconds=2.0,
)

MOCK_REVIEWER_OUTPUT = AgentResult(
    output="""Everything looks good.

REVIEW_RESULT_START
passed: true
scope_ok: true
criteria_met: true
tests_ok: true
notes: Clean implementation
REVIEW_RESULT_END""",
    exit_code=0,
    duration_seconds=1.5,
)


def _init_git_repo(path: Path):
    subprocess.run(["git", "init"], cwd=path, capture_output=True)
    subprocess.run(["git", "checkout", "-b", "main"], cwd=path, capture_output=True)
    (path / "src").mkdir()
    (path / "src" / "app.py").write_text("# main app")
    subprocess.run(["git", "add", "."], cwd=path, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=path, capture_output=True,
        env={"GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@t.com",
             "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "t@t.com",
             "HOME": str(path), "PATH": "/usr/bin:/bin:/usr/local/bin"},
    )


@patch("conveyor.core.orchestrator.ClaudeCodeAdapter")
def test_full_flow(MockOrchestratorAdapter, tmp_path):
    # Setup git repo
    _init_git_repo(tmp_path)

    # Init conveyor
    run_init(tmp_path)
    conveyor_dir = tmp_path / ".conveyor"
    store = MarkdownStore(conveyor_dir)
    config = load_config(conveyor_dir / "config.toml")

    # Mock orchestrator
    mock_orch = MagicMock()
    mock_orch.execute.return_value = MOCK_ORCHESTRATOR_OUTPUT
    MockOrchestratorAdapter.return_value = mock_orch

    # Run orchestrator
    graph = run_orchestrator("Add a hello endpoint", tmp_path)
    assert len(graph.tasks) == 1
    assert graph.tasks[0]["title"] == "Create hello module"
    assert graph.tasks[0]["agent"] == "backend"

    # Create intent and issues
    intent = Intent(id="INT-001", title="Add hello endpoint", message="Add a hello endpoint")
    intent.status = "in_progress"

    issue = Issue(
        id="ISS-001",
        intent="INT-001",
        title="Create hello module",
        agent="backend",
        branch="conveyor/iss-001-create-hello-module",
        depends_on=[],
        risk=RiskLevel.LOW,
        files_allowed=["src/hello.py"],
        acceptance_criteria=["src/hello.py exists with hello() function"],
    )
    intent.issues = ["ISS-001"]
    store.save_intent(intent)
    store.save_issue(issue)

    # Verify the issue was persisted correctly
    loaded = store.load_issue("ISS-001")
    assert loaded.title == "Create hello module"
    assert loaded.status == IssueStatus.CREATED

    # Mock the worker adapter (used for both worker and reviewer calls)
    mock_worker_adapter = MagicMock()
    mock_worker_adapter.execute.side_effect = [MOCK_WORKER_OUTPUT, MOCK_REVIEWER_OUTPUT]

    # Patch git operations in branch module so we don't need a real git
    # branch during runner execution, and patch run_tests to skip
    with patch("conveyor.execution.runner.checkout_branch") as mock_checkout, \
         patch("conveyor.execution.runner.create_branch") as mock_create_br, \
         patch("conveyor.execution.runner.merge_branch", return_value=True) as mock_merge, \
         patch("conveyor.execution.runner.branch_diff", return_value="diff --git a/src/hello.py b/src/hello.py\nnew file\n") as mock_diff, \
         patch("conveyor.execution.runner.changed_files", return_value=["src/hello.py"]) as mock_changed, \
         patch("conveyor.execution.runner.run_tests") as mock_tests:

        # Tests pass (no test command configured means auto-pass)
        from conveyor.validation.checks import TestResult
        mock_tests.return_value = TestResult(output="No test command configured", exit_code=0)

        runner = Runner(
            issues=[issue],
            store=store,
            config=config,
            repo_dir=tmp_path,
            adapter=mock_worker_adapter,
        )

        # Step 1: created -> queued
        events = runner.advance_once()
        assert issue.status == IssueStatus.QUEUED
        assert any("queued" in e for e in events)

        # Step 2: queued -> running (deps satisfied since no deps)
        events = runner.advance_once()
        assert issue.status == IssueStatus.RUNNING
        assert any("running" in e for e in events)

        # Step 3: running -> validating (executes worker agent)
        events = runner.advance_once()
        assert issue.status == IssueStatus.VALIDATING
        assert any("validating" in e for e in events)
        # Verify worker agent was called
        assert mock_worker_adapter.execute.call_count == 1
        # Verify branch was created
        mock_create_br.assert_called_once_with(
            "conveyor/iss-001-create-hello-module", tmp_path
        )

        # Step 4: validating -> complete (reviewer passes, auto-merge for low risk)
        events = runner.advance_once()
        assert issue.status == IssueStatus.COMPLETE
        assert any("merged" in e or "complete" in e.lower() for e in events)
        # Verify reviewer was called (second call to execute)
        assert mock_worker_adapter.execute.call_count == 2
        # Verify merge happened
        mock_merge.assert_called_once_with(
            "conveyor/iss-001-create-hello-module", tmp_path
        )

    # Verify final state was persisted
    final = store.load_issue("ISS-001")
    assert final.status == IssueStatus.COMPLETE
    assert final.agent_report  # Agent report was parsed and saved
    assert final.reviewer_verdict  # Reviewer verdict was parsed and saved

    # Verify activity log captured the journey
    assert len(issue.activity_log) > 0

    # Verify the runner reports all terminal
    assert runner.all_terminal()
