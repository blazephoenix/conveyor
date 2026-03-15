from typer.testing import CliRunner
from conveyor.cli import app

runner = CliRunner()


def test_cli_has_init_command():
    result = runner.invoke(app, ["init", "--help"])
    assert result.exit_code == 0


def test_cli_has_intent_command():
    result = runner.invoke(app, ["intent", "--help"])
    assert result.exit_code == 0


def test_cli_has_status_command():
    result = runner.invoke(app, ["status", "--help"])
    assert result.exit_code == 0


def test_cli_has_issues_command():
    result = runner.invoke(app, ["issues", "--help"])
    assert result.exit_code == 0


def test_cli_has_review_command():
    result = runner.invoke(app, ["review", "--help"])
    assert result.exit_code == 0


def test_cli_has_log_command():
    result = runner.invoke(app, ["log", "--help"])
    assert result.exit_code == 0
