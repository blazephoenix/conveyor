# How Conveyor Works

This document explains the end-to-end flow of Conveyor — from typing an intent to seeing merged code.

## Overview

Conveyor is an event-driven state machine. When you run `conveyor intent "..."`, four things happen in sequence:

1. **Orchestration** — An AI agent analyzes your codebase and decomposes the intent into a task graph
2. **Execution** — Each task is executed by a specialized agent on its own branch
3. **Validation** — A reviewer agent checks each task's output against acceptance criteria
4. **Governance** — Approved work is merged (or paused for your review based on risk)

## Step 1: Initialization (`conveyor init`)

Before using Conveyor, you initialize it in your repo:

```bash
conveyor init
```

This does:

- **Scans the file tree** to understand project structure
- **Detects your stack** — looks for `package.json` (Node.js), `pyproject.toml` (Python), `Cargo.toml` (Rust), etc.
- **Creates `.conveyor/`** directory with:
  - `config.toml` — execution settings, governance rules, test commands
  - `agents/` — agent definition files with stack-specific prompts
  - `intents/`, `issues/`, `sessions/` — empty, populated during execution
- **Reads `CLAUDE.md`** — if present, uses it as project conventions context

### Stack-Aware Agents

Agents are created with prompts tailored to your stack. A Node.js project gets agents that know about TypeScript, async/await, and Next.js conventions. A Python project gets agents that know about pytest, type hints, and PEP 8.

## Step 2: Orchestration (`conveyor intent "..."`)

When you run an intent, the orchestrator:

1. **Gathers context**: file tree, recent git history, CLAUDE.md
2. **Builds an orchestrator prompt**: includes your intent, the codebase context, and instructions for producing a task graph
3. **Calls Claude Code** via subprocess (`claude --print -p <prompt>`)
4. **Parses the response**: extracts a JSON task graph from between `CONVEYOR_PLAN_START` and `CONVEYOR_PLAN_END` markers

Each task in the graph has:
- **title** — what to do
- **agent** — who does it (frontend, backend, testing, devops)
- **files_allowed** — what files the agent can touch
- **files_forbidden** — what files the agent must not touch
- **depends_on** — which tasks must complete first
- **risk** — low, medium, or high
- **acceptance_criteria** — how to verify the work

The tasks are topologically sorted (Kahn's algorithm) so dependencies are respected.

## Step 3: Execution (Runner State Machine)

The runner processes each issue through these states:

```
CREATED -> QUEUED -> RUNNING -> VALIDATING -> COMPLETE
                                           -> FAILED
                                           -> BLOCKED (upstream failed)
                                           -> PAUSED (needs approval)
```

For each task in dependency order:

### 3a. Branch Creation
```
git checkout main
git checkout -b conveyor/iss-001-add-user-model
```

### 3b. Agent Dispatch
The runner builds a 6-section prompt:

1. **Identity** — the agent's role, stack-specific instructions, boundaries
2. **Task** — issue ID, title, acceptance criteria, allowed files
3. **Codebase context** — relevant file contents
4. **Prior work** — output from completed upstream tasks
5. **Constraints** — forbidden files
6. **Commit and Report** — instructions to commit and output a structured report

The prompt is sent to Claude Code via subprocess. The agent writes code, runs commands, and commits to the branch.

### 3c. Validation
After the agent completes:

1. **Run tests** — if a test command is configured
2. **Check scope** — verify the agent only touched allowed files
3. **Dispatch reviewer** — a reviewer agent checks the diff against acceptance criteria

### 3d. Governance Gate
Based on risk level and reviewer verdict:

- **Low risk + passed** -> auto-merge to main
- **Medium risk + passed** -> pause, ask user to approve
- **High risk** -> pause before execution AND before merge
- **Failed** -> mark as failed, block downstream tasks

## Step 4: Completion

After all tasks are processed, the runner:
- Checks out back to main
- Reports a summary (completed, failed, blocked counts)
- Updates intent status (complete/partial)

## Data Flow

```
User Intent (string)
    |
    v
Orchestrator Prompt (file tree + git log + CLAUDE.md + intent)
    |
    v
Claude Code subprocess -> orchestrator output (analysis + JSON task graph)
    |
    v
Task Graph (parsed, topologically sorted)
    |
    v
For each task:
    |-- Worker Prompt (identity + task + context + constraints + report format)
    |       |
    |       v
    |   Claude Code subprocess -> agent creates files, commits
    |       |
    |       v
    |   Validation (tests + scope check + reviewer agent)
    |       |
    |       v
    '-- Governance (auto-merge / pause / fail)
```

## File Format

All state is stored as markdown with YAML frontmatter. Example issue:

```markdown
---
id: ISS-001
intent: INT-001
title: Add User model
status: complete
agent: backend
branch: conveyor/iss-001-add-user-model
depends_on: []
risk: low
created: '2026-03-15T05:11:21.675974+00:00'
---

# Add User model

## Acceptance criteria
- [x] File exists at src/models/user.py
- [x] User class with email and password fields

## Constraints
Files allowed: src/models/user.py
Files forbidden: src/api/*

## Agent report
files_created: src/models/user.py
notes: Created User model with email and password fields

## Reviewer verdict
passed: true
scope_ok: true
notes: Clean implementation, follows existing patterns

## Activity log
- [2026-03-15T05:11:21Z] ISS-001 status: created -> queued
- [2026-03-15T05:11:21Z] ISS-001 status: queued -> running
- [2026-03-15T05:11:45Z] ISS-001 agent_done: completed in 24.0s
- [2026-03-15T05:12:10Z] ISS-001 merged: auto-merged to main
```

## Retrying Failed Tasks

If a task fails (agent error, scope violation, reviewer rejection):

```bash
# Retry a specific issue
conveyor retry ISS-001

# Retry all failed issues for an intent
conveyor retry --intent INT-001

# Auto-detect and retry most recent failures
conveyor retry
```

The retry command resets failed/blocked issues to `CREATED`, unblocks downstream dependencies, and re-runs the state machine.
