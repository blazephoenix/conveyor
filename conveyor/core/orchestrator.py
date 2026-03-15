from __future__ import annotations

from pathlib import Path

from conveyor.core.context import gather_file_tree, gather_git_log
from conveyor.core.planner import parse_plan, TaskGraph
from conveyor.execution.adapter import ClaudeCodeAdapter
from conveyor.execution.prompt import build_orchestrator_prompt


def run_orchestrator(
    intent_message: str,
    repo_dir: Path,
    claude_md: str = "",
    adapter: ClaudeCodeAdapter | None = None,
) -> TaskGraph:
    adapter = adapter or ClaudeCodeAdapter()

    file_tree = gather_file_tree(repo_dir)
    git_log = gather_git_log(repo_dir)

    prompt = build_orchestrator_prompt(
        intent_message=intent_message,
        file_tree=file_tree,
        git_log=git_log,
        claude_md=claude_md,
    )

    result = adapter.execute(
        prompt=prompt,
        workdir=str(repo_dir),
        timeout=600,  # Orchestrator gets more time to think
    )

    if not result.success:
        return TaskGraph(analysis=f"Orchestrator failed: {result.output}")

    return parse_plan(result.output)
