from __future__ import annotations

from conveyor.tracking.models import Issue, Agent


def build_worker_prompt(
    issue: Issue,
    agent: Agent,
    codebase_context: str,
    prior_work: str,
    agent_prompt: str = "",
) -> str:
    sections = []

    # Section 1: Identity — use orchestrator-generated prompt if available
    if agent_prompt:
        identity = f"## 1. Identity\n\n{agent_prompt}"
    else:
        identity = (
            f"## 1. Identity\n\n"
            f"You are a Conveyor {agent.name} agent. Your role: {agent.role}."
        )
    identity += (
        "\n\n**Rules (always apply):**\n"
        "- Do EXACTLY what is asked, no more, no less.\n"
        "- Do NOT modify files outside your allowed scope.\n"
        "- Follow existing patterns in the codebase.\n"
        "- Be precise and minimal."
    )
    sections.append(identity)

    # Section 2: Task
    criteria = "\n".join(f"- {c}" for c in issue.acceptance_criteria)
    sections.append(f"""## 2. Task

Issue: {issue.id}
Title: {issue.title}
Branch: {issue.branch}

Acceptance criteria:
{criteria}

Files to create/modify: {', '.join(issue.files_allowed)}""")

    # Section 3: Codebase context
    sections.append(f"""## 3. Codebase context

{codebase_context}""")

    # Section 4: Prior work
    if prior_work:
        sections.append(f"""## 4. Prior work

The following upstream tasks have already been completed and merged:

{prior_work}""")
    else:
        sections.append("## 4. Prior work\n\nNo upstream dependencies. You are starting fresh.")

    # Section 5: Constraints
    forbidden = ", ".join(issue.files_forbidden) if issue.files_forbidden else "none"
    sections.append(f"""## 5. Constraints

Files you MUST NOT touch: {forbidden}
Stay within your assigned scope. Do not refactor unrelated code.""")

    # Section 6: Reporting
    sections.append("""## 6. Reporting

When you are done, output a report block in EXACTLY this format:

```
CONVEYOR_REPORT_START
files_created: <comma-separated list>
files_modified: <comma-separated list>
lines_added: <number>
tests_added: <number>
tests_passing: <true/false>
notes: <brief summary of what you did>
CONVEYOR_REPORT_END
```""")

    # Agent history
    if agent.issues_completed:
        history = f"\n\nYou have previously worked on: {', '.join(agent.issues_completed)}"
        if agent.files_familiar:
            history += f"\nYou are familiar with: {', '.join(agent.files_familiar)}"
        sections[0] += history

    return "\n\n".join(sections)


def build_orchestrator_prompt(
    intent_message: str,
    file_tree: str,
    git_log: str,
    claude_md: str = "",
) -> str:
    claude_section = ""
    if claude_md:
        claude_section = f"""## Project conventions (from CLAUDE.md)

{claude_md}

"""

    return f"""You are the Conveyor orchestrator. Your job is to analyze a codebase and decompose a user's intent into a dependency-aware task graph.

## Intent

{intent_message}

{claude_section}## File tree

{file_tree}

## Recent git history

{git_log}

## Instructions

Analyze the codebase and the intent. Produce a task graph.

For each task, specify:
- title: short descriptive name
- agent: one of (frontend, backend, testing, devops)
- agent_prompt: a rich, detailed system prompt for this specific agent, tailored to the project's stack, frameworks, and conventions. Follow this structure:
  1. Role identity ("You are a [stack] [role] specialist")
  2. Core responsibilities (3-5 numbered items specific to this task)
  3. Quality standards (bullet points with stack-specific conventions — e.g., "use type hints" for Python, "use async/await" for Node.js, "check errors with if err != nil" for Go)
  4. Boundaries (what the agent must NOT touch)
- files_allowed: files this task should create or modify
- files_forbidden: files this task must NOT touch
- depends_on: list of task numbers this depends on (e.g., [1, 2])
- risk: low (new files only), medium (modifies existing files), high (architectural changes)
- acceptance_criteria: list of concrete criteria

The agent_prompt is critical — it should reflect the EXACT frameworks and patterns you observe in the codebase. For example, if you see Next.js App Router, the prompt should reference App Router conventions, not Pages Router. If you see pytest fixtures, the testing prompt should mention fixtures specifically.

Output your plan in EXACTLY this format:

```
CONVEYOR_PLAN_START
[
  {{
    "task_number": 1,
    "title": "...",
    "agent": "backend",
    "agent_prompt": "You are a [specific] specialist...\\n\\n**Core Responsibilities:**\\n...",
    "files_allowed": ["src/..."],
    "files_forbidden": ["src/..."],
    "depends_on": [],
    "risk": "low",
    "acceptance_criteria": ["..."]
  }}
]
CONVEYOR_PLAN_END
```

Before the plan block, write a brief analysis explaining your reasoning."""


def build_reviewer_prompt(
    issue: Issue,
    diff: str,
    test_output: str,
    test_exit_code: int,
) -> str:
    criteria = "\n".join(f"- {c}" for c in issue.acceptance_criteria)
    allowed = ", ".join(issue.files_allowed) if issue.files_allowed else "any"
    test_status = "PASSED" if test_exit_code == 0 else "FAILED"

    return f"""You are the Conveyor reviewer agent. Review the work done for issue {issue.id}.

## Task

Title: {issue.title}
Acceptance criteria:
{criteria}

Files allowed: {allowed}

## Branch diff

```
{diff}
```

## Test results ({test_status})

```
{test_output}
```

## Instructions

Review the diff against the acceptance criteria and constraints.

Check:
1. **Scope** — Did the agent only touch allowed files?
2. **Completeness** — Are all acceptance criteria met?
3. **Quality** — Is the code clean, following existing patterns?
4. **Tests** — Did tests pass? Were appropriate tests added?

Output your verdict in EXACTLY this format:

```
REVIEW_RESULT_START
passed: <true/false>
scope_ok: <true/false>
criteria_met: <true/false>
tests_ok: <true/false>
notes: <brief explanation of your verdict>
REVIEW_RESULT_END
```"""
