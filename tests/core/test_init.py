from pathlib import Path

from conveyor.core.init import run_init


def test_init_creates_conveyor_dir(tmp_path):
    run_init(tmp_path)
    assert (tmp_path / ".conveyor").is_dir()
    assert (tmp_path / ".conveyor" / "intents").is_dir()
    assert (tmp_path / ".conveyor" / "issues").is_dir()
    assert (tmp_path / ".conveyor" / "agents").is_dir()
    assert (tmp_path / ".conveyor" / "sessions").is_dir()


def test_init_creates_config(tmp_path):
    run_init(tmp_path)
    assert (tmp_path / ".conveyor" / "config.toml").exists()


def test_init_creates_default_agents(tmp_path):
    run_init(tmp_path)
    agents_dir = tmp_path / ".conveyor" / "agents"
    assert (agents_dir / "frontend.md").exists()
    assert (agents_dir / "backend.md").exists()
    assert (agents_dir / "testing.md").exists()
    assert (agents_dir / "devops.md").exists()
    assert (agents_dir / "reviewer.md").exists()


def test_init_adds_gitignore_entry(tmp_path):
    # Create existing .gitignore
    (tmp_path / ".gitignore").write_text("node_modules/\n")
    run_init(tmp_path)
    content = (tmp_path / ".gitignore").read_text()
    assert ".conveyor/" in content
    assert "node_modules/" in content


def test_init_creates_gitignore_if_missing(tmp_path):
    run_init(tmp_path)
    content = (tmp_path / ".gitignore").read_text()
    assert ".conveyor/" in content


def test_init_detects_python_stack(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\n')
    result = run_init(tmp_path)
    assert "Python" in result.stack_detected


def test_init_detects_node_stack(tmp_path):
    (tmp_path / "package.json").write_text('{"name": "test"}')
    result = run_init(tmp_path)
    assert "Node.js" in result.stack_detected


def test_init_reads_claude_md(tmp_path):
    (tmp_path / "CLAUDE.md").write_text("# Project conventions\nUse black for formatting.")
    result = run_init(tmp_path)
    assert result.claude_md is not None
    assert "black" in result.claude_md


def test_init_is_idempotent(tmp_path):
    run_init(tmp_path)
    run_init(tmp_path)  # Should not crash or duplicate entries
    content = (tmp_path / ".gitignore").read_text()
    assert content.count(".conveyor/") == 1
