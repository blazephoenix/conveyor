import typer

app = typer.Typer(name="conveyor", help="AI-native project orchestration")


@app.command()
def init():
    """Scan repo, create .conveyor/, detect stack."""
    from pathlib import Path
    from conveyor.core.init import run_init

    repo_dir = Path.cwd()
    result = run_init(repo_dir)

    typer.echo(f"Created {result.conveyor_dir}")
    typer.echo(f"Scanned {result.file_count} files")
    if result.stack_detected:
        typer.echo(f"Detected: {', '.join(result.stack_detected)}")
    if result.claude_md:
        typer.echo("CLAUDE.md found — using as project profile")
    typer.echo("Default agents created (frontend, backend, testing, devops, reviewer)")


@app.command()
def intent(message: str = typer.Argument(..., help="The intent to execute")):
    """Decompose an intent into a task graph and execute it."""
    typer.echo("Not implemented yet")


@app.command()
def status():
    """Show current intent progress and issue states."""
    typer.echo("Not implemented yet")


@app.command()
def issues(issue_id: str = typer.Argument(None, help="Specific issue ID")):
    """List issues or show detail for a specific issue."""
    typer.echo("Not implemented yet")


@app.command()
def review():
    """Review pending medium/high risk merges."""
    typer.echo("Not implemented yet")


@app.command()
def log(issue: str = typer.Option(None, "--issue", help="Filter by issue ID")):
    """Show activity trail."""
    typer.echo("Not implemented yet")
