from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from conveyor.config import default_config, save_config
from conveyor.tracking.markdown import MarkdownStore
from conveyor.tracking.models import Agent


STACK_INDICATORS = {
    "pyproject.toml": "Python",
    "setup.py": "Python",
    "requirements.txt": "Python",
    "package.json": "Node.js",
    "tsconfig.json": "TypeScript",
    "Cargo.toml": "Rust",
    "go.mod": "Go",
    "Gemfile": "Ruby",
    "pom.xml": "Java",
    "build.gradle": "Java",
}

AGENT_DEFAULTS = {
    "frontend": "Frontend specialist. UI components, styles, client-side logic.",
    "backend": "Backend specialist. APIs, models, business logic, migrations.",
    "testing": "Testing specialist. Write and fix tests, ensure meaningful coverage.",
    "devops": "DevOps specialist. CI/CD, Docker, infrastructure configs.",
    "reviewer": "Code review specialist. Verify scope, correctness, and test coverage.",
}


@dataclass
class InitResult:
    conveyor_dir: Path
    stack_detected: list[str] = field(default_factory=list)
    claude_md: str | None = None
    file_count: int = 0


def run_init(repo_dir: Path) -> InitResult:
    conveyor_dir = repo_dir / ".conveyor"
    result = InitResult(conveyor_dir=conveyor_dir)

    # Create .conveyor/ and subdirs via MarkdownStore
    store = MarkdownStore(conveyor_dir)
    store._ensure_dirs()

    # Write config.toml
    config_path = conveyor_dir / "config.toml"
    if not config_path.exists():
        save_config(default_config(), config_path)

    # Detect stack
    for filename, stack in STACK_INDICATORS.items():
        if (repo_dir / filename).exists() and stack not in result.stack_detected:
            result.stack_detected.append(stack)

    # Create lightweight agent stubs — the orchestrator enriches these at intent-time
    for name, role in AGENT_DEFAULTS.items():
        agent_path = conveyor_dir / "agents" / f"{name}.md"
        if not agent_path.exists():
            store.save_agent(Agent(name=name, role=role))

    # Add .conveyor/ to .gitignore
    gitignore_path = repo_dir / ".gitignore"
    if gitignore_path.exists():
        content = gitignore_path.read_text()
        if ".conveyor/" not in content:
            with open(gitignore_path, "a") as f:
                f.write("\n.conveyor/\n")
    else:
        gitignore_path.write_text(".conveyor/\n")

    # Read CLAUDE.md
    claude_md_path = repo_dir / "CLAUDE.md"
    if claude_md_path.exists():
        result.claude_md = claude_md_path.read_text()

    # Count files (simple, no tree-sitter)
    result.file_count = sum(
        1 for f in repo_dir.rglob("*")
        if f.is_file()
        and ".git" not in f.parts
        and ".conveyor" not in f.parts
        and ".venv" not in f.parts
    )

    return result
