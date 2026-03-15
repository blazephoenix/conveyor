<div align="center">

```
 ██████╗ ██████╗ ███╗   ██╗██╗   ██╗███████╗██╗   ██╗ ██████╗ ██████╗
██╔════╝██╔═══██╗████╗  ██║██║   ██║██╔════╝╚██╗ ██╔╝██╔═══██╗██╔══██╗
██║     ██║   ██║██╔██╗ ██║██║   ██║█████╗   ╚████╔╝ ██║   ██║██████╔╝
██║     ██║   ██║██║╚██╗██║╚██╗ ██╔╝██╔══╝    ╚██╔╝  ██║   ██║██╔══██╗
╚██████╗╚██████╔╝██║ ╚████║ ╚████╔╝ ███████╗   ██║   ╚██████╔╝██║  ██║
 ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝  ╚═══╝  ╚══════╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝
```

**AI-native project orchestration for engineering teams**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-orange.svg)](#%EF%B8%8F-status)

[Getting Started](#-getting-started) · [How It Works](#-how-it-works) · [Commands](#-commands) · [Docs](docs/) · [Contributing](CONTRIBUTING.md)

</div>

---

## What is Conveyor?

Conveyor is a CLI tool that takes a plain-English intent — like *"Add user authentication with JWT"* — and decomposes it into a dependency-aware task graph, assigns each task to a specialized agent (frontend, backend, testing, devops), executes them sequentially via [Claude Code](https://docs.anthropic.com/en/docs/claude-code), validates results with a reviewer agent, and merges through governance gates.

Think of it as a project manager that actually writes the code.

```
You say:  "Add a health endpoint to the API"

Conveyor:
  1. Scans your codebase (file tree, git history, stack detection)
  2. Calls an orchestrator to decompose the intent into tasks
  3. Creates branches, dispatches agents, reviews their work
  4. Auto-merges low-risk changes, pauses for your approval on high-risk ones
  5. Reports results
```

## Warning: Status

**This is an early alpha (v0.1.0).** Things will break. The API will change. Here be dragons.

What works:
- Init, intent decomposition, sequential execution, review, merge
- Stack detection (Python, Node.js, TypeScript, Rust, Go)
- Risk-based governance gates
- Retry failed tasks

What doesn't (yet):
- Parallel task execution
- Permission bubbling from Claude Code subprocesses
- Recovery from mid-execution crashes
- Windows support (untested)

If you hit a bug, [open an issue](https://github.com/blazephoenix/conveyor/issues). We'd genuinely appreciate it.

## Getting Started

### Prerequisites

- **Python 3.11+** — Conveyor uses `StrEnum` and modern type hints
- **Claude Code CLI** — installed and authenticated ([install guide](https://docs.anthropic.com/en/docs/claude-code))
- **Git** — any recent version

### Install

```bash
# From source (recommended during alpha)
git clone https://github.com/blazephoenix/conveyor.git
cd conveyor
pip install -e .

# Or with uv
uv pip install -e .
```

### Quick Start

```bash
# 1. Navigate to any git repo
cd your-project

# 2. Initialize Conveyor
conveyor init

# 3. Run an intent
conveyor intent "Add a health endpoint to the API"
```

Conveyor will scan your repo, detect your stack, create a plan, ask for your approval, and execute.

## How It Works

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────┐
│  Your Intent │────>│ Orchestrator │────>│  Task Graph  │────>│  Runner  │
│  (plain text)│     │ (Claude Code)│     │ (dependency  │     │  (state  │
│              │     │              │     │  ordered)    │     │  machine)│
└─────────────┘     └──────────────┘     └─────────────┘     └────┬─────┘
                                                                   │
                    ┌──────────────┐     ┌─────────────┐          │
                    │   Reviewer   │<────│   Worker     │<─────────┘
                    │   Agent      │     │   Agent      │
                    │ (validates)  │     │ (executes)   │
                    └──────┬───────┘     └─────────────┘
                           │
                    ┌──────v───────┐
                    │  Governance  │
                    │  (merge/     │
                    │   pause/fail)│
                    └──────────────┘
```

### The Flow

1. **`conveyor init`** — Scans your repo, detects stack (Python, Node.js, TypeScript, etc.), creates `.conveyor/` with config and agent definitions
2. **`conveyor intent "..."`** — Sends your intent + codebase context to an orchestrator agent that produces a task graph
3. **Execution** — For each task in dependency order:
   - Creates a feature branch
   - Dispatches the assigned agent (backend, frontend, testing, devops) with a tailored prompt
   - Agent writes code, commits to the branch
   - Runs tests (if configured)
   - Dispatches a reviewer agent to validate scope, correctness, and quality
4. **Governance** — Based on risk level:
   - **Low risk**: Auto-merge to main
   - **Medium risk**: Pause for your approval before merging
   - **High risk**: Pause for plan approval before execution, then again before merging

### Data Layer

Conveyor stores everything as markdown files with YAML frontmatter in `.conveyor/`:

```
.conveyor/
├── config.toml          # Project configuration
├── intents/             # Your requests (INT-001, INT-002, ...)
│   └── INT-001-add-auth.md
├── issues/              # Decomposed tasks (ISS-001, ISS-002, ...)
│   ├── ISS-001-add-user-model.md
│   └── ISS-002-add-login-endpoint.md
├── agents/              # Agent definitions and history
│   ├── frontend.md
│   ├── backend.md
│   ├── testing.md
│   ├── devops.md
│   └── reviewer.md
└── sessions/            # Full agent execution transcripts
    └── SES-001-ISS-001.md
```

No database. No external services. Everything is local, human-readable, and git-friendly.

## Commands

| Command | Description |
|---------|-------------|
| `conveyor init` | Scan repo, detect stack, create `.conveyor/` directory |
| `conveyor intent "..."` | Decompose an intent into tasks and execute |
| `conveyor status` | Show current intent progress and issue states |
| `conveyor issues [ID]` | List all issues or inspect a specific one |
| `conveyor retry [ID]` | Retry failed or blocked issues |
| `conveyor review` | Review pending medium/high risk merges |
| `conveyor log [--issue ID]` | Show activity trail |

### Flags

| Flag | Command | Description |
|------|---------|-------------|
| `--yes, -y` | `intent` | Auto-approve the plan without prompting |
| `--issue ID` | `log` | Filter activity log by issue |

## Configuration

After running `conveyor init`, edit `.conveyor/config.toml`:

```toml
[conveyor]
version = "0.1.0"

[execution]
timeout_seconds = 300       # Max time per agent execution
sequential = true           # Sequential task execution (parallel not yet supported)

[governance]
auto_merge_low_risk = true  # Auto-merge low risk tasks
review_medium_risk = true   # Pause for approval on medium risk
review_high_risk = true     # Pause for approval on high risk

[agents]
roster = ["frontend", "backend", "testing", "devops", "reviewer"]

[testing]
command = ""                # e.g. "pytest", "npm test" — leave empty to skip

[claude]
permission_mode = "bypassPermissions"  # Claude Code permission mode for agents
```

See [docs/configuration.md](docs/configuration.md) for the full reference.

## Architecture

```
conveyor/
├── cli.py                  # Typer CLI — 7 commands
├── config.py               # TOML config read/write
├── core/
│   ├── init.py             # Repo scanning, stack detection, agent creation
│   ├── orchestrator.py     # Intent decomposition via Claude Code
│   ├── planner.py          # Parse orchestrator output, topological sort
│   ├── context.py          # File tree, git log, codebase context assembly
│   └── governance.py       # Risk-based approval gates
├── execution/
│   ├── adapter.py          # Claude Code subprocess wrapper
│   ├── branch.py           # Git branch operations
│   ├── runner.py           # State machine — the core execution loop
│   └── prompt.py           # Prompt builder for worker/reviewer/orchestrator
├── validation/
│   └── checks.py           # Test runner, report parser, scope checker
└── tracking/
    ├── models.py           # Intent, Issue, Agent, AgentResult dataclasses
    ├── markdown.py         # Markdown + YAML frontmatter store
    └── events.py           # Activity log event system
```

### Built With

- [Python 3.11+](https://www.python.org/) — core runtime
- [Typer](https://typer.tiangolo.com/) — CLI framework
- [Rich](https://rich.readthedocs.io/) — terminal formatting
- [PyYAML](https://pyyaml.org/) — frontmatter parsing
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — AI agent execution

## Testing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest -v

# 79 tests covering all modules
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

Short version: fork, branch, test, PR. We're in early alpha — everything is fair game for improvement.

## License

MIT License. See [LICENSE](LICENSE) for details.
