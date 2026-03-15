from __future__ import annotations

import subprocess
from pathlib import Path


def _git(args: list[str], workdir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        cwd=workdir,
        capture_output=True,
        text=True,
    )


def current_branch(workdir: Path) -> str:
    result = _git(["rev-parse", "--abbrev-ref", "HEAD"], workdir)
    return result.stdout.strip()


def create_branch(name: str, workdir: Path) -> None:
    _git(["checkout", "-b", name], workdir)


def checkout_branch(name: str, workdir: Path) -> None:
    _git(["checkout", name], workdir)


def merge_branch(branch: str, workdir: Path) -> bool:
    result = _git(["merge", branch, "--no-ff", "-m", f"Merge {branch}"], workdir)
    return result.returncode == 0


def branch_diff(branch: str, base: str, workdir: Path) -> str:
    result = _git(["diff", f"{base}...{branch}"], workdir)
    return result.stdout


def changed_files(branch: str, base: str, workdir: Path) -> list[str]:
    result = _git(["diff", "--name-only", f"{base}...{branch}"], workdir)
    return [f for f in result.stdout.strip().split("\n") if f]
