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
    import json
    from pathlib import Path
    from rich.console import Console
    from rich.table import Table

    from conveyor.config import load_config
    from conveyor.core.orchestrator import run_orchestrator
    from conveyor.core.planner import TaskGraph
    from conveyor.execution.runner import Runner
    from conveyor.tracking.markdown import MarkdownStore
    from conveyor.tracking.models import Intent, Issue, IssueStatus, RiskLevel
    from conveyor.tracking.events import emit

    console = Console()
    repo_dir = Path.cwd()
    conveyor_dir = repo_dir / ".conveyor"

    if not conveyor_dir.exists():
        console.print("[red]Not a Conveyor project. Run 'conveyor init' first.[/red]")
        raise typer.Exit(1)

    config = load_config(conveyor_dir / "config.toml")
    store = MarkdownStore(conveyor_dir)

    # Read CLAUDE.md if present
    claude_md = ""
    claude_md_path = repo_dir / "CLAUDE.md"
    if claude_md_path.exists():
        claude_md = claude_md_path.read_text()

    # Run orchestrator
    console.print("\nOrchestrator analyzing codebase...\n")
    graph = run_orchestrator(
        intent_message=message,
        repo_dir=repo_dir,
        claude_md=claude_md,
    )

    if not graph.tasks:
        console.print("[red]Orchestrator could not produce a plan.[/red]")
        if graph.analysis:
            console.print(f"\n{graph.analysis}")
        raise typer.Exit(1)

    # Display analysis
    if graph.analysis:
        console.print(graph.analysis)
        console.print()

    # Display plan table
    table = Table(title=f"Plan: {len(graph.tasks)} tasks")
    table.add_column("Task", style="bold")
    table.add_column("Agent")
    table.add_column("Risk")
    table.add_column("Depends on")
    table.add_column("Files")

    for t in graph.topological_order():
        deps = ", ".join(str(d) for d in t.get("depends_on", []))
        files = ", ".join(t.get("files_allowed", []))
        risk_color = {"low": "green", "medium": "yellow", "high": "red"}.get(t["risk"], "white")
        table.add_row(
            f"{t['task_number']}. {t['title']}",
            t["agent"],
            f"[{risk_color}]{t['risk']}[/{risk_color}]",
            deps or "—",
            files,
        )

    console.print(table)
    console.print()

    # Approval prompt
    choice = typer.prompt("[a]pprove  [r]eject", default="a")
    if choice.lower() != "a":
        console.print("Rejected.")
        raise typer.Exit(0)

    # Create intent and issues
    intent_id = store.next_intent_id()
    intent_obj = Intent(
        id=intent_id,
        title=message[:60],
        message=message,
        status="in_progress",
    )

    issues_list = []
    task_num_to_issue_id = {}

    for t in graph.topological_order():
        issue_id = store.next_issue_id()
        task_num_to_issue_id[t["task_number"]] = issue_id

        dep_ids = [task_num_to_issue_id[d] for d in t.get("depends_on", []) if d in task_num_to_issue_id]
        slug = t["title"].lower().replace(" ", "-")[:30]
        branch = f"conveyor/{issue_id.lower()}-{slug}"

        issue_obj = Issue(
            id=issue_id,
            intent=intent_id,
            title=t["title"],
            agent=t.get("agent", "backend"),
            branch=branch,
            depends_on=dep_ids,
            risk=RiskLevel(t.get("risk", "low")),
            files_allowed=t.get("files_allowed", []),
            files_forbidden=t.get("files_forbidden", []),
            acceptance_criteria=t.get("acceptance_criteria", []),
        )
        issues_list.append(issue_obj)
        intent_obj.issues.append(issue_id)
        store.save_issue(issue_obj)

    intent_obj.orchestrator_analysis = graph.analysis
    store.save_intent(intent_obj)

    # Run the state machine
    console.print("\nExecuting...\n")

    def on_pause(paused_issue: Issue) -> bool:
        review_type = paused_issue.review_type
        console.print(f"\n[bold]{paused_issue.id}: {paused_issue.title}[/bold]")
        console.print(f"  Review type: {review_type}")
        console.print(f"  Risk: {paused_issue.risk}")
        console.print(f"  Branch: {paused_issue.branch}")
        choice = typer.prompt("  [a]pprove  [r]eject", default="a")
        return choice.lower() == "a"

    runner = Runner(
        issues=issues_list,
        store=store,
        config=config,
        repo_dir=repo_dir,
    )

    events = runner.run(on_pause=on_pause)

    # Summary
    console.print()
    completed = sum(1 for i in issues_list if i.status == IssueStatus.COMPLETE)
    failed = sum(1 for i in issues_list if i.status == IssueStatus.FAILED)
    blocked = sum(1 for i in issues_list if i.status == IssueStatus.BLOCKED)

    if completed == len(issues_list):
        console.print(f"[green]Intent complete. {completed} tasks merged.[/green]")
        intent_obj.status = "complete"
    else:
        console.print(f"Completed: {completed}, Failed: {failed}, Blocked: {blocked}")
        intent_obj.status = "partial"

    store.save_intent(intent_obj)


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
