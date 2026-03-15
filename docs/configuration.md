# Configuration

Conveyor is configured via `.conveyor/config.toml`, created when you run `conveyor init`.

## Full Reference

```toml
[conveyor]
version = "0.1.0"

[execution]
timeout_seconds = 300       # Max seconds per agent execution
sequential = true           # Run tasks one at a time (parallel not yet supported)

[governance]
auto_merge_low_risk = true  # Auto-merge when risk=low and reviewer passes
review_medium_risk = true   # Pause for user approval on risk=medium
review_high_risk = true     # Pause for user approval on risk=high

[agents]
roster = ["frontend", "backend", "testing", "devops", "reviewer"]

[testing]
command = ""                # Test command to run after each agent (e.g. "pytest", "npm test")

[claude]
permission_mode = "bypassPermissions"  # Claude Code permission mode for subprocess agents
```

## Settings Explained

### `[execution]`

**`timeout_seconds`** (default: 300)

How long each agent gets to complete its work. If an agent takes longer than this, it's killed and the task is marked as failed. Increase this for complex tasks.

**`sequential`** (default: true)

Tasks are executed one at a time in dependency order. Parallel execution is planned but not yet implemented.

### `[governance]`

Controls when Conveyor pauses for your approval vs. auto-merging.

| Risk Level | `auto_merge_low_risk=true` | `review_medium_risk=true` | `review_high_risk=true` |
|------------|---------------------------|---------------------------|--------------------------|
| **low** | Auto-merge | Auto-merge | Auto-merge |
| **medium** | Auto-merge | Pause for approval | Pause for approval |
| **high** | Auto-merge | Pause for approval | Pause for approval (twice: plan + merge) |

Risk levels are assigned by the orchestrator:
- **low** — new files only, no existing code modified
- **medium** — modifies existing files
- **high** — architectural changes, touches core infrastructure

To auto-merge everything (use with caution):
```toml
[governance]
auto_merge_low_risk = true
review_medium_risk = false
review_high_risk = false
```

### `[testing]`

**`command`** (default: "")

The command Conveyor runs after each agent to verify the codebase still works. Examples:

```toml
# Python
command = "pytest"

# Node.js
command = "npm test"

# Go
command = "go test ./..."

# Skip tests (default)
command = ""
```

When empty, the test step is skipped and the reviewer relies solely on the diff.

### `[claude]`

**`permission_mode`** (default: "bypassPermissions")

Controls what the Claude Code subprocess agents are allowed to do. Options:

| Mode | What agents can do |
|------|-------------------|
| `bypassPermissions` | Everything — read, write, execute commands (default) |
| `acceptEdits` | Read and edit files, but cannot run bash commands |
| `default` | Standard Claude Code permissions — will prompt (but can't in subprocess) |

`bypassPermissions` is the default because agents need to create files, run git commands, and sometimes execute build tools. If you want tighter control, use `acceptEdits` — but agents won't be able to run tests or git commit.

### `[agents]`

**`roster`** (default: ["frontend", "backend", "testing", "devops", "reviewer"])

The list of agent roles available. Each agent gets a markdown file in `.conveyor/agents/` with stack-specific instructions created at init time.

You can remove agents you don't need:
```toml
# Backend-only project
roster = ["backend", "testing", "reviewer"]
```

## Agent Configuration

Agent prompts are stored in `.conveyor/agents/<name>.md`. They're generated at init time based on your detected stack. You can edit them directly to customize agent behavior.

Example — adding a project-specific rule to the backend agent:

```markdown
---
name: backend
role: "You are a Node.js/TypeScript backend specialist.\n\n**Core Responsibilities:**\n..."
---
```

Edit the `role` field to add your own instructions. Changes take effect on the next `conveyor intent`.
