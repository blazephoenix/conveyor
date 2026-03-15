from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum


class IssueStatus(StrEnum):
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    VALIDATING = "validating"
    COMPLETE = "complete"
    FAILED = "failed"
    BLOCKED = "blocked"
    PAUSED = "paused"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Intent:
    id: str
    title: str
    message: str
    status: str = "pending"
    created: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    issues: list[str] = field(default_factory=list)
    orchestrator_analysis: str = ""
    activity_log: list[str] = field(default_factory=list)


@dataclass
class Issue:
    id: str
    intent: str
    title: str
    agent: str
    branch: str
    depends_on: list[str]
    risk: RiskLevel
    status: IssueStatus = IssueStatus.CREATED
    files_allowed: list[str] = field(default_factory=list)
    files_forbidden: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    created: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed: datetime | None = None
    agent_prompt: str = ""
    agent_report: str = ""
    reviewer_verdict: str = ""
    review_type: str = ""
    activity_log: list[str] = field(default_factory=list)

    @property
    def is_terminal(self) -> bool:
        return self.status in (
            IssueStatus.COMPLETE,
            IssueStatus.FAILED,
            IssueStatus.BLOCKED,
        )


@dataclass
class Agent:
    name: str
    role: str
    issues_completed: list[str] = field(default_factory=list)
    files_familiar: list[str] = field(default_factory=list)
    history: list[str] = field(default_factory=list)


@dataclass
class AgentResult:
    output: str
    exit_code: int
    duration_seconds: float

    @property
    def success(self) -> bool:
        return self.exit_code == 0
