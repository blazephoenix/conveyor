from __future__ import annotations

import fnmatch
import subprocess
from pathlib import Path

IGNORE_DIRS = {".git", ".conveyor", ".venv", "node_modules", "__pycache__", ".tox"}


def gather_file_tree(repo_dir: Path, max_depth: int = 4) -> str:
    lines = []
    _walk_tree(repo_dir, repo_dir, lines, max_depth, depth=0)
    return "\n".join(lines)


def _walk_tree(root: Path, current: Path, lines: list, max_depth: int, depth: int):
    if depth > max_depth:
        return
    items = sorted(current.iterdir(), key=lambda p: (not p.is_dir(), p.name))
    for item in items:
        if item.name in IGNORE_DIRS:
            continue
        indent = "  " * depth
        if item.is_dir():
            lines.append(f"{indent}{item.name}/")
            _walk_tree(root, item, lines, max_depth, depth + 1)
        else:
            lines.append(f"{indent}{item.name}")


def gather_git_log(repo_dir: Path, max_entries: int = 20) -> str:
    result = subprocess.run(
        ["git", "log", f"--max-count={max_entries}", "--oneline"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def gather_codebase_context(
    repo_dir: Path,
    files_relevant: list[str],
    sibling_patterns: list[str] | None = None,
    max_file_size: int = 10_000,
) -> str:
    sections = []

    # Include relevant files
    for file_path in files_relevant:
        full_path = repo_dir / file_path
        if full_path.exists() and full_path.stat().st_size <= max_file_size:
            content = full_path.read_text()
            sections.append(f"### {file_path}\n```\n{content}\n```")

    # Include sibling files
    if sibling_patterns:
        seen = set(files_relevant)
        for pattern in sibling_patterns:
            for match in repo_dir.glob(pattern):
                rel = str(match.relative_to(repo_dir))
                if rel not in seen and match.stat().st_size <= max_file_size:
                    seen.add(rel)
                    content = match.read_text()
                    sections.append(f"### {rel} (sibling)\n```\n{content}\n```")

    return "\n\n".join(sections)


def gather_prior_work(
    repo_dir: Path,
    completed_files: list[str],
    max_file_size: int = 10_000,
) -> str:
    sections = []
    for file_path in completed_files:
        full_path = repo_dir / file_path
        if full_path.exists() and full_path.stat().st_size <= max_file_size:
            content = full_path.read_text()
            sections.append(f"### {file_path} (from upstream task)\n```\n{content}\n```")
    return "\n\n".join(sections) if sections else "No prior work from upstream tasks."
