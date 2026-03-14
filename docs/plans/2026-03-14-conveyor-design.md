# Conveyor — Design Document

> AI-native project orchestration for engineering teams that ship fast.
> Agents are first-class. Humans are the board.

---

## 1. What is Conveyor?

Conveyor is a CLI-first orchestrator that sits on top of coding agents (Claude Code) and coordinates them to execute multi-step engineering tasks on real repositories. Humans provide intent, Conveyor decomposes it into a dependency-aware task graph, assigns named agent roles, executes sequentially, validates via a reviewer agent, and merges through governance gates.

### Core loop

```
Board gives intent → Orchestrator reads codebase + decomposes into task graph
→ named agents execute on branches → reviewer validates → governance gate → merge → done
```

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────┐
│  CLI (Typer)                                             │
│  conveyor init · intent · status · issues · review · log │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│  Orchestrator                                            │
│                                                          │
│  ┌──────────────┐ ┌───────────────┐ ┌────────────────┐ │
│  │ Orchestrator │ │ Governance    │ │ State machine  │ │
│  │ (Claude Code │ │ 3-tier risk   │ │ Issue lifecycle│ │
│  │  subprocess) │ │ gates         │ │ runner         │ │
│  └──────────────┘ └───────────────┘ └────────────────┘ │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Context assembly                                  │   │
│  │ File selection · CLAUDE.md · prior work · scope   │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────┐ ┌────────────────────────────────┐   │
│  │ Branch mgmt  │ │ Tracking                       │   │
│  │ Create/merge │ │ Markdown files in .conveyor/    │   │
│  └──────────────┘ └────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│  Agent adapter (Claude Code CLI subprocess)              │
│  Single adapter — used for orchestrator and all agents   │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│  Reviewer agent                                          │
│  Scope check · file check · test results · code review   │
│  Tests run as direct subprocess, results fed to reviewer │
└─────────────────────────────────────────────────────────┘
```

### Key design decisions

- **No separate API call for orchestrator** — everything goes through Claude Code subprocess
- **No SQLite** — markdown files in `.conveyor/` are the data layer
- **No tree-sitter** — orchestrator reads codebase directly via Claude Code (TODO: add tree-sitter later for scale)
- **No retry loops** — fail fast, report to user, let them decide
- **Sequential execution only** — tasks run one at a time in dependency order
- **Web UI is nice-to-have** — not in v1 scope

---

## 3. Project structure

```
conveyor/
├── conveyor/
│   ├── __init__.py
│   ├── cli.py                    # Typer CLI entry point
│   ├── core/
│   │   ├── orchestrator.py       # Analyzes codebase, decomposes intent
│   │   ├── context.py            # Context assembly — file selection for prompts
│   │   ├── planner.py            # Parse orchestrator output into task graph
│   │   └── governance.py         # Risk assessment, approval gates
│   ├── execution/
│   │   ├── adapter.py            # Claude Code subprocess adapter
│   │   ├── branch.py             # Git branch create/checkout/merge
│   │   ├── runner.py             # State machine — runs task graph sequentially
│   │   └── prompt.py             # Prompt assembler (6-section builder)
│   ├── validation/
│   │   └── checks.py             # Test runner (direct subprocess)
│   ├── tracking/
│   │   ├── models.py             # Intent, Issue, Agent dataclasses
│   │   ├── markdown.py           # Read/write .conveyor/ markdown files
│   │   └── events.py             # Activity log event system
│   └── config.py                 # .conveyor/config.toml management
├── pyproject.toml
├── tests/
└── docs/
    └── plans/
```

---

## 4. Data layer — `.conveyor/` directory

No database. Everything is markdown with YAML frontmatter.

```
.conveyor/
├── config.toml
├── intents/
│   └── INT-001-add-jwt-auth.md
├── issues/
│   └── ISS-001-user-model.md
├── agents/
│   ├── frontend.md
│   ├── backend.md
│   ├── testing.md
│   ├── devops.md
│   └── reviewer.md
└── sessions/
    └── SES-001-ISS-001.md
```

### File formats

**Intent file:**

```markdown
---
id: INT-001
title: Add user authentication with JWT tokens
status: in_progress
created: 2026-03-14T10:32:00Z
---

# Add user authentication with JWT tokens

## Board intent
[Original request from the user]

## Orchestrator analysis
[Orchestrator's reasoning about what needs to change and why]

## Task graph
[Table of issues with dependencies, risk, agent assignments]

## Activity log
[Timestamped events]
```

**Issue file:**

```markdown
---
id: ISS-001
intent: INT-001
title: Add User model and database migration
status: complete
agent: backend
branch: conveyor/iss-001-user-model
depends_on: []
risk: low
created: 2026-03-14T10:32:00Z
completed: 2026-03-14T10:32:52Z
---

# Add User model and database migration

## Acceptance criteria
- [ ] User model in src/models/user.py
- [ ] Alembic migration generated

## Constraints
Files allowed: src/models/user.py, alembic/versions/*
Files forbidden: src/api/*, src/auth/*

## Agent report
[Parsed CONVEYOR_REPORT output]

## Reviewer verdict
[Reviewer agent's assessment]

## Activity log
[Timestamped events]
```

**Agent file:**

```markdown
---
name: backend
role: APIs, models, business logic, migrations
issues_completed: [ISS-001, ISS-005]
files_familiar: [src/models/*, src/api/*]
---

# Backend agent

## History
- ISS-001: Added User model (2026-03-14)
- ISS-005: Added billing endpoints (2026-03-15)
```

### Design notes

- IDs are sequential: `INT-001`, `ISS-001`, `SES-001`. Generated by counting existing files + 1.
- Session files store raw Claude Code stdout per execution.
- Gitignored by default. `conveyor init` adds `.conveyor/` to `.gitignore`.
- Trade-off: globbing + YAML parsing is slow at scale. SQLite is the upgrade path when needed.

---

## 5. State machine & issue lifecycle

```
created → queued → running → validating → complete
                                  │
                                  ├── failed
                                  ├── blocked (upstream failed)
                                  └── paused (board intervention needed)
```

### Runner loop

```python
while not all_terminal(issues):
    for issue in topological_order(issues):
        match issue.status:
            case "created":
                issue.status = "queued"

            case "queued":
                if all_deps_complete(issue):
                    if issue.risk == "high":
                        issue.status = "paused"
                        prompt_board_review(issue, review_type="plan")
                    else:
                        issue.status = "running"
                elif any_dep_failed(issue):
                    issue.status = "blocked"

            case "running":
                result = execute_agent(issue)
                issue.status = "validating"

            case "validating":
                # Run tests (direct subprocess), then reviewer agent
                test_result = run_tests(issue)
                review = run_reviewer(issue, test_result)
                if review.passed:
                    if issue.risk == "low":
                        auto_merge(issue)
                        issue.status = "complete"
                    else:
                        issue.status = "paused"
                        prompt_board_review(issue, review_type="merge")
                else:
                    issue.status = "failed"

            case "paused":
                # Waiting for user via CLI
                pass
```

### Key properties

- Topological order ensures dependencies run first
- Governance gates are natural state transitions (`paused` with review type)
- `blocked` cascades when an upstream fails
- No retries — `failed` is terminal, user decides next steps
- State persisted to issue markdown after every transition — Ctrl+C safe, runner resumes by re-reading files

### Parked for v2: reopen flow

Board should be able to comment on completed/failed issues, triggering the orchestrator to re-evaluate and restart the state machine. Adds `reopened` state that feeds back into `queued`. Architecture supports this — not implementing in v1.

---

## 6. Agent roster

Named roles, not anonymous workers. Each has a persistent identity and history.

| Agent | Role | Assigned when |
|---|---|---|
| `frontend` | UI components, styles, client-side logic | Task touches frontend files |
| `backend` | APIs, models, business logic, migrations | Task touches server-side code |
| `testing` | Write/fix tests | Task is explicitly about test coverage |
| `devops` | CI/CD, Docker, infra configs | Task touches deployment/config files |
| `reviewer` | Post-execution review, code quality | Runs after every agent execution |

### Assignment

- Orchestrator tags each task with an agent role in its plan output
- If not specified, runner infers from files being touched
- Roster is configurable in `config.toml` — users can add/remove/rename agents
- Each agent's history gets injected into its prompt, so an agent "remembers" prior work on related files

---

## 7. Agent adapter & prompt assembly

### Single adapter

```python
class AgentAdapter:
    def execute(self, prompt: str, workdir: str, timeout: int) -> AgentResult:
        result = subprocess.run(
            ["claude", "--print", "-p", prompt],
            cwd=workdir,
            capture_output=True,
            timeout=timeout,
        )
        return AgentResult(
            output=result.stdout,
            exit_code=result.returncode,
            duration=...,
        )
```

Used for orchestrator, all worker agents, and the reviewer agent. Same interface, different prompts.

### Orchestrator prompt receives

- The board's intent
- CLAUDE.md contents (if exists)
- File tree of the target repo
- Recent git history
- Instructions to output a structured task graph (JSON block within markdown)

### Worker prompt — 6-section builder

1. **Identity** — you are a Conveyor [role] agent, do exactly what's asked, stay in scope
2. **Task** — issue ID, title, acceptance criteria, files to create/modify
3. **Codebase context** — relevant file tree, pattern reference files (siblings)
4. **Prior work** — output of upstream dependency tasks (files/interfaces they created)
5. **Constraints** — files you must NOT touch (other agents' scope)
6. **Reporting** — output a `CONVEYOR_REPORT` block

### Reviewer prompt receives

- The task assignment (acceptance criteria, allowed files)
- The branch diff
- Test output (from direct subprocess)
- Instructions to check: scope violations, missing files, report format, code quality
- Output a structured `REVIEW_RESULT` block

### Context budget

Target ~40% of context window for the assembled prompt, leaving 60% for the agent to think and work.

File selection priority:
1. Files the task will modify (current state)
2. 1-2 sibling files for pattern matching
3. Config/settings if relevant
4. Test patterns if tests are expected
5. Cap based on available window

---

## 8. Validation

Tests are run as a direct subprocess, not by the reviewer agent. The reviewer reads the results.

### Flow

```
agent executes → tests run (subprocess) → reviewer agent runs → pass? → governance → merge
                                                                   │
                                                                   no → failed
```

### Test runner

- Conveyor detects or reads test command from `config.toml` (e.g., `pytest`, `npm test`)
- Runs it as a subprocess against the branch
- Captures stdout/stderr and exit code
- Passes results to the reviewer agent as part of its prompt

### On failure

- Issue status → `failed`
- Branch left as-is (user can inspect)
- `conveyor status` shows failure details
- User decides: fix manually, re-run, or move on

---

## 9. Merge strategy

Sequential, dependency-ordered.

1. Task graph gives topological order — no-dependency tasks first
2. After reviewer approves, governance gate applies:
   - **Low risk** → auto-merge to main
   - **Medium risk** → user approves via `conveyor review`
   - **High risk** → user approved plan upfront, now approves merge too
3. Each merge: `git checkout main && git merge <branch>`
4. Merge conflict → `failed`. No auto-resolution. Bad decomposition should surface, not be hidden.
5. After merge, downstream tasks proceed — their prompts include merged work as "prior work"

### Branch naming

`conveyor/iss-001-short-description`

### Cleanup

Branches left after intent completes. Manual cleanup or future `conveyor cleanup` command.

---

## 10. CLI commands

```bash
conveyor init                     # Scan repo, create .conveyor/, detect stack
conveyor intent "..."             # Orchestrator decomposes, shows plan, user approves
conveyor status                   # Current intent progress, issue states
conveyor issues                   # List all issues with status
conveyor issues ISS-001           # Detail for specific issue
conveyor review                   # Review pending medium/high risk merges
conveyor log                      # Full activity trail
conveyor log --issue ISS-001      # Logs for specific issue
```

### `conveyor init` does

- Creates `.conveyor/` directory structure
- Adds `.conveyor/` to `.gitignore`
- Generates `config.toml` with defaults
- Creates default agent files (frontend, backend, testing, devops, reviewer)
- Detects stack from config files (package.json, pyproject.toml, etc.)
- Reads CLAUDE.md if present

### `conveyor intent` flow

1. Orchestrator call (Claude Code) — reads codebase, decomposes intent
2. Parse output into issues with task graph
3. Display plan table (tasks, deps, risk, agent assignments)
4. User: `[a]pprove [e]dit [r]eject`
5. On approve → write intent + issue files → start runner state machine

---

## 11. Configuration

```toml
[conveyor]
version = "0.1.0"

[execution]
timeout_seconds = 300
sequential = true

[governance]
auto_merge_low_risk = true
review_medium_risk = true
review_high_risk = true

[agents]
roster = ["frontend", "backend", "testing", "devops", "reviewer"]

[testing]
command = ""    # Auto-detected or user-specified
```

---

## 12. Parked for v2

- **Reopen flow** — board comments on issues, orchestrator re-evaluates, state machine restarts
- **Reviewer auto-run toggle** — reviewer triggered explicitly instead of after every execution
- **Tree-sitter indexing** — AST parsing for import graphs, symbol extraction, conflict detection
- **SQLite data layer** — when markdown file globbing gets slow
- **Web UI** — FastAPI read-only dashboard (`conveyor web`)
- **Parallel execution** — git worktrees, concurrent agents
- **Retry loops** — automatic retry with feedback prompts on failure
- **Auto-conflict-resolution** — merger agent attempts to resolve git conflicts
- **Token budgets / cost tracking**
- **Custom agent roles**
- **`conveyor cleanup`** — branch cleanup command
