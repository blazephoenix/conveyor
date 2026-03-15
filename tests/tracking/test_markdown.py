import tempfile
from pathlib import Path

from conveyor.tracking.markdown import MarkdownStore
from conveyor.tracking.models import Intent, Issue, Agent, IssueStatus, RiskLevel


def test_write_and_read_intent(tmp_path):
    store = MarkdownStore(tmp_path)
    intent = Intent(
        id="INT-001",
        title="Add authentication",
        message="Add user authentication with JWT tokens",
    )
    store.save_intent(intent)

    path = tmp_path / "intents" / "INT-001-add-authentication.md"
    assert path.exists()

    loaded = store.load_intent("INT-001")
    assert loaded.id == "INT-001"
    assert loaded.title == "Add authentication"
    assert loaded.message == "Add user authentication with JWT tokens"


def test_write_and_read_issue(tmp_path):
    store = MarkdownStore(tmp_path)
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
    store.save_issue(issue)

    path = tmp_path / "issues" / "ISS-001-add-user-model.md"
    assert path.exists()

    loaded = store.load_issue("ISS-001")
    assert loaded.id == "ISS-001"
    assert loaded.agent == "backend"
    assert loaded.risk == RiskLevel.LOW
    assert loaded.status == IssueStatus.CREATED


def test_write_and_read_agent(tmp_path):
    store = MarkdownStore(tmp_path)
    agent = Agent(name="backend", role="APIs, models, business logic")
    store.save_agent(agent)

    path = tmp_path / "agents" / "backend.md"
    assert path.exists()

    loaded = store.load_agent("backend")
    assert loaded.name == "backend"
    assert loaded.role == "APIs, models, business logic"


def test_list_issues_for_intent(tmp_path):
    store = MarkdownStore(tmp_path)
    for i in range(3):
        issue = Issue(
            id=f"ISS-00{i+1}",
            intent="INT-001",
            title=f"Task {i+1}",
            agent="backend",
            branch=f"conveyor/iss-00{i+1}-task",
            depends_on=[],
            risk=RiskLevel.LOW,
        )
        store.save_issue(issue)

    issues = store.list_issues(intent_id="INT-001")
    assert len(issues) == 3


def test_next_intent_id(tmp_path):
    store = MarkdownStore(tmp_path)
    assert store.next_intent_id() == "INT-001"
    intent = Intent(id="INT-001", title="First", message="first intent")
    store.save_intent(intent)
    assert store.next_intent_id() == "INT-002"


def test_next_issue_id(tmp_path):
    store = MarkdownStore(tmp_path)
    assert store.next_issue_id() == "ISS-001"


def test_save_session(tmp_path):
    store = MarkdownStore(tmp_path)
    store.save_session("SES-001", "ISS-001", "Full agent output here")
    path = tmp_path / "sessions" / "SES-001-ISS-001.md"
    assert path.exists()
    assert "Full agent output here" in path.read_text()
