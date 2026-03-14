# Conveyor — Build plan

> AI-native project orchestration for engineering teams that ship fast.
> Agents are first-class. Humans are the board.

---

## 1. What is Conveyor?

Conveyor is a CLI-first orchestrator that sits on top of coding agents (Claude Code, Cursor, Codex, etc.) and coordinates them to execute multi-step engineering tasks on real repositories. It borrows the organizational metaphor from Paperclip (board → CEO → workers, tickets, governance) but rethinks everything for software engineering specifically.

### Core loop

```
Board gives intent → CEO reads codebase + decomposes into task graph
→ agents execute on branches → validation → merge → done
```

### What makes it different from Paperclip

| Aspect | Paperclip | Conveyor |
|---|---|---|
| Domain | Any business | Software engineering teams |
| Context | Ticket descriptions | Codebase graph, git history, CLAUDE.md, live system state |
| Decomposition | Flat task list | Dependency-aware task graph with conflict analysis |
| Execution | Agent heartbeats | Branch-per-task, Claude Code subprocess |
| Coordination | Org chart delegation | File-level conflict detection, ordered merges |
| Governance | Board approves hires/strategy | Risk-based: auto-merge low risk, board reviews medium/high |

### Inspirations

- [Boris Tane — "The SDLC Is Dead"](https://boristane.com/blog/the-software-development-lifecycle-is-dead): the SDLC collapsed into intent → agent → observe → repeat. The bottleneck is context, not process.
- [Paperclip](https://paperclip.ing/): open-source orchestration for agent-run companies. Board/CEO/worker hierarchy, ticket system, governance, cost control.
- [Nominal](https://nominal.dev/): AI agents for observability — the feedback loop that closes the cycle.

---

## 2. Architecture overview

```
┌──────────────────────────────────────────────────────────┐
│  Board interface layer                                    │
│  CLI (primary) · Web dashboard (read-only) · API          │
└──────────────────────┬───────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│  Orchestrator core                                        │
│                                                           │
│  ┌──────────────┐ ┌───────────────┐ ┌──────────────┐    │
│  │ CEO agent    │ │ Governance    │ │ Cost control  │    │
│  │ Decomposes   │ │ Risk gates    │ │ Token budgets │    │
│  │ intent       │ │ Approval flow │ │              │    │
│  └──────────────┘ └───────────────┘ └──────────────┘    │
│                                                           │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Context engine (the key differentiator)             │  │
│  │ Codebase index · CLAUDE.md · Agent memory · Git     │  │
│  └────────────────────────────────────────────────────┘  │
│                                                           │
│  ┌─────────────────────┐ ┌────────────────────────────┐  │
│  │ Branch coordination │ │ Issue system               │  │
│  │ Conflict detection  │ │ Agent-native, not Jira     │  │
│  │ Merge queue         │ │ Markdown + SQLite           │  │
│  └─────────────────────┘ └────────────────────────────┘  │
└──────────────────────┬───────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│  Execution layer — agent adapters                         │
│  Claude Code (POC) · Cursor · Codex · Custom/HTTP         │
└──────────────────────┬───────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│  Validation layer                                         │
│  File checks · Test runner · Scope enforcement · Retry    │
└──────────────────────┬───────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│  Feedback loop — observability                            │
│  CI/CD results · Test output · Failures feed back as      │
│  context for the agent that shipped it                    │
└──────────────────────────────────────────────────────────┘
```

---

## 3. CLI design

### Commands

```bash
conveyor init              # Index repo, detect stack, setup .conveyor/
conveyor intent "..."      # Give a goal, CEO decomposes + board reviews
conveyor status            # Show current intent progress, agent states
conveyor issues            # List all issues with status
conveyor issues ISS-001    # Show detail for a specific issue
conveyor review            # Review pending medium/high risk merges
conveyor log               # Full audit trail
conveyor log --issue ISS-001   # Logs for specific issue
conveyor log --session SES-001 # Full agent session transcript
conveyor web               # Launch local read-only web dashboard
conveyor reindex           # Force re-index of the codebase
```

### Example session

```bash
$ cd my-project
$ conveyor init
✓ Indexed 2,680 files, 186k LOC
✓ Detected: Python 3.12 · FastAPI · TypeScript · React · PostgreSQL
✓ CLAUDE.md found — using as project profile
✓ Created .conveyor/ directory

$ conveyor intent "Add user authentication with JWT tokens and a /login endpoint"

🤔 CEO analyzing codebase...

📋 Plan: 3 tasks, 2 parallelizable

  Task 1: Add User model + migration
  ├── Branch: conveyor/iss-001-user-model
  ├── Files: src/models/user.py (create), alembic/versions/... (create)
  ├── Risk: low (additive, no existing files modified)
  └── Depends on: nothing

  Task 2: Create JWT auth utilities
  ├── Branch: conveyor/iss-002-jwt-utils
  ├── Files: src/auth/jwt.py (create), src/auth/__init__.py (create)
  ├── Risk: low (new module)
  └── Depends on: nothing (parallel with Task 1)

  Task 3: Wire /login and /register endpoints
  ├── Branch: conveyor/iss-003-auth-endpoints
  ├── Files: src/api/routes.py (modify), src/api/auth.py (create)
  ├── Risk: medium (modifies existing routes.py)
  └── Depends on: Task 1, Task 2

  [a]pprove  [e]dit  [r]eject  [?] explain reasoning

$ a

⚡ Executing...
   [Task 1] Running on conveyor/iss-001-user-model...
   [Task 2] Running on conveyor/iss-002-jwt-utils...
   [Task 1] ✓ Validation passed (47s)
   [Task 1] ✓ Auto-merged (low risk)
   [Task 2] ✓ Validation passed (32s)
   [Task 2] ✓ Auto-merged (low risk)
   [Task 3] Dependencies met, starting...
   [Task 3] Running on conveyor/iss-003-auth-endpoints...
   [Task 3] ✓ Validation passed (58s)
   [Task 3] ⏸ Awaiting board review (medium risk)

$ conveyor review

  ISS-003: Wire /login and /register endpoints
  Branch: conveyor/iss-003-auth-endpoints
  Files modified: src/api/routes.py (+12 lines), src/api/auth.py (created, 34 lines)
  Tests: 4 added, all passing

  [a]pprove merge  [d]iff  [r]eject  [?] show session log

$ a

   [Task 3] ✓ Merged to main

✅ Intent complete. 5 files created, 1 modified.
```

---

## 4. Indexing

### Two-layer approach

**Layer 1 — Static analysis (free, instant, any language)**

Runs on `conveyor init` and incrementally on each intent.

- File tree with sizes, types, content hashes
- Git metadata: recent commits, hotspots (most-changed files), contributors
- Stack detection from config files (package.json, pyproject.toml, Cargo.toml, etc.)
- Import graph + symbol extraction via tree-sitter (Python, TypeScript, JavaScript, Go, Rust, Java, Ruby)
- Fallback: regex-based import detection for unsupported languages
- Config file detection: CI, lint, test, deploy configurations

**Layer 2 — LLM-assisted analysis (runs once on init, cheap)**

- Directory-level summaries for top-level modules (not per-file on large repos)
- Pattern detection: conventions, idioms, architectural patterns
- Module map: what each directory is responsible for
- On-demand per-file summaries when the CEO drills into a specific area

### Scaling strategy

| Repo size | Init behavior |
|---|---|
| < 100 files | Full per-file Layer 2 analysis |
| 100–1,000 files | Layer 2 on key files only (entry points, configs, most-imported) |
| 1,000–10,000 files | Directory-level Layer 2 only, per-file on demand |
| 10,000+ files | Directory-level Layer 2 for top 2 levels, everything else on demand |

### Storage

- `index.json` — file tree, hashes, cached symbols, import edges
- `conveyor.db` (files table) — queryable file metadata with summaries
- Content hashes enable incremental updates: only re-analyze changed files

### Project profile

Conveyor does NOT create its own profile file. It reads:

1. `CLAUDE.md` at repo root (primary — human-authored conventions)
2. `.claude/settings.json` (Claude Code settings)
3. Auto-generated index data augments these with structural analysis

If no `CLAUDE.md` exists, `conveyor init` can optionally generate one as a starting point.

---

## 5. The CEO agent

### How it differs from Paperclip's CEO

Paperclip's CEO is a business strategist. Conveyor's CEO is a **tech lead + architect + PM hybrid**. It must understand code architecture to decompose tasks correctly.

### Decision flow

```
Board intent arrives
       │
       ▼
Phase 1 — Understand before decomposing
  • Read CLAUDE.md + index data
  • Identify relevant modules and files
  • Check CI/deploy/system state
  • Review past intent and issue history
       │
       ▼
Phase 2 — Dependency-aware decomposition
  • Build task graph with explicit dependencies
  • Analyze file-level overlap between tasks
  • Decide what can run in parallel vs sequential
  • Assess risk per task
       │
       ▼
Phase 3 — Risk assessment
  • Low risk: new files, additive changes → auto-merge after validation
  • Medium risk: modifying existing files → board reviews before merge
  • High risk: architectural changes, auth, data model → board reviews plan AND merge
       │
       ▼
Phase 4 — Dispatch + monitor
  • Create branches, assign agents
  • Watch task graph execution
  • Trigger downstream tasks when dependencies complete
  • Re-plan if an agent's work changes the approach
```

### CEO prompt structure

The CEO is called via the Anthropic API (not Claude Code) since it doesn't write files — it thinks and produces structured plans.

The CEO receives:
- CLAUDE.md (full contents)
- Auto-generated index data (relevant modules, import graph, symbols)
- Relevant file contents (for areas the intent will touch)
- Git hotspots for affected areas
- Previous intent/issue history from `.conveyor/`
- The board's intent

The CEO outputs:
- Analysis of what needs to change and why
- A task graph (tasks + dependencies + parallel groups)
- Per-task: files to create/modify, acceptance criteria, risk level, constraints
- Notes for the board explaining reasoning

---

## 6. Agent prompting (worker agents)

### Prompt assembly pipeline

Each worker agent (Claude Code) receives a carefully assembled prompt with 6 sections:

```
┌─────────────────────────────────────────────┐
│ 1. Identity                                  │
│    You are a Conveyor worker agent.          │
│    Do exactly what is asked, no more.        │
│    Don't modify files outside your scope.    │
├─────────────────────────────────────────────┤
│ 2. Task                                      │
│    Issue ID, title, acceptance criteria,     │
│    files to create/modify, parent intent.    │
├─────────────────────────────────────────────┤
│ 3. Codebase context                          │
│    Relevant file tree, sample files showing  │
│    patterns to follow (the "pattern refs").  │
├─────────────────────────────────────────────┤
│ 4. Prior work                                │
│    Output of upstream dependency tasks —     │
│    the files and interfaces they created.    │
├─────────────────────────────────────────────┤
│ 5. Constraints                               │
│    DO NOT touch these files (other agents'   │
│    scope). Use these patterns. Avoid these.  │
├─────────────────────────────────────────────┤
│ 6. Reporting                                 │
│    Output a structured CONVEYOR_REPORT with  │
│    files changed, lines added, test results. │
└─────────────────────────────────────────────┘
```

### Context budget

Target: ~40% of context window for the assembled prompt, leaving 60% for the agent to think and work.

Selection logic for "pattern reference" files:
1. Always include files the task will modify (agent needs current state)
2. Include 1–2 "sibling" files (e.g., if creating user.py, show post.py)
3. Include config/settings if the task touches configuration
4. Include relevant test patterns if tests are expected
5. Cap total included file content based on available window

### Structured output

Agents must end with a parseable report:

```
CONVEYOR_REPORT_START
files_created: src/auth/jwt.py, tests/test_jwt.py
files_modified: src/config.py
lines_added: 87
tests_added: 4
tests_passing: true
notes: Added JWT_SECRET and JWT_EXPIRY_HOURS to Settings class
CONVEYOR_REPORT_END
```

This gets parsed by the runner and written to the issue file automatically.

---

## 7. Validation and failure handling

### Post-execution validation

After every agent completes, before merge:

```python
def validate(issue, branch):
    1. File existence — did agent create expected files?
    2. Scope check — did agent touch only allowed files?
    3. Test runner — do tests pass on this branch?
    4. Report parsing — did agent produce valid report?
```

### Failure taxonomy

**Hard failures — agent can't complete**

| Failure | Detection | Recovery |
|---|---|---|
| Process crash | Subprocess exit code ≠ 0, timeout | Retry once with same prompt. If fails again, pause + escalate to board. |
| Budget exceeded | Token/time limit hit | Pause issue, notify board with what was accomplished. |
| Git failure | Branch/merge error | Log error, retry branch creation. If persistent, escalate. |

**Soft failures — agent finished but output is wrong**

| Failure | Detection | Recovery |
|---|---|---|
| Tests fail | pytest exit code ≠ 0 | Retry with feedback prompt including test output. |
| Missing files | Expected files not on branch | Retry with feedback prompt listing what's missing. |
| Bad report | CONVEYOR_REPORT block missing/malformed | Retry with reminder about report format. |

Retry prompt includes:
- What went wrong (test output, missing files, etc.)
- The agent's previous changes (so it knows what it already did)
- Specific instructions to fix the issue

**Boundary violations — agent went off-script**

| Violation | Detection | Recovery |
|---|---|---|
| Scope creep (touched extra files) | git diff vs allowed files | If small: revert extra files, re-validate. If large: reset branch, re-prompt with stricter constraints. |
| Constraint breach (modified forbidden files) | git diff vs forbidden list | Reset branch, re-prompt. |
| Rogue behavior (unexpected actions) | Diff analysis, anomaly detection | Reset branch, escalate to board. |

**Cascade failures — one failure affects downstream tasks**

| Scenario | Detection | Recovery |
|---|---|---|
| Upstream incomplete | Task dependency not met | Pause all downstream tasks, notify board. Board chooses: retry / skip / replan / abort. |
| Upstream was wrong | Board catches bad output post-merge | New corrective intent. CEO reads previous issue files to understand what was built and what needs fixing. |

### Retry loop

```
Agent executes → Validate → Pass? → Merge
                              │
                              No
                              │
                         Retries left? (max 2)
                         ├── Yes → Retry with feedback prompt
                         └── No  → Pause + escalate to board
                                   Board: retry / skip / replan / abort
```

### Issue lifecycle statuses

```
created → queued → running → validating → complete
                                 │
                                 ├── [retry with feedback] → running
                                 ├── failed (after max retries)
                                 ├── blocked (upstream failed)
                                 ├── paused (board intervention needed)
                                 └── skipped (board decided to skip)
```

---

## 8. Tracking and observability

### .conveyor/ directory

```
.conveyor/
├── conveyor.db          # SQLite — single source of truth
├── index.json           # File tree + hashes + cached analysis
├── config.toml          # Settings (retry limits, auto-merge rules, etc.)
├── intents/
│   ├── INT-001-add-jwt-auth.md
│   └── INT-002-fix-perf.md
├── issues/
│   ├── ISS-001-user-model.md
│   ├── ISS-002-jwt-utils.md
│   └── ISS-003-auth-endpoints.md
├── agents/
│   ├── ceo.md           # CEO context + decision history
│   └── worker-01.md     # Per-agent history
└── sessions/
    ├── SES-001-ISS-001.md   # Full Claude Code transcript
    └── SES-002-ISS-002.md
```

Gitignored by default. User can choose to commit for audit trail.

### Issue file format

YAML frontmatter (machine-parseable) + markdown body (human-readable):

```markdown
---
id: ISS-001
intent: INT-001
title: Add User model and database migration
status: complete
assignee: worker-01
branch: conveyor/iss-001-user-model
depends_on: []
risk: low
created: 2026-03-14T10:32:00Z
completed: 2026-03-14T10:32:52Z
duration_seconds: 47
---

# Add User model and database migration

## Context from CEO
[What the CEO told the agent to do and why]

## Acceptance criteria
- [x] User model in src/models/user.py
- [x] Alembic migration generated
- [x] Model registered in __init__.py

## Files planned → Files actually changed
[Diff between plan and reality]

## Activity log
[Timestamped record of every event]
```

### Intent file format

Similar structure: board's original request, CEO's analysis, the plan table, approval status, and rollup of all spawned issues with outcome.

### Agent files

Each agent accumulates context over time:
- What issues they've worked on
- What patterns they've learned
- What files they're familiar with
- Error history (what went wrong and how it was fixed)

This feeds into future prompt assembly — an agent that has worked on the billing module before gets assigned billing-related tasks, and their context already includes familiarity with those files.

### Local web UI

Read-only FastAPI dashboard that queries conveyor.db:
- Table of intents with status and timing
- Drill into issues: dependency graph, file changes, activity log
- Session viewer: full agent transcripts
- Simple, minimal, no auth needed (it's localhost)

Launched with: `conveyor web` → opens browser to `http://localhost:8787`

---

## 9. Execution model

### POC: sequential execution

For the POC, agents run sequentially. Tasks within the same parallel group run one after another. This is simpler and avoids the complexity of git worktrees.

```
Parallel group 1: ISS-001 then ISS-002 (sequential, same branch base)
Parallel group 2: ISS-003 (after group 1 completes)
```

### Future: parallel execution with git worktrees

Each agent gets its own worktree (separate working directory, same repo). True parallelism. Adds complexity around disk space and merge ordering.

### Agent adapter interface

```python
class AgentAdapter:
    """Interface for any coding agent backend."""
    
    def execute(self, prompt: str, workdir: str, timeout: int) -> AgentResult:
        """Run the agent with the given prompt in the given directory."""
        ...

class ClaudeCodeAdapter(AgentAdapter):
    """Calls Claude Code CLI via subprocess."""
    
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

### Merge strategy

Tasks merge in dependency order (topological sort):
1. Tasks with no dependencies merge first
2. Each merge happens on top of the updated main
3. If merge conflicts occur, the merger agent attempts auto-resolution
4. If auto-resolution fails, escalate to board

---

## 10. Configuration

### config.toml

```toml
[conveyor]
version = "0.1.0"

[execution]
agent = "claude-code"         # Default agent adapter
timeout_seconds = 300         # Per-task timeout
max_retries = 2               # Retry limit before escalating
sequential = true             # POC: sequential execution

[governance]
auto_merge_low_risk = true    # Low risk tasks merge without board review
review_medium_risk = true     # Medium risk requires board approval
review_high_risk = true       # High risk requires plan AND merge approval

[indexing]
use_tree_sitter = true        # Rich parsing for supported languages
llm_summaries = true          # LLM-assisted directory/file summaries
reindex_on_intent = true      # Refresh index before each intent

[tracking]
markdown_files = true         # Generate .conveyor/ markdown files
gitignore = true              # .conveyor/ gitignored by default

[ceo]
model = "claude-sonnet-4-20250514"   # Model for CEO analysis
max_tasks_per_intent = 10            # Safety limit
```

---

## 11. Project structure

```
conveyor/
├── conveyor/
│   ├── __init__.py
│   ├── cli.py                    # Typer CLI entry point
│   ├── core/
│   │   ├── ceo.py                # CEO agent — analysis + decomposition
│   │   ├── context.py            # Context engine — index queries, file selection
│   │   ├── planner.py            # Task graph builder + dependency resolver
│   │   └── governance.py         # Risk assessment, approval flow
│   ├── indexing/
│   │   ├── static.py             # Layer 1 — file tree, git, config detection
│   │   ├── treesitter.py         # Tree-sitter import graph + symbols
│   │   ├── llm.py                # Layer 2 — LLM summaries, pattern detection
│   │   └── profile.py            # CLAUDE.md reader + index augmentation
│   ├── execution/
│   │   ├── branch.py             # Git branch management
│   │   ├── claude_code.py        # Claude Code CLI adapter
│   │   ├── merger.py             # Ordered merge + conflict handling
│   │   ├── runner.py             # Task runner, sequential/parallel dispatch
│   │   └── prompt.py             # Prompt assembler (6-section builder)
│   ├── validation/
│   │   ├── runner.py             # Post-execution validation orchestrator
│   │   ├── checks.py             # Individual checks (files, tests, scope)
│   │   ├── feedback.py           # Build retry prompts from failures
│   │   └── recovery.py           # Revert, retry, escalate logic
│   ├── tracking/
│   │   ├── store.py              # SQLite read/write
│   │   ├── models.py             # Intent, Issue, Session, Agent data models
│   │   ├── markdown.py           # Generate .conveyor/ markdown files
│   │   └── events.py             # Activity log event system
│   ├── web/
│   │   ├── app.py                # FastAPI read-only dashboard
│   │   ├── templates/            # Jinja2 templates
│   │   └── static/
│   └── config.py                 # .conveyor/ config management
├── pyproject.toml
├── README.md
└── tests/
```

---

## 12. Build phases

### Phase 1 — Skeleton + init (days 1–2)

- CLI entry point with Typer
- `conveyor init`: file tree scan, git analysis, stack detection, config.toml generation
- CLAUDE.md reader
- SQLite store with schema for intents, issues, sessions
- `.conveyor/` directory management

**Milestone: `conveyor init` works on a real repo and produces useful output.**

### Phase 2 — CEO + planning (days 3–4)

- CEO agent via Anthropic API
- Context engine: gather relevant files from index for a given intent
- Planner: parse CEO output into task graph with dependencies
- Risk assessment based on files affected
- `conveyor intent` command: intent → CEO analysis → plan display → approval prompt

**Milestone: `conveyor intent "..."` produces a sensible plan with tasks, deps, and risk levels on a real repo.**

### Phase 3 — Execution (days 5–7)

- Claude Code adapter (subprocess wrapper)
- Prompt assembler (6-section builder)
- Branch management (create, checkout)
- Sequential task runner
- Report parser (CONVEYOR_REPORT extraction)
- Issue + session markdown file generation

**Milestone: full loop works — intent → plan → approve → agents write code on branches → report back.**

### Phase 4 — Validation + merge (days 8–9)

- Post-execution validation (files, tests, scope)
- Retry with feedback prompts
- Scope violation detection + recovery
- Ordered merge (topological sort of dependency graph)
- Auto-merge low risk, pause medium/high for review
- `conveyor review` command

**Milestone: agents produce code, it gets validated, and clean code merges to main. Failures retry or escalate.**

### Phase 5 — Polish + web UI (days 10–12)

- `conveyor status`, `conveyor issues`, `conveyor log` commands
- Local web dashboard (read-only)
- Incremental re-indexing after intents complete
- Agent memory/context files
- Tree-sitter integration for Python + TypeScript
- Error handling, edge cases, UX polish

**Milestone: complete, usable POC that works on real repos with real code changes.**

---

## 13. Open questions and risks

### Design questions to revisit

1. **CEO coding capability**: Should the CEO be able to write code (prototype/spike before decomposing) or stay as a pure coordinator? Currently designed as pure coordinator.

2. **CEO architectural stance**: How opinionated should the CEO be about architecture? Currently unspecified — needs a decision between enforcing patterns from CLAUDE.md, advising, or being hands-off.

3. **Parallel execution timing**: When to move from sequential to worktree-based parallel execution? Deferred for POC but the architecture should make the transition clean.

4. **Agent identity**: Should there be distinct worker agents with persistent identity and memory, or are they stateless executors that just receive a prompt? Currently designed with persistent agent files, but the value of this is unproven.

5. **Incremental intents**: What happens when the board gives a second intent while the first is still running? Queue it? Let the CEO interleave? Reject until current intent completes?

6. **Multi-repo**: This design assumes a single repo. How would it work for monorepos or multi-repo projects?

### Technical risks

1. **CEO decomposition quality**: The entire system depends on the CEO producing good task graphs. If decomposition is bad (wrong dependencies, missed conflicts, over/under-decomposition), everything downstream suffers. Mitigation: the board reviews the plan before execution.

2. **Prompt context overflow**: Large repos with complex tasks may exceed the context window when assembling the worker prompt. Mitigation: aggressive context budgeting, summarization instead of full file contents.

3. **Claude Code reliability**: Subprocess-based orchestration of Claude Code is brittle — processes can hang, produce unexpected output, or interact with the filesystem in unintended ways. Mitigation: timeouts, validation, scope enforcement.

4. **Merge conflicts**: Even with conflict analysis, agents working on related code may produce subtle incompatibilities that aren't merge conflicts in the git sense but are logical conflicts. Mitigation: test runner catches some of these, but not all.

5. **Cost**: Each intent requires multiple LLM calls (CEO analysis + N worker agents + potential retries). For complex intents on large repos, costs could add up. Mitigation: token budgets per task, cost tracking, efficient context selection.

---

## 14. Tech stack (POC)

| Component | Choice | Rationale |
|---|---|---|
| Language | Python 3.11+ | Fast to prototype, good subprocess handling |
| CLI framework | Typer | Clean, modern, good UX out of the box |
| Database | SQLite | Zero setup, single file, good enough for local tool |
| CEO agent | Anthropic API (Claude Sonnet) | Direct API call, structured output, cheaper than Opus for planning |
| Worker agent | Claude Code CLI | `claude --print -p "..."`, subprocess |
| Indexing | tree-sitter (via py-tree-sitter) | Multi-language parsing, single API |
| Web UI | FastAPI + Jinja2 | Lightweight, same language as CLI |
| Testing | pytest | Standard Python testing |
| Packaging | pyproject.toml + pip | Standard Python packaging |

---

## 15. Success criteria for the POC

The POC is successful if:

1. `conveyor init` correctly analyzes a real 100+ file repo and produces useful index data
2. `conveyor intent` with a non-trivial feature request (e.g., "add authentication") produces a sensible multi-task plan
3. Worker agents execute on branches and produce working code that follows the repo's existing patterns
4. Validation catches failures and retry prompts fix them
5. Merge produces a clean main branch with all changes integrated
6. The whole flow is traceable — every decision, every agent action, every file change is logged in `.conveyor/`
7. A developer can review the `.conveyor/issues/` directory and understand exactly what happened and why