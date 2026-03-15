from conveyor.tracking.models import (
    Intent,
    Issue,
    Agent,
    AgentResult,
    IssueStatus,
    RiskLevel,
)
from datetime import datetime


def test_issue_status_enum():
    assert IssueStatus.CREATED == "created"
    assert IssueStatus.QUEUED == "queued"
    assert IssueStatus.RUNNING == "running"
    assert IssueStatus.VALIDATING == "validating"
    assert IssueStatus.COMPLETE == "complete"
    assert IssueStatus.FAILED == "failed"
    assert IssueStatus.BLOCKED == "blocked"
    assert IssueStatus.PAUSED == "paused"


def test_risk_level_enum():
    assert RiskLevel.LOW == "low"
    assert RiskLevel.MEDIUM == "medium"
    assert RiskLevel.HIGH == "high"


def test_issue_creation():
    issue = Issue(
        id="ISS-001",
        intent="INT-001",
        title="Add User model",
        agent="backend",
        branch="conveyor/iss-001-user-model",
        depends_on=[],
        risk=RiskLevel.LOW,
        files_allowed=["src/models/user.py"],
        files_forbidden=["src/api/*"],
        acceptance_criteria=["User model exists"],
    )
    assert issue.status == IssueStatus.CREATED
    assert issue.id == "ISS-001"
    assert issue.is_terminal is False


def test_issue_terminal_states():
    issue = Issue(
        id="ISS-001",
        intent="INT-001",
        title="Test",
        agent="backend",
        branch="conveyor/iss-001-test",
        depends_on=[],
        risk=RiskLevel.LOW,
    )
    assert issue.is_terminal is False
    issue.status = IssueStatus.COMPLETE
    assert issue.is_terminal is True
    issue.status = IssueStatus.FAILED
    assert issue.is_terminal is True
    issue.status = IssueStatus.BLOCKED
    assert issue.is_terminal is True


def test_intent_creation():
    intent = Intent(
        id="INT-001",
        title="Add authentication",
        message="Add user authentication with JWT tokens",
    )
    assert intent.status == "pending"
    assert intent.id == "INT-001"


def test_agent_creation():
    agent = Agent(name="backend", role="APIs, models, business logic, migrations")
    assert agent.issues_completed == []
    assert agent.files_familiar == []


def test_agent_result():
    result = AgentResult(output="some output", exit_code=0, duration_seconds=42.5)
    assert result.success is True
    result2 = AgentResult(output="error", exit_code=1, duration_seconds=10.0)
    assert result2.success is False
