from unittest.mock import patch, MagicMock
from pathlib import Path

from conveyor.execution.runner import Runner
from conveyor.tracking.models import Issue, IssueStatus, RiskLevel, Intent, AgentResult
from conveyor.tracking.markdown import MarkdownStore
from conveyor.config import default_config


def _make_issues():
    return [
        Issue(
            id="ISS-001", intent="INT-001", title="Task 1",
            agent="backend", branch="conveyor/iss-001-task-1",
            depends_on=[], risk=RiskLevel.LOW,
            files_allowed=["src/a.py"], acceptance_criteria=["file exists"],
        ),
        Issue(
            id="ISS-002", intent="INT-001", title="Task 2",
            agent="backend", branch="conveyor/iss-002-task-2",
            depends_on=["ISS-001"], risk=RiskLevel.LOW,
            files_allowed=["src/b.py"], acceptance_criteria=["file exists"],
        ),
    ]


def test_initial_transition_created_to_queued(tmp_path):
    store = MarkdownStore(tmp_path / ".conveyor")
    issues = _make_issues()
    runner = Runner(
        issues=issues,
        store=store,
        config=default_config(),
        repo_dir=tmp_path,
    )
    runner.advance_once()
    assert issues[0].status == IssueStatus.QUEUED


def test_dependency_blocks_downstream(tmp_path):
    store = MarkdownStore(tmp_path / ".conveyor")
    issues = _make_issues()
    issues[0].status = IssueStatus.FAILED
    runner = Runner(
        issues=issues,
        store=store,
        config=default_config(),
        repo_dir=tmp_path,
    )
    runner.advance_once()
    assert issues[1].status == IssueStatus.BLOCKED


def test_all_terminal_detects_completion(tmp_path):
    store = MarkdownStore(tmp_path / ".conveyor")
    issues = _make_issues()
    issues[0].status = IssueStatus.COMPLETE
    issues[1].status = IssueStatus.COMPLETE
    runner = Runner(
        issues=issues,
        store=store,
        config=default_config(),
        repo_dir=tmp_path,
    )
    assert runner.all_terminal() is True


def test_all_terminal_false_when_running(tmp_path):
    store = MarkdownStore(tmp_path / ".conveyor")
    issues = _make_issues()
    issues[0].status = IssueStatus.RUNNING
    runner = Runner(
        issues=issues,
        store=store,
        config=default_config(),
        repo_dir=tmp_path,
    )
    assert runner.all_terminal() is False
