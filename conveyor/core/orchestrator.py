from __future__ import annotations

from pathlib import Path
from typing import Callable

from conveyor.core.context import gather_file_tree, gather_git_log
from conveyor.core.planner import parse_plan, TaskGraph
from conveyor.execution.adapter import ClaudeCodeAdapter
from conveyor.execution.prompt import build_orchestrator_prompt


def run_orchestrator(
    intent_message: str,
    repo_dir: Path,
    claude_md: str = "",
    adapter: ClaudeCodeAdapter | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> TaskGraph:
    def _emit(msg: str) -> None:
        if on_progress:
            on_progress(msg)

    adapter = adapter or ClaudeCodeAdapter()

    _emit("Scanning file tree...")
    file_tree = gather_file_tree(repo_dir)
    file_count = file_tree.count("\n") + 1
    _emit(f"Found {file_count} entries in file tree")

    _emit("Reading git history...")
    git_log = gather_git_log(repo_dir)
    commit_count = len(git_log.strip().split("\n")) if git_log.strip() else 0
    _emit(f"Found {commit_count} recent commits")

    if claude_md:
        _emit("Loading project conventions from CLAUDE.md")

    _emit("Assembling orchestrator prompt...")
    prompt = build_orchestrator_prompt(
        intent_message=intent_message,
        file_tree=file_tree,
        git_log=git_log,
        claude_md=claude_md,
    )

    _emit("Sending to orchestrator — analyzing codebase and decomposing intent...")
    result = adapter.execute(
        prompt=prompt,
        workdir=str(repo_dir),
        timeout=600,
    )

    if not result.success:
        _emit("Orchestrator failed")
        return TaskGraph(analysis=f"Orchestrator failed: {result.output}")

    _emit(f"Orchestrator responded in {result.duration_seconds:.1f}s — parsing plan...")
    graph = parse_plan(result.output)
    _emit(f"Extracted {len(graph.tasks)} tasks from plan")

    return graph
