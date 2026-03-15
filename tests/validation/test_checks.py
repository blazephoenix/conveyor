from unittest.mock import patch, MagicMock

from conveyor.validation.checks import (
    run_tests,
    parse_agent_report,
    parse_reviewer_verdict,
    check_scope,
    TestResult,
)


def test_parse_agent_report():
    output = """
Some agent output here...

CONVEYOR_REPORT_START
files_created: src/models/user.py, tests/test_user.py
files_modified: src/config.py
lines_added: 87
tests_added: 4
tests_passing: true
notes: Added User model with email and password fields
CONVEYOR_REPORT_END

Done!
"""
    report = parse_agent_report(output)
    assert report["files_created"] == "src/models/user.py, tests/test_user.py"
    assert report["lines_added"] == "87"
    assert report["tests_passing"] == "true"
    assert report["notes"] == "Added User model with email and password fields"


def test_parse_agent_report_missing():
    report = parse_agent_report("No report here")
    assert report == {}


def test_parse_reviewer_verdict_pass():
    output = """
Review looks good.

REVIEW_RESULT_START
passed: true
scope_ok: true
criteria_met: true
tests_ok: true
notes: All acceptance criteria met, code follows existing patterns
REVIEW_RESULT_END
"""
    verdict = parse_reviewer_verdict(output)
    assert verdict["passed"] == "true"
    assert verdict["scope_ok"] == "true"


def test_parse_reviewer_verdict_fail():
    output = """
REVIEW_RESULT_START
passed: false
scope_ok: false
criteria_met: true
tests_ok: true
notes: Agent modified src/api/routes.py which was forbidden
REVIEW_RESULT_END
"""
    verdict = parse_reviewer_verdict(output)
    assert verdict["passed"] == "false"
    assert verdict["scope_ok"] == "false"


def test_check_scope_pass():
    changed = ["src/models/user.py", "tests/test_user.py"]
    allowed = ["src/models/*", "tests/*"]
    forbidden = ["src/api/*"]
    ok, violations = check_scope(changed, allowed, forbidden)
    assert ok is True
    assert violations == []


def test_check_scope_forbidden_violation():
    changed = ["src/models/user.py", "src/api/routes.py"]
    allowed = ["src/models/*", "src/api/*"]
    forbidden = ["src/api/*"]
    ok, violations = check_scope(changed, allowed, forbidden)
    assert ok is False
    assert "src/api/routes.py" in violations[0]


@patch("conveyor.validation.checks.subprocess.run")
def test_run_tests_passes(mock_run):
    mock_run.return_value = MagicMock(
        stdout="4 passed", stderr="", returncode=0
    )
    result = run_tests("pytest", "/tmp/repo")
    assert result.passed is True
    assert result.exit_code == 0
    assert "4 passed" in result.output


@patch("conveyor.validation.checks.subprocess.run")
def test_run_tests_fails(mock_run):
    mock_run.return_value = MagicMock(
        stdout="1 failed, 3 passed", stderr="", returncode=1
    )
    result = run_tests("pytest", "/tmp/repo")
    assert result.passed is False


def test_run_tests_no_command():
    result = run_tests("", "/tmp/repo")
    assert result.passed is True
    assert "no test command" in result.output.lower()
