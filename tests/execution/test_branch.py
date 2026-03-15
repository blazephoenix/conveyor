import subprocess
from pathlib import Path

from conveyor.execution.branch import (
    create_branch,
    checkout_branch,
    merge_branch,
    current_branch,
    branch_diff,
)


def _init_git_repo(path: Path):
    """Helper to create a git repo with an initial commit."""
    subprocess.run(["git", "init"], cwd=path, capture_output=True)
    subprocess.run(["git", "checkout", "-b", "main"], cwd=path, capture_output=True)
    (path / "README.md").write_text("# Test")
    subprocess.run(["git", "add", "."], cwd=path, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=path,
        capture_output=True,
        env={"GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@test.com",
             "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@test.com",
             "HOME": str(path), "PATH": "/usr/bin:/bin:/usr/local/bin"},
    )


def test_create_branch(tmp_path):
    _init_git_repo(tmp_path)
    create_branch("conveyor/iss-001-test", tmp_path)
    assert current_branch(tmp_path) == "conveyor/iss-001-test"


def test_checkout_branch(tmp_path):
    _init_git_repo(tmp_path)
    create_branch("conveyor/iss-001-test", tmp_path)
    checkout_branch("main", tmp_path)
    assert current_branch(tmp_path) == "main"
    checkout_branch("conveyor/iss-001-test", tmp_path)
    assert current_branch(tmp_path) == "conveyor/iss-001-test"


def test_merge_branch_clean(tmp_path):
    _init_git_repo(tmp_path)
    create_branch("conveyor/iss-001-test", tmp_path)
    (tmp_path / "new_file.py").write_text("print('hello')")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "add file"],
        cwd=tmp_path,
        capture_output=True,
        env={"GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@test.com",
             "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@test.com",
             "HOME": str(tmp_path), "PATH": "/usr/bin:/bin:/usr/local/bin"},
    )
    checkout_branch("main", tmp_path)
    success = merge_branch("conveyor/iss-001-test", tmp_path)
    assert success is True
    assert (tmp_path / "new_file.py").exists()


def test_branch_diff(tmp_path):
    _init_git_repo(tmp_path)
    create_branch("conveyor/iss-001-test", tmp_path)
    (tmp_path / "new_file.py").write_text("print('hello')")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "add file"],
        cwd=tmp_path,
        capture_output=True,
        env={"GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@test.com",
             "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@test.com",
             "HOME": str(tmp_path), "PATH": "/usr/bin:/bin:/usr/local/bin"},
    )
    diff = branch_diff("conveyor/iss-001-test", "main", tmp_path)
    assert "new_file.py" in diff
