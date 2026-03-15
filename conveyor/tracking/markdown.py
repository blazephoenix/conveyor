from __future__ import annotations

import re
from pathlib import Path

import yaml

from conveyor.tracking.models import (
    Agent,
    Intent,
    Issue,
    IssueStatus,
    RiskLevel,
)


def _slugify(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len].rstrip("-")


def _dump_frontmatter(data: dict, body: str) -> str:
    fm = yaml.dump(data, default_flow_style=False, sort_keys=False).strip()
    return f"---\n{fm}\n---\n\n{body}"


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    match = re.match(r"^---\n(.*?)\n---\n\n?(.*)", text, re.DOTALL)
    if not match:
        return {}, text
    fm = yaml.safe_load(match.group(1)) or {}
    body = match.group(2)
    return fm, body


class MarkdownStore:
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.intents_dir = self.base_dir / "intents"
        self.issues_dir = self.base_dir / "issues"
        self.agents_dir = self.base_dir / "agents"
        self.sessions_dir = self.base_dir / "sessions"

    def _ensure_dirs(self):
        for d in (self.intents_dir, self.issues_dir, self.agents_dir, self.sessions_dir):
            d.mkdir(parents=True, exist_ok=True)

    # --- Intents ---

    def save_intent(self, intent: Intent) -> Path:
        self._ensure_dirs()
        slug = _slugify(intent.title)
        path = self.intents_dir / f"{intent.id}-{slug}.md"
        fm = {
            "id": intent.id,
            "title": intent.title,
            "status": intent.status,
            "created": intent.created.isoformat(),
            "issues": intent.issues,
        }
        body = f"# {intent.title}\n\n"
        body += f"## Board intent\n{intent.message}\n\n"
        body += f"## Orchestrator analysis\n{intent.orchestrator_analysis}\n\n"
        body += "## Activity log\n"
        for entry in intent.activity_log:
            body += f"- {entry}\n"
        path.write_text(_dump_frontmatter(fm, body))
        return path

    def load_intent(self, intent_id: str) -> Intent:
        path = self._find_file(self.intents_dir, intent_id)
        fm, body = _parse_frontmatter(path.read_text())
        return Intent(
            id=fm["id"],
            title=fm["title"],
            message=self._extract_section(body, "Board intent"),
            status=fm.get("status", "pending"),
            issues=fm.get("issues", []),
            orchestrator_analysis=self._extract_section(body, "Orchestrator analysis"),
        )

    def list_intents(self) -> list[Intent]:
        if not self.intents_dir.exists():
            return []
        return [
            self.load_intent(self._id_from_path(p))
            for p in sorted(self.intents_dir.glob("INT-*.md"))
        ]

    def next_intent_id(self) -> str:
        existing = sorted(self.intents_dir.glob("INT-*.md")) if self.intents_dir.exists() else []
        num = len(existing) + 1
        return f"INT-{num:03d}"

    # --- Issues ---

    def save_issue(self, issue: Issue) -> Path:
        self._ensure_dirs()
        slug = _slugify(issue.title)
        path = self.issues_dir / f"{issue.id}-{slug}.md"
        fm = {
            "id": issue.id,
            "intent": issue.intent,
            "title": issue.title,
            "status": str(issue.status),
            "agent": issue.agent,
            "branch": issue.branch,
            "depends_on": issue.depends_on,
            "risk": str(issue.risk),
            "created": issue.created.isoformat(),
        }
        if issue.completed:
            fm["completed"] = issue.completed.isoformat()
        if issue.review_type:
            fm["review_type"] = issue.review_type

        body = f"# {issue.title}\n\n"
        if issue.agent_prompt:
            body += f"## Agent prompt\n{issue.agent_prompt}\n\n"
        body += "## Acceptance criteria\n"
        for c in issue.acceptance_criteria:
            body += f"- [ ] {c}\n"
        body += f"\n## Constraints\nFiles allowed: {', '.join(issue.files_allowed)}\n"
        body += f"Files forbidden: {', '.join(issue.files_forbidden)}\n\n"
        body += f"## Agent report\n{issue.agent_report}\n\n"
        body += f"## Reviewer verdict\n{issue.reviewer_verdict}\n\n"
        body += "## Activity log\n"
        for entry in issue.activity_log:
            body += f"- {entry}\n"
        path.write_text(_dump_frontmatter(fm, body))
        return path

    def load_issue(self, issue_id: str) -> Issue:
        path = self._find_file(self.issues_dir, issue_id)
        fm, body = _parse_frontmatter(path.read_text())
        return Issue(
            id=fm["id"],
            intent=fm["intent"],
            title=fm["title"],
            status=IssueStatus(fm.get("status", "created")),
            agent=fm.get("agent", ""),
            branch=fm.get("branch", ""),
            depends_on=fm.get("depends_on", []),
            risk=RiskLevel(fm.get("risk", "low")),
            files_allowed=self._parse_file_list(body, "Files allowed"),
            files_forbidden=self._parse_file_list(body, "Files forbidden"),
            agent_prompt=self._extract_section(body, "Agent prompt"),
            agent_report=self._extract_section(body, "Agent report"),
            reviewer_verdict=self._extract_section(body, "Reviewer verdict"),
            review_type=fm.get("review_type", ""),
        )

    def list_issues(self, intent_id: str | None = None) -> list[Issue]:
        if not self.issues_dir.exists():
            return []
        issues = [
            self.load_issue(self._id_from_path(p))
            for p in sorted(self.issues_dir.glob("ISS-*.md"))
        ]
        if intent_id:
            issues = [i for i in issues if i.intent == intent_id]
        return issues

    def next_issue_id(self) -> str:
        existing = sorted(self.issues_dir.glob("ISS-*.md")) if self.issues_dir.exists() else []
        num = len(existing) + 1
        return f"ISS-{num:03d}"

    # --- Agents ---

    def save_agent(self, agent: Agent) -> Path:
        self._ensure_dirs()
        path = self.agents_dir / f"{agent.name}.md"
        fm = {
            "name": agent.name,
            "role": agent.role,
            "issues_completed": agent.issues_completed,
            "files_familiar": agent.files_familiar,
        }
        body = f"# {agent.name.title()} agent\n\n## History\n"
        for entry in agent.history:
            body += f"- {entry}\n"
        path.write_text(_dump_frontmatter(fm, body))
        return path

    def load_agent(self, name: str) -> Agent:
        path = self.agents_dir / f"{name}.md"
        fm, body = _parse_frontmatter(path.read_text())
        return Agent(
            name=fm["name"],
            role=fm["role"],
            issues_completed=fm.get("issues_completed", []),
            files_familiar=fm.get("files_familiar", []),
        )

    def list_agents(self) -> list[Agent]:
        if not self.agents_dir.exists():
            return []
        return [
            self.load_agent(p.stem)
            for p in sorted(self.agents_dir.glob("*.md"))
        ]

    # --- Sessions ---

    def save_session(self, session_id: str, issue_id: str, output: str) -> Path:
        self._ensure_dirs()
        path = self.sessions_dir / f"{session_id}-{issue_id}.md"
        path.write_text(f"# Session {session_id} — {issue_id}\n\n```\n{output}\n```\n")
        return path

    def next_session_id(self) -> str:
        existing = sorted(self.sessions_dir.glob("SES-*.md")) if self.sessions_dir.exists() else []
        num = len(existing) + 1
        return f"SES-{num:03d}"

    # --- Helpers ---

    def _find_file(self, directory: Path, prefix: str) -> Path:
        matches = list(directory.glob(f"{prefix}-*.md"))
        if not matches:
            raise FileNotFoundError(f"No file found for {prefix} in {directory}")
        return matches[0]

    @staticmethod
    def _id_from_path(path: Path) -> str:
        # "INT-001-some-slug.md" -> "INT-001"
        parts = path.stem.split("-")
        return f"{parts[0]}-{parts[1]}"

    @staticmethod
    def _extract_section(body: str, heading: str) -> str:
        pattern = rf"## {re.escape(heading)}\n(.*?)(?=\n## |\Z)"
        match = re.search(pattern, body, re.DOTALL)
        return match.group(1).strip() if match else ""

    @staticmethod
    def _parse_file_list(body: str, label: str) -> list[str]:
        pattern = rf"{re.escape(label)}: (.*)"
        match = re.search(pattern, body)
        if not match:
            return []
        return [f.strip() for f in match.group(1).split(",") if f.strip()]
