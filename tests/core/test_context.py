import subprocess
from pathlib import Path

from conveyor.core.context import (
    gather_file_tree,
    gather_git_log,
    gather_codebase_context,
    gather_prior_work,
)


def _make_repo(path: Path):
    subprocess.run(["git", "init"], cwd=path, capture_output=True)
    subprocess.run(["git", "checkout", "-b", "main"], cwd=path, capture_output=True)
    (path / "src").mkdir()
    (path / "src" / "app.py").write_text("print('hello')")
    (path / "src" / "utils.py").write_text("def helper(): pass")
    (path / "README.md").write_text("# Test")
    subprocess.run(["git", "add", "."], cwd=path, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=path, capture_output=True,
        env={"GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@t.com",
             "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "t@t.com",
             "HOME": str(path), "PATH": "/usr/bin:/bin:/usr/local/bin"},
    )


def test_gather_file_tree(tmp_path):
    _make_repo(tmp_path)
    tree = gather_file_tree(tmp_path)
    assert "src/" in tree
    assert "app.py" in tree
    assert ".git" not in tree


def test_gather_git_log(tmp_path):
    _make_repo(tmp_path)
    log = gather_git_log(tmp_path)
    assert "initial" in log


def test_gather_codebase_context(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('hello')")
    (tmp_path / "src" / "utils.py").write_text("def helper(): pass")
    context = gather_codebase_context(
        repo_dir=tmp_path,
        files_relevant=["src/app.py"],
        sibling_patterns=["src/*.py"],
    )
    assert "app.py" in context
    assert "print('hello')" in context


def test_gather_prior_work(tmp_path):
    # Simulate a completed upstream issue
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "model.py").write_text("class User: pass")
    work = gather_prior_work(
        repo_dir=tmp_path,
        completed_files=["src/model.py"],
    )
    assert "class User" in work
