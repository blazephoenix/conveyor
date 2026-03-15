from __future__ import annotations

from conveyor.config import ConveyorConfig
from conveyor.tracking.models import Issue, RiskLevel


def needs_plan_approval(issue: Issue, config: ConveyorConfig) -> bool:
    return issue.risk == RiskLevel.HIGH and config.review_high_risk


def needs_merge_approval(issue: Issue, config: ConveyorConfig) -> bool:
    if issue.risk == RiskLevel.HIGH and config.review_high_risk:
        return True
    if issue.risk == RiskLevel.MEDIUM and config.review_medium_risk:
        return True
    if issue.risk == RiskLevel.LOW and not config.auto_merge_low_risk:
        return True
    return False


def auto_merge_allowed(issue: Issue, config: ConveyorConfig) -> bool:
    return not needs_merge_approval(issue, config)
