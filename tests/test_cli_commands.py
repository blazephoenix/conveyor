import os
from pathlib import Path
from typer.testing import CliRunner
from conveyor.cli import app
from conveyor.tracking.markdown import MarkdownStore
from conveyor.tracking.models import Intent, Issue, IssueStatus, RiskLevel

runner = CliRunner()


def _setup_conveyor(tmp_path: Path):
    """Create a .conveyor/ dir with sample data."""
    conveyor_dir = tmp_path / ".conveyor"
    store = MarkdownStore(conveyor_dir)
    store._ensure_dirs()

    intent = Intent(id="INT-001", title="Add auth", message="Add authentication")
    intent.status = "in_progress"
    intent.issues = ["ISS-001", "ISS-002"]
    store.save_intent(intent)

    store.save_issue(Issue(
        id="ISS-001", intent="INT-001", title="Add User model",
        agent="backend", branch="conveyor/iss-001-user-model",
        depends_on=[], risk=RiskLevel.LOW, status=IssueStatus.COMPLETE,
    ))
    store.save_issue(Issue(
        id="ISS-002", intent="INT-001", title="Add login endpoint",
        agent="backend", branch="conveyor/iss-002-login",
        depends_on=["ISS-001"], risk=RiskLevel.MEDIUM, status=IssueStatus.PAUSED,
        review_type="merge",
    ))
    return conveyor_dir


def test_status_command(tmp_path):
    _setup_conveyor(tmp_path)
    os.chdir(tmp_path)
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "INT-001" in result.output


def test_issues_list(tmp_path):
    _setup_conveyor(tmp_path)
    os.chdir(tmp_path)
    result = runner.invoke(app, ["issues"])
    assert result.exit_code == 0
    assert "ISS-001" in result.output
    assert "ISS-002" in result.output


def test_issues_detail(tmp_path):
    _setup_conveyor(tmp_path)
    os.chdir(tmp_path)
    result = runner.invoke(app, ["issues", "ISS-001"])
    assert result.exit_code == 0
    assert "User model" in result.output


def test_log_command(tmp_path):
    _setup_conveyor(tmp_path)
    os.chdir(tmp_path)
    result = runner.invoke(app, ["log"])
    assert result.exit_code == 0
