# Contributing to Conveyor

Thanks for your interest in contributing. Conveyor is in early alpha — there's a lot to do and we welcome all kinds of help.

## Getting Set Up

```bash
# Clone and install
git clone https://github.com/blazephoenix/conveyor.git
cd conveyor

# Create a venv with Python 3.12 (3.11+ required)
uv venv --python 3.12 .venv
source .venv/bin/activate

# Install with dev dependencies
uv pip install -e ".[dev]"

# Verify everything works
pytest -v
```

## Development Workflow

1. **Fork the repo** and create a branch from `main`
2. **Write tests first** — we follow TDD. Write the failing test, then the implementation
3. **Run the test suite** — all 79+ tests must pass before submitting
4. **Commit with clear messages** — `feat:`, `fix:`, `refactor:`, `test:`, `docs:` prefixes
5. **Open a PR** against `main`

```bash
# Run tests
pytest -v

# Run a specific test file
pytest tests/core/test_planner.py -v

# Run with output
pytest -v -s
```

## Project Structure

```
conveyor/
├── cli.py              # CLI commands (Typer)
├── config.py           # Configuration
├── core/               # Business logic
│   ├── init.py         # Repo initialization
│   ├── orchestrator.py # Intent decomposition
│   ├── planner.py      # Task graph parsing
│   ├── context.py      # Codebase context assembly
│   └── governance.py   # Approval gates
├── execution/          # Task execution
│   ├── adapter.py      # Claude Code subprocess
│   ├── branch.py       # Git operations
│   ├── runner.py       # State machine
│   └── prompt.py       # Prompt templates
├── validation/         # Post-execution checks
│   └── checks.py       # Test runner, scope checker
└── tracking/           # Data layer
    ├── models.py       # Dataclasses
    ├── markdown.py     # File I/O
    └── events.py       # Event logging
```

## What to Work On

### Good First Issues

- Add more stack detection (Ruby, Java, C#)
- Improve error messages when Claude Code CLI is not installed
- Add `--dry-run` flag to `intent` command
- Add color to `conveyor status` output

### Medium

- Add a `conveyor reset` command to clean up stale branches and state
- Persist and display per-task timing in issue markdown
- Add `conveyor diff` to show what an intent changed across all its branches
- Better config validation with helpful error messages

### Big

- Parallel task execution for independent tasks
- Interactive permission bubbling from Claude Code subprocesses
- Resume execution after crash (reconstruct state from `.conveyor/` files)
- Plugin system for custom agents

## Code Conventions

- **Python 3.11+** — use type hints, `StrEnum`, `dataclasses`
- **No external database** — the `.conveyor/` directory is the data layer
- **Tests are mandatory** — no PR without tests
- **Keep it simple** — prefer stdlib over dependencies. We have 3 runtime deps (typer, pyyaml, rich)
- **Subprocess only** — Claude Code is invoked via `claude --print`. No SDK, no API keys

## Testing Philosophy

- Unit tests for all modules
- Integration test (`tests/test_integration.py`) validates the full flow with mocked Claude Code
- Tests that need git repos use `tmp_path` fixtures
- Mock the Claude Code subprocess, never call it in tests

## Submitting a PR

1. Ensure all tests pass: `pytest -v`
2. Keep PRs focused — one feature or fix per PR
3. Update tests for any behavior changes
4. Update docs if adding commands or config options

## Reporting Bugs

[Open an issue](https://github.com/blazephoenix/conveyor/issues) with:

- What you ran (command + arguments)
- What happened (error output)
- What you expected
- Your environment (OS, Python version, Claude Code version)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
