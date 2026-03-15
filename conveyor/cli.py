import typer

app = typer.Typer(name="conveyor", help="AI-native project orchestration")


@app.command()
def init():
    """Scan repo, create .conveyor/, detect stack."""
    from pathlib import Path
    from rich.console import Console
    from rich.panel import Panel
    from conveyor.core.init import run_init

    console = Console()
    repo_dir = Path.cwd()
    result = run_init(repo_dir)

    banner = (
        "\n"
        "[bold cyan]"
        " ██████╗ ██████╗ ███╗   ██╗██╗   ██╗███████╗██╗   ██╗ ██████╗ ██████╗ \n"
        "██╔════╝██╔═══██╗████╗  ██║██║   ██║██╔════╝╚██╗ ██╔╝██╔═══██╗██╔══██╗\n"
        "██║     ██║   ██║██╔██╗ ██║██║   ██║█████╗   ╚████╔╝ ██║   ██║██████╔╝\n"
        "██║     ██║   ██║██║╚██╗██║╚██╗ ██╔╝██╔══╝    ╚██╔╝  ██║   ██║██╔══██╗\n"
        "╚██████╗╚██████╔╝██║ ╚████║ ╚████╔╝ ███████╗   ██║   ╚██████╔╝██║  ██║\n"
        " ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝  ╚═══╝  ╚══════╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝\n"
        "[/bold cyan]"
        "  [dim]───────────────────────────────────────────────────────[/dim]\n"
        "  AI-native project orchestration\n"
    )
    console.print(banner)

    console.print("[bold]┌[/bold]   [bold]conveyor init[/bold]")
    console.print("[bold]│[/bold]")
    console.print(f"[bold]│[/bold]  Project: {repo_dir}")
    console.print("[bold]│[/bold]")

    console.print(f"[bold]◆[/bold]  Initialized .conveyor/")
    console.print(f"[bold]│[/bold]")
    console.print(f"[bold]◆[/bold]  Scanned {result.file_count} files")
    if result.stack_detected:
        console.print(f"[bold]│[/bold]")
        console.print(f"[bold]◇[/bold]  Detected: [bold]{', '.join(result.stack_detected)}[/bold]")
    if result.claude_md:
        console.print(f"[bold]│[/bold]")
        console.print(f"[bold]◇[/bold]  CLAUDE.md found — using as project profile")
    console.print(f"[bold]│[/bold]")
    console.print(f"[bold]◆[/bold]  Agents created: frontend, backend, testing, devops, reviewer")

    console.print("[bold]│[/bold]")
    console.print("[bold]◇[/bold]  [bold]Next commands[/bold] ────────────────────────────────╮")
    console.print("[bold]│[/bold]                                                    [bold]│[/bold]")
    console.print("[bold]│[/bold]  [cyan]conveyor intent \"...\"[/cyan]  Decompose and execute     [bold]│[/bold]")
    console.print("[bold]│[/bold]  [cyan]conveyor status[/cyan]       Show intent progress       [bold]│[/bold]")
    console.print("[bold]│[/bold]  [cyan]conveyor issues[/cyan]       List or inspect issues      [bold]│[/bold]")
    console.print("[bold]│[/bold]  [cyan]conveyor review[/cyan]       Review pending merges       [bold]│[/bold]")
    console.print("[bold]│[/bold]  [cyan]conveyor log[/cyan]          Show activity trail         [bold]│[/bold]")
    console.print("[bold]│[/bold]                                                    [bold]│[/bold]")
    console.print("[bold]├[/bold]────────────────────────────────────────────────────╯")
    console.print("[bold]│[/bold]")
    console.print("[bold]└[/bold]  Ready!")


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

    # Run orchestrator with progress
    console.print()
    console.print("[bold]┌[/bold]   [bold]conveyor intent[/bold]")
    console.print("[bold]│[/bold]")
    console.print(f"[bold]│[/bold]  Intent: [cyan]{message}[/cyan]")
    console.print("[bold]│[/bold]")

    def orchestrator_progress(msg: str) -> None:
        console.print(f"[bold]│[/bold]  [dim]{msg}[/dim]")

    graph = run_orchestrator(
        intent_message=message,
        repo_dir=repo_dir,
        claude_md=claude_md,
        on_progress=orchestrator_progress,
    )
    console.print("[bold]│[/bold]")

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
        import re
        slug = re.sub(r"[^a-z0-9]+", "-", t["title"].lower()).strip("-")[:30].rstrip("-")
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
            agent_prompt=t.get("agent_prompt", ""),
        )
        issues_list.append(issue_obj)
        intent_obj.issues.append(issue_id)
        store.save_issue(issue_obj)

    intent_obj.orchestrator_analysis = graph.analysis
    store.save_intent(intent_obj)

    # Run the state machine
    console.print("[bold]│[/bold]")
    console.print("[bold]◇[/bold]  [bold]Executing task graph...[/bold]")
    console.print("[bold]│[/bold]")

    def execution_progress(msg: str) -> None:
        console.print(f"[bold]│[/bold]  [dim]{msg}[/dim]")

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
        on_progress=execution_progress,
    )

    events = runner.run(on_pause=on_pause)

    # Summary
    console.print("[bold]│[/bold]")
    completed = sum(1 for i in issues_list if i.status == IssueStatus.COMPLETE)
    failed = sum(1 for i in issues_list if i.status == IssueStatus.FAILED)
    blocked = sum(1 for i in issues_list if i.status == IssueStatus.BLOCKED)

    console.print("[bold]◇[/bold]  [bold]Summary[/bold] ─────────────────────────────────────╮")
    console.print("[bold]│[/bold]                                                    [bold]│[/bold]")
    if completed == len(issues_list):
        console.print(f"[bold]│[/bold]  [green]All {completed} tasks completed and merged[/green]         [bold]│[/bold]")
        intent_obj.status = "complete"
    else:
        console.print(f"[bold]│[/bold]  Completed: {completed}  Failed: {failed}  Blocked: {blocked}              [bold]│[/bold]")
        intent_obj.status = "partial"
    console.print("[bold]│[/bold]                                                    [bold]│[/bold]")
    console.print("[bold]├[/bold]────────────────────────────────────────────────────╯")
    console.print("[bold]│[/bold]")
    if completed == len(issues_list):
        console.print("[bold]└[/bold]  [green]Intent complete![/green]")
    else:
        console.print("[bold]└[/bold]  Run [cyan]conveyor status[/cyan] or [cyan]conveyor issues[/cyan] for details")

    store.save_intent(intent_obj)


@app.command()
def status():
    """Show current intent progress and issue states."""
    from pathlib import Path
    from rich.console import Console
    from rich.table import Table
    from conveyor.tracking.markdown import MarkdownStore

    console = Console()
    store = MarkdownStore(Path.cwd() / ".conveyor")

    intents = store.list_intents()
    if not intents:
        console.print("No intents found.")
        return

    for intent_obj in intents:
        console.print(f"\n[bold]{intent_obj.id}: {intent_obj.title}[/bold]  ({intent_obj.status})")
        issues_list = store.list_issues(intent_id=intent_obj.id)
        table = Table()
        table.add_column("Issue")
        table.add_column("Status")
        table.add_column("Agent")
        table.add_column("Risk")
        for issue_obj in issues_list:
            status_color = {
                "complete": "green", "failed": "red", "blocked": "yellow",
                "running": "cyan", "paused": "magenta",
            }.get(str(issue_obj.status), "white")
            table.add_row(
                f"{issue_obj.id}: {issue_obj.title}",
                f"[{status_color}]{issue_obj.status}[/{status_color}]",
                issue_obj.agent,
                str(issue_obj.risk),
            )
        console.print(table)


@app.command()
def issues(issue_id: str = typer.Argument(None, help="Specific issue ID")):
    """List issues or show detail for a specific issue."""
    from pathlib import Path
    from rich.console import Console
    from conveyor.tracking.markdown import MarkdownStore

    console = Console()
    store = MarkdownStore(Path.cwd() / ".conveyor")

    if issue_id:
        try:
            issue_obj = store.load_issue(issue_id)
            console.print(f"\n[bold]{issue_obj.id}: {issue_obj.title}[/bold]")
            console.print(f"Status: {issue_obj.status}")
            console.print(f"Agent: {issue_obj.agent}")
            console.print(f"Branch: {issue_obj.branch}")
            console.print(f"Risk: {issue_obj.risk}")
            console.print(f"Depends on: {', '.join(issue_obj.depends_on) or '—'}")
            if issue_obj.acceptance_criteria:
                console.print("\nAcceptance criteria:")
                for c in issue_obj.acceptance_criteria:
                    console.print(f"  - {c}")
            if issue_obj.agent_report:
                console.print(f"\nAgent report:\n{issue_obj.agent_report}")
            if issue_obj.reviewer_verdict:
                console.print(f"\nReviewer verdict:\n{issue_obj.reviewer_verdict}")
            if issue_obj.activity_log:
                console.print("\nActivity log:")
                for entry in issue_obj.activity_log:
                    console.print(f"  {entry}")
        except FileNotFoundError:
            console.print(f"[red]Issue {issue_id} not found.[/red]")
    else:
        all_issues = store.list_issues()
        if not all_issues:
            console.print("No issues found.")
            return
        for issue_obj in all_issues:
            status_color = {
                "complete": "green", "failed": "red", "blocked": "yellow",
                "running": "cyan", "paused": "magenta",
            }.get(str(issue_obj.status), "white")
            console.print(
                f"  {issue_obj.id}: [{status_color}]{issue_obj.status}[/{status_color}] "
                f"{issue_obj.title} ({issue_obj.agent}, {issue_obj.risk})"
            )


@app.command()
def review():
    """Review pending medium/high risk merges."""
    from pathlib import Path
    from rich.console import Console
    from conveyor.tracking.markdown import MarkdownStore
    from conveyor.tracking.models import IssueStatus
    from conveyor.execution.branch import checkout_branch, merge_branch, branch_diff

    console = Console()
    repo_dir = Path.cwd()
    store = MarkdownStore(repo_dir / ".conveyor")

    paused = [i for i in store.list_issues() if i.status == IssueStatus.PAUSED]
    if not paused:
        console.print("Nothing to review.")
        return

    for issue_obj in paused:
        console.print(f"\n[bold]{issue_obj.id}: {issue_obj.title}[/bold]")
        console.print(f"  Review type: {issue_obj.review_type}")
        console.print(f"  Risk: {issue_obj.risk}")
        console.print(f"  Branch: {issue_obj.branch}")

        choice = typer.prompt("  [a]pprove  [d]iff  [r]eject", default="a")
        if choice.lower() == "d":
            diff = branch_diff(issue_obj.branch, "main", repo_dir)
            console.print(diff)
            choice = typer.prompt("  [a]pprove  [r]eject", default="a")

        if choice.lower() == "a":
            if issue_obj.review_type == "merge":
                checkout_branch("main", repo_dir)
                ok = merge_branch(issue_obj.branch, repo_dir)
                if ok:
                    issue_obj.status = IssueStatus.COMPLETE
                    console.print("  [green]Merged[/green]")
                else:
                    issue_obj.status = IssueStatus.FAILED
                    console.print("  [red]Merge conflict[/red]")
            elif issue_obj.review_type == "plan":
                issue_obj.status = IssueStatus.QUEUED
                issue_obj.review_type = ""
                console.print("  [green]Plan approved[/green]")
            store.save_issue(issue_obj)
        else:
            issue_obj.status = IssueStatus.FAILED
            store.save_issue(issue_obj)
            console.print("  [red]Rejected[/red]")


@app.command()
def log(issue: str = typer.Option(None, "--issue", help="Filter by issue ID")):
    """Show activity trail."""
    from pathlib import Path
    from rich.console import Console
    from conveyor.tracking.markdown import MarkdownStore

    console = Console()
    store = MarkdownStore(Path.cwd() / ".conveyor")

    if issue:
        try:
            issue_obj = store.load_issue(issue)
            console.print(f"\n[bold]Log for {issue_obj.id}: {issue_obj.title}[/bold]\n")
            for entry in issue_obj.activity_log:
                console.print(f"  {entry}")
        except FileNotFoundError:
            console.print(f"[red]Issue {issue} not found.[/red]")
    else:
        all_issues = store.list_issues()
        for issue_obj in all_issues:
            if issue_obj.activity_log:
                console.print(f"\n[bold]{issue_obj.id}: {issue_obj.title}[/bold]")
                for entry in issue_obj.activity_log:
                    console.print(f"  {entry}")
