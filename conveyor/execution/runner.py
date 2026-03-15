from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from conveyor.config import ConveyorConfig
from conveyor.core.governance import auto_merge_allowed, needs_plan_approval
from conveyor.execution.adapter import ClaudeCodeAdapter
from conveyor.execution.branch import (
    create_branch,
    checkout_branch,
    merge_branch,
    branch_diff,
    changed_files,
)
from conveyor.execution.prompt import (
    build_worker_prompt,
    build_reviewer_prompt,
)
from conveyor.core.context import (
    gather_codebase_context,
    gather_prior_work,
)
from conveyor.tracking.events import emit
from conveyor.tracking.markdown import MarkdownStore
from conveyor.tracking.models import (
    Agent,
    AgentResult,
    Issue,
    IssueStatus,
    RiskLevel,
)
from conveyor.validation.checks import (
    run_tests,
    parse_agent_report,
    parse_reviewer_verdict,
    check_scope,
)


class Runner:
    def __init__(
        self,
        issues: list[Issue],
        store: MarkdownStore,
        config: ConveyorConfig,
        repo_dir: Path,
        adapter: ClaudeCodeAdapter | None = None,
        on_progress: Callable[[str], None] | None = None,
    ):
        self.issues = issues
        self.store = store
        self.config = config
        self.repo_dir = repo_dir
        self.adapter = adapter or ClaudeCodeAdapter()
        self._issue_map = {i.id: i for i in issues}
        self._on_progress = on_progress

    def _emit_progress(self, msg: str) -> None:
        if self._on_progress:
            self._on_progress(msg)

    def all_terminal(self) -> bool:
        return all(
            i.status in (IssueStatus.COMPLETE, IssueStatus.FAILED, IssueStatus.BLOCKED)
            for i in self.issues
        )

    def _all_deps_complete(self, issue: Issue) -> bool:
        for dep_id in issue.depends_on:
            dep = self._issue_map.get(dep_id)
            if dep is None or dep.status != IssueStatus.COMPLETE:
                return False
        return True

    def _any_dep_failed(self, issue: Issue) -> bool:
        for dep_id in issue.depends_on:
            dep = self._issue_map.get(dep_id)
            if dep and dep.status in (IssueStatus.FAILED, IssueStatus.BLOCKED):
                return True
        return False

    def _topological_order(self) -> list[Issue]:
        in_degree = {i.id: 0 for i in self.issues}
        for i in self.issues:
            for dep in i.depends_on:
                if dep in in_degree:
                    in_degree[i.id] += 1
        queue = sorted([id for id, d in in_degree.items() if d == 0])
        result = []
        while queue:
            node = queue.pop(0)
            result.append(self._issue_map[node])
            for i in self.issues:
                if node in i.depends_on:
                    in_degree[i.id] -= 1
                    if in_degree[i.id] == 0:
                        queue.append(i.id)
        return result

    def advance_once(self) -> list[str]:
        """Advance each issue by one state transition. Returns list of events."""
        events = []
        for issue in self._topological_order():
            match issue.status:
                case IssueStatus.CREATED:
                    if self._any_dep_failed(issue):
                        issue.status = IssueStatus.BLOCKED
                        emit(issue.activity_log, issue.id, "status", "created -> blocked (upstream failed)")
                        events.append(f"{issue.id}: blocked (upstream failed)")
                    else:
                        issue.status = IssueStatus.QUEUED
                        emit(issue.activity_log, issue.id, "status", "created -> queued")
                        events.append(f"{issue.id}: created -> queued")
                    self.store.save_issue(issue)

                case IssueStatus.QUEUED:
                    if self._all_deps_complete(issue):
                        if needs_plan_approval(issue, self.config):
                            issue.status = IssueStatus.PAUSED
                            issue.review_type = "plan"
                            emit(issue.activity_log, issue.id, "status", "queued -> paused (high risk, needs plan approval)")
                            events.append(f"{issue.id}: paused for plan review")
                        else:
                            issue.status = IssueStatus.RUNNING
                            emit(issue.activity_log, issue.id, "status", "queued -> running")
                            events.append(f"{issue.id}: queued -> running")
                    elif self._any_dep_failed(issue):
                        issue.status = IssueStatus.BLOCKED
                        emit(issue.activity_log, issue.id, "status", "queued -> blocked (upstream failed)")
                        events.append(f"{issue.id}: blocked (upstream failed)")
                    self.store.save_issue(issue)

                case IssueStatus.RUNNING:
                    events.extend(self._execute_agent(issue))

                case IssueStatus.VALIDATING:
                    events.extend(self._validate_and_review(issue))

                case IssueStatus.PAUSED:
                    pass  # Waiting for user via CLI

        return events

    def _execute_agent(self, issue: Issue) -> list[str]:
        events = []
        emit(issue.activity_log, issue.id, "agent_start", f"{issue.agent} agent executing")

        # Create branch
        self._emit_progress(f"[{issue.id}] Creating branch {issue.branch}")
        checkout_branch("main", self.repo_dir)
        create_branch(issue.branch, self.repo_dir)

        # Load agent
        self._emit_progress(f"[{issue.id}] Loading {issue.agent} agent")
        try:
            agent = self.store.load_agent(issue.agent)
        except FileNotFoundError:
            agent = Agent(name=issue.agent, role=issue.agent)

        # Gather context
        self._emit_progress(f"[{issue.id}] Gathering codebase context for {', '.join(issue.files_allowed)}")
        completed_files = []
        for dep_id in issue.depends_on:
            dep = self._issue_map.get(dep_id)
            if dep:
                completed_files.extend(dep.files_allowed)

        codebase_ctx = gather_codebase_context(
            repo_dir=self.repo_dir,
            files_relevant=issue.files_allowed,
            sibling_patterns=[],
        )
        prior = gather_prior_work(self.repo_dir, completed_files)
        if completed_files:
            self._emit_progress(f"[{issue.id}] Loaded prior work from {len(completed_files)} upstream files")

        # Build prompt and execute
        self._emit_progress(f"[{issue.id}] Dispatching {issue.agent} agent — {issue.title}")
        prompt = build_worker_prompt(
            issue=issue,
            agent=agent,
            codebase_context=codebase_ctx,
            prior_work=prior,
            agent_prompt=issue.agent_prompt,
        )
        result = self.adapter.execute(
            prompt=prompt,
            workdir=str(self.repo_dir),
            timeout=self.config.timeout_seconds,
        )

        # Save session
        session_id = self.store.next_session_id()
        self.store.save_session(session_id, issue.id, result.output)

        # Parse report
        report = parse_agent_report(result.output)
        if report:
            issue.agent_report = "\n".join(f"{k}: {v}" for k, v in report.items())
            self._emit_progress(f"[{issue.id}] Agent report: {report.get('notes', 'done')}")

        if result.success:
            issue.status = IssueStatus.VALIDATING
            emit(issue.activity_log, issue.id, "agent_done", f"completed in {result.duration_seconds:.1f}s")
            self._emit_progress(f"[{issue.id}] Agent completed in {result.duration_seconds:.1f}s — moving to validation")
            events.append(f"{issue.id}: agent completed -> validating")
        else:
            issue.status = IssueStatus.FAILED
            emit(issue.activity_log, issue.id, "agent_failed", f"exit code {result.exit_code}")
            events.append(f"{issue.id}: agent failed (exit {result.exit_code})")

        self.store.save_issue(issue)
        return events

    def _validate_and_review(self, issue: Issue) -> list[str]:
        events = []

        # Run tests
        if self.config.test_command:
            self._emit_progress(f"[{issue.id}] Running tests: {self.config.test_command}")
        else:
            self._emit_progress(f"[{issue.id}] No test command configured — skipping tests")
        test_result = run_tests(self.config.test_command, str(self.repo_dir))
        self._emit_progress(f"[{issue.id}] Tests {'passed' if test_result.passed else 'FAILED'}")
        emit(issue.activity_log, issue.id, "tests",
             f"{'passed' if test_result.passed else 'failed'}")

        # Get diff and check scope
        self._emit_progress(f"[{issue.id}] Checking diff and scope compliance...")
        diff = branch_diff(issue.branch, "main", self.repo_dir)
        files_changed = changed_files(issue.branch, "main", self.repo_dir)
        if files_changed:
            self._emit_progress(f"[{issue.id}] Files changed: {', '.join(files_changed)}")
        scope_ok, violations = check_scope(
            files_changed, issue.files_allowed, issue.files_forbidden
        )
        if not scope_ok:
            self._emit_progress(f"[{issue.id}] Scope violation: {'; '.join(violations)}")
        else:
            self._emit_progress(f"[{issue.id}] Scope check passed")

        # Run reviewer agent
        self._emit_progress(f"[{issue.id}] Dispatching reviewer agent...")
        reviewer_prompt = build_reviewer_prompt(
            issue=issue,
            diff=diff,
            test_output=test_result.output,
            test_exit_code=test_result.exit_code,
        )
        review_result = self.adapter.execute(
            prompt=reviewer_prompt,
            workdir=str(self.repo_dir),
            timeout=self.config.timeout_seconds,
        )
        verdict = parse_reviewer_verdict(review_result.output)
        issue.reviewer_verdict = "\n".join(f"{k}: {v}" for k, v in verdict.items())
        self._emit_progress(f"[{issue.id}] Reviewer verdict: {'PASSED' if verdict.get('passed') == 'true' else 'REJECTED'} — {verdict.get('notes', '')}")

        passed = verdict.get("passed", "false") == "true" and scope_ok and test_result.passed

        if passed:
            if auto_merge_allowed(issue, self.config):
                checkout_branch("main", self.repo_dir)
                merge_ok = merge_branch(issue.branch, self.repo_dir)
                if merge_ok:
                    issue.status = IssueStatus.COMPLETE
                    issue.completed = datetime.now(timezone.utc)
                    emit(issue.activity_log, issue.id, "merged", "auto-merged to main")
                    events.append(f"{issue.id}: auto-merged")

                    # Update agent history
                    try:
                        agent = self.store.load_agent(issue.agent)
                        agent.issues_completed.append(issue.id)
                        agent.files_familiar.extend(issue.files_allowed)
                        agent.history.append(f"{issue.id}: {issue.title}")
                        self.store.save_agent(agent)
                    except FileNotFoundError:
                        pass
                else:
                    issue.status = IssueStatus.FAILED
                    emit(issue.activity_log, issue.id, "merge_failed", "merge conflict")
                    events.append(f"{issue.id}: merge conflict -> failed")
            else:
                issue.status = IssueStatus.PAUSED
                issue.review_type = "merge"
                emit(issue.activity_log, issue.id, "status", "awaiting board merge review")
                events.append(f"{issue.id}: awaiting board review")
        else:
            issue.status = IssueStatus.FAILED
            reasons = []
            if not test_result.passed:
                reasons.append("tests failed")
            if not scope_ok:
                reasons.append(f"scope violations: {violations}")
            if verdict.get("passed") != "true":
                reasons.append(f"reviewer rejected: {verdict.get('notes', '')}")
            emit(issue.activity_log, issue.id, "failed", "; ".join(reasons))
            events.append(f"{issue.id}: failed -- {'; '.join(reasons)}")

        self.store.save_issue(issue)
        return events

    def run(self, on_pause=None) -> list[str]:
        """Run the full state machine until all issues are terminal or paused.

        on_pause: optional callback called when an issue needs board review.
                  signature: on_pause(issue: Issue) -> bool
                  returns True if approved, False if rejected.
        """
        all_events = []
        while not self.all_terminal():
            has_paused = any(i.status == IssueStatus.PAUSED for i in self.issues)
            has_actionable = any(
                i.status in (IssueStatus.CREATED, IssueStatus.QUEUED,
                             IssueStatus.RUNNING, IssueStatus.VALIDATING)
                for i in self.issues
            )

            if has_paused and not has_actionable and on_pause:
                for issue in self.issues:
                    if issue.status == IssueStatus.PAUSED:
                        approved = on_pause(issue)
                        if approved:
                            if issue.review_type == "plan":
                                issue.status = IssueStatus.QUEUED
                                issue.review_type = ""
                            elif issue.review_type == "merge":
                                checkout_branch("main", self.repo_dir)
                                merge_ok = merge_branch(issue.branch, self.repo_dir)
                                if merge_ok:
                                    issue.status = IssueStatus.COMPLETE
                                    issue.completed = datetime.now(timezone.utc)
                                else:
                                    issue.status = IssueStatus.FAILED
                            self.store.save_issue(issue)
                        else:
                            issue.status = IssueStatus.FAILED
                            self.store.save_issue(issue)
            elif not has_actionable:
                break

            events = self.advance_once()
            all_events.extend(events)

        return all_events
