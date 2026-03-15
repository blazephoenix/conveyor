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

Conveyor is not on PyPI yet. Install from source:

```bash
# 1. Clone the repo
git clone https://github.com/blazephoenix/conveyor.git
cd conveyor

# 2. Create a virtual environment (Python 3.11+ required)
python3 -m venv .venv
source .venv/bin/activate

# Or with uv (recommended — handles Python version automatically)
uv venv --python 3.12 .venv
source .venv/bin/activate

# 3. Install in editable mode
pip install -e .
# or: uv pip install -e .
```

### Using Conveyor in another project

Since Conveyor is installed from source into its own venv, you have two options:

```bash
# Option A: Activate the venv first, then commands work normally
source /path/to/conveyor/.venv/bin/activate
cd your-project
conveyor init
conveyor intent "Add a health endpoint"

# Option B: Use the full path every time (no activation needed)
cd your-project
/path/to/conveyor/.venv/bin/conveyor init
/path/to/conveyor/.venv/bin/conveyor intent "Add a health endpoint"
```

> **Tip:** You can alias it in your shell profile:
> ```bash
> alias conveyor="/path/to/conveyor/.venv/bin/conveyor"
> ```

### Walkthrough

Here's a complete example — initializing Conveyor in a Next.js project and running an intent.

#### Step 1: Initialize

```bash
cd your-project
conveyor init
```

You'll see:

```
 ██████╗ ██████╗ ███╗   ██╗██╗   ██╗███████╗██╗   ██╗ ██████╗ ██████╗
██╔════╝██╔═══██╗████╗  ██║██║   ██║██╔════╝╚██╗ ██╔╝██╔═══██╗██╔══██╗
██║     ██║   ██║██╔██╗ ██║██║   ██║█████╗   ╚████╔╝ ██║   ██║██████╔╝
██║     ██║   ██║██║╚██╗██║╚██╗ ██╔╝██╔══╝    ╚██╔╝  ██║   ██║██╔══██╗
╚██████╗╚██████╔╝██║ ╚████║ ╚████╔╝ ███████╗   ██║   ╚██████╔╝██║  ██║
 ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝  ╚═══╝  ╚══════╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝
...
┌   conveyor init
│
│  Project: /home/you/your-project
│
◆  Initialized .conveyor/
◆  Scanned 847 files
◇  Detected: Node.js, TypeScript
◆  Agents created: frontend, backend, testing, devops, reviewer
│
◇  Next commands ─────────────────────────────────╮
│  conveyor intent "..."  Decompose and execute    │
│  conveyor status       Show intent progress      │
│  ...                                             │
├──────────────────────────────────────────────────╯
│
└  Ready!
```

This creates a `.conveyor/` directory with config, agent definitions (tailored to your detected stack), and empty directories for intents, issues, and sessions.

#### Step 2: Run an intent

```bash
conveyor intent "Create a health endpoint in the API routes"
```

Conveyor will:

**1. Analyze your codebase** — scans file tree, reads git history, loads CLAUDE.md if present:

```
┌   conveyor intent
│
│  Intent: Create a health endpoint in the API routes
│
│  [0s] Scanning file tree...
│  [0s] Found 30 entries in file tree
│  [1s] Reading git history...
│  [1s] Assembling orchestrator prompt...
│  [1s] Sending to orchestrator — analyzing codebase and decomposing intent...
│  [25s] Orchestrator responded in 24.9s — parsing plan...
│  [25s] Extracted 2 tasks from plan
```

**2. Show the plan** — a table of tasks with agents, risk levels, and dependencies:

```
                         Plan: 2 tasks
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Task               ┃ Agent   ┃ Risk ┃ Depends on ┃ Files                 ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━┩
│ 1. Create GET      │ backend │ low  │ —          │ src/app/api/health/   │
│    /api/health     │         │      │            │ route.ts              │
│ 2. Verify endpoint │ testing │ low  │ 1          │                       │
│    passes lint     │         │      │            │                       │
└────────────────────┴─────────┴──────┴────────────┴───────────────────────┘

[a]pprove  [r]eject [a]:
```

**3. Execute** — type `a` (or press Enter) to approve. Conveyor creates branches, dispatches agents, and shows progress:

```
◇  Executing task graph... (2 tasks)
│
│  [27s | 0%] [ISS-001] Creating branch conveyor/iss-001-create-get-api-health-route
│  [27s | 0%] [ISS-001] Dispatching backend agent — Create GET /api/health route
│  [55s | 16%] [ISS-001] Agent completed in 28.0s — moving to validation
│  [55s | 16%] [ISS-001] Scope check passed
│  [56s | 33%] [ISS-001] Dispatching reviewer agent...
│  [78s | 50%] [ISS-001] Reviewer verdict: PASSED — All criteria met
│  ...
│  [120s | 100%] Returning to main branch
│
◇  Summary ──────────────────────────────────────╮
│                                                 │
│  All 2 tasks completed and merged               │
│  Total time: 2m00s                              │
│                                                 │
├─────────────────────────────────────────────────╯
│
└  Intent complete!
```

Use `--yes` to skip the approval prompt: `conveyor intent --yes "..."`.

#### Step 3: If something fails

Tasks can fail if the agent produces bad code, violates scope, or the reviewer rejects the work. When that happens:

```bash
# See what failed
conveyor status
conveyor issues ISS-001    # detailed view with agent report + reviewer verdict

# Retry the failed task (also unblocks downstream tasks)
conveyor retry ISS-001

# Or retry all failed tasks automatically
conveyor retry
```

#### Step 4: Review medium/high risk changes

If a task is medium or high risk, Conveyor pauses and asks for your approval before merging:

```bash
conveyor review
```

You can view the diff before deciding:

```
ISS-003: Add authentication middleware
  Review type: merge
  Risk: medium
  Branch: conveyor/iss-003-add-auth-middleware
  [a]pprove  [d]iff  [r]eject:
```

#### Step 5: Check the activity trail

```bash
# Full activity log across all issues
conveyor log

# Log for a specific issue
conveyor log --issue ISS-001
```

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
