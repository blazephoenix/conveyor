from conveyor.execution.prompt import (
    build_worker_prompt,
    build_orchestrator_prompt,
    build_reviewer_prompt,
)
from conveyor.tracking.models import Issue, Agent, RiskLevel


def test_build_worker_prompt_has_all_sections():
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
        acceptance_criteria=["User model in src/models/user.py"],
    )
    agent = Agent(name="backend", role="APIs, models, business logic")
    prompt = build_worker_prompt(
        issue=issue,
        agent=agent,
        codebase_context="File tree here",
        prior_work="",
    )
    assert "Conveyor" in prompt
    assert "backend" in prompt
    assert "ISS-001" in prompt
    assert "User model" in prompt
    assert "src/models/user.py" in prompt
    assert "src/api/*" in prompt
    assert "CONVEYOR_REPORT" in prompt


def test_build_orchestrator_prompt():
    prompt = build_orchestrator_prompt(
        intent_message="Add user authentication with JWT",
        file_tree="src/\n  models/\n  api/",
        git_log="abc123 initial commit",
        claude_md="Use black for formatting",
    )
    assert "Add user authentication with JWT" in prompt
    assert "src/" in prompt
    assert "CONVEYOR_PLAN" in prompt


def test_build_reviewer_prompt():
    issue = Issue(
        id="ISS-001",
        intent="INT-001",
        title="Add User model",
        agent="backend",
        branch="conveyor/iss-001-user-model",
        depends_on=[],
        risk=RiskLevel.LOW,
        files_allowed=["src/models/user.py"],
        acceptance_criteria=["User model in src/models/user.py"],
    )
    prompt = build_reviewer_prompt(
        issue=issue,
        diff="diff --git a/src/models/user.py ...",
        test_output="4 passed",
        test_exit_code=0,
    )
    assert "ISS-001" in prompt
    assert "diff" in prompt
    assert "4 passed" in prompt
    assert "REVIEW_RESULT" in prompt
